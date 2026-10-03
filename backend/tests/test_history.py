"""
Tests for Step 15 -- History & Activity Center.

Sessions are seeded straight into the (mongomock) collections in the shape the
real services write them, because History is a read layer over those
collections -- that is exactly what is being tested. No AI service is involved.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from bson import ObjectId

from app.db.collections import Collections
from tests.test_communication import _register_and_login

NOW = datetime(2026, 10, 2, 12, 0, 0)  # naive UTC, the way MongoDB hands datetimes back
URL = "/api/v1/history"


# --- Helpers ----------------------------------------------------------------------------------


def _auth(client, email):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _uid(fake_db, email) -> ObjectId:
    return fake_db[Collections.USERS].find_one({"email": email})["_id"]


def _ago(**kwargs) -> datetime:
    return NOW - timedelta(**kwargs)


def _practice(uid, *, title="Linux Basics", category="Linux", started=None, status="completed", score=80):
    started = started or _ago(days=1)
    return {
        "user_id": uid, "topic_slug": title.lower().replace(" ", "-"), "topic_title": title,
        "category": category, "difficulty": "beginner", "started_at": started,
        "completed_at": started + timedelta(minutes=9) if status == "completed" else None,
        "status": status,
        "questions": [
            {"question_id": "q1", "question": "What does chmod do?", "type": "short_answer", "options": None,
             "correct_answer": None, "ideal_answer": "Changes file permissions", "explanation": "chmod = change mode"},
            {"question_id": "q2", "question": "Which is a shell?", "type": "multiple_choice",
             "options": ["bash", "png"], "correct_answer": "bash", "ideal_answer": None,
             "explanation": "bash is a shell"},
        ],
        "answers": {"q1": {"answer": "changes permissions", "score": 90, "correct": True,
                           "feedback": "Good", "missing_points": [], "answered_at": started}},
        "score": score if status == "completed" else None,
        "questions_answered": 1, "correct_answers": 1, "weak_areas": [], "recommendations": ["Keep going"],
    }


def _ctf(uid, *, title="Login bypass", category="web_security", created=None, status="completed"):
    created = created or _ago(days=2)
    return {
        "user_id": uid, "platform": "TryHackMe", "category": category, "difficulty": "easy", "title": title,
        "description": "Found a login page", "user_notes": "", "status": status,
        "messages": [{"role": "user", "content": "help", "created_at": created}],
        "hint_history": [{"level": "hint_1", "content": "Look at the form", "requested_at": created}],
        "hints_used": 1, "flag": None, "created_at": created, "updated_at": created,
        "completed_at": created + timedelta(minutes=30) if status == "completed" else None,
    }


def _communication(uid, *, title="Asking a senior for help", started=None, score=72):
    started = started or _ago(days=3)
    return {
        "user_id": uid, "scenario_id": ObjectId(), "scenario_title": title, "category": "seniors",
        "mode": "professional", "difficulty": "intermediate", "ai_role": "Senior engineer",
        "user_role": "Junior analyst", "objective": "Ask clearly", "status": "completed",
        "messages": [{"role": "user", "content": "Hi", "timestamp": started}],
        "evaluation": {"overall_score": score, "summary": "Clear and polite."},
        "started_at": started, "updated_at": started, "completed_at": started + timedelta(minutes=12),
    }


def _interview(uid, *, itype="cybersecurity", started=None, score=78, status="completed"):
    started = started or _ago(days=4)
    return {
        "user_id": uid, "interview_type": itype, "difficulty": "intermediate", "mode": "text",
        "question_count": 1, "current_question_number": 1, "status": status, "reveal_feedback": False,
        "topic_plan": [], "version": 1, "started_at": started, "updated_at": started,
        "completed_at": started + timedelta(minutes=18) if status == "completed" else None,
        "questions": [{
            "question_number": 1, "question": "What is a SIEM?", "topic": "siem", "focus": "basics",
            "asked_at": started, "answer": "A log aggregator", "answer_input_type": "text",
            "technical_evaluation": {"technical_score": 80}, "communication_evaluation": {"communication_score": 70},
            "improved_answer": "Better answer", "follow_up_questions": [],
            "internal": {"probe": "SECRET-EVALUATOR-NOTE"},
        }],
        "final_evaluation": {"overall_score": score, "technical_score": 80, "communication_score": 70}
        if status == "completed" else None,
    }


def _pressure(uid, *, started=None, score=65, level=3):
    started = started or _ago(days=5)
    return {
        "user_id": uid, "pressure_level": level, "mode": "interview", "interview_type": "technical",
        "difficulty": "beginner", "input_mode": "text", "question_count": 1, "current_question_number": 1,
        "status": "completed", "started_at": started, "updated_at": started,
        "completed_at": started + timedelta(minutes=10),
        "questions": [{
            "question_number": 1, "question": "Explain DNS fast", "topic": "networking", "focus": "dns",
            "condition": {"type": "none"}, "asked_at": started, "answer": "It resolves names",
            "answer_input_type": "text", "technical_evaluation": {"technical_score": 60},
            "communication_evaluation": {"communication_score": 70}, "improved_answer": None,
            "follow_up_questions": [],
        }],
        "final_evaluation": {"overall_score": score}, "self_reported_difficulty": None,
    }


def _voice(uid, *, topic=None, mode="cybersecurity", started=None, status="completed"):
    started = started or _ago(hours=5)
    return {
        "user_id": uid, "mode": mode, "difficulty": "intermediate", "topic": topic, "config": {},
        "status": status, "linked": None,
        "messages": [
            {"role": "assistant", "text": "Hello, ready?", "timestamp": started, "audio_available": True},
            {"role": "user", "text": "Yes I am", "timestamp": started, "duration_seconds": 3.2,
             "voice_analysis": {"word_count": 3}},
        ],
        "turn_count": 2, "user_turn_count": 1, "assistant_turn_count": 1,
        "started_at": started, "activated_at": started, "last_activity_at": started + timedelta(minutes=7),
        "ended_at": started + timedelta(minutes=7) if status == "completed" else None,
        "summary": {"duration_seconds": 420, "evaluation": {"overall_score": 81}},
        "processing_token": "INTERNAL-LOCK-TOKEN", "processing_since": None,
    }


def _insert(fake_db, collection, doc) -> str:
    return str(fake_db[collection].insert_one(doc).inserted_id)


@pytest.fixture()
def alice(client, fake_db):
    headers = _auth(client, "alice@example.com")
    return headers, _uid(fake_db, "alice@example.com")


@pytest.fixture()
def seeded(fake_db, alice):
    """One activity of every type for alice, dated so the newest-first order is known."""
    _, uid = alice
    ids = {
        "voice_conversation": _insert(fake_db, Collections.VOICE_CONVERSATION_SESSIONS, _voice(uid)),  # 5h ago
        "cybersecurity_practice": _insert(fake_db, Collections.PRACTICE_SESSIONS, _practice(uid)),  # 1d
        "ctf": _insert(fake_db, Collections.CTF_SESSIONS, _ctf(uid)),  # 2d
        "communication": _insert(fake_db, Collections.COMMUNICATION_SESSIONS, _communication(uid)),  # 3d
        "interview": _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(uid)),  # 4d
        "pressure_training": _insert(fake_db, Collections.PRESSURE_SESSIONS, _pressure(uid)),  # 5d
    }
    return ids


def _get(client, headers, params=None, path=""):
    return client.get(f"{URL}{path}", params=params, headers=headers)


# --- Authentication ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["", "/summary", "/interview/" + "a" * 24])
def test_unauthenticated_requests_are_rejected(client, path):
    response = client.get(f"{URL}{path}")
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_invalid_token_is_rejected(client):
    assert client.get(URL, headers={"Authorization": "Bearer not-a-token"}).status_code == 401


# --- Empty state --------------------------------------------------------------------------------


def test_empty_history_returns_clean_empty_response(client, alice):
    headers, _ = alice
    data = _get(client, headers).json()["data"]
    assert data == {"items": [], "page": 1, "limit": 20, "total": 0, "has_next": False}

    summary = _get(client, headers, path="/summary").json()["data"]
    assert summary["total"] == 0
    assert all(t["count"] == 0 for t in summary["types"])


# --- Listing ----------------------------------------------------------------------------------


def test_history_lists_every_activity_type_newest_first(client, alice, seeded):
    headers, _ = alice
    data = _get(client, headers).json()["data"]

    assert data["total"] == 6
    assert [i["type"] for i in data["items"]] == [
        "voice_conversation", "cybersecurity_practice", "ctf", "communication", "interview", "pressure_training",
    ]
    assert [i["id"] for i in data["items"]] == [seeded[t] for t in (
        "voice_conversation", "cybersecurity_practice", "ctf", "communication", "interview", "pressure_training")]


def test_oldest_sort_reverses_order(client, alice, seeded):
    headers, _ = alice
    types = [i["type"] for i in _get(client, headers, {"sort": "oldest"}).json()["data"]["items"]]
    assert types[0] == "pressure_training" and types[-1] == "voice_conversation"


def test_normalized_fields_use_real_stored_data(client, alice, seeded):
    headers, _ = alice
    by_type = {i["type"]: i for i in _get(client, headers).json()["data"]["items"]}

    interview = by_type["interview"]
    assert interview["title"] == "Cybersecurity Interview"
    assert interview["score"] == 78
    assert interview["status"] == "completed"
    assert interview["duration_seconds"] == 18 * 60
    assert interview["metadata"]["question_count"] == 1
    assert interview["created_at"].endswith("Z") or "+00:00" in interview["created_at"]  # explicit UTC

    assert by_type["cybersecurity_practice"]["title"] == "Linux Basics"
    assert by_type["cybersecurity_practice"]["score"] == 80
    assert by_type["cybersecurity_practice"]["metadata"]["correct_answers"] == 1

    assert by_type["ctf"]["score"] is None  # CTF has no numeric score; never invented
    assert by_type["ctf"]["metadata"]["hints_used"] == 1
    assert by_type["ctf"]["description"] == "TryHackMe · Web Security"

    assert by_type["communication"]["score"] == 72
    assert by_type["communication"]["title"] == "Asking a senior for help"

    assert by_type["pressure_training"]["title"] == "Pressure Training · Level 3"
    assert by_type["pressure_training"]["score"] == 65

    voice = by_type["voice_conversation"]
    assert voice["title"] == "Cybersecurity Q&A"
    assert voice["duration_seconds"] == 420
    assert voice["score"] == 81
    assert voice["metadata"]["turn_count"] == 2


def test_in_progress_sessions_report_status_and_no_score_or_duration(client, fake_db, alice):
    headers, uid = alice
    _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(uid, status="in_progress"))
    voice = _voice(uid, status="active")
    voice["summary"] = None
    _insert(fake_db, Collections.VOICE_CONVERSATION_SESSIONS, voice)

    items = _get(client, headers).json()["data"]["items"]
    assert {i["status"] for i in items} == {"in_progress"}
    assert all(i["score"] is None and i["completed_at"] is None for i in items)


def test_absurd_elapsed_time_is_hidden_rather_than_shown(client, fake_db, alice):
    headers, uid = alice
    doc = _interview(uid)
    doc["completed_at"] = doc["started_at"] + timedelta(days=2)  # left open for two days
    _insert(fake_db, Collections.INTERVIEW_SESSIONS, doc)
    assert _get(client, headers).json()["data"]["items"][0]["duration_seconds"] is None


# --- Response safety ----------------------------------------------------------------------------


def test_list_never_exposes_internal_fields(client, alice, seeded):
    headers, uid = alice
    raw = json.dumps(_get(client, headers).json())
    for forbidden in ("user_id", "processing_token", "INTERNAL-LOCK-TOKEN", "SECRET-EVALUATOR-NOTE", str(uid)):
        assert forbidden not in raw


# --- Pagination ---------------------------------------------------------------------------------


def test_pagination_walks_all_items_without_overlap(client, fake_db, alice):
    headers, uid = alice
    for n in range(7):
        _insert(fake_db, Collections.PRACTICE_SESSIONS, _practice(uid, title=f"P{n}", started=_ago(hours=n + 1)))
    for n in range(6):
        _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(uid, started=_ago(hours=n, minutes=30)))

    seen: list[str] = []
    page = 1
    while True:
        data = _get(client, headers, {"page": page, "limit": 5}).json()["data"]
        assert data["total"] == 13 and data["page"] == page and data["limit"] == 5
        assert len(data["items"]) <= 5
        seen.extend(i["id"] for i in data["items"])
        if not data["has_next"]:
            break
        page += 1

    assert page == 3
    assert len(seen) == 13 and len(set(seen)) == 13
    # Mixed sources still come out globally newest-first across page boundaries.
    full = _get(client, headers, {"limit": 50}).json()["data"]["items"]
    assert [i["id"] for i in full] == seen
    stamps = [i["created_at"] for i in full]
    assert stamps == sorted(stamps, reverse=True)


def test_page_beyond_the_end_is_empty_not_an_error(client, alice, seeded):
    headers, _ = alice
    data = _get(client, headers, {"page": 9, "limit": 5}).json()["data"]
    assert data["items"] == [] and data["has_next"] is False and data["total"] == 6


def test_limit_and_page_are_validated(client, alice):
    headers, _ = alice
    assert _get(client, headers, {"limit": 51}).status_code == 422
    assert _get(client, headers, {"limit": 0}).status_code == 422
    assert _get(client, headers, {"page": 0}).status_code == 422


def test_pages_deeper_than_the_window_are_refused_cleanly(client, fake_db, alice, monkeypatch):
    from app.services.history import history_service as module

    headers, uid = alice
    monkeypatch.setattr(module, "MAX_WINDOW", 4)
    for n in range(8):
        _insert(fake_db, Collections.PRACTICE_SESSIONS, _practice(uid, started=_ago(hours=n + 1)))
    assert _get(client, headers, {"page": 2, "limit": 2}).status_code == 200
    response = _get(client, headers, {"page": 3, "limit": 2})
    assert response.status_code == 422
    assert response.json()["error_code"] == "PAGE_OUT_OF_RANGE"


# --- Type filter --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "activity_type",
    ["cybersecurity_practice", "ctf", "communication", "interview", "pressure_training", "voice_conversation"],
)
def test_type_filter_returns_only_that_type(client, alice, seeded, activity_type):
    headers, _ = alice
    data = _get(client, headers, {"type": activity_type}).json()["data"]
    assert data["total"] == 1
    assert [i["type"] for i in data["items"]] == [activity_type]


def test_unknown_type_is_rejected(client, alice):
    headers, _ = alice
    assert _get(client, headers, {"type": "mentor"}).status_code == 422


# --- Search -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "term, expected",
    [
        ("linux", {"cybersecurity_practice"}),
        ("LINUX", {"cybersecurity_practice"}),  # case-insensitive
        ("login", {"ctf"}),
        ("web security", {"ctf"}),  # slug stored as web_security
        ("senior", {"communication"}),
        ("interview", {"interview", "pressure_training"}),  # title word + pressure session in interview mode
        ("voice", {"voice_conversation"}),
        ("pressure", {"pressure_training"}),
        ("nothing-matches-this", set()),
    ],
)
def test_search_matches_titles_and_topics(client, alice, seeded, term, expected):
    headers, _ = alice
    items = _get(client, headers, {"search": term}).json()["data"]["items"]
    assert {i["type"] for i in items} == expected


def test_search_is_literal_not_a_regex(client, fake_db, alice, seeded):
    headers, _ = alice
    # ".*" would match everything if it were treated as a pattern.
    assert _get(client, headers, {"search": ".*"}).json()["data"]["total"] == 0
    assert _get(client, headers, {"search": "(["}).status_code == 200


def test_search_combines_with_type_filter_and_counts_match_filtered_total(client, fake_db, alice):
    headers, uid = alice
    _insert(fake_db, Collections.PRACTICE_SESSIONS, _practice(uid, title="Linux Basics"))
    _insert(fake_db, Collections.PRACTICE_SESSIONS, _practice(uid, title="Phishing 101", category="Social Engineering"))
    _insert(fake_db, Collections.CTF_SESSIONS, _ctf(uid, title="Linux privesc", category="linux"))

    both = _get(client, headers, {"search": "linux"}).json()["data"]
    assert both["total"] == 2
    only_practice = _get(client, headers, {"search": "linux", "type": "cybersecurity_practice"}).json()["data"]
    assert only_practice["total"] == 1 and only_practice["items"][0]["title"] == "Linux Basics"


# --- Date filtering -----------------------------------------------------------------------------


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def test_start_date_filters_out_older_activity(client, alice, seeded):
    headers, _ = alice
    data = _get(client, headers, {"start_date": _iso(_ago(days=2, hours=12))}).json()["data"]
    assert {i["type"] for i in data["items"]} == {"voice_conversation", "cybersecurity_practice", "ctf"}
    assert data["total"] == 3


def test_end_date_and_custom_range(client, alice, seeded):
    headers, _ = alice
    ended = _get(client, headers, {"end_date": _iso(_ago(days=3, hours=12))}).json()["data"]
    assert {i["type"] for i in ended["items"]} == {"interview", "pressure_training"}

    ranged = _get(
        client, headers, {"start_date": _iso(_ago(days=4, hours=12)), "end_date": _iso(_ago(days=2, hours=12))}
    ).json()["data"]
    assert {i["type"] for i in ranged["items"]} == {"communication", "interview"}


def test_date_filter_accepts_timezone_offsets(client, alice, seeded):
    headers, _ = alice
    # 2026-10-01 12:00 UTC == 17:30 at +05:30; the practice session (started 1d ago, 12:00 UTC) sits on it.
    start = quote("2026-10-01T17:30:00+05:30")
    data = _get(client, headers, {"start_date": "2026-10-01T17:30:00+05:30"}).json()["data"]
    assert "cybersecurity_practice" in {i["type"] for i in data["items"]}
    assert start  # (url-quoting kept for clarity when run by hand)


def test_inverted_date_range_is_a_clear_error(client, alice):
    headers, _ = alice
    response = _get(client, headers, {"start_date": _iso(NOW), "end_date": _iso(_ago(days=1))})
    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_DATE_RANGE"


def test_garbage_date_is_a_validation_error(client, alice):
    headers, _ = alice
    assert _get(client, headers, {"start_date": "yesterday-ish"}).status_code == 422


# --- Summary ------------------------------------------------------------------------------------


def test_summary_counts_come_from_real_data(client, fake_db, alice, seeded):
    headers, uid = alice
    _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(uid, itype="hr"))
    _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(uid, itype="mixed"))

    summary = _get(client, headers, path="/summary").json()["data"]
    counts = {t["type"]: t["count"] for t in summary["types"]}
    assert counts == {
        "cybersecurity_practice": 1, "ctf": 1, "communication": 1,
        "interview": 3, "pressure_training": 1, "voice_conversation": 1,
    }
    assert summary["total"] == 8
    assert {t["label"] for t in summary["types"]} >= {"Interview", "Voice Conversation"}


# --- Ownership ----------------------------------------------------------------------------------


@pytest.fixture()
def bob(client, fake_db):
    headers = _auth(client, "bob@example.com")
    return headers, _uid(fake_db, "bob@example.com")


def test_users_only_see_their_own_history(client, fake_db, alice, bob, seeded):
    alice_headers, _ = alice
    bob_headers, bob_id = bob
    _insert(fake_db, Collections.INTERVIEW_SESSIONS, _interview(bob_id, itype="hr"))

    assert _get(client, alice_headers).json()["data"]["total"] == 6
    bobs = _get(client, bob_headers).json()["data"]
    assert bobs["total"] == 1 and bobs["items"][0]["title"] == "HR Interview"
    assert _get(client, bob_headers, path="/summary").json()["data"]["total"] == 1


def test_user_id_query_parameter_is_ignored(client, alice, bob, seeded):
    bob_headers, _ = bob
    _, alice_id = alice
    data = _get(client, bob_headers, {"user_id": str(alice_id)}).json()["data"]
    assert data["total"] == 0 and data["items"] == []


def test_search_and_filters_never_cross_users(client, fake_db, alice, bob, seeded):
    bob_headers, _ = bob
    assert _get(client, bob_headers, {"search": "linux"}).json()["data"]["total"] == 0
    assert _get(client, bob_headers, {"type": "interview"}).json()["data"]["total"] == 0


@pytest.mark.parametrize(
    "activity_type",
    ["cybersecurity_practice", "ctf", "communication", "interview", "pressure_training", "voice_conversation"],
)
def test_user_cannot_open_another_users_activity(client, alice, bob, seeded, activity_type):
    bob_headers, _ = bob
    response = _get(client, bob_headers, path=f"/{activity_type}/{seeded[activity_type]}")
    assert response.status_code == 404
    assert response.json()["error_code"] == "ACTIVITY_NOT_FOUND"
    # Identical to a genuinely missing id, so ids can't be probed for existence.
    missing = _get(client, bob_headers, path=f"/{activity_type}/{ObjectId()}")
    assert missing.status_code == 404 and missing.json() == response.json()


# --- Detail -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "activity_type",
    ["cybersecurity_practice", "ctf", "communication", "interview", "pressure_training", "voice_conversation"],
)
def test_owner_can_open_each_activity_type(client, alice, seeded, activity_type):
    headers, _ = alice
    response = _get(client, headers, path=f"/{activity_type}/{seeded[activity_type]}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["activity"]["id"] == seeded[activity_type]
    assert data["activity"]["type"] == activity_type
    assert isinstance(data["detail"], dict) and data["detail"]


def test_interview_detail_has_questions_answers_and_evaluation(client, alice, seeded):
    headers, _ = alice
    detail = _get(client, headers, path=f"/interview/{seeded['interview']}").json()["data"]["detail"]
    question = detail["questions"][0]
    assert question["question"] == "What is a SIEM?"
    assert question["answer"] == "A log aggregator"
    assert question["technical_evaluation"] == {"technical_score": 80}
    assert detail["final_evaluation"]["overall_score"] == 78
    assert "SECRET-EVALUATOR-NOTE" not in json.dumps(detail)  # evaluator-internal field stays internal


def test_voice_detail_has_transcript_and_hides_lock_token(client, alice, seeded):
    headers, _ = alice
    raw = _get(client, headers, path=f"/voice_conversation/{seeded['voice_conversation']}").json()
    session = raw["data"]["detail"]
    assert [m["role"] for m in session["messages"]] == ["assistant", "user"]
    assert session["messages"][1]["text"] == "Yes I am"
    assert "INTERNAL-LOCK-TOKEN" not in json.dumps(raw)


def test_ctf_and_communication_detail_have_conversation(client, alice, seeded):
    headers, _ = alice
    ctf = _get(client, headers, path=f"/ctf/{seeded['ctf']}").json()["data"]["detail"]
    assert ctf["hints"][0]["level"] == "hint_1" and ctf["messages"][0]["content"] == "help"
    comm = _get(client, headers, path=f"/communication/{seeded['communication']}").json()["data"]["detail"]
    assert comm["evaluation"]["overall_score"] == 72 and comm["messages"][0]["content"] == "Hi"


def test_practice_detail_only_reveals_answers_for_answered_questions(client, alice, seeded):
    headers, _ = alice
    detail = _get(client, headers, path=f"/cybersecurity_practice/{seeded['cybersecurity_practice']}").json()[
        "data"
    ]["detail"]
    answered, unanswered = detail["questions"]

    assert answered["answered"] is True
    assert answered["answer"] == "changes permissions" and answered["score"] == 90
    assert answered["ideal_answer"] == "Changes file permissions"

    assert unanswered["answered"] is False
    for secret in ("correct_answer", "ideal_answer", "explanation", "answer", "feedback"):
        assert secret not in unanswered
    assert "bash is a shell" not in json.dumps(unanswered)
    assert '"correct_answer"' not in json.dumps(detail)  # the raw answer key is never exposed


def test_malformed_activity_id_is_a_404_not_a_500(client, alice):
    headers, _ = alice
    assert _get(client, headers, path="/interview/not-an-object-id").status_code == 404


def test_unknown_activity_type_in_detail_is_rejected(client, alice, seeded):
    headers, _ = alice
    assert _get(client, headers, path=f"/mentor/{seeded['interview']}").status_code == 422


def test_detail_id_must_match_the_requested_type(client, alice, seeded):
    headers, _ = alice
    # A real, owned interview id asked for as a CTF is not found.
    assert _get(client, headers, path=f"/ctf/{seeded['interview']}").status_code == 404


# --- Regression guard ---------------------------------------------------------------------------


def test_history_does_not_write_anything(client, fake_db, alice, seeded):
    headers, _ = alice
    before = {name: fake_db[name].count_documents({}) for name in fake_db.list_collection_names()}
    _get(client, headers)
    _get(client, headers, path="/summary")
    _get(client, headers, path=f"/interview/{seeded['interview']}")
    after = {name: fake_db[name].count_documents({}) for name in fake_db.list_collection_names()}
    assert before == after
    assert not {"history", "activity_history", "user_history", "session_history"} & set(after)
