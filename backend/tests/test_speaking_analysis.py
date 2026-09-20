"""
Speaking-analysis unit tests (pure functions — no database, no network).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from app.services.ai.ai_service import AIProviderError, AIResponse
from app.services.communication.analysis_service import (
    SpeakingAnalysisService,
    aggregate_voice_analyses,
    analyze_transcript,
    build_metric_insights,
    calculate_pause_metrics,
    calculate_speaking_rate,
    compose_voice_summary,
    speaking_rate_label,
)
from app.utils.text_analysis import (
    count_sentences,
    count_words,
    detect_filler_words,
    find_overused_words,
    find_repeated_words,
)


class TestCounts:
    def test_word_count_handles_contractions_and_punctuation(self):
        assert count_words("Don't stop, well-known people!") == 4

    def test_sentence_count(self):
        assert count_sentences("Hello there. How are you? I am fine") == 3

    def test_unpunctuated_text_is_one_sentence(self):
        assert count_sentences("hello there my friend") == 1

    def test_empty_transcript(self):
        assert count_words("") == 0
        assert count_sentences("   ") == 0
        result = analyze_transcript("")
        assert result["word_count"] == 0
        assert result["sentence_count"] == 0
        assert result["speaking_rate_wpm"] is None
        assert result["clarity_score"] is None
        assert result["total_filler_words"] == 0


class TestFillerWords:
    def test_hesitations_and_discourse_words_are_counted(self):
        fillers, total = detect_filler_words("Um, I think, uh, basically it works. Actually, um, yes.")
        assert fillers == {"um": 2, "actually": 1, "basically": 1, "uh": 1}
        assert total == 5

    def test_like_as_verb_or_comparison_is_not_a_filler(self):
        for text in (
            "I like cybersecurity and I would like to learn more.",
            "It was like a game.",
            "Something like this works.",
            "He looks like his father.",
        ):
            assert detect_filler_words(text)[1] == 0, text

    def test_like_as_filler_is_counted(self):
        assert detect_filler_words("I was, like, really nervous.")[1] == 1
        assert detect_filler_words("It was like really hard.")[1] == 1

    def test_so_only_counts_as_filler_when_used_as_one(self):
        assert detect_filler_words("So, yeah, I did that.")[1] == 1
        assert detect_filler_words("I think so, but I'm not sure.")[1] == 0
        assert detect_filler_words("I was tired so I left.")[1] == 0

    def test_you_know_and_i_mean_are_contextual(self):
        assert detect_filler_words("It was hard, you know.")[1] == 1
        assert detect_filler_words("Do you know how to do it?")[1] == 0
        assert detect_filler_words("As you know, it is late.")[1] == 0
        assert detect_filler_words("I mean, it was fine.")[1] == 1
        assert detect_filler_words("What I mean is that it works.")[1] == 0

    def test_filler_list_is_configurable(self):
        fillers, total = detect_filler_words("Right, so um that is right.", ["right"])
        assert fillers == {"right": 2}
        assert total == 2  # "um" isn't in the custom list

    def test_output_shape_matches_spec(self):
        fillers, total = detect_filler_words("Um um uh basically basically")
        assert fillers == {"basically": 2, "um": 2, "uh": 1}
        assert total == 5


class TestRepetition:
    def test_immediate_repeats(self):
        repeated, total = find_repeated_words("I I think the the plan is, is good.")
        assert repeated == {"i": 1, "is": 1, "the": 1}
        assert total == 3

    def test_legitimate_or_cross_sentence_repeats_ignored(self):
        assert find_repeated_words("That was fun. Fun is good.")[1] == 0
        assert find_repeated_words("He had had enough.")[1] == 0

    def test_overused_content_words_need_enough_text(self):
        assert find_overused_words("internship internship internship") == {}
        filler = "we met on monday then went home and rested while friends called later to chat about weather before dinner arrived at seven"
        text = "internship " * 3 + filler
        assert find_overused_words(text) == {"internship": 3}


class TestSpeakingRate:
    def test_wpm_formula(self):
        assert calculate_speaking_rate(120, 60.0) == 120
        assert calculate_speaking_rate(52, 23.6) == 132

    def test_wpm_unavailable_without_reliable_duration(self):
        assert calculate_speaking_rate(50, None) is None
        assert calculate_speaking_rate(50, 0) is None
        assert calculate_speaking_rate(3, 1.0) is None  # too short to trust
        assert calculate_speaking_rate(0, 30.0) is None

    def test_interpretation_bands(self):
        assert speaking_rate_label(80) == "slow"
        assert speaking_rate_label(100) == "moderate"
        assert speaking_rate_label(160) == "moderate"
        assert speaking_rate_label(161) == "fast"
        assert speaking_rate_label(None) is None


class TestPauses:
    def test_pauses_from_timestamps(self):
        # gaps: 0.1 (ignored), 2.5 (long), 0.6 (pause)
        intervals = [(0.0, 1.0), (1.1, 2.0), (4.5, 5.0), (5.6, 6.0)]
        metrics = calculate_pause_metrics(intervals)
        assert metrics == {
            "pause_count": 2,
            "long_pauses": 1,
            "average_pause_seconds": 1.55,
            "longest_pause_seconds": 2.5,
            "total_pause_seconds": 3.1,
            "granularity": "word",
        }

    def test_fluent_speech_measured_but_no_pauses(self):
        metrics = calculate_pause_metrics([(0, 1), (1.05, 2), (2.1, 3)])
        assert metrics["pause_count"] == 0
        assert metrics["average_pause_seconds"] is None
        assert metrics["longest_pause_seconds"] is None

    def test_missing_timestamps_are_none_not_zero(self):
        assert calculate_pause_metrics(None) is None
        assert calculate_pause_metrics([]) is None
        assert calculate_pause_metrics([(0.0, 1.0)]) is None  # one item: no gaps to measure

    def test_invalid_intervals_are_ignored(self):
        assert calculate_pause_metrics([(0, 1), (float("nan"), 2), (5, 4)]) is None

    def test_unsorted_and_overlapping_intervals(self):
        metrics = calculate_pause_metrics([(3.0, 4.0), (0.0, 2.5), (1.0, 3.2)])
        assert metrics["pause_count"] == 0


class TestAnalyzeTranscript:
    TRANSCRIPT = (
        "Um, I would like to know more about cybersecurity internships. "
        "I was, like, really interested, basically. I I studied networking."
    )

    def test_full_analysis(self):
        pauses = calculate_pause_metrics([(0, 1), (1.1, 2), (4.5, 5), (5.1, 6)])
        result = analyze_transcript(self.TRANSCRIPT, duration_seconds=12.0, pause_metrics=pauses)
        assert result["word_count"] == 20
        assert result["sentence_count"] == 3
        assert result["speaking_rate_wpm"] == 100
        assert result["speaking_rate_label"] == "moderate"
        assert result["filler_words"] == {"basically": 1, "like": 1, "um": 1}
        assert result["total_filler_words"] == 3
        assert result["repeated_words"] == {"i": 1}
        assert result["pause_count"] == 1
        assert result["long_pauses"] == 1
        assert result["longest_pause_seconds"] == 2.5
        for key in ("clarity_score", "vocabulary_score", "conciseness_score"):
            assert 0 <= result[key] <= 100
        assert "grammar_score" not in result  # not measurable without the AI

    def test_audio_fields_are_none_without_metadata(self):
        result = analyze_transcript(self.TRANSCRIPT)
        assert result["duration_seconds"] is None
        assert result["speaking_rate_wpm"] is None
        assert result["pause_count"] is None
        assert result["longest_pause_seconds"] is None
        assert result["word_count"] == 20  # text metrics still work

    def test_very_short_answers_are_not_scored(self):
        result = analyze_transcript("Yes, I agree.", duration_seconds=3.0)
        assert result["clarity_score"] is None
        assert result["conciseness_score"] is None

    def test_more_fillers_means_lower_clarity(self):
        clean = analyze_transcript("I studied networking and Linux basics before starting practical labs at home.")
        messy = analyze_transcript("Um, I basically studied, uh, networking and, um, actually Linux basically before labs.")
        assert messy["clarity_score"] < clean["clarity_score"]

    def test_custom_filler_list(self):
        result = analyze_transcript("Right so I think right this works well for me today.", filler_words=["right"])
        assert result["filler_words"] == {"right": 2}


class TestAggregation:
    def _msg(self, text, duration, pauses=None):
        return analyze_transcript(text, duration_seconds=duration, pause_metrics=pauses)

    def test_weighted_rate_and_merged_fillers(self):
        a = self._msg("Um " + "word " * 29, 30.0)  # 30 words / 30s = 60 wpm
        b = self._msg("Basically " + "word " * 59, 30.0)  # 60 words / 30s = 120 wpm
        agg = aggregate_voice_analyses([a, b])
        assert agg["voice_message_count"] == 2
        assert agg["total_words_spoken"] == 90
        assert agg["average_speaking_rate_wpm"] == 90  # 90 words / 1 minute
        assert agg["total_filler_words"] == 2
        assert agg["filler_words"] == {"basically": 1, "um": 1}

    def test_pause_aggregation_and_missing_pause_data(self):
        p1 = calculate_pause_metrics([(0, 1), (3.5, 4)])  # one 2.5s pause
        p2 = calculate_pause_metrics([(0, 1), (1.7, 2)])  # one 0.7s pause
        agg = aggregate_voice_analyses([self._msg("word " * 20, 10, p1), self._msg("word " * 20, 10, p2)])
        assert agg["pause_count"] == 2
        assert agg["long_pauses"] == 1
        assert agg["average_pause_seconds"] == 1.6
        assert agg["longest_pause_seconds"] == 2.5

        no_pauses = aggregate_voice_analyses([self._msg("word " * 20, 10, None)])
        assert no_pauses["pause_count"] is None
        assert no_pauses["longest_pause_seconds"] is None

    def test_empty(self):
        assert aggregate_voice_analyses([]) is None

    def test_metric_insights_are_factual(self):
        agg = aggregate_voice_analyses(
            [self._msg("Um, basically, um, I studied networking " + "and practiced labs " * 6, 60.0)]
        )
        strengths, improvements = build_metric_insights(agg)
        assert any("Reduce filler words" in i and '"um"' in i for i in improvements)
        assert any("slower side" in i for i in improvements)
        # no psychological claims
        joined = " ".join(strengths + improvements).lower()
        for word in ("anxiety", "nervous", "diagnos", "confidence"):
            assert word not in joined


class _FakeAI:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        self.calls.append((system_prompt, user_message))
        if self.error:
            raise self.error
        return AIResponse(text=self.response, model="fake")


def _voice_session():
    now = datetime.now(timezone.utc)
    text = "Um, I studied networking and Linux basics before starting the practical labs at home."
    return {
        "scenario_title": "Ask a senior about careers",
        "objective": "Practice asking questions",
        "messages": [
            {"role": "assistant", "content": "Hi, how can I help?", "timestamp": now},
            {
                "role": "user",
                "content": text,
                "input_type": "voice",
                "timestamp": now,
                "voice_analysis": analyze_transcript(text, duration_seconds=8.0),
            },
        ],
    }


GOOD_AI = json.dumps(
    {
        "clarity_score": 90,
        "grammar_score": 80,
        "vocabulary_score": 70,
        "conciseness_score": 85,
        "strengths": ["Clear structure."],
        "improvements": ["Add a concrete example."],
        "summary": "Clear spoken answers.",
    }
)


class TestSpeakingAnalysisService:
    def test_blends_deterministic_and_ai_scores(self):
        service = SpeakingAnalysisService(_FakeAI(response=GOOD_AI))
        session = _voice_session()
        summary = asyncio.run(service.build_voice_summary(session))
        det = aggregate_voice_analyses([session["messages"][1]["voice_analysis"]])
        assert summary["ai_feedback_available"] is True
        assert summary["grammar_score"] == 80  # AI-only
        expected = round(0.6 * 90 + 0.4 * det["clarity_score"])
        assert summary["clarity_score"] == expected
        assert "Clear structure." in summary["strengths"]
        assert summary["summary"] == "Clear spoken answers."
        assert summary["total_words_spoken"] == det["total_words_spoken"]

    def test_prompt_marks_spoken_turns_and_includes_metrics(self):
        fake = _FakeAI(response=GOOD_AI)
        asyncio.run(SpeakingAnalysisService(fake).build_voice_summary(_voice_session()))
        system_prompt, user_prompt = fake.calls[0]
        assert "spoken-communication coach" in system_prompt
        assert "anxiety" in system_prompt  # instructs the model NOT to comment on it
        assert "Learner (spoken):" in user_prompt
        assert "Average speaking rate" in user_prompt

    def test_ai_failure_degrades_to_metrics_only(self):
        service = SpeakingAnalysisService(_FakeAI(error=AIProviderError("boom")))
        summary = asyncio.run(service.build_voice_summary(_voice_session()))
        assert summary["ai_feedback_available"] is False
        assert summary["grammar_score"] is None
        assert summary["total_words_spoken"] > 0
        assert summary["clarity_score"] is not None  # deterministic baseline

    def test_invalid_ai_json_degrades_to_metrics_only(self):
        for bad in ("not json", json.dumps({"clarity_score": 500}), "[1,2]"):
            service = SpeakingAnalysisService(_FakeAI(response=bad))
            summary = asyncio.run(service.build_voice_summary(_voice_session()))
            assert summary["ai_feedback_available"] is False

    def test_no_voice_messages_returns_none_and_makes_no_ai_call(self):
        fake = _FakeAI(response=GOOD_AI)
        session = {"messages": [{"role": "user", "content": "typed", "input_type": "text"}]}
        assert asyncio.run(SpeakingAnalysisService(fake).build_voice_summary(session)) is None
        assert fake.calls == []

    def test_compose_without_ai(self):
        agg = aggregate_voice_analyses([analyze_transcript("word " * 30, duration_seconds=20)])
        summary = compose_voice_summary(agg, None)
        assert summary["ai_feedback_available"] is False
        assert summary["summary"] is None
