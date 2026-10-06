"""
Tests for Step 18 -- Advanced Interview & Communication Analytics.

Same conventions as the other suites: mongomock `fake_db` + `client`, real JWT auth,
and sessions inserted directly in the shape earlier steps store them. No Gemini call
is ever made (a fake AI service is injected where the optional summary is tested).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.core.dependencies import get_analytics_service
from app.db.collections import Collections
from app.main import app
from app.services.ai.ai_service import AIProviderError
from app.services.analytics import config
from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.answer_analytics import classify_length, structure_markers
from app.services.analytics.common import DateRange, InvalidRangeError, change_label, compare, resolve_range
from app.services.analytics.facts import load_facts
from app.services.analytics.readiness import readiness_report
from app.services.analytics.trend_analytics import bucket_key, trend_direction
from tests.test_communication import _register_and_login

NOW = datetime.now(timezone.utc)
SECRET = "UNIQUE-TRANSCRIPT-SENTINEL-8841"
FILLER_TEXT = "um " + "word " * 40


def _auth(client, email):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _uid(fake_db, email) -> ObjectId:
    return fake_db[Collections.USERS].find_one({"email": email})["_id"]


def voice(wpm=130, filler_rate=1.0, words=60, duration=28.0, pauses=4, long_pauses=0, repeats=0):
    return {"word_count": words, "duration_seconds": duration, "speaking_rate_wpm": wpm,
            "total_filler_words": round(words * filler_rate / 100), "filler_rate_per_100_words": filler_rate,
            "total_repeated_words": repeats, "pause_count": pauses, "long_pauses": long_pauses,
            "average_pause_seconds": 0.8, "average_sentence_length": 12.0}


def answer(tech=80, comm=75, *, text="word " * 60, structure=70, vox=None, depth=70, completeness=70, follow=None, topic="linux"):
    rec = {
        "question_number": 1, "question": "Q?", "topic": topic, "focus": "f", "asked_at": NOW,
        "answer": text, "answer_input_type": "voice" if vox else "text", "answered_at": NOW,
        "voice_analysis": vox,
        "technical_evaluation": {"technical_score": tech, "accuracy": tech, "completeness": completeness,
                                 "relevance": tech, "depth": depth, "practical_reasoning": None, "feedback": "x"},
        "communication_evaluation": {"communication_score": comm, "clarity": comm, "grammar": comm,
                                     "vocabulary": comm, "structure": structure, "conciseness": comm,
                                     "professionalism": comm, "relevance": comm, "feedback": "x"},
        "follow_up_questions": [],
    }
    for ftech in follow or []:
        fu = answer(ftech, comm, text="word " * 40)
        fu.pop("follow_up_questions"); fu["question"] = "Why?"; fu["asked_at"] = NOW
        rec["follow_up_questions"].append(fu)
    return rec


def interview(fake_db, uid, *, days_ago=1, itype="technical", tech=80, comm=75, overall=None, questions=None,
              topic_scores=None, difficulty="intermediate", count=5):
    questions = questions if questions is not None else [answer(tech, comm)]
    at = NOW - timedelta(days=days_ago)
    fake_db[Collections.INTERVIEW_SESSIONS].insert_one({
        "user_id": uid, "interview_type": itype, "difficulty": difficulty, "mode": "text", "question_count": count,
        "status": "completed", "started_at": at, "completed_at": at, "questions": questions,
        "final_evaluation": {"overall_score": overall if overall is not None else round((tech + comm) / 2),
                             "technical_score": tech, "communication_score": comm,
                             "answered_questions": len(questions), "topic_scores": topic_scores or []},
    })


def pressure(fake_db, uid, *, days_ago=1, tech=70, comm=55, handling=60, questions=None):
    questions = questions if questions is not None else [answer(tech, comm)]
    at = NOW - timedelta(days=days_ago)
    fake_db[Collections.PRESSURE_SESSIONS].insert_one({
        "user_id": uid, "interview_type": "technical", "difficulty": "intermediate", "pressure_level": 3,
        "mode": "interview", "question_count": 5, "status": "completed", "started_at": at, "completed_at": at,
        "questions": questions,
        "final_evaluation": {"overall_score": round((tech + comm) / 2), "technical_score": tech,
                             "communication_score": comm, "pressure_handling_score": handling,
                             "response_control_score": 60, "answered_questions": len(questions), "topic_scores": []},
    })


def comm_session(fake_db, uid, *, days_ago=1, overall=70, confidence=70, messages=None):
    at = NOW - timedelta(days=days_ago)
    fake_db[Collections.COMMUNICATION_SESSIONS].insert_one({
        "user_id": uid, "scenario_title": "S", "category": "managers", "mode": "professional",
        "difficulty": "beginner", "status": "completed", "started_at": at, "completed_at": at,
        "messages": messages or [],
        "evaluation": {"overall_score": overall, "clarity_score": overall, "grammar_score": overall,
                       "vocabulary_score": overall, "professionalism_score": overall,
                       "confidence_score": confidence, "relevance_score": overall, "conversation_flow_score": overall},
    })


def practice(fake_db, uid, category, score, *, questions=5, days_ago=2):
    at = NOW - timedelta(days=days_ago)
    fake_db[Collections.PRACTICE_SESSIONS].insert_one({
        "user_id": uid, "category": category, "topic_slug": f"{category}-t", "difficulty": "beginner",
        "status": "completed", "score": score, "questions_answered": questions,
        "correct_answers": round(questions * score / 100), "started_at": at, "completed_at": at,
    })


def get(client, path, headers, **params):
    return client.get(f"/api/v1/analytics/{path}", headers=headers, params=params)


# ------------------------------------------------------------------ auth & ownership
def test_all_endpoints_require_authentication(client):
    for name in ("overview", "interviews", "communication", "speaking", "pressure", "domains", "trends", "insights", "readiness"):
        assert client.get(f"/api/v1/analytics/{name}").status_code == 401


def test_user_cannot_see_another_users_analytics(client, fake_db):
    a, b = _auth(client, "a@example.com"), _auth(client, "b@example.com")
    uid_a = _uid(fake_db, "a@example.com")
    for i in range(4):
        interview(fake_db, uid_a, days_ago=i + 1)
    assert get(client, "overview", a).json()["data"]["counts"]["interviews"] == 4
    other = get(client, "overview", b).json()["data"]
    assert other["counts"]["interviews"] == 0
    assert other["data"]["status"] == "none"


def test_user_id_query_parameter_is_ignored(client, fake_db):
    _auth(client, "a@example.com"); b = _auth(client, "b@example.com")
    interview(fake_db, _uid(fake_db, "a@example.com"))
    r = get(client, "overview", b, user_id=str(_uid(fake_db, "a@example.com")))
    assert r.json()["data"]["counts"]["interviews"] == 0


# ------------------------------------------------------------------ empty / early data
def test_empty_state_has_no_fabricated_numbers(client):
    h = _auth(client, "empty@example.com")
    data = get(client, "overview", h).json()["data"]
    assert data["data"]["status"] == "none"
    assert data["data"]["message"] == "Complete your first interview to unlock analytics."
    assert data["scores"] == {"technical": None, "communication": None, "confidence": None, "overall": None}
    assert data["readiness"]["available"] is False and data["readiness"]["score"] is None
    for name in ("interviews", "communication", "speaking", "pressure", "domains", "trends", "insights", "readiness"):
        assert get(client, name, h).status_code == 200


def test_early_data_is_flagged(client, fake_db):
    h = _auth(client, "early@example.com")
    interview(fake_db, _uid(fake_db, "early@example.com"))
    d = get(client, "overview", h).json()["data"]["data"]
    assert d["status"] == "early" and "More practice is needed" in d["message"]


# ------------------------------------------------------------------ date ranges / validation
def test_date_range_filters_sessions(client, fake_db):
    h = _auth(client, "range@example.com"); uid = _uid(fake_db, "range@example.com")
    interview(fake_db, uid, days_ago=3)
    interview(fake_db, uid, days_ago=20)
    interview(fake_db, uid, days_ago=60)
    counts = {r: get(client, "overview", h, range=r).json()["data"]["counts"]["interviews"] for r in ("7d", "30d", "90d", "all")}
    assert counts == {"7d": 1, "30d": 2, "90d": 3, "all": 3}


def test_custom_date_range(client, fake_db):
    h = _auth(client, "custom@example.com"); uid = _uid(fake_db, "custom@example.com")
    interview(fake_db, uid, days_ago=3)
    interview(fake_db, uid, days_ago=40)
    d = (NOW - timedelta(days=45)).date().isoformat(), (NOW - timedelta(days=30)).date().isoformat()
    r = get(client, "overview", h, start_date=d[0], end_date=d[1]).json()["data"]
    assert r["counts"]["interviews"] == 1 and r["range"] == "custom"


@pytest.mark.parametrize("params", [
    {"range": "bogus"}, {"range": "1y"},
    {"start_date": "2026-02-01", "end_date": "2026-01-01"},
    {"start_date": "not-a-date"},
    {"end_date": (date.today() + timedelta(days=30)).isoformat()},
    {"start_date": "2001-01-01", "end_date": "2026-01-01"},
])
def test_invalid_query_parameters_are_rejected(client, params):
    h = _auth(client, "inv@example.com")
    r = get(client, "overview", h, **params)
    assert r.status_code == 422 and r.json()["success"] is False


def test_resolve_range_unit():
    assert resolve_range("all").start is None
    with pytest.raises(InvalidRangeError):
        resolve_range("nope")


# ------------------------------------------------------------------ comparison & labels
def test_change_labels_do_not_exaggerate():
    assert change_label(13) == "Significant improvement"
    assert change_label(5) == "Improving"
    assert change_label(2) == "Stable" and change_label(-2) == "Stable"
    assert change_label(-5) == "Slight decline"
    assert change_label(-12) == "Needs attention"
    assert change_label(-12, higher_is_better=False) == "Significant improvement"  # e.g. filler rate fell
    assert change_label(None) is None


def test_compare_needs_samples_on_both_sides():
    assert compare([60], [80, 82])["available"] is False
    c = compare([66, 70], [80, 82])
    assert (c["previous"], c["current"], c["change"], c["label"]) == (68, 81, 13, "Significant improvement")


def test_overview_previous_vs_current(client, fake_db):
    h = _auth(client, "cmp@example.com"); uid = _uid(fake_db, "cmp@example.com")
    for d in (40, 35):   # previous 30d window (30-60 days ago)
        interview(fake_db, uid, days_ago=d, tech=66, comm=60)
    for d in (5, 3):
        interview(fake_db, uid, days_ago=d, tech=80, comm=74)
    cmp_ = get(client, "overview", h, range="30d").json()["data"]["comparison"]
    assert cmp_["available"] and cmp_["technical"]["change"] == 14
    assert cmp_["technical"]["label"] == "Significant improvement"
    assert get(client, "overview", h, range="all").json()["data"]["comparison"]["available"] is False


# ------------------------------------------------------------------ trends
def test_bucketing_and_direction():
    assert bucket_key(datetime(2026, 10, 7, tzinfo=timezone.utc), "week") == "2026-10-05"   # Monday
    assert bucket_key(datetime(2026, 10, 7, tzinfo=timezone.utc), "month") == "2026-10"
    pts = lambda vals: [{"period": str(i), "value": v, "samples": 1} for i, v in enumerate(vals)]
    assert trend_direction(pts([60, 62]), higher_is_better=True) == "insufficient_data"
    assert trend_direction(pts([60, 65, 72, 80]), higher_is_better=True) == "improving"
    assert trend_direction(pts([80, 70, 62, 55]), higher_is_better=True) == "declining"
    assert trend_direction(pts([70, 71, 70, 72]), higher_is_better=True) == "stable"
    assert trend_direction(pts([6, 5, 3, 2]), higher_is_better=False) == "improving"   # fewer fillers


def test_trends_endpoint_uses_real_sessions_only(client, fake_db):
    h = _auth(client, "tr@example.com"); uid = _uid(fake_db, "tr@example.com")
    for i, score in enumerate((60, 70, 80)):
        interview(fake_db, uid, days_ago=6 - i * 2, tech=score, comm=score)
    s = get(client, "trends", h, range="7d").json()["data"]
    assert s["granularity"] == "day"
    tech = s["series"]["technical"]
    assert [p["value"] for p in tech["points"]] == [60, 70, 80] and tech["direction"] == "improving"
    assert s["series"]["confidence"]["points"] == []      # no communication sessions => no points, not zeros


# ------------------------------------------------------------------ interview modes & domains
def test_mode_aggregation_only_existing_modes(client, fake_db):
    h = _auth(client, "mode@example.com"); uid = _uid(fake_db, "mode@example.com")
    for score in (80, 84):
        interview(fake_db, uid, itype="cybersecurity", tech=score, comm=score)
    interview(fake_db, uid, itype="hr", tech=60, comm=70, overall=66)
    pressure(fake_db, uid)
    modes = {m["mode"]: m for m in get(client, "interviews", h).json()["data"]["modes"]}
    assert set(modes) == {"cybersecurity", "hr", "pressure"}      # no red_team, soc, ... placeholders
    assert modes["cybersecurity"]["overall_score"] == 82 and modes["cybersecurity"]["sessions"] == 2
    assert modes["hr"]["reliable"] is False


def test_domain_aggregation_combines_sources_and_gates_sparse_domains(client, fake_db):
    h = _auth(client, "dom@example.com"); uid = _uid(fake_db, "dom@example.com")
    practice(fake_db, uid, "Networking", 90, questions=5)
    interview(fake_db, uid, topic_scores=[{"topic": "network_security", "label": "Network Security", "average_score": 70, "questions": 5},
                                          {"topic": "digital_forensics", "label": "DF", "average_score": 30, "questions": 2}])
    practice(fake_db, uid, "Linux", 55, questions=5)
    data = get(client, "domains", h).json()["data"]
    domains = {d["domain"]: d for d in data["domains"]}
    assert domains["Networking"]["score"] == 80 and domains["Networking"]["questions"] == 10
    assert domains["Linux"]["band"] == "weak"
    assert "Digital Forensics" not in domains                      # only 2 questions
    forensics = next(d for d in data["insufficient_data"] if d["domain"] == "Digital Forensics")
    assert forensics["score"] is None
    assert data["weakest"][0]["domain"] == "Linux"


# ------------------------------------------------------------------ communication
def test_communication_dimensions_and_missing_sources_are_none(client, fake_db):
    h = _auth(client, "c1@example.com"); uid = _uid(fake_db, "c1@example.com")
    interview(fake_db, uid, questions=[answer(80, 70, structure=50)])
    d = {x["key"]: x["score"] for x in get(client, "communication", h).json()["data"]["dimensions"]}
    assert d["structure"] == 50 and d["conciseness"] == 70
    assert "confidence" not in d                                   # no communication session => not invented


def test_weakness_requires_repeated_evidence(client, fake_db):
    h = _auth(client, "w@example.com"); uid = _uid(fake_db, "w@example.com")
    interview(fake_db, uid, questions=[answer(vox=voice(filler_rate=6.0)) for _ in range(4)])
    assert get(client, "communication", h).json()["data"]["weaknesses"] == []      # 4 samples < 5
    interview(fake_db, uid, days_ago=2, questions=[answer(vox=voice(filler_rate=6.0))])
    w = {x["id"]: x for x in get(client, "communication", h).json()["data"]["weaknesses"]}
    assert w["filler_words"]["samples"] == 5 and w["filler_words"]["rate"] == 1.0


def test_one_bad_answer_never_creates_a_weakness(client, fake_db):
    h = _auth(client, "w2@example.com"); uid = _uid(fake_db, "w2@example.com")
    qs = [answer(vox=voice(filler_rate=1.0)) for _ in range(5)] + [answer(vox=voice(filler_rate=9.0, long_pauses=3))]
    interview(fake_db, uid, questions=qs)
    assert get(client, "communication", h).json()["data"]["weaknesses"] == []


def test_length_classification_depends_on_question_kind():
    assert classify_length(35, "technical") == "appropriate"
    assert classify_length(35, "behavioral") == "too_short"
    assert classify_length(300, "scenario") == "long"
    assert classify_length(300, "behavioral") == "very_long"


def test_structure_markers_follow_question_kind():
    tech = "TCP is a connection oriented protocol because it tracks delivery. For example, web traffic uses it. In practice it is common. " + "filler " * 10
    m = structure_markers(tech, "technical", 40)
    assert m["stages"] == {"definition": True, "explanation": True, "example": True, "practical_relevance": True}
    assert structure_markers("short answer", "technical", 2) is None        # too short to assess, not "unstructured"
    scenario = structure_markers("I would investigate the logs, then isolate the host and report the outcome. " + "x " * 20, "scenario", 35)
    assert scenario["stages"]["action"] and scenario["stages"]["investigation"]


def test_length_report_has_min_max_average(client, fake_db):
    h = _auth(client, "len@example.com"); uid = _uid(fake_db, "len@example.com")
    interview(fake_db, uid, questions=[answer(text="word " * 10), answer(text="word " * 100), answer(text="word " * 400)])
    r = get(client, "communication", h).json()["data"]["length"]
    assert (r["min_words"], r["max_words"], r["average_words"]) == (10, 400, 170)
    assert r["distribution"]["too_short"] == 1 and r["distribution"]["very_long"] == 1


# ------------------------------------------------------------------ speaking
def test_speaking_is_not_available_without_voice(client, fake_db):
    h = _auth(client, "nv@example.com")
    interview(fake_db, _uid(fake_db, "nv@example.com"))
    s = get(client, "speaking", h).json()["data"]
    assert s["available"] is False and s["metrics"] is None and s["message"] == "No voice answers yet."


def test_speaking_metrics(client, fake_db):
    h = _auth(client, "sp@example.com"); uid = _uid(fake_db, "sp@example.com")
    interview(fake_db, uid, questions=[answer(vox=voice(wpm=120, filler_rate=2.0, words=100, duration=50, pauses=6, long_pauses=1)),
                                       answer(vox=voice(wpm=140, filler_rate=4.0, words=100, duration=50, pauses=4, long_pauses=0)),
                                       answer(vox=voice(wpm=130, filler_rate=3.0, words=100, duration=50, pauses=5, long_pauses=1))])
    m = get(client, "speaking", h).json()["data"]["metrics"]
    assert m["words_per_minute"] == 130 and m["filler_per_100_words"] == 3.0
    assert m["pauses_per_minute"] == 6.0 and m["long_pauses"] == 2 and m["average_answer_seconds"] == 50.0


def test_pause_metrics_are_none_when_not_measured(client, fake_db):
    h = _auth(client, "np@example.com"); uid = _uid(fake_db, "np@example.com")
    interview(fake_db, uid, questions=[answer(vox=voice(pauses=None, long_pauses=None)) for _ in range(3)])
    m = get(client, "speaking", h).json()["data"]["metrics"]
    assert m["pauses_per_minute"] is None and m["long_pauses"] is None and m["words_per_minute"] == 130


def test_voice_conversation_sessions_are_not_double_counted(client, fake_db):
    h = _auth(client, "vc@example.com"); uid = _uid(fake_db, "vc@example.com")
    interview(fake_db, uid, questions=[answer(vox=voice()) for _ in range(3)])
    fake_db[Collections.VOICE_CONVERSATION_SESSIONS].insert_one({
        "user_id": uid, "status": "completed", "started_at": NOW,
        "linked": {"kind": "interview"}, "messages": [{"role": "user", "text": "x", "voice_analysis": voice()}] * 5})
    assert get(client, "speaking", h).json()["data"]["spoken_answers"] == 3


# ------------------------------------------------------------------ pressure
def test_pressure_comparison_and_insight(client, fake_db):
    h = _auth(client, "pr@example.com"); uid = _uid(fake_db, "pr@example.com")
    for d in (3, 5):
        interview(fake_db, uid, days_ago=d, tech=82, comm=78)
        pressure(fake_db, uid, days_ago=d, tech=80, comm=62)
    p = get(client, "pressure", h).json()["data"]
    assert p["comparison_available"] and p["differences"] == {"technical": -2, "communication": -16}
    assert any("technical performance stays stable" in i for i in p["insights"])
    assert p["normal"]["confidence"] is None
    text = json.dumps(p).lower()
    assert not any(w in text for w in ("anxiety", "nervous", "diagnos", "stress disorder"))


def test_pressure_without_baseline_or_data(client, fake_db):
    h = _auth(client, "pr2@example.com"); uid = _uid(fake_db, "pr2@example.com")
    assert get(client, "pressure", h).json()["data"]["available"] is False
    pressure(fake_db, uid)
    p = get(client, "pressure", h).json()["data"]
    assert p["available"] and p["comparison_available"] is False and "normal interviews" in p["message"]


# ------------------------------------------------------------------ follow-ups & readiness
def test_follow_up_analytics(client, fake_db):
    h = _auth(client, "fu@example.com"); uid = _uid(fake_db, "fu@example.com")
    interview(fake_db, uid, questions=[answer(80, follow=[70]) for _ in range(5)])
    f = get(client, "interviews", h).json()["data"]["follow_ups"]
    assert f["available"] and f["follow_up_answers"] == 5 and f["technical_score"] == 70
    assert f["difference_vs_main"] == -10 and f["consistency"] == 90
    interview(fake_db, uid, days_ago=2, questions=[answer(80)])
    assert get(client, "interviews", h, range="7d").status_code == 200


def test_readiness_not_enough_data(client, fake_db):
    h = _auth(client, "rd@example.com"); uid = _uid(fake_db, "rd@example.com")
    for d in (1, 2):
        interview(fake_db, uid, days_ago=d)
    r = get(client, "readiness", h).json()["data"]
    assert r["available"] is False and r["score"] is None and r["message"] == "Not enough data"


def test_readiness_formula_renormalises_available_components(client, fake_db):
    h = _auth(client, "rd2@example.com"); uid = _uid(fake_db, "rd2@example.com")
    for d in (1, 2, 3, 4):   # consistency needs 4 sessions
        interview(fake_db, uid, days_ago=d, tech=80, comm=60, overall=70)
    r = get(client, "readiness", h).json()["data"]
    # technical 80 (0.35), communication 60 (0.25), consistency 100 (0.10; stdev 0)
    expected = round((80 * 0.35 + 60 * 0.25 + 100 * 0.10) / 0.70)
    assert r["available"] and r["score"] == expected
    assert r["coverage"] == 0.7
    assert {m["key"] for m in r["missing_components"]} == {"confidence", "follow_up", "pressure"}
    assert r["formula"]["technical"] == 0.35


def test_readiness_with_all_components(client, fake_db):
    h = _auth(client, "rd3@example.com"); uid = _uid(fake_db, "rd3@example.com")
    for d in (1, 2, 3, 4):
        interview(fake_db, uid, days_ago=d, tech=80, comm=70, overall=75, questions=[answer(80, 70, follow=[60])] * 2)
        comm_session(fake_db, uid, days_ago=d, confidence=50)
    for d in (1, 2):
        pressure(fake_db, uid, days_ago=d, handling=40)
    r = get(client, "readiness", h).json()["data"]
    assert r["coverage"] == 1.0
    assert r["score"] == round(80 * .35 + 70 * .25 + 50 * .15 + 100 * .10 + 60 * .10 + 40 * .05)


# ------------------------------------------------------------------ insights, recommendations, AI
def _rich_user(client, fake_db, email):
    h = _auth(client, email); uid = _uid(fake_db, email)
    for d in (40, 35):
        interview(fake_db, uid, days_ago=d, tech=62, comm=60)
    for d in (6, 4, 2):
        interview(fake_db, uid, days_ago=d, tech=82, comm=72,
                  questions=[answer(82, 72, vox=voice(filler_rate=6.0)) for _ in range(2)])
    practice(fake_db, uid, "Linux", 50, questions=6)
    return h


def test_insights_recommendations_and_evidence(client, fake_db):
    h = _rich_user(client, fake_db, "ins@example.com")
    d = get(client, "insights", h).json()["data"]
    kinds = {i["kind"] for i in d["insights"]}
    assert "improvement" in kinds and "communication" in kinds
    assert all(i["evidence"] for i in d["insights"])
    action = next(a for a in d["next_actions"] if a["weakness"] == "High filler-word usage")
    assert "speaking practice" in action["action"] and action["route"] == "/communication"
    assert any(a["weakness"] == "Weak Linux reasoning" and a["route"] == "/cybersecurity" for a in d["next_actions"])
    assert d["ai_summary"] is None                                  # opt-in only


def test_no_transcript_leakage(client, fake_db):
    h = _auth(client, "leak@example.com"); uid = _uid(fake_db, "leak@example.com")
    interview(fake_db, uid, questions=[answer(text=SECRET + " word" * 50)])
    for name in ("overview", "interviews", "communication", "speaking", "pressure", "domains", "trends", "insights", "readiness"):
        assert SECRET not in get(client, name, h).text


class _FakeAI:
    def __init__(self, text=None, fail=False):
        self.text, self.fail, self.prompts = text, fail, []

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        self.prompts.append(user_message)
        if self.fail:
            raise AIProviderError("boom")
        from app.services.ai.ai_service import AIResponse
        return AIResponse(text=self.text, model="fake")


def test_ai_summary_is_optional_compact_and_falls_back(client, fake_db):
    h = _rich_user(client, fake_db, "ai@example.com")
    fake = _FakeAI('{"summary": "Nice progress overall."}')
    app.dependency_overrides[get_analytics_service] = lambda: AnalyticsService(fake)
    try:
        d = get(client, "insights", h, ai_summary="true", range="all").json()["data"]
        assert d["ai_summary"] == "Nice progress overall."
        assert len(fake.prompts) == 1 and len(fake.prompts[0]) < 2500
        assert "word word" not in fake.prompts[0]                    # no transcripts
        failing = _FakeAI(fail=True)
        app.dependency_overrides[get_analytics_service] = lambda: AnalyticsService(failing)
        d = get(client, "insights", h, ai_summary="true", range="all").json()["data"]
        assert d["ai_summary"] is None and d["insights"]              # deterministic insights survive
    finally:
        app.dependency_overrides.pop(get_analytics_service, None)


def test_internal_errors_are_not_exposed(client, fake_db):
    h = _auth(client, "err@example.com")

    class Boom(AnalyticsService):
        def overview(self, *a, **k):
            raise RuntimeError("mongodb://secret-host/internal failure")

    app.dependency_overrides[get_analytics_service] = lambda: Boom()
    try:
        r = get(client, "overview", h)
    finally:
        app.dependency_overrides.pop(get_analytics_service, None)
    assert r.status_code == 500 and "secret-host" not in r.text and r.json()["error_code"] == "INTERNAL_SERVER_ERROR"


def test_result_size_is_bounded(fake_db):
    uid = ObjectId()
    for i in range(config.MAX_SESSIONS_PER_SOURCE + 5):
        interview(fake_db, uid, days_ago=1)
    facts = load_facts(fake_db, user_id=str(uid), window=DateRange(None, NOW + timedelta(days=1), "all"))
    assert len(facts.interviews) == config.MAX_SESSIONS_PER_SOURCE and facts.truncated is True


def test_readiness_report_pure_function_requires_both_core_components():
    from app.services.analytics.facts import Facts
    assert readiness_report(Facts())["available"] is False
