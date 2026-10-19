"""Phase 23 -- aptitude sessions, scoring, expiry, idempotency, ownership, analytics, weak topics."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from app.core.rate_limit import reset_rate_limits
from app.db.collections import Collections
from app.services.aptitude import bank, sessions
from tests.test_communication import _register_and_login

URL = "/api/v1/aptitude"
LEAK = {"correct_index", "explanation", "formula", "verification", "fingerprint", "correct_option", "is_correct"}


@pytest.fixture()
def apt(client, fake_db, monkeypatch):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    reset_rate_limits()
    monkeypatch.setattr(sessions, "_rng", random.Random(7))
    return client


def _auth(client, email="apt@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _start(client, h, **body):
    body.setdefault("mode", "topic")
    if body["mode"] == "topic" and "topic_ids" not in body and "subtopic_ids" not in body:
        body["topic_ids"] = ["number-system"]
    return client.post(f"{URL}/sessions", json=body, headers=h)


def _raw(db, sid):
    return db[Collections.APTITUDE_SESSIONS].find_one({"_id": ObjectId(sid)})


def _displayed_correct(db, sid, qid):
    """Test-only: look up which displayed option is correct, straight from the database."""
    s = _raw(db, sid)
    order = next(q["option_order"] for q in s["questions"] if q["question_id"] == qid)
    correct = db[Collections.APTITUDE_QUESTIONS].find_one({"question_id": qid})["correct_index"]
    return order.index(correct)


def _answer(client, h, sid, qid, index, **extra):
    return client.put(f"{URL}/sessions/{sid}/answers/{qid}", json={"selected_index": index, **extra}, headers=h)


def _play(client, db, h, sid, qids, pattern):
    """pattern: list of 'c' (correct) / 'w' (wrong) / 'u' (skip), per question."""
    for qid, p in zip(qids, pattern):
        if p == "u":
            continue
        good = _displayed_correct(db, sid, qid)
        assert _answer(client, h, sid, qid, good if p == "c" else (good + 1) % 4).status_code == 200


def _qids(body):
    return [q["question_id"] for q in body["data"]["questions"]]


# --- Auth and public surface ------------------------------------------------------------------


class TestAuthAndListing:
    @pytest.mark.parametrize("method,path", [
        ("get", "/syllabus"), ("get", "/questions"), ("post", "/sessions"), ("get", "/sessions"), ("get", "/progress"), ("get", "/recommendations"),
        ("get", f"/sessions/{'a' * 24}"), ("get", f"/sessions/{'a' * 24}/result"), ("post", f"/sessions/{'a' * 24}/submit"),
        ("put", f"/sessions/{'a' * 24}/answers/apt-0123456789"),
    ])
    def test_every_endpoint_requires_authentication(self, apt, method, path):
        assert getattr(apt, method)(f"{URL}{path}").status_code == 401

    def test_syllabus_payload(self, apt):
        r = apt.get(f"{URL}/syllabus", headers=_auth(apt))
        data = r.json()["data"]
        assert r.status_code == 200 and data["totals"]["topics"] == 26 and data["totals"]["subtopics"] == 88
        assert all("subtopics" in t and "items" in t for t in data["topics"])

    def test_question_listing_has_no_answers(self, apt):
        h = _auth(apt)
        r = apt.get(f"{URL}/questions?topic_id=percentage&limit=50", headers=h)
        items = r.json()["data"]["items"]
        assert r.status_code == 200 and items and all(not (set(i) & LEAK) for i in items)
        assert set(items[0]) == {"question_id", "topic_id", "subtopic_id", "question_type", "difficulty", "statement", "options", "est_time_seconds", "data"}

    def test_listing_filters_pagination_and_validation(self, apt):
        h = _auth(apt)
        r = apt.get(f"{URL}/questions?difficulty=hard&question_type=multi_step&limit=5&page=1", headers=h).json()["data"]
        assert all(i["difficulty"] == "hard" and i["question_type"] == "multi_step" for i in r["items"]) and r["limit"] == 5
        for bad in ("limit=0", "limit=51", "page=0", "difficulty=extreme", "topic_id=Bad_ID!", "question_type=x", "subtopic_id=../etc"):
            assert apt.get(f"{URL}/questions?{bad}", headers=h).status_code == 422, bad

    def test_filter_cannot_inject_a_query(self, apt):
        h = _auth(apt)
        assert apt.get(f"{URL}/questions?topic_id[$ne]=x", headers=h).status_code in (200, 422)
        r = apt.get(f"{URL}/questions", params={"topic_id": '{"$ne": ""}'}, headers=h)
        assert r.status_code == 422


# --- Creating sessions ------------------------------------------------------------------------


class TestCreateSession:
    def test_topic_session_hides_answers_and_stores_a_shuffle(self, apt, fake_db):
        h = _auth(apt)
        r = _start(apt, h, question_count=6, difficulty="easy")
        body = r.json()
        assert r.status_code == 201 and body["data"]["question_count"] == 6
        for q in body["data"]["questions"]:
            assert not (set(q) & {"correct_index", "explanation", "formula"}) and q["feedback"] is None and q["difficulty"] == "easy"
            assert len(set(q["options"])) == 4
        raw = _raw(fake_db, body["data"]["session_id"])
        assert all(sorted(q["option_order"]) == [0, 1, 2, 3] for q in raw["questions"])
        assert any(q["option_order"] != [0, 1, 2, 3] for q in raw["questions"])
        assert str(raw["user_id"]) == str(fake_db[Collections.USERS].find_one({"email": "apt@example.com"})["_id"])

    def test_displayed_options_are_a_permutation_of_the_stored_ones(self, apt, fake_db):
        h = _auth(apt)
        body = _start(apt, h, question_count=5).json()["data"]
        for q in body["questions"]:
            stored = fake_db[Collections.APTITUDE_QUESTIONS].find_one({"question_id": q["question_id"]})["options"]
            assert sorted(q["options"]) == sorted(stored)

    def test_topic_mode_requires_a_topic(self, apt):
        r = apt.post(f"{URL}/sessions", json={"mode": "topic", "question_count": 5}, headers=_auth(apt))
        assert r.status_code == 422 and r.json()["error_code"] == "TOPIC_REQUIRED"

    def test_unknown_or_mismatched_ids_are_rejected(self, apt):
        h = _auth(apt)
        assert _start(apt, h, topic_ids=["nope"]).json()["error_code"] == "UNKNOWN_TOPIC"
        assert _start(apt, h, mode="topic", subtopic_ids=["nope"]).json()["error_code"] == "UNKNOWN_SUBTOPIC"
        assert _start(apt, h, topic_ids=["calendar"], subtopic_ids=["unit-digit"]).json()["error_code"] == "SUBTOPIC_TOPIC_MISMATCH"

    def test_fewer_questions_than_requested_is_reported_honestly(self, apt):
        r = _start(apt, _auth(apt), mode="topic", subtopic_ids=["unit-digit"], question_count=50).json()["data"]
        assert r["requested_count"] == 50 and 0 < r["question_count"] < 50

    def test_empty_selection_is_a_clean_conflict(self, apt, fake_db):
        fake_db[Collections.APTITUDE_QUESTIONS].update_many({"topic_id": "clocks"}, {"$set": {"status": "inactive"}})
        r = _start(apt, _auth(apt), topic_ids=["clocks"])
        assert r.status_code == 409 and r.json()["error_code"] == "NO_QUESTIONS"

    @pytest.mark.parametrize("body", [
        {"mode": "topic", "question_count": 0}, {"mode": "topic", "question_count": 61}, {"mode": "mixed", "timer_minutes": 0}, {"mode": "mixed", "timer_minutes": 181},
        {"mode": "bogus"}, {"mode": "mixed", "difficulty": "insane"}, {"mode": "mixed", "topic_ids": ["Bad ID"]}, {"mode": "mixed", "topic_ids": ["a"] * 27}, {},
    ])
    def test_invalid_requests_are_rejected(self, apt, body):
        assert apt.post(f"{URL}/sessions", json=body, headers=_auth(apt)).status_code == 422

    def test_scenario_mode_only_serves_scenario_style_questions(self, apt, fake_db):
        body = _start(apt, _auth(apt), mode="scenario", question_count=15).json()["data"]
        assert body["question_count"] == 15
        types = {fake_db[Collections.APTITUDE_QUESTIONS].find_one({"question_id": q["question_id"]})["question_type"] for q in body["questions"]}
        assert types <= {"scenario", "multi_step"}

    def test_mixed_mode_spreads_across_topics(self, apt):
        body = _start(apt, _auth(apt), mode="mixed", question_count=20).json()["data"]
        assert len({q["topic_id"] for q in body["questions"]}) >= 12

    def test_questions_within_a_session_are_unique(self, apt):
        qids = _qids(_start(apt, _auth(apt), mode="mixed", question_count=40).json())
        assert len(qids) == len(set(qids)) == 40

    def test_timed_mock_defaults_and_rules(self, apt):
        h = _auth(apt)
        body = _start(apt, h, mode="timed_mock", question_count=10).json()["data"]
        assert body["exam_mode"] and not body["immediate_feedback"] and body["timer_minutes"] == 15
        assert body["expires_at"] and 0 < body["remaining_seconds"] <= 900
        bad = _start(apt, h, mode="timed_mock", question_count=5, immediate_feedback=True)
        assert bad.status_code == 422 and bad.json()["error_code"] == "FEEDBACK_NOT_ALLOWED"

    def test_prefers_questions_the_user_has_not_seen(self, apt):
        h = _auth(apt)
        first = _start(apt, h, mode="topic", subtopic_ids=["number-series"], question_count=4).json()["data"]
        sid = first["session_id"]
        apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        second = _start(apt, h, mode="topic", subtopic_ids=["number-series"], question_count=4).json()["data"]
        assert not ({q["question_id"] for q in first["questions"]} & {q["question_id"] for q in second["questions"]}) or second["question_count"] < 8

    def test_open_session_cap(self, apt, monkeypatch):
        monkeypatch.setattr(sessions, "MAX_OPEN_SESSIONS", 2)
        h = _auth(apt)
        assert _start(apt, h).status_code == 201 and _start(apt, h).status_code == 201
        r = _start(apt, h)
        assert r.status_code == 409 and r.json()["error_code"] == "TOO_MANY_OPEN_SESSIONS"

    def test_creation_is_rate_limited(self, apt):
        h = _auth(apt)
        codes = [_start(apt, h, question_count=1).status_code for _ in range(17)]
        assert codes.count(201) == 15 and codes[-1] == 429
        r = _start(apt, h)
        assert r.status_code == 429 and r.json()["error_code"] == "RATE_LIMITED" and "retry-after" in r.headers


# --- Answers ------------------------------------------------------------------------------------


class TestAnswers:
    def _session(self, apt, fake_db, **body):
        h = _auth(apt)
        data = _start(apt, h, question_count=body.pop("question_count", 5), **body).json()["data"]
        return h, data["session_id"], [q["question_id"] for q in data["questions"]]

    def test_exam_mode_never_reveals_anything_before_submit(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db, mode="timed_mock")
        r = _answer(apt, h, sid, qids[0], 1).json()["data"]
        assert r["feedback"] is None and r["locked"] is False
        resumed = apt.get(f"{URL}/sessions/{sid}", headers=h)
        assert all(not (set(q) & {"correct_index", "explanation", "formula"}) and q["feedback"] is None for q in resumed.json()["data"]["questions"])
        assert apt.get(f"{URL}/sessions/{sid}/result", headers=h).status_code == 409

    def test_answers_can_be_changed_until_submission_in_exam_mode(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db, mode="timed_mock")
        _answer(apt, h, sid, qids[0], 0)
        _answer(apt, h, sid, qids[0], 2, marked_for_review=True)
        q = apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]
        assert q["selected_index"] == 2 and q["marked_for_review"] is True
        _answer(apt, h, sid, qids[0], None)
        assert apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]["selected_index"] is None

    def test_immediate_feedback_reveals_one_answer_and_locks_it(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db, mode="topic", topic_ids=["number-system"], immediate_feedback=True)
        good = _displayed_correct(fake_db, sid, qids[0])
        r = _answer(apt, h, sid, qids[0], (good + 1) % 4).json()["data"]
        assert r["locked"] and r["feedback"]["is_correct"] is False and r["feedback"]["correct_index"] == good and r["feedback"]["explanation"]
        again = _answer(apt, h, sid, qids[0], good)
        assert again.status_code == 409 and again.json()["error_code"] == "ANSWER_LOCKED"
        assert apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]["feedback"]["correct_index"] == good
        assert apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][1]["feedback"] is None

    def test_forged_fields_in_the_body_are_ignored(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db, mode="timed_mock")
        good = _displayed_correct(fake_db, sid, qids[0])
        r = apt.put(f"{URL}/sessions/{sid}/answers/{qids[0]}", headers=h, json={"selected_index": (good + 1) % 4, "is_correct": True, "correct_index": (good + 1) % 4, "score": 99, "user_id": "x"})
        assert r.status_code == 200
        res = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert res["score"] == 0 and res["incorrect"] == 1

    @pytest.mark.parametrize("body", [{"selected_index": 4}, {"selected_index": -1}, {"selected_index": "a"}, {"selected_index": 1, "time_spent_seconds": -5}, {"selected_index": 1, "time_spent_seconds": 99999}])
    def test_invalid_answers_are_rejected(self, apt, fake_db, body):
        h, sid, qids = self._session(apt, fake_db)
        assert apt.put(f"{URL}/sessions/{sid}/answers/{qids[0]}", json=body, headers=h).status_code == 422

    def test_question_must_belong_to_the_session(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db, mode="topic", topic_ids=["clocks"])
        other = fake_db[Collections.APTITUDE_QUESTIONS].find_one({"topic_id": "calendar"})["question_id"]
        r = _answer(apt, h, sid, other, 0)
        assert r.status_code == 422 and r.json()["error_code"] == "QUESTION_NOT_IN_SESSION"
        assert apt.put(f"{URL}/sessions/{sid}/answers/not-an-id", json={"selected_index": 0}, headers=h).status_code == 422

    def test_cannot_answer_after_submission(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db)
        apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        r = _answer(apt, h, sid, qids[0], 0)
        assert r.status_code == 409 and r.json()["error_code"] == "SESSION_COMPLETED"

    def test_reported_time_is_clamped_to_the_server_clock(self, apt, fake_db):
        h, sid, qids = self._session(apt, fake_db)
        _answer(apt, h, sid, qids[0], 0, time_spent_seconds=3000)
        assert _raw(fake_db, sid)["answers"][qids[0]]["time_spent"] <= 2


# --- Scoring and finalisation ---------------------------------------------------------------


class TestScoring:
    def test_server_side_score_and_breakdown(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=10).json()["data"]
        sid, qids = data["session_id"], [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, sid, qids, list("cccwwu" "cuuu"))
        r = apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        res = r.json()["data"]
        assert r.status_code == 200
        assert (res["total_questions"], res["correct"], res["incorrect"], res["unanswered"], res["score"]) == (10, 4, 2, 4, 4)
        assert res["accuracy"] == 40.0 and res["correct"] + res["incorrect"] + res["unanswered"] == 10
        assert sum(t["total"] for t in res["topic_performance"]) == 10 and sum(t["correct"] for t in res["topic_performance"]) == 4
        assert "no negative marking" in res["scoring_policy"]
        by_q = {q["question_id"]: q for q in res["questions"]}
        assert by_q[qids[0]]["outcome"] == "correct" and by_q[qids[3]]["outcome"] == "incorrect" and by_q[qids[5]]["outcome"] == "unanswered"
        for q in res["questions"]:
            assert q["explanation"] and 0 <= q["correct_index"] <= 3
            assert q["options"][q["correct_index"]] in q["explanation"]
            if q["outcome"] == "correct":
                assert q["selected_index"] == q["correct_index"]

    def test_revision_topics_list_only_weak_ones(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=8).json()["data"]
        sid, qids = data["session_id"], [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, sid, qids, list("cccccccc"))
        assert apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]["revision_topics"] == []
        data = _start(apt, h, mode="mixed", question_count=8).json()["data"]
        sid, qids = data["session_id"], [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, sid, qids, list("wwwwwwww"))
        rev = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]["revision_topics"]
        assert rev and all(r["accuracy"] < 70 and r["subtopics"] for r in rev)

    def test_submit_is_idempotent_and_records_attempts_once(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=6).json()["data"]
        sid, qids = data["session_id"], [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, sid, qids, list("cwcwcw"))
        first = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        second = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        third = apt.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert first["score"] == second["score"] == third["score"] == 3
        assert first["finished_at"] == second["finished_at"]
        assert fake_db[Collections.APTITUDE_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 6
        progress = apt.get(f"{URL}/progress", headers=h).json()["data"]
        assert progress["sessions_completed"] == 1 and progress["questions_presented"] == 6

    def test_lost_finalise_race_does_not_double_count(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=5).json()["data"]
        sid = data["session_id"]
        uid = str(fake_db[Collections.USERS].find_one({"email": "apt@example.com"})["_id"])
        for _ in range(3):  # three "simultaneous" calls through the service layer
            sessions.finalize(fake_db, uid, sid)
        assert fake_db[Collections.APTITUDE_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 5

    def test_half_finished_finalise_is_repaired(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=5).json()["data"]
        sid = data["session_id"]
        fake_db[Collections.APTITUDE_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"status": "completed", "finished_at": datetime.now(UTC)}})  # crashed before result/attempts
        res = apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        assert res.status_code == 200 and res.json()["data"]["unanswered"] == 5
        assert fake_db[Collections.APTITUDE_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 5

    def test_empty_submission_is_scored_zero(self, apt):
        h = _auth(apt)
        sid = _start(apt, h, question_count=4).json()["data"]["session_id"]
        res = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert res["score"] == 0 and res["unanswered"] == 4 and res["accuracy"] == 0

    def test_time_taken_is_measured_by_the_server(self, apt, fake_db):
        h = _auth(apt)
        sid = _start(apt, h, question_count=4).json()["data"]["session_id"]
        fake_db[Collections.APTITUDE_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"started_at": datetime.now(UTC) - timedelta(seconds=120)}})
        res = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert 118 <= res["time_taken_seconds"] <= 125 and res["average_seconds_per_question"] == pytest.approx(res["time_taken_seconds"] / 4, abs=0.1)


# --- Timer ----------------------------------------------------------------------------------


class TestExpiry:
    def _mock(self, apt, fake_db, count=5, minutes=10):
        h = _auth(apt)
        data = _start(apt, h, mode="timed_mock", question_count=count, timer_minutes=minutes).json()["data"]
        return h, data["session_id"], [q["question_id"] for q in data["questions"]]

    def _expire(self, fake_db, sid, seconds_ago):
        now = datetime.now(UTC)
        fake_db[Collections.APTITUDE_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"started_at": now - timedelta(minutes=10, seconds=seconds_ago), "expires_at": now - timedelta(seconds=seconds_ago)}})

    def test_expired_session_is_auto_submitted_with_saved_answers(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        _play(apt, fake_db, h, sid, qids, list("ccw"))
        self._expire(fake_db, sid, 60)
        body = apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
        assert body["status"] == "completed" and body["remaining_seconds"] == 0
        res = apt.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert res["auto_submitted"] is True and (res["correct"], res["incorrect"], res["unanswered"]) == (2, 1, 2)
        assert res["time_taken_seconds"] == 600  # capped at the duration, not the 60 s overrun

    def test_answers_after_expiry_are_refused_and_trigger_submission(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        self._expire(fake_db, sid, 60)
        r = _answer(apt, h, sid, qids[0], 0)
        assert r.status_code == 409 and r.json()["error_code"] == "SESSION_EXPIRED"
        assert _raw(fake_db, sid)["status"] == "completed" and _raw(fake_db, sid)["auto_submitted"] is True
        assert fake_db[Collections.APTITUDE_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 5

    def test_last_second_answer_inside_grace_is_accepted(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        self._expire(fake_db, sid, 1)
        assert _answer(apt, h, sid, qids[0], 0).status_code == 200

    def test_manual_submit_after_expiry_is_flagged_auto(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        self._expire(fake_db, sid, 30)
        res = apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert res["auto_submitted"] is True and res["time_taken_seconds"] <= 600

    def test_expired_sessions_are_swept_when_starting_a_new_one(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        self._expire(fake_db, sid, 120)
        _start(apt, h)
        assert _raw(fake_db, sid)["status"] == "completed"

    def test_untimed_sessions_never_expire(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h).json()["data"]
        assert data["expires_at"] is None and data["remaining_seconds"] is None
        fake_db[Collections.APTITUDE_SESSIONS].update_one({"_id": ObjectId(data["session_id"])}, {"$set": {"started_at": datetime.now(UTC) - timedelta(days=3)}})
        assert apt.get(f"{URL}/sessions/{data['session_id']}", headers=h).json()["data"]["status"] == "in_progress"

    def test_resuming_returns_remaining_time_and_saved_answers(self, apt, fake_db):
        h, sid, qids = self._mock(apt, fake_db)
        _answer(apt, h, sid, qids[1], 3, marked_for_review=True)
        body = apt.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
        assert body["questions"][1]["selected_index"] == 3 and body["questions"][1]["marked_for_review"]
        assert 0 < body["remaining_seconds"] <= 600 and body["server_time"]


# --- Ownership and isolation ------------------------------------------------------------------


class TestIsolation:
    def test_other_users_cannot_touch_a_session(self, apt, fake_db):
        a, b = _auth(apt, "a@example.com"), _auth(apt, "b@example.com")
        data = _start(apt, a, question_count=4).json()["data"]
        sid, qid = data["session_id"], data["questions"][0]["question_id"]
        apt.post(f"{URL}/sessions/{sid}/submit", headers=a)
        for r in (apt.get(f"{URL}/sessions/{sid}", headers=b), apt.get(f"{URL}/sessions/{sid}/result", headers=b), apt.post(f"{URL}/sessions/{sid}/submit", headers=b), _answer(apt, b, sid, qid, 0)):
            assert r.status_code == 404 and r.json()["error_code"] == "NOT_FOUND"

    def test_missing_and_foreign_sessions_look_identical(self, apt):
        a, b = _auth(apt, "a@example.com"), _auth(apt, "b@example.com")
        sid = _start(apt, a).json()["data"]["session_id"]
        foreign = apt.get(f"{URL}/sessions/{sid}", headers=b)
        missing = apt.get(f"{URL}/sessions/{'0' * 24}", headers=b)
        assert foreign.status_code == missing.status_code == 404 and foreign.json() == missing.json()

    def test_malformed_session_ids_are_rejected(self, apt):
        h = _auth(apt)
        for bad in ("123", "z" * 24, "../etc/passwd", "A" * 24):
            assert apt.get(f"{URL}/sessions/{bad}", headers=h).status_code in (404, 422)

    def test_history_and_progress_are_per_user(self, apt, fake_db):
        a, b = _auth(apt, "a@example.com"), _auth(apt, "b@example.com")
        data = _start(apt, a, question_count=5, mode="mixed").json()["data"]
        _play(apt, fake_db, a, data["session_id"], [q["question_id"] for q in data["questions"]], list("ccccc"))
        apt.post(f"{URL}/sessions/{data['session_id']}/submit", headers=a)
        assert apt.get(f"{URL}/sessions", headers=b).json()["data"]["total"] == 0
        pb = apt.get(f"{URL}/progress", headers=b).json()["data"]
        assert pb["sessions_completed"] == 0 and pb["questions_presented"] == 0 and pb["recent_sessions"] == []
        assert apt.get(f"{URL}/progress", headers=a).json()["data"]["correct"] == 5

    def test_user_id_in_the_body_is_never_trusted(self, apt, fake_db):
        a, b = _auth(apt, "a@example.com"), _auth(apt, "b@example.com")
        b_id = str(fake_db[Collections.USERS].find_one({"email": "b@example.com"})["_id"])
        r = apt.post(f"{URL}/sessions", json={"mode": "mixed", "question_count": 3, "user_id": b_id}, headers=a)
        assert r.status_code == 201
        assert apt.get(f"{URL}/sessions", headers=b).json()["data"]["total"] == 0 and apt.get(f"{URL}/sessions", headers=a).json()["data"]["total"] == 1


# --- Progress, history and weak topics ---------------------------------------------------------


class TestProgressAndWeakTopics:
    def _finish(self, apt, db, h, pattern, **body):
        data = _start(apt, h, **{"question_count": len(pattern), **body}).json()["data"]
        sid = data["session_id"]
        _play(apt, db, h, sid, [q["question_id"] for q in data["questions"]], pattern)
        return apt.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]

    def test_empty_progress_has_no_invented_data(self, apt):
        p = apt.get(f"{URL}/progress", headers=_auth(apt)).json()["data"]
        assert p["sessions_completed"] == 0 and p["questions_answered"] == 0 and p["accuracy"] == 0 and p["topic_accuracy"] == [] and p["trend"] == []
        assert p["improvement_points"] is None and p["average_seconds_per_question"] is None and p["weak_topics"] == []

    def test_progress_aggregates_real_attempts(self, apt, fake_db):
        h = _auth(apt)
        self._finish(apt, fake_db, h, list("ccww"), mode="topic", topic_ids=["number-system"])
        self._finish(apt, fake_db, h, list("cuuu"), mode="topic", topic_ids=["percentage"])
        p = apt.get(f"{URL}/progress", headers=h).json()["data"]
        assert (p["sessions_completed"], p["questions_presented"], p["questions_answered"], p["correct"], p["incorrect"], p["unanswered"]) == (2, 8, 5, 3, 2, 3)
        assert p["accuracy"] == 60.0
        topics = {t["topic_id"]: t for t in p["topic_accuracy"]}
        assert topics["number-system"]["accuracy"] == 50.0 and topics["percentage"]["answered"] == 1 and topics["percentage"]["presented"] == 4
        assert len(p["recent_sessions"]) == 2 and p["recent_sessions"][0]["finished_at"] >= p["recent_sessions"][1]["finished_at"]
        assert sum(d["answered"] for d in p["difficulty_accuracy"]) == 5

    def test_improvement_compares_early_and_late_sessions(self, apt, fake_db):
        h = _auth(apt)
        for pattern in ("wwww", "wwwc", "cccw", "cccc"):
            self._finish(apt, fake_db, h, list(pattern), mode="mixed")
        p = apt.get(f"{URL}/progress", headers=h).json()["data"]
        assert [round(t["accuracy"]) for t in p["trend"]] == [0, 25, 75, 100] and p["improvement_points"] == 75.0

    def test_history_is_paginated_newest_first(self, apt, fake_db):
        h = _auth(apt)
        for _ in range(3):
            self._finish(apt, fake_db, h, list("cc"), mode="mixed")
        page = apt.get(f"{URL}/sessions?limit=2&page=1", headers=h).json()["data"]
        assert page["total"] == 3 and len(page["items"]) == 2 and page["has_next"] and page["items"][0]["score"] == 2
        assert len(apt.get(f"{URL}/sessions?limit=2&page=2", headers=h).json()["data"]["items"]) == 1
        assert apt.get(f"{URL}/sessions?limit=51", headers=h).status_code == 422

    def test_weak_mode_without_history_is_refused(self, apt):
        r = _start(apt, _auth(apt), mode="weak")
        assert r.status_code == 409 and r.json()["error_code"] == "NO_HISTORY"
        rec = apt.get(f"{URL}/recommendations", headers=_auth(apt, "x@example.com")).json()["data"]
        assert rec["has_history"] is False and rec["weak_topics"] == [] and "Complete a few practice sessions" in rec["message"]

    def test_weak_topic_requires_enough_answers(self, apt, fake_db):
        h = _auth(apt)
        self._finish(apt, fake_db, h, list("www"), mode="topic", topic_ids=["clocks"])  # only 3 answered -> not enough evidence
        assert apt.get(f"{URL}/recommendations", headers=h).json()["data"]["weak_topics"] == []

    def test_weak_topics_are_detected_from_verified_performance(self, apt, fake_db):
        h = _auth(apt)
        self._finish(apt, fake_db, h, list("wwwwww"), mode="topic", topic_ids=["number-system"], question_count=6)
        self._finish(apt, fake_db, h, list("cccccc"), mode="topic", topic_ids=["percentage"], question_count=6)
        rec = apt.get(f"{URL}/recommendations", headers=h).json()["data"]
        assert [w["topic_id"] for w in rec["weak_topics"]] == ["number-system"]
        assert rec["weak_topics"][0]["accuracy"] == 0.0 and rec["weak_topics"][0]["answered"] == 6 and rec["weak_topics"][0]["reason"]
        assert rec["incorrect_question_count"] == 6

    def test_weak_session_targets_incorrect_questions_and_weak_topics_only(self, apt, fake_db):
        h = _auth(apt)
        wrong = self._finish(apt, fake_db, h, list("wwwwww"), mode="topic", topic_ids=["number-system"], question_count=6)
        wrong_ids = {q["question_id"] for q in wrong["questions"]}
        self._finish(apt, fake_db, h, list("cccccc"), mode="topic", topic_ids=["percentage"], question_count=6)
        data = _start(apt, h, mode="weak", question_count=10).json()["data"]
        qids = [q["question_id"] for q in data["questions"]]
        assert wrong_ids <= set(qids[:6]) and {q["topic_id"] for q in data["questions"]} == {"number-system"}

    def test_fixed_mistakes_leave_the_weak_pool(self, apt, fake_db):
        h = _auth(apt)
        first = self._finish(apt, fake_db, h, list("wwwwww"), mode="topic", topic_ids=["clocks"], question_count=6)
        ids = [q["question_id"] for q in first["questions"]]
        data = _start(apt, h, mode="weak", question_count=6).json()["data"]
        redo = [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, data["session_id"], redo, list("c" * len(redo)))
        apt.post(f"{URL}/sessions/{data['session_id']}/submit", headers=h)
        rec = apt.get(f"{URL}/recommendations", headers=h).json()["data"]
        assert rec["incorrect_question_count"] == 0 and set(ids) >= set(redo)

    def test_weak_mode_with_nothing_weak_is_a_clean_conflict(self, apt, fake_db):
        h = _auth(apt)
        self._finish(apt, fake_db, h, list("cccccc"), mode="mixed", question_count=6)
        r = _start(apt, h, mode="weak")
        assert r.status_code == 409 and r.json()["error_code"] == "NO_WEAK_AREAS"


# --- History Center integration -------------------------------------------------------------


class TestHistoryCenter:
    def test_completed_session_appears_in_the_shared_history(self, apt, fake_db):
        h = _auth(apt)
        data = _start(apt, h, mode="mixed", question_count=4).json()["data"]
        sid, qids = data["session_id"], [q["question_id"] for q in data["questions"]]
        _play(apt, fake_db, h, sid, qids, list("ccwu"))
        apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        listing = apt.get("/api/v1/history?type=aptitude", headers=h).json()["data"]
        item = listing["items"][0]
        assert item["type"] == "aptitude" and item["id"] == sid and item["status"] == "completed" and item["score"] == 50
        assert item["metadata"]["question_count"] == 4 and item["title"] == "Mixed Practice"
        summary = apt.get("/api/v1/history/summary", headers=h).json()["data"]
        assert {"type": "aptitude", "label": "Aptitude", "count": 1}.items() <= next(t for t in summary["types"] if t["type"] == "aptitude").items()

    def test_history_detail_returns_the_result_only_after_submission(self, apt, fake_db):
        h = _auth(apt)
        sid = _start(apt, h, mode="timed_mock", question_count=3).json()["data"]["session_id"]
        mid = apt.get(f"/api/v1/history/aptitude/{sid}", headers=h).json()["data"]["detail"]
        assert "questions" in mid and all(not (set(q) & {"correct_index", "explanation"}) for q in mid["questions"])
        apt.post(f"{URL}/sessions/{sid}/submit", headers=h)
        done = apt.get(f"/api/v1/history/aptitude/{sid}", headers=h).json()["data"]["detail"]
        assert all("explanation" in q and "correct_index" in q for q in done["questions"])

    def test_history_detail_is_owner_only(self, apt):
        a, b = _auth(apt, "a@example.com"), _auth(apt, "b@example.com")
        sid = _start(apt, a).json()["data"]["session_id"]
        assert apt.get(f"/api/v1/history/aptitude/{sid}", headers=b).status_code == 404
        assert apt.get("/api/v1/history?type=aptitude", headers=b).json()["data"]["total"] == 0
