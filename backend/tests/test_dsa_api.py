"""Phase 24 -- DSA sessions: modes, scoring, expiry, idempotency, ownership, answer-key isolation, analytics, history."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from app.core.rate_limit import reset_rate_limits
from app.db.collections import Collections
from app.services.dsa import bank, sessions
from tests.test_communication import _register_and_login

URL = "/api/v1/dsa"
SECRET_KEYS = {"correct_index", "explanation", "verification", "fingerprint", "is_correct", "reference_solution", "test_cases", "trace", "complexity", "content_hash"}


@pytest.fixture()
def dsa(client, fake_db, monkeypatch):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    reset_rate_limits()
    monkeypatch.setattr(sessions, "_rng", random.Random(11))
    return client


def _auth(client, email="dsa@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _start(client, h, **body):
    body.setdefault("mode", "topic")
    if body["mode"] == "topic" and "topic_ids" not in body and "subtopic_ids" not in body:
        body["topic_ids"] = ["sorting-searching"]
    return client.post(f"{URL}/sessions", json=body, headers=h)


def _raw(db, sid):
    return db[Collections.DSA_SESSIONS].find_one({"_id": ObjectId(sid)})


def _displayed_correct(db, sid, qid):
    s = _raw(db, sid)
    order = next(q["option_order"] for q in s["questions"] if q["question_id"] == qid)
    return order.index(db[Collections.DSA_QUESTIONS].find_one({"question_id": qid})["correct_index"])


def _answer(client, h, sid, qid, index=None, **extra):
    body = {**({"selected_index": index} if index is not None else {}), **extra}
    return client.put(f"{URL}/sessions/{sid}/answers/{qid}", json=body, headers=h)


def _play(client, db, h, sid, qids, pattern):
    for qid, p in zip(qids, pattern):
        if p == "u":
            continue
        good = _displayed_correct(db, sid, qid)
        assert _answer(client, h, sid, qid, good if p == "c" else (good + 1) % 4).status_code == 200


def _qids(resp):
    return [q["question_id"] for q in resp.json()["data"]["questions"]]


def _doc(db, qid):
    return db[Collections.DSA_QUESTIONS].find_one({"question_id": qid})


class TestAuthAndListing:
    @pytest.mark.parametrize("method,path", [
        ("get", "/syllabus"), ("get", "/questions"), ("post", "/sessions"), ("get", "/sessions"), ("get", "/progress"), ("get", "/recommendations"),
        ("get", f"/sessions/{'a' * 24}"), ("get", f"/sessions/{'a' * 24}/result"), ("post", f"/sessions/{'a' * 24}/submit"),
        ("put", f"/sessions/{'a' * 24}/answers/dsa-0123456789"), ("put", f"/sessions/{'a' * 24}/self-assessment/dsa-0123456789"),
    ])
    def test_every_endpoint_requires_authentication(self, dsa, method, path):
        assert getattr(dsa, method)(f"{URL}{path}").status_code == 401

    def test_there_is_no_run_code_endpoint(self, dsa):
        h = _auth(dsa)
        for path in ("/run", "/execute", "/sessions/" + "a" * 24 + "/run", "/sessions/" + "a" * 24 + "/execute"):
            assert dsa.post(f"{URL}{path}", json={"code": "print(1)"}, headers=h).status_code in (404, 405)

    def test_syllabus_payload_is_honest(self, dsa):
        d = dsa.get(f"{URL}/syllabus", headers=_auth(dsa)).json()["data"]
        assert d["totals"]["topics"] == 10 and d["totals"]["subtopics"] == 54 and d["totals"]["subtopics_implemented"] == 54
        assert d["execution"]["automated_code_execution"] is False and "not run" in d["execution"]["message"]
        assert all(s["question_count"] >= 4 for t in d["topics"] for s in t["subtopics"])

    def test_question_listing_has_no_answers(self, dsa):
        r = dsa.get(f"{URL}/questions?topic_id=graphs&limit=50", headers=_auth(dsa)).json()["data"]
        assert r["items"] and all(not (set(i) & SECRET_KEYS) for i in r["items"])
        assert set(r["items"][0]) == {"question_id", "topic_id", "subtopic_id", "format", "interaction", "coding_type", "difficulty", "statement", "code", "options", "constraints", "est_time_seconds", "coding"}

    def test_coding_listing_hides_reference_and_hidden_tests(self, dsa):
        items = dsa.get(f"{URL}/questions?format=coding&limit=50", headers=_auth(dsa)).json()["data"]["items"]
        code = [i for i in items if i["interaction"] == "code"]
        assert code
        for i in code:
            assert set(i["coding"]) == {"function_name", "template", "sample_io", "visible_tests", "hidden_test_count"} and i["coding"]["hidden_test_count"] >= 1
            assert i["options"] == [] and all(set(t) == {"label", "args", "expected"} for t in i["coding"]["visible_tests"])

    def test_validation_of_filters(self, dsa):
        h = _auth(dsa)
        for bad in ("limit=0", "limit=51", "page=0", "difficulty=extreme", "topic_id=Bad_ID!", "format=essay", "subtopic_id=../etc"):
            assert dsa.get(f"{URL}/questions?{bad}", headers=h).status_code == 422, bad
        assert dsa.get(f"{URL}/questions", params={"topic_id": '{"$ne": ""}'}, headers=h).status_code == 422


class TestCreateSessions:
    def test_topic_mode_requires_a_topic(self, dsa):
        assert dsa.post(f"{URL}/sessions", json={"mode": "topic"}, headers=_auth(dsa)).json()["error_code"] == "TOPIC_REQUIRED"

    def test_unknown_and_mismatched_filters(self, dsa):
        h = _auth(dsa)
        assert _start(dsa, h, topic_ids=["nope"]).json()["error_code"] == "UNKNOWN_TOPIC"
        assert _start(dsa, h, mode="interview", subtopic_ids=["nope"]).json()["error_code"] == "UNKNOWN_SUBTOPIC"
        assert _start(dsa, h, mode="interview", topic_ids=["graphs"], subtopic_ids=["bubble-sort"]).json()["error_code"] == "SUBTOPIC_TOPIC_MISMATCH"

    @pytest.mark.parametrize("bad", [{"question_count": 0}, {"question_count": 51}, {"timer_minutes": 0}, {"timer_minutes": 999}, {"mode": "bogus"}, {"difficulty": "extreme"}])
    def test_request_validation(self, dsa, bad):
        assert _start(dsa, _auth(dsa), **{"mode": "interview", **bad}).status_code == 422

    def test_topic_practice_filters_topic_difficulty_and_count(self, dsa, fake_db):
        r = _start(dsa, _auth(dsa), mode="topic", topic_ids=["graphs"], difficulty="medium", question_count=6)
        assert r.status_code == 201
        d = r.json()["data"]
        assert d["question_count"] == 6 and all(q["topic_id"] == "graphs" and q["difficulty"] == "medium" and q["interaction"] == "mcq" for q in d["questions"])
        assert d["exam_mode"] is False and d["immediate_feedback"] is True

    def test_subtopic_selection(self, dsa):
        d = _start(dsa, _auth(dsa), mode="topic", subtopic_ids=["bfs"], question_count=5).json()["data"]
        assert {q["subtopic_id"] for q in d["questions"]} == {"bfs"}

    def test_no_questions_for_filters_is_a_clear_conflict(self, dsa, fake_db):
        fake_db[Collections.DSA_QUESTIONS].update_many({"subtopic_id": "bfs"}, {"$set": {"status": "inactive"}})
        r = _start(dsa, _auth(dsa), mode="topic", subtopic_ids=["bfs"])
        assert r.status_code == 409 and r.json()["error_code"] == "NO_QUESTIONS"

    def test_mode_formats(self, dsa):
        h = _auth(dsa)
        expect = {"interview": {"conceptual", "scenario", "complexity"}, "tracing": {"trace", "output"}, "complexity": {"complexity"}}
        for mode, fmts in expect.items():
            qs = _start(dsa, h, mode=mode, question_count=15).json()["data"]["questions"]
            assert qs and {q["format"] for q in qs} <= fmts and all(q["interaction"] == "mcq" for q in qs), mode

    def test_interview_mode_mixes_direct_and_scenario(self, dsa):
        qs = _start(dsa, _auth(dsa), mode="interview", question_count=40).json()["data"]["questions"]
        assert {"conceptual", "scenario"} <= {q["format"] for q in qs}

    def test_coding_mode_contains_only_coding_and_both_kinds(self, dsa):
        qs = _start(dsa, _auth(dsa), mode="coding", question_count=50).json()["data"]["questions"]
        assert {q["format"] for q in qs} == {"coding"} and {q["interaction"] for q in qs} == {"mcq", "code"}
        assert all(q["hints"] for q in qs)

    def test_scored_modes_never_contain_ungradable_code_questions(self, dsa):
        h = _auth(dsa)
        for mode in ("topic", "interview", "tracing", "complexity", "timed_mock"):
            body = {"mode": mode, "question_count": 50}
            if mode == "topic":
                body["topic_ids"] = ["recursion"]
            assert all(q["interaction"] == "mcq" for q in dsa.post(f"{URL}/sessions", json=body, headers=h).json()["data"]["questions"]), mode

    def test_options_are_shuffled_but_keep_four_distinct_options(self, dsa, fake_db):
        qs = _start(dsa, _auth(dsa), mode="timed_mock", question_count=30).json()["data"]["questions"]
        assert all(len(q["options"]) == 4 and len(set(q["options"])) == 4 for q in qs)
        s = _raw(fake_db, _start(dsa, _auth(dsa, "o@example.com"), mode="timed_mock", question_count=30).json()["data"]["session_id"])
        assert any(q["option_order"] != [0, 1, 2, 3] for q in s["questions"])

    def test_timed_mock_spans_the_syllabus(self, dsa):
        d = _start(dsa, _auth(dsa), mode="timed_mock", question_count=40).json()["data"]
        assert d["exam_mode"] and d["immediate_feedback"] is False and d["timer_minutes"] == 60 and d["remaining_seconds"] > 3500
        assert len({q["topic_id"] for q in d["questions"]}) >= 8

    def test_mock_rejects_immediate_feedback(self, dsa):
        r = _start(dsa, _auth(dsa), mode="timed_mock", immediate_feedback=True)
        assert r.status_code == 422 and r.json()["error_code"] == "FEEDBACK_NOT_ALLOWED"

    def test_prefers_unseen_questions(self, dsa, fake_db):
        h = _auth(dsa)
        first = _start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=3).json()["data"]
        sid, qids = first["session_id"], _qids(_start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=3))
        assert sid
        s1 = _start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=3).json()["data"]
        _play(dsa, fake_db, h, s1["session_id"], [q["question_id"] for q in s1["questions"]], "ccc")
        dsa.post(f"{URL}/sessions/{s1['session_id']}/submit", headers=h)
        s2 = _start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=3).json()["data"]
        assert not ({q["question_id"] for q in s1["questions"]} & {q["question_id"] for q in s2["questions"]}) and qids

    def test_too_many_open_sessions(self, dsa, monkeypatch):
        monkeypatch.setattr(sessions, "MAX_OPEN_SESSIONS", 2)
        h = _auth(dsa)
        for _ in range(2):
            assert _start(dsa, h, mode="interview").status_code == 201
        assert _start(dsa, h, mode="interview").json()["error_code"] == "TOO_MANY_OPEN_SESSIONS"


class TestAnswerKeyLeakage:
    def test_session_payload_has_no_answers_before_submission(self, dsa):
        for mode in ("timed_mock", "tracing", "coding", "complexity"):
            h = _auth(dsa, f"{mode}@example.com")
            body = _start(dsa, h, mode=mode, question_count=15, **({"immediate_feedback": False})).json()
            for q in body["data"]["questions"]:
                assert not (set(q) & SECRET_KEYS - {"feedback"}), mode
                assert q["feedback"] is None
                if q["coding"]:
                    assert "reference_solution" not in q["coding"]

    def test_mock_never_shows_hints_or_feedback_and_result_is_hidden_until_submit(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=6).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        assert all(q["hints"] == [] for q in d["questions"])
        r = _answer(dsa, h, sid, qids[0], 0)
        assert r.status_code == 200 and r.json()["data"]["feedback"] is None and r.json()["data"]["locked"] is False
        res = dsa.get(f"{URL}/sessions/{sid}/result", headers=h)
        assert res.status_code == 409 and res.json()["error_code"] == "SESSION_NOT_FINISHED"
        assert not (set(dsa.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]) & {"correct_index", "explanation"})

    def test_resumed_session_never_reveals_keys(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=5).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, sid, qids, "cwcuw")
        again = dsa.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
        assert all(not (set(q) & {"correct_index", "explanation", "trace"}) for q in again["questions"]) and again["questions"][0]["selected_index"] is not None


class TestAnswering:
    def test_immediate_feedback_locks_and_reveals_one_answer(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="topic", topic_ids=["trees"], question_count=3).json()["data"]
        sid, q = d["session_id"], d["questions"][0]
        good = _displayed_correct(fake_db, sid, q["question_id"])
        r = _answer(dsa, h, sid, q["question_id"], good).json()["data"]
        assert r["locked"] and r["feedback"]["is_correct"] is True and r["feedback"]["correct_index"] == good and r["feedback"]["explanation"]
        assert _answer(dsa, h, sid, q["question_id"], (good + 1) % 4).json()["error_code"] == "ANSWER_LOCKED"
        other = d["questions"][1]["question_id"]
        wrong = (_displayed_correct(fake_db, sid, other) + 1) % 4
        fb = _answer(dsa, h, sid, other, wrong).json()["data"]["feedback"]
        assert fb["is_correct"] is False and fb["correct_index"] != wrong

    def test_trace_feedback_includes_intermediate_states(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="tracing", question_count=20).json()["data"]
        q = next(q for q in d["questions"] if q["format"] == "trace")
        fb = _answer(dsa, h, d["session_id"], q["question_id"], 0).json()["data"]["feedback"]
        assert fb["trace"] and all(set(s) == {"label", "state"} for s in fb["trace"])

    def test_marking_and_changing_answers_in_a_mock(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3).json()["data"]
        sid, qid = d["session_id"], d["questions"][0]["question_id"]
        assert _answer(dsa, h, sid, qid, 1, marked_for_review=True).json()["data"]["marked_for_review"] is True
        _answer(dsa, h, sid, qid, 2)
        q = dsa.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]
        assert q["selected_index"] == 2 and q["marked_for_review"] is False

    def test_answer_validation(self, dsa):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3).json()["data"]
        sid, qid = d["session_id"], d["questions"][0]["question_id"]
        assert _answer(dsa, h, sid, qid, 4).status_code == 422 and _answer(dsa, h, sid, qid, -1).status_code == 422
        assert dsa.put(f"{URL}/sessions/{sid}/answers/{qid}", json={"selected_index": "x"}, headers=h).status_code == 422
        assert _answer(dsa, h, sid, "dsa-0000000000", 1).json()["error_code"] == "QUESTION_NOT_IN_SESSION"
        assert dsa.put(f"{URL}/sessions/{sid}/answers/bad-id", json={"selected_index": 1}, headers=h).status_code == 422
        assert dsa.put(f"{URL}/sessions/{sid}/answers/{qid}", json={"code": "x" * 8001}, headers=h).status_code == 422
        assert _answer(dsa, h, sid, qid, code="print(1)").json()["error_code"] == "WRONG_ANSWER_TYPE"

    def test_client_cannot_supply_score_correctness_or_user(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=4).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        for qid in qids:
            wrong = (_displayed_correct(fake_db, sid, qid) + 1) % 4
            assert _answer(dsa, h, sid, qid, wrong, is_correct=True, correct_index=0, score=100, user_id="x", outcome="correct").status_code == 200
        res = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert res["correct"] == 0 and res["incorrect"] == 4 and res["score"] == 0

    def test_cannot_answer_after_submission(self, dsa):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3).json()["data"]
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        r = _answer(dsa, h, d["session_id"], d["questions"][0]["question_id"], 1)
        assert r.status_code == 409 and r.json()["error_code"] == "SESSION_COMPLETED"


class TestScoringAndResults:
    def test_server_computed_scores_and_breakdown(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=10).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, sid, qids, "ccccwwwuuu")
        r = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert (r["correct"], r["incorrect"], r["unanswered"], r["score"], r["accuracy"]) == (4, 3, 3, 4, 40.0)  # pattern ccccwwwuuu
        assert r["total_questions"] == r["graded_questions"] == 10 and r["ungraded_questions"] == 0
        assert sum(t["total"] for t in r["topic_performance"]) == 10 and "no negative marking" in r["scoring_policy"]
        assert r["average_seconds_per_question"] >= 0 and r["time_taken_seconds"] >= 0

    def test_result_contains_explanations_traces_and_complexity(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="complexity", question_count=6).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, sid, qids, "cwcwcw")
        r = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert all(q["explanation"] and q["correct_index"] is not None and q["complexity"]["time"] for q in r["questions"])
        assert r["complexity_summary"] and all(c["complexity"]["time"] for c in r["complexity_summary"])
        for q in r["questions"]:
            assert (q["outcome"] == "correct") == (q["selected_index"] == q["correct_index"])

    def test_result_has_traces_for_tracing_sessions(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="tracing", question_count=15).json()["data"]
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        r = dsa.get(f"{URL}/sessions/{d['session_id']}/result", headers=h).json()["data"]
        assert any(q["trace"] for q in r["questions"] if q["format"] == "trace")

    def test_revision_topics_are_derived_from_the_answers(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=8).json()["data"]
        _play(dsa, fake_db, h, d["session_id"], [q["question_id"] for q in d["questions"]], "wwwwwwww")
        rev = dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h).json()["data"]["revision_topics"]
        assert rev and all(x["accuracy"] < 70 and x["subtopics"] for x in rev)
        d = _start(dsa, h, mode="timed_mock", question_count=8).json()["data"]
        _play(dsa, fake_db, h, d["session_id"], [q["question_id"] for q in d["questions"]], "cccccccc")
        assert dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h).json()["data"]["revision_topics"] == []

    def test_submit_is_idempotent_and_records_attempts_once(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=6).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, sid, qids, "cwcwcw")
        a = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        b = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        c = dsa.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert a["score"] == b["score"] == c["score"] == 3 and a["finished_at"] == b["finished_at"]
        assert fake_db[Collections.DSA_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 6
        assert dsa.get(f"{URL}/progress", headers=h).json()["data"]["sessions_completed"] == 1

    def test_duplicate_final_submission_through_the_service_layer(self, dsa, fake_db):
        h = _auth(dsa)
        sid = _start(dsa, h, mode="timed_mock", question_count=5).json()["data"]["session_id"]
        uid = str(fake_db[Collections.USERS].find_one({"email": "dsa@example.com"})["_id"])
        for _ in range(3):
            sessions.finalize(fake_db, uid, sid)
        assert fake_db[Collections.DSA_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 5

    def test_half_finished_finalise_is_repaired(self, dsa, fake_db):
        h = _auth(dsa)
        sid = _start(dsa, h, mode="timed_mock", question_count=4).json()["data"]["session_id"]
        fake_db[Collections.DSA_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"status": "completed", "finished_at": datetime.now(UTC)}})
        r = dsa.get(f"{URL}/sessions/{sid}/result", headers=h)
        assert r.status_code == 200 and r.json()["data"]["total_questions"] == 4
        assert fake_db[Collections.DSA_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 4


class TestTimerExpiry:
    def _expire(self, db, sid, minutes_ago=5):
        db[Collections.DSA_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(minutes=minutes_ago)}})

    def test_expired_session_auto_finalises_on_read(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=5, timer_minutes=10).json()["data"]
        sid, qids = d["session_id"], [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, sid, qids, "ccuuu")
        self._expire(fake_db, sid)
        s = dsa.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
        assert s["status"] == "completed" and s["remaining_seconds"] == 0
        r = dsa.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert r["auto_submitted"] is True and r["correct"] == 2 and r["unanswered"] == 3 and r["time_taken_seconds"] <= 600

    def test_late_answer_is_rejected_and_not_scored(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3, timer_minutes=5).json()["data"]
        sid, qid = d["session_id"], d["questions"][0]["question_id"]
        self._expire(fake_db, sid)
        r = _answer(dsa, h, sid, qid, _displayed_correct(fake_db, sid, qid))
        assert r.status_code == 409 and r.json()["error_code"] == "SESSION_EXPIRED"
        assert dsa.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]["correct"] == 0

    def test_grace_period_accepts_a_just_in_time_answer(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3, timer_minutes=5).json()["data"]
        sid, qid = d["session_id"], d["questions"][0]["question_id"]
        fake_db[Collections.DSA_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}})
        assert _answer(dsa, h, sid, qid, 1).status_code == 200

    def test_expired_sessions_are_swept_when_starting_another(self, dsa, fake_db):
        h = _auth(dsa)
        sid = _start(dsa, h, mode="timed_mock", question_count=3, timer_minutes=5).json()["data"]["session_id"]
        self._expire(fake_db, sid)
        _start(dsa, h, mode="interview")
        assert _raw(fake_db, sid)["status"] == "completed"
        assert fake_db[Collections.DSA_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 3

    def test_result_time_is_capped_at_the_time_limit(self, dsa, fake_db):
        h = _auth(dsa)
        sid = _start(dsa, h, mode="timed_mock", question_count=3, timer_minutes=5).json()["data"]["session_id"]
        fake_db[Collections.DSA_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"started_at": datetime.now(UTC) - timedelta(hours=3), "expires_at": datetime.now(UTC) - timedelta(hours=2, minutes=55)}})
        assert dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]["time_taken_seconds"] <= 300


class TestCodingQuestions:
    def _coding_session(self, dsa, h, count=50):
        return _start(dsa, h, mode="coding", question_count=count).json()["data"]

    def test_code_answers_are_saved_and_never_executed(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h)
        q = next(q for q in d["questions"] if q["interaction"] == "code")
        r = _answer(dsa, h, d["session_id"], q["question_id"], code="def f():\n    import os; os.system('echo pwned')\n").json()["data"]
        assert r["feedback"] is None and r["code_answer"].startswith("def f()")
        again = dsa.get(f"{URL}/sessions/{d['session_id']}", headers=h).json()["data"]["questions"]
        assert next(x for x in again if x["question_id"] == q["question_id"])["code_answer"].startswith("def f()")

    def test_reveal_returns_reference_tests_and_an_honest_note(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h)
        q = next(q for q in d["questions"] if q["interaction"] == "code")
        r = _answer(dsa, h, d["session_id"], q["question_id"], code="def x(): pass", reveal=True).json()["data"]
        fb = r["feedback"]
        assert r["locked"] and fb["kind"] == "code" and fb["reference_solution"] and any(not t["visible"] for t in fb["test_cases"]) and "NOT run" in fb["execution_note"]

    def test_reveal_needs_code_and_is_ignored_in_exams(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h)
        q = next(q for q in d["questions"] if q["interaction"] == "code")
        assert _answer(dsa, h, d["session_id"], q["question_id"], code="   ", reveal=True).json()["data"]["feedback"] is None

    def test_code_questions_are_ungraded_and_excluded_from_accuracy(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h, 40)
        sid = d["session_id"]
        mcq = [q["question_id"] for q in d["questions"] if q["interaction"] == "mcq"]
        code = [q["question_id"] for q in d["questions"] if q["interaction"] == "code"]
        assert mcq and code
        for qid in mcq[:3]:
            _answer(dsa, h, sid, qid, _displayed_correct(fake_db, sid, qid))
        for qid in code:
            _answer(dsa, h, sid, qid, code="def anything():\n    return 42\n")
        r = dsa.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert r["ungraded_questions"] == len(code) and r["graded_questions"] == len(mcq) and r["correct"] == 3
        assert r["accuracy"] == round(100 * 3 / len(mcq), 1) and r["score"] == 3
        cq = next(q for q in r["questions"] if q["interaction"] == "code")
        assert cq["outcome"] == "ungraded" and cq["reference_solution"] and cq["test_cases"] and cq["code_answer"] and "NOT run" in cq["execution_note"]
        assert all(t["topic_id"] for t in r["topic_performance"]) and sum(t["total"] for t in r["topic_performance"]) == len(mcq)

    def test_code_attempts_do_not_affect_analytics(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h, 40)
        for q in d["questions"]:
            if q["interaction"] == "code":
                _answer(dsa, h, d["session_id"], q["question_id"], code="def nothing(): pass")
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        p = dsa.get(f"{URL}/progress", headers=h).json()["data"]
        assert p["ungraded_code"] > 0 and p["questions_answered"] == 0 and p["accuracy"] == 0.0 and p["weak_topics"] == []

    def test_self_assessment_flow(self, dsa, fake_db):
        h = _auth(dsa)
        d = self._coding_session(dsa, h, 40)
        sid = d["session_id"]
        code = [q["question_id"] for q in d["questions"] if q["interaction"] == "code"]
        mcq = next(q["question_id"] for q in d["questions"] if q["interaction"] == "mcq")
        put = lambda qid, v: dsa.put(f"{URL}/sessions/{sid}/self-assessment/{qid}", json={"verdict": v}, headers=h)  # noqa: E731
        assert put(code[0], "passed").json()["error_code"] == "SESSION_NOT_FINISHED"
        _answer(dsa, h, sid, code[0], code="def f(): pass")
        dsa.post(f"{URL}/sessions/{sid}/submit", headers=h)
        before = dsa.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        ok = put(code[0], "partial")
        assert ok.status_code == 200 and ok.json()["data"] == {"question_id": code[0], "self_assessment": "partial", "counts_toward_score": False}
        assert put(code[1], "passed").json()["error_code"] == "NO_CODE_SUBMITTED"
        assert put(mcq, "passed").json()["error_code"] == "NOT_A_CODING_QUESTION"
        assert put(code[0], "great").status_code == 422
        after = dsa.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert next(q for q in after["questions"] if q["question_id"] == code[0])["self_assessment"] == "partial"
        assert (after["score"], after["accuracy"]) == (before["score"], before["accuracy"])

    def test_self_assessment_is_owner_only(self, dsa):
        a, b = _auth(dsa, "a@example.com"), _auth(dsa, "b@example.com")
        d = self._coding_session(dsa, a)
        qid = next(q["question_id"] for q in d["questions"] if q["interaction"] == "code")
        assert dsa.put(f"{URL}/sessions/{d['session_id']}/self-assessment/{qid}", json={"verdict": "passed"}, headers=b).status_code == 404


class TestOwnershipAndIsolation:
    def test_other_users_cannot_touch_a_session(self, dsa, fake_db):
        a, b = _auth(dsa, "a@example.com"), _auth(dsa, "b@example.com")
        d = _start(dsa, a, mode="timed_mock", question_count=3).json()["data"]
        sid, qid = d["session_id"], d["questions"][0]["question_id"]
        assert dsa.get(f"{URL}/sessions/{sid}", headers=b).status_code == 404
        assert _answer(dsa, b, sid, qid, 1).status_code == 404
        assert dsa.post(f"{URL}/sessions/{sid}/submit", headers=b).status_code == 404
        assert dsa.get(f"{URL}/sessions/{sid}/result", headers=b).status_code == 404
        assert dsa.get(f"{URL}/sessions/{'f' * 24}", headers=b).status_code == 404  # same answer as "exists but not yours"
        assert _raw(fake_db, sid)["status"] == "in_progress" and not _raw(fake_db, sid)["answers"]

    def test_history_and_progress_are_per_user(self, dsa, fake_db):
        a, b = _auth(dsa, "a@example.com"), _auth(dsa, "b@example.com")
        d = _start(dsa, a, mode="timed_mock", question_count=5).json()["data"]
        _play(dsa, fake_db, a, d["session_id"], [q["question_id"] for q in d["questions"]], "ccwwu")
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=a)
        assert dsa.get(f"{URL}/sessions", headers=a).json()["data"]["total"] == 1
        assert dsa.get(f"{URL}/sessions", headers=b).json()["data"]["total"] == 0
        assert dsa.get(f"{URL}/progress", headers=b).json()["data"]["questions_presented"] == 0
        assert dsa.get(f"{URL}/progress", headers=a).json()["data"]["questions_presented"] == 5

    def test_user_id_in_the_body_is_ignored(self, dsa, fake_db):
        a, b = _auth(dsa, "a@example.com"), _auth(dsa, "b@example.com")
        uid_b = str(fake_db[Collections.USERS].find_one({"email": "b@example.com"})["_id"])
        sid = dsa.post(f"{URL}/sessions", json={"mode": "interview", "user_id": uid_b}, headers=a).json()["data"]["session_id"]
        assert str(_raw(fake_db, sid)["user_id"]) != uid_b and dsa.get(f"{URL}/sessions/{sid}", headers=b).status_code == 404

    def test_history_is_paginated_newest_first(self, dsa):
        h = _auth(dsa)
        ids = [_start(dsa, h, mode="interview", question_count=3).json()["data"]["session_id"] for _ in range(3)]
        page = dsa.get(f"{URL}/sessions?limit=2&page=1", headers=h).json()["data"]
        assert [i["session_id"] for i in page["items"]] == ids[::-1][:2] and page["has_next"] and page["total"] == 3


class TestProgressAndWeakTopics:
    def test_no_history_means_no_invented_numbers(self, dsa):
        h = _auth(dsa)
        p = dsa.get(f"{URL}/progress", headers=h).json()["data"]
        assert p["sessions_completed"] == 0 and p["questions_answered"] == 0 and p["accuracy"] == 0.0 and p["weak_topics"] == [] and p["trend"] == []
        rec = dsa.get(f"{URL}/recommendations", headers=h).json()["data"]
        assert rec["has_history"] is False and rec["weak_topics"] == [] and "Complete a few practice sessions" in rec["message"]

    def test_weak_mode_without_history_is_refused(self, dsa):
        r = _start(dsa, _auth(dsa), mode="weak")
        assert r.status_code == 409 and r.json()["error_code"] == "NO_HISTORY"

    def test_progress_matches_the_recorded_answers(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=10).json()["data"]
        _play(dsa, fake_db, h, d["session_id"], [q["question_id"] for q in d["questions"]], "cccwwuuuuu")
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        p = dsa.get(f"{URL}/progress", headers=h).json()["data"]
        assert (p["questions_presented"], p["questions_answered"], p["correct"], p["incorrect"], p["unanswered"], p["accuracy"]) == (10, 5, 3, 2, 5, 60.0)
        assert sum(t["presented"] for t in p["topic_accuracy"]) == 10 and p["recent_sessions"][0]["score"] == 3

    def test_weak_topics_need_enough_evidence(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=3).json()["data"]
        _play(dsa, fake_db, h, d["session_id"], [q["question_id"] for q in d["questions"]], "www")
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        assert dsa.get(f"{URL}/recommendations", headers=h).json()["data"]["weak_topics"] == []

    def test_weak_topic_detected_and_weak_session_targets_mistakes(self, dsa, fake_db):
        h = _auth(dsa)
        wrong_ids = set()
        for _ in range(2):
            d = _start(dsa, h, mode="topic", topic_ids=["graphs"], question_count=8).json()["data"]
            qids = [q["question_id"] for q in d["questions"]]
            _play(dsa, fake_db, h, d["session_id"], qids, "wwwwwwww")
            wrong_ids |= set(qids)
            dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        rec = dsa.get(f"{URL}/recommendations", headers=h).json()["data"]
        assert [w["topic_id"] for w in rec["weak_topics"]] == ["graphs"] and rec["weak_topics"][0]["accuracy"] == 0.0 and rec["incorrect_question_count"] > 0
        weak = _start(dsa, h, mode="weak", question_count=6).json()["data"]
        assert weak["question_count"] == 6 and {q["question_id"] for q in weak["questions"]} <= wrong_ids  # repeat mistakes come first
        assert {q["topic_id"] for q in weak["questions"]} == {"graphs"}

    def test_a_question_answered_correctly_later_is_no_longer_a_repeat_mistake(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=3).json()["data"]
        qids = [q["question_id"] for q in d["questions"]]
        _play(dsa, fake_db, h, d["session_id"], qids, "www")
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        assert dsa.get(f"{URL}/recommendations", headers=h).json()["data"]["incorrect_question_count"] == 3
        # make the retry later than the first attempt
        d2 = _start(dsa, h, mode="topic", subtopic_ids=["bfs"], question_count=6).json()["data"]
        again = [q["question_id"] for q in d2["questions"] if q["question_id"] in qids]
        _play(dsa, fake_db, h, d2["session_id"], again, "c" * len(again))
        dsa.post(f"{URL}/sessions/{d2['session_id']}/submit", headers=h)
        assert dsa.get(f"{URL}/recommendations", headers=h).json()["data"]["incorrect_question_count"] == 3 - len(again)


class TestHistoryIntegration:
    def test_completed_session_appears_in_the_shared_history(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="timed_mock", question_count=4).json()["data"]
        sid = d["session_id"]
        _play(dsa, fake_db, h, sid, [q["question_id"] for q in d["questions"]], "ccwu")
        dsa.post(f"{URL}/sessions/{sid}/submit", headers=h)
        item = dsa.get("/api/v1/history?type=dsa", headers=h).json()["data"]["items"][0]
        assert item["type"] == "dsa" and item["id"] == sid and item["status"] == "completed" and item["score"] == 50 and item["title"] == "DSA Timed Mock Test"
        assert item["metadata"]["question_count"] == 4 and item["metadata"]["graded_count"] == 4
        summary = dsa.get("/api/v1/history/summary", headers=h).json()["data"]
        assert next(t for t in summary["types"] if t["type"] == "dsa")["count"] == 1

    def test_coding_only_session_has_no_score_in_history(self, dsa, fake_db):
        h = _auth(dsa)
        d = _start(dsa, h, mode="coding", question_count=50).json()["data"]
        only_code = [q for q in d["questions"] if q["interaction"] == "code"]
        assert only_code
        dsa.post(f"{URL}/sessions/{d['session_id']}/submit", headers=h)
        item = dsa.get("/api/v1/history?type=dsa", headers=h).json()["data"]["items"][0]
        assert item["metadata"]["graded_count"] == d["question_count"] - len(only_code)

    def test_history_detail_returns_the_result_only_after_submission(self, dsa):
        h = _auth(dsa)
        sid = _start(dsa, h, mode="timed_mock", question_count=3).json()["data"]["session_id"]
        mid = dsa.get(f"/api/v1/history/dsa/{sid}", headers=h).json()["data"]["detail"]
        assert all(not (set(q) & {"correct_index", "explanation"}) for q in mid["questions"])
        dsa.post(f"{URL}/sessions/{sid}/submit", headers=h)
        done = dsa.get(f"/api/v1/history/dsa/{sid}", headers=h).json()["data"]["detail"]
        assert all("explanation" in q and "correct_index" in q for q in done["questions"])

    def test_history_detail_is_owner_only(self, dsa):
        a, b = _auth(dsa, "a@example.com"), _auth(dsa, "b@example.com")
        sid = _start(dsa, a, mode="interview").json()["data"]["session_id"]
        assert dsa.get(f"/api/v1/history/dsa/{sid}", headers=b).status_code == 404
        assert dsa.get("/api/v1/history?type=dsa", headers=b).json()["data"]["total"] == 0
