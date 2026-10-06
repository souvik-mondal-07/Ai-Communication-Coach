"""
Step 18 integration tests: analytics over sessions produced by the REAL Step 9/10
endpoints (scripted fake AI, no network), not hand-built documents. These guard
against the analytics layer drifting from the shapes earlier steps actually store.
"""

from __future__ import annotations

import pytest

from app.core.dependencies import get_interview_service, get_pressure_service
from app.db.collections import Collections
from app.main import app
from app.services.interview.interview_service import InterviewService
from app.services.pressure.pressure_service import PressureService
from tests.test_analytics import get
from tests.test_interview import ScriptedInterviewAI, _answer as interview_answer, _finish as interview_finish, _new as new_interview
from tests.test_pressure import _finish as pressure_finish, _new as new_pressure

META = {"duration_seconds": 12.0, "language": "en",
        "pause_metrics": {"pause_count": 2, "long_pauses": 1, "average_pause_seconds": 1.5,
                          "longest_pause_seconds": 2.1, "total_pause_seconds": 3.0, "granularity": "word"}}
SPOKEN = "Um, a SIEM basically collects logs, uh, and correlates them, you know, to raise alerts for the team."


@pytest.fixture()
def ai():
    fake = ScriptedInterviewAI()
    app.dependency_overrides[get_interview_service] = lambda: InterviewService(ai_service_=fake)
    app.dependency_overrides[get_pressure_service] = lambda: PressureService(ai_service_=fake)
    yield fake
    app.dependency_overrides.pop(get_interview_service, None)
    app.dependency_overrides.pop(get_pressure_service, None)


def test_real_interview_flows_into_analytics(client, ai, fake_db):
    headers, sid, _ = new_interview(client, "int-a@example.com", interview_type="technical", question_count=5)
    final = interview_finish(client, headers, sid)["final_evaluation"]

    overview = get(client, "overview", headers).json()["data"]
    assert overview["counts"]["interviews"] == 1
    assert overview["scores"]["technical"] == final["technical_score"]
    assert overview["scores"]["communication"] == final["communication_score"]
    assert overview["scores"]["overall"] == final["overall_score"]
    assert overview["scores"]["confidence"] is None            # interviews store no confidence score

    modes = get(client, "interviews", headers).json()["data"]["modes"]
    assert [m["mode"] for m in modes] == ["technical"]

    comm = get(client, "communication", headers).json()["data"]
    assert comm["length"]["available"] and comm["length"]["answers"] >= 5
    assert {d["key"] for d in comm["dimensions"]} >= {"clarity", "structure", "conciseness"}
    assert get(client, "speaking", headers).json()["data"]["available"] is False   # typed answers only

    # Refresh: analytics are derived on read, so a second call is identical.
    assert get(client, "overview", headers).json()["data"]["scores"] == overview["scores"]


def test_real_voice_answers_flow_into_speaking_metrics(client, ai, fake_db):
    headers, sid, _ = new_interview(client, "int-v@example.com", mode="voice", question_count=5)
    for _ in range(3):
        assert interview_answer(client, headers, sid, SPOKEN, input_type="voice", audio_metadata=META).status_code == 200
    interview_finish(client, headers, sid)

    s = get(client, "speaking", headers).json()["data"]
    assert s["available"] and s["spoken_answers"] == 3
    m = s["metrics"]
    assert m["words_per_minute"] is None or m["words_per_minute"] == 90   # 18 words / 12 s, per Step 8
    assert m["filler_per_100_words"] > 0
    assert m["long_pauses"] == 3 and m["average_answer_seconds"] == 12.0
    assert "self_corrections" in s["not_tracked"]


def test_real_pressure_session_compares_with_normal(client, ai, fake_db):
    headers, sid, _ = new_interview(client, "int-p@example.com", interview_type="cybersecurity", question_count=5)
    interview_finish(client, headers, sid)

    for _ in range(2):
        p_headers, p_sid, _ = new_pressure(client, "int-p@example.com", question_count=5, pressure_level=2)
        pressure_finish(client, p_headers, p_sid)

    stored = fake_db[Collections.PRESSURE_SESSIONS].find_one({})["final_evaluation"]
    p = get(client, "pressure", headers).json()["data"]
    assert p["available"] and p["pressure"]["sessions"] == 2
    assert p["pressure_handling_score"] == stored["pressure_handling_score"]
    assert p["normal"]["sessions"] == 1
    modes = {m["mode"] for m in get(client, "interviews", headers).json()["data"]["modes"]}
    assert "pressure" in modes
