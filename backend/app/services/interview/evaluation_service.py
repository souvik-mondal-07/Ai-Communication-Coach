"""
Interview evaluation service.

Two **separate** evaluations per answer, run in parallel through the existing
`AIService`:

* **Technical** — accuracy, completeness, relevance, depth (and practical
  reasoning for scenarios). Ignores how well the answer was written/spoken.
* **Communication** — clarity, grammar, vocabulary, structure, conciseness,
  professionalism, relevance. Ignores technical correctness.

They are separate model calls with separate prompts, so a fluent wrong answer
can't lift the technical score and a correct-but-clumsy one can't lift the
communication score. Headline numbers are *computed here* from the rubric
sub-scores (never taken from the model), so they're consistent and a
candidate can't talk the model into an arbitrary total.

For spoken answers the Step 8 voice-analysis (`analysis_service`) is reused —
deterministic metrics are blended into the communication scores exactly as in
the communication coach. Nothing is reimplemented here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.services.ai.ai_service import AIService, ai_service
from app.services.communication.analysis_service import (
    aggregate_voice_analyses,
    blend_scores,
    compose_voice_summary,
    format_metrics_for_prompt,
)
from app.services.interview import prompts
from app.services.interview.structured_ai import (
    Score,
    StructuredOutputError,
    generate_validated,
)
from app.services.interview.topics import TOPICS, topic_label
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Below this average, a topic is reported as a weak area for this interview.
WEAK_TOPIC_THRESHOLD = 60
STRONG_TOPIC_THRESHOLD = 75

# (technical weight, communication weight) for the overall score.
OVERALL_WEIGHTS: dict[str, tuple[float, float]] = {
    "hr": (0.40, 0.60),
    "technical": (0.65, 0.35),
    "cybersecurity": (0.65, 0.35),
    "scenario_based": (0.65, 0.35),
    "mixed": (0.55, 0.45),
}

_QUESTION_KIND = {
    "behavioral": "HR / behavioural",
    "technical": "technical knowledge",
    "scenario": "scenario-based (practical reasoning)",
}


class InterviewEvaluationError(Exception):
    """Evaluating an answer failed (provider error or unusable output)."""


# --- Validated AI output shapes (internal) --------------------------------------


class _TechnicalOut(BaseModel):
    accuracy: Score
    completeness: Score
    relevance: Score
    depth: Score
    practical_reasoning: Score | None = None
    feedback: str = Field(min_length=1, max_length=1500)
    improved_answer: str = Field(default="", max_length=2500)
    follow_up_suggested: bool = False
    follow_up_focus: str = Field(default="", max_length=400)


class _CommunicationOut(BaseModel):
    clarity: Score
    grammar: Score
    vocabulary: Score
    structure: Score
    conciseness: Score
    professionalism: Score
    relevance: Score
    feedback: str = Field(min_length=1, max_length=1500)


class _FinalOut(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    technical_weaknesses: list[str] = Field(default_factory=list)
    communication_weaknesses: list[str] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=2500)


@dataclass
class AnswerEvaluation:
    technical: dict
    communication: dict
    improved_answer: str
    internal: dict = field(default_factory=dict)  # never sent to clients


# --- Deterministic scoring -------------------------------------------------------


def compute_technical_score(sub: dict, *, scenario: bool) -> int:
    """Weighted rubric total. Scenario questions also weigh practical reasoning."""
    if scenario and sub.get("practical_reasoning") is not None:
        weights = {
            "accuracy": 0.30,
            "completeness": 0.20,
            "relevance": 0.10,
            "depth": 0.15,
            "practical_reasoning": 0.25,
        }
    else:
        weights = {"accuracy": 0.40, "completeness": 0.25, "relevance": 0.15, "depth": 0.20}
    return round(sum(sub[k] * w for k, w in weights.items()))


def compute_communication_score(dims: dict) -> int:
    keys = ("clarity", "grammar", "vocabulary", "structure", "conciseness", "professionalism", "relevance")
    return round(sum(dims[k] for k in keys) / len(keys))


def _mean(values: list[float]) -> int | None:
    return round(sum(values) / len(values)) if values else None


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


# --- Session digests -------------------------------------------------------------


def answered_records(question: dict) -> list[dict]:
    """All answered prompts of one question: the main answer, then its follow-ups."""
    records = [question] + list(question.get("follow_up_questions", []))
    return [r for r in records if r.get("answer") and r.get("technical_evaluation")]


def question_scores(question: dict) -> tuple[int | None, int | None]:
    """A question's technical/communication score = mean over its answers (main + follow-ups)."""
    records = answered_records(question)
    return (
        _mean([r["technical_evaluation"]["technical_score"] for r in records]),
        _mean([r["communication_evaluation"]["communication_score"] for r in records]),
    )


def _voice_analyses(questions: list[dict]) -> list[dict]:
    out: list[dict] = []
    for q in questions:
        for r in [q] + list(q.get("follow_up_questions", [])):
            if r.get("answer_input_type") == "voice" and r.get("voice_analysis"):
                out.append(r["voice_analysis"])
    return out


def compute_final_scores(session: dict) -> dict:
    """Deterministic overall/technical/communication scores and per-topic averages."""
    per_question = []
    for q in session["questions"]:
        tech, comm = question_scores(q)
        if tech is not None and comm is not None:
            per_question.append({"topic": q["topic"], "technical": tech, "communication": comm})

    technical = _mean([p["technical"] for p in per_question]) or 0
    communication = _mean([p["communication"] for p in per_question]) or 0
    w_tech, w_comm = OVERALL_WEIGHTS.get(session["interview_type"], (0.6, 0.4))
    overall = round(technical * w_tech + communication * w_comm)

    by_topic: dict[str, list[int]] = {}
    for p in per_question:
        by_topic.setdefault(p["topic"], []).append(p["technical"])
    topic_scores = [
        {
            "topic": topic,
            "label": topic_label(topic),
            "average_score": _mean(scores),
            "questions": len(scores),
        }
        for topic, scores in by_topic.items()
    ]
    topic_scores.sort(key=lambda t: t["average_score"])
    return {
        "overall_score": overall,
        "technical_score": technical,
        "communication_score": communication,
        "topic_scores": topic_scores,
        "answered_questions": len(per_question),
    }


def build_digest(session: dict) -> str:
    lines = []
    for q in session["questions"]:
        tech, comm = question_scores(q)
        if tech is None:
            continue
        main = q["technical_evaluation"]
        lines.append(
            f"Q{q['question_number']} [{topic_label(q['topic'])}] technical {tech}, communication {comm}\n"
            f"  Question: {_clip(q['question'], 200)}\n"
            f"  Answer excerpt: {prompts.wrap_untrusted(_clip(q['answer'], 220), limit=240)}\n"
            f"  Technical note: {_clip(main['feedback'], 200)}"
        )
        for fu in q.get("follow_up_questions", []):
            if fu.get("answer") and fu.get("technical_evaluation"):
                lines.append(
                    f"  Follow-up: {_clip(fu['question'], 160)} -> technical "
                    f"{fu['technical_evaluation']['technical_score']}"
                )
    return "\n".join(lines)


def match_recommendations(
    recommended_topics: list[str], weak_topics: list[dict], learning_topics: list[dict]
) -> list[dict]:
    """
    Ground recommendations in real Step 5 learning topics where possible:
    AI-suggested subjects that name an existing topic get its slug, and weak
    interview areas with no such match fall back to a topic from the matching
    learning category. Entries without a slug are still shown (as plain text).
    """

    def norm(text: str) -> str:
        return " ".join("".join(c.lower() if c.isalnum() else " " for c in text).split())

    by_title = [(norm(t["title"]), t) for t in learning_topics]
    items: list[dict] = []
    seen: set[str] = set()

    def add(title: str, slug: str | None) -> None:
        key = slug or norm(title)
        if key in seen or len(items) >= 5:
            return
        seen.add(key)
        items.append({"title": title, "slug": slug})

    for name in recommended_topics:
        n = norm(name)
        match = next((t for title_norm, t in by_title if title_norm and (title_norm in n or n in title_norm)), None)
        add(match["title"] if match else name, match["slug"] if match else None)

    for weak in weak_topics:
        topic = TOPICS.get(weak["topic"])
        if topic is None or not topic.learning_categories:
            continue
        candidates = [t for t in learning_topics if t.get("category") in topic.learning_categories]
        if candidates and not any(i["slug"] == candidates[0]["slug"] for i in items):
            # Only add when the AI's list hasn't already covered this area.
            covered = any(
                i["slug"] and any(c["slug"] == i["slug"] for c in candidates) for i in items
            )
            if not covered:
                add(candidates[0]["title"], candidates[0]["slug"])
    return items


# --- Service ---------------------------------------------------------------------


class InterviewEvaluationService:
    """Evaluates interview answers and whole interviews via the existing AIService."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    async def evaluate_answer(
        self,
        *,
        difficulty: str,
        topic: str,
        question: str,
        answer: str,
        input_type: str,
        voice_analysis: dict | None,
    ) -> AnswerEvaluation:
        """Evaluate one answer (technical and communication in parallel)."""
        kind = TOPICS[topic].kind if topic in TOPICS else "technical"
        spoken = input_type == "voice"

        metrics = ""
        if spoken and voice_analysis:
            aggregate = aggregate_voice_analyses([voice_analysis])
            metrics = format_metrics_for_prompt(aggregate) if aggregate else ""

        try:
            tech_out, comm_out = await asyncio.gather(
                generate_validated(
                    self._ai_service,
                    user_prompt=prompts.build_technical_evaluation_prompt(
                        difficulty=difficulty,
                        topic=topic,
                        kind=_QUESTION_KIND.get(kind, kind),
                        question=question,
                        answer=answer,
                    ),
                    system_prompt=prompts.TECHNICAL_EVALUATION_PROMPT,
                    model=_TechnicalOut,
                ),
                generate_validated(
                    self._ai_service,
                    user_prompt=prompts.build_communication_evaluation_prompt(
                        difficulty=difficulty,
                        question=question,
                        answer=answer,
                        spoken=spoken,
                        metrics=metrics,
                    ),
                    system_prompt=prompts.COMMUNICATION_EVALUATION_PROMPT,
                    model=_CommunicationOut,
                ),
            )
        except StructuredOutputError as exc:
            raise InterviewEvaluationError("AI returned an unusable evaluation.") from exc
        # AIServiceError from either call propagates to the caller unchanged.

        scenario = kind == "scenario"
        tech_sub = tech_out.model_dump()
        if not scenario:
            tech_sub["practical_reasoning"] = None  # only meaningful for scenarios
        technical = {
            "technical_score": compute_technical_score(tech_sub, scenario=scenario),
            "accuracy": tech_sub["accuracy"],
            "completeness": tech_sub["completeness"],
            "relevance": tech_sub["relevance"],
            "depth": tech_sub["depth"],
            "practical_reasoning": tech_sub["practical_reasoning"],
            "feedback": tech_out.feedback.strip(),
        }

        comm_dims = comm_out.model_dump()
        if spoken and voice_analysis:
            # Same blending as the Step 8 speaking analysis: measured metrics
            # (filler words, repetition, sentence length) temper the AI's view.
            for ai_key, det_key in (
                ("clarity", "clarity_score"),
                ("vocabulary", "vocabulary_score"),
                ("conciseness", "conciseness_score"),
            ):
                comm_dims[ai_key] = blend_scores(voice_analysis.get(det_key), comm_dims[ai_key])
        communication = {
            "communication_score": compute_communication_score(comm_dims),
            **{k: comm_dims[k] for k in (
                "clarity", "grammar", "vocabulary", "structure",
                "conciseness", "professionalism", "relevance",
            )},
            "feedback": comm_out.feedback.strip(),
        }

        return AnswerEvaluation(
            technical=technical,
            communication=communication,
            improved_answer=tech_out.improved_answer.strip(),
            internal={
                "follow_up_suggested": tech_out.follow_up_suggested,
                "follow_up_focus": tech_out.follow_up_focus.strip(),
            },
        )

    async def build_final_evaluation(self, session: dict, *, learning_topics: list[dict]) -> dict:
        """
        Final evaluation for an interview with at least one answered question.

        Scores, topic averages and voice metrics are deterministic. Gemini
        writes the narrative (strengths, weaknesses, recommendations,
        summary); if that fails, the interview still completes with a
        deterministic narrative and `ai_narrative_available: false`.
        """
        scores = compute_final_scores(session)
        weak = [
            t for t in scores["topic_scores"]
            if t["average_score"] < WEAK_TOPIC_THRESHOLD and t["topic"] != "hr"
        ]

        narrative: _FinalOut | None = None
        try:
            narrative = await generate_validated(
                self._ai_service,
                user_prompt=prompts.build_final_evaluation_prompt(
                    interview_type=session["interview_type"],
                    difficulty=session["difficulty"],
                    scores=scores,
                    digest=build_digest(session),
                    weak_topics=[t["label"] for t in weak],
                ),
                system_prompt=prompts.FINAL_EVALUATION_PROMPT,
                model=_FinalOut,
            )
        except Exception as exc:  # noqa: BLE001 - completion must not fail on the narrative
            logger.warning("Final interview narrative unavailable: %s", type(exc).__name__)

        def items(values: list[str], limit: int = 6) -> list[str]:
            return [v.strip()[:400] for v in values if isinstance(v, str) and v.strip()][:limit]

        if narrative is not None:
            strengths = items(narrative.strengths)
            weaknesses = items(narrative.weaknesses)
            technical_weaknesses = items(narrative.technical_weaknesses)
            communication_weaknesses = items(narrative.communication_weaknesses)
            recommended_topics = items(narrative.recommended_topics, 5)
            recommendations = items(narrative.recommendations)
            summary = narrative.summary.strip() or "Interview completed."
        else:
            strong = [t["label"] for t in scores["topic_scores"] if t["average_score"] >= STRONG_TOPIC_THRESHOLD]
            strengths = [f"Solid performance on {label}." for label in strong[:3]]
            technical_weaknesses = [
                f"{t['label']} scored {t['average_score']}/100 in this interview." for t in weak[:4]
            ]
            weaknesses = list(technical_weaknesses)
            communication_weaknesses = (
                ["Communication scored below 60/100 — review the feedback on each answer."]
                if scores["communication_score"] < WEAK_TOPIC_THRESHOLD
                else []
            )
            recommended_topics = [t["label"] for t in weak[:3]]
            recommendations = ["Review the per-question feedback and improved answers."]
            summary = (
                f"Interview completed with an overall score of {scores['overall_score']}/100 "
                f"(technical {scores['technical_score']}, communication {scores['communication_score']}). "
                "A written AI summary wasn't available; the scores and per-question feedback are complete."
            )

        final = {
            **scores,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "technical_weaknesses": technical_weaknesses,
            "communication_weaknesses": communication_weaknesses,
            "recommended_topics": recommended_topics,
            "recommendations": recommendations,
            "recommended_practice": match_recommendations(recommended_topics, weak, learning_topics),
            "weak_topics": weak,
            "summary": summary,
            "ai_narrative_available": narrative is not None,
        }

        analyses = _voice_analyses(session["questions"])
        aggregate = aggregate_voice_analyses(analyses) if analyses else None
        if aggregate is not None:
            # Deterministic Step 8 metrics only — no extra AI call.
            final["voice_summary"] = compose_voice_summary(aggregate, None)
        return final


interview_evaluation_service = InterviewEvaluationService()
