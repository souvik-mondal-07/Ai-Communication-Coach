"""Phase 25 -- DBMS & SQL lab API: auth, listing, sandbox endpoint, modes, server-side scoring, SQL flows, idempotency, ownership, analytics, history."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from app.core.rate_limit import reset_rate_limits
from app.db.collections import Collections
from app.services.dbms_sql import bank, sessions
from tests.test_communication import _register_and_login

URL = "/api/v1/dbms-sql"
SECRET = {"correct_index", "explanation", "verification", "fingerprint", "content_hash", "reference_sql", "expected", "expected_rows", "is_correct", "review_status", "correct_answer"}
ALL_MODES = ["topic", "mixed", "interview", "sql_lab", "predict_output", "debug", "complete", "design_lab", "transaction_lab", "nosql_lab", "timed_mock"]


@pytest.fixture()
def lab(client, fake_db, monkeypatch):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    reset_rate_limits()
    monkeypatch.setattr(sessions, "_rng", random.Random(7))
    return client


def _auth(client, email="lab@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _uid(db, email="lab@example.com"):
    return db[Collections.USERS].find_one({"email": email})["_id"]


def _start(client, h, **body):
    body.setdefault("mode", "mixed")
    if body["mode"] == "topic" and "topic_ids" not in body:
        body["topic_ids"] = ["keys"]
    return client.post(f"{URL}/sessions", json=body, headers=h)


def _raw(db, sid):
    return db[Collections.DBMS_SQL_SESSIONS].find_one({"_id": ObjectId(sid)})


def _doc(db, qid):
    return db[Collections.DBMS_SQL_QUESTIONS].find_one({"question_id": qid})


def _displayed_correct(db, sid, qid):
    s = _raw(db, sid)
    order = next(q["option_order"] for q in s["questions"] if q["question_id"] == qid)
    return order.index(_doc(db, qid)["correct_index"])


def _answer(client, h, sid, qid, index=None, **extra):
    body = {**({"selected_index": index} if index is not None else {}), **extra}
    return client.put(f"{URL}/sessions/{sid}/answers/{qid}", json=body, headers=h)


def _check(client, h, sid, qid, **body):
    return client.post(f"{URL}/sessions/{sid}/questions/{qid}/check", json=body, headers=h)


def _qs(resp):
    return resp.json()["data"]["questions"]


def _find(resp, interaction=None, text=None):
    for q in _qs(resp):
        if (interaction is None or q["interaction"] == interaction) and (text is None or text in q["statement"]):
            return q
    raise AssertionError("question not in session")


def _walk(obj):
    """Yield every key anywhere in a JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _sql_session(client, h, text=None, **body):
    r = _start(client, h, mode="sql_lab", question_count=50, **body)
    assert r.status_code == 201
    q = _find(r, "sql", text)
    return r.json()["data"]["session_id"], q, r


class TestAuthentication:
    @pytest.mark.parametrize("method,path", [
        ("get", "/syllabus"), ("get", "/coverage"), ("get", "/datasets/practice"), ("get", "/questions"), ("post", "/sandbox/run"), ("post", "/sessions"), ("get", "/sessions"),
        ("get", "/progress"), ("get", "/recommendations"), ("get", f"/sessions/{'a' * 24}"), ("get", f"/sessions/{'a' * 24}/result"), ("post", f"/sessions/{'a' * 24}/submit"),
        ("put", f"/sessions/{'a' * 24}/answers/dbq-0123456789"), ("post", f"/sessions/{'a' * 24}/questions/dbq-0123456789/check"),
        ("post", f"/sessions/{'a' * 24}/questions/dbq-0123456789/reveal"), ("post", f"/sessions/{'a' * 24}/questions/dbq-0123456789/hint"),
    ])
    def test_every_route_requires_a_token(self, lab, method, path):
        assert getattr(lab, method)(URL + path).status_code == 401

    def test_a_garbage_token_is_rejected(self, lab):
        assert lab.get(f"{URL}/syllabus", headers={"Authorization": "Bearer nope"}).status_code == 401


class TestSyllabusDatasetListing:
    def test_syllabus_has_all_units_and_real_counts(self, lab, fake_db):
        h = _auth(lab)
        d = lab.get(f"{URL}/syllabus", headers=h).json()["data"]
        assert len(d["units"]) == 7 and d["topics_total"] == 70 and d["topics_implemented"] == 70
        assert d["question_total"] == fake_db[Collections.DBMS_SQL_QUESTIONS].count_documents({"status": "active"})
        assert d["sql_engine"]["read_only"] is True

    def test_coverage_report(self, lab):
        d = lab.get(f"{URL}/coverage", headers=_auth(lab)).json()["data"]
        assert len(d["rows"]) == 70 and d["manual_review"] > 0 and d["machine_verified"] > 0

    def test_dataset_schema_and_rows(self, lab):
        d = lab.get(f"{URL}/datasets/practice", headers=_auth(lab)).json()["data"]
        assert [t["name"] for t in d["tables"]] == ["departments", "employees", "projects", "employee_projects", "customers", "orders"]
        emp = next(t for t in d["tables"] if t["name"] == "employees")
        assert emp["row_count"] == 16 and len(emp["rows"]) == 16
        assert next(c for c in emp["columns"] if c["name"] == "dept_id")["references"] == "departments.dept_id"
        assert any(r[4] is None for r in emp["rows"])  # the NULL-salary edge case is visible
        assert d["indexes"] and "CREATE TABLE" in d["ddl"]

    def test_unknown_dataset_is_404(self, lab):
        assert lab.get(f"{URL}/datasets/nope", headers=_auth(lab)).status_code == 404

    def test_question_listing_is_answer_free(self, lab):
        h = _auth(lab)
        data = lab.get(f"{URL}/questions", params={"limit": 50}, headers=h).json()["data"]
        assert data["items"] and data["limit"] == 50
        assert not (SECRET & set(_walk(data["items"])))
        assert "reference_sql" not in str(data) and "hints" not in {k for it in data["items"] for k in it}

    def test_listing_filters_and_pagination(self, lab):
        h = _auth(lab)
        d = lab.get(f"{URL}/questions", params={"unit_id": "unit-g", "interaction": "mcq", "limit": 5, "page": 2}, headers=h).json()["data"]
        assert d["page"] == 2 and len(d["items"]) == 5 and all(i["unit_id"] == "unit-g" for i in d["items"])
        sql = lab.get(f"{URL}/questions", params={"interaction": "sql", "limit": 50}, headers=h).json()["data"]
        assert sql["items"] and all(i["sql"]["expected_columns"] for i in sql["items"])
        assert lab.get(f"{URL}/questions", params={"difficulty": "hard"}, headers=h).json()["data"]["total"] > 0

    @pytest.mark.parametrize("params", [{"limit": 51}, {"limit": 0}, {"page": 0}, {"difficulty": "extreme"}, {"format": "bogus"}, {"unit_id": "Bad Id!"}, {"interaction": "x"}])
    def test_bad_query_parameters_are_422(self, lab, params):
        assert lab.get(f"{URL}/questions", params=params, headers=_auth(lab)).status_code == 422


class TestSandboxEndpoint:
    def test_runs_a_query(self, lab):
        r = lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT dept_name FROM departments ORDER BY dept_name"}, headers=_auth(lab))
        d = r.json()["data"]
        assert r.status_code == 200 and d["ok"] and d["rows"][0] == ["Engineering"] and d["columns"] == ["dept_name"]

    @pytest.mark.parametrize("sql", ["DROP TABLE employees", "SELECT * FROM sqlite_master", "SELECT 1; SELECT 2", "PRAGMA table_info(employees)", "ATTACH 'x' AS y", "SELECT load_extension('x')"])
    def test_unsafe_sql_is_a_normal_response_with_ok_false(self, lab, sql):
        r = lab.post(f"{URL}/sandbox/run", json={"sql": sql}, headers=_auth(lab))
        d = r.json()["data"]
        assert r.status_code == 200 and d["ok"] is False and d["rows"] == [] and d["error"]["kind"] in ("not_allowed", "unknown_object")
        assert "Traceback" not in r.text

    def test_input_size_is_bounded(self, lab):
        h = _auth(lab)
        assert lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT " + "1," * 3000 + "1"}, headers=h).status_code == 422
        assert lab.post(f"{URL}/sandbox/run", json={"sql": ""}, headers=h).status_code == 422
        assert lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1", "dataset_id": "../etc"}, headers=h).status_code == 422

    def test_unknown_dataset_is_refused_safely(self, lab):
        d = lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1", "dataset_id": "other"}, headers=_auth(lab)).json()["data"]
        assert d["ok"] is False

    def test_runaway_query_is_stopped_and_service_stays_up(self, lab):
        h = _auth(lab)
        r = lab.post(f"{URL}/sandbox/run", json={"sql": "WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM c) SELECT count(*) FROM c"}, headers=h)
        assert r.json()["data"]["error"]["kind"] == "timeout"
        assert lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1"}, headers=h).json()["data"]["ok"]

    def test_execution_is_rate_limited(self, lab):
        h = _auth(lab)
        codes = [lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1"}, headers=h).status_code for _ in range(32)]
        assert codes[:30] == [200] * 30 and codes[30] == 429 and "RATE_LIMITED" in lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1"}, headers=h).text

    def test_sandbox_never_touches_application_data(self, lab, fake_db):
        h = _auth(lab)
        before = fake_db[Collections.USERS].count_documents({})
        r = lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT * FROM users"}, headers=h).json()["data"]
        assert r["ok"] is False and fake_db[Collections.USERS].count_documents({}) == before


class TestSessionCreation:
    @pytest.mark.parametrize("mode", ALL_MODES)
    def test_every_mode_starts_and_is_answer_free(self, lab, mode):
        h = _auth(lab, f"{mode}@example.com")
        r = _start(lab, h, mode=mode, question_count=8)
        assert r.status_code == 201, r.text
        data = r.json()["data"]
        assert data["questions"] and data["status"] == "in_progress"
        assert not (SECRET & set(_walk(data))), "an answer key leaked into the session payload"
        assert "reference_sql" not in str(data) and '"hints": [' in str(data).replace("'", '"')

    @pytest.mark.parametrize("mode,check", [
        ("sql_lab", lambda q: q["interaction"] == "sql" and q["format"] == "query"),
        ("predict_output", lambda q: q["format"] == "output"),
        ("debug", lambda q: q["format"] == "debug"),
        ("complete", lambda q: q["format"] == "complete"),
        ("interview", lambda q: q["format"] in ("concept", "scenario")),
        ("design_lab", lambda q: q["unit_id"] == "unit-d" or q["format"] == "design"),
        ("transaction_lab", lambda q: q["unit_id"] == "unit-f" or q["format"] == "transaction"),
        ("nosql_lab", lambda q: q["unit_id"] == "unit-g"),
    ])
    def test_modes_select_the_right_questions(self, lab, mode, check):
        h = _auth(lab, f"{mode}-sel@example.com")
        qs = _qs(_start(lab, h, mode=mode, question_count=30))
        assert qs and all(check(q) for q in qs)

    def test_topic_mode_requires_a_topic_and_filters_to_it(self, lab):
        h = _auth(lab)
        assert lab.post(f"{URL}/sessions", json={"mode": "topic"}, headers=h).status_code == 422
        qs = _qs(_start(lab, h, mode="topic", topic_ids=["joins"], question_count=20))
        assert qs and {q["topic_id"] for q in qs} == {"joins"}

    def test_mixed_mode_spans_several_units(self, lab):
        qs = _qs(_start(lab, _auth(lab), mode="mixed", question_count=30))
        assert len({q["unit_id"] for q in qs}) >= 4

    def test_mixed_mode_respects_unit_filter(self, lab):
        qs = _qs(_start(lab, _auth(lab), mode="mixed", unit_ids=["unit-a", "unit-b"], question_count=20))
        assert {q["unit_id"] for q in qs} <= {"unit-a", "unit-b"} and len({q["unit_id"] for q in qs}) == 2

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_difficulty_filter(self, lab, difficulty):
        qs = _qs(_start(lab, _auth(lab, f"{difficulty}@example.com"), mode="mixed", difficulty=difficulty, question_count=15))
        assert qs and {q["difficulty"] for q in qs} == {difficulty}

    @pytest.mark.parametrize("body", [{"mode": "bogus"}, {"mode": "mixed", "question_count": 0}, {"mode": "mixed", "question_count": 51}, {"mode": "mixed", "difficulty": "x"},
                                      {"mode": "mixed", "unit_ids": ["unit-z"]}, {"mode": "mixed", "topic_ids": ["nope"]}, {"mode": "timed_mock", "timer_minutes": 181},
                                      {"mode": "mixed", "topic_ids": ["Bad Id"]}])
    def test_invalid_requests_are_422(self, lab, body):
        assert lab.post(f"{URL}/sessions", json=body, headers=_auth(lab)).status_code == 422

    def test_question_count_is_respected_and_questions_are_unique(self, lab):
        qs = _qs(_start(lab, _auth(lab), mode="mixed", question_count=12))
        assert len(qs) == 12 and len({q["question_id"] for q in qs}) == 12

    def test_timed_mock_defaults_and_rejects_feedback(self, lab):
        h = _auth(lab)
        d = _start(lab, h, mode="timed_mock", question_count=10).json()["data"]
        assert d["exam_mode"] and d["immediate_feedback"] is False and d["timer_minutes"] >= 1 and d["remaining_seconds"] > 0
        assert lab.post(f"{URL}/sessions", json={"mode": "timed_mock", "immediate_feedback": True}, headers=h).status_code == 422
        custom = _start(lab, h, mode="timed_mock", question_count=5, timer_minutes=7).json()["data"]
        assert custom["timer_minutes"] == 7

    def test_open_session_cap(self, lab, monkeypatch):
        monkeypatch.setattr(sessions, "MAX_OPEN_SESSIONS", 2)
        h = _auth(lab)
        assert _start(lab, h).status_code == 201 and _start(lab, h).status_code == 201
        r = _start(lab, h)
        assert r.status_code == 409 and r.json()["error_code"] == "TOO_MANY_OPEN_SESSIONS"

    def test_weak_mode_needs_history(self, lab):
        r = _start(lab, _auth(lab), mode="weak")
        assert r.status_code == 409 and r.json()["error_code"] == "NO_HISTORY"

    def test_create_is_rate_limited(self, lab, monkeypatch):
        monkeypatch.setattr(sessions, "MAX_OPEN_SESSIONS", 1000)
        h = _auth(lab)
        codes = [_start(lab, h, question_count=1).status_code for _ in range(16)]
        assert codes[:15] == [201] * 15 and codes[15] == 429


class TestMcqScoring:
    def _session(self, lab, h, n=6, **kw):
        r = _start(lab, h, mode="mixed", question_count=n * 3, **kw)
        data = r.json()["data"]
        mcqs = [q for q in data["questions"] if q["interaction"] == "mcq"][:n]
        return data["session_id"], mcqs

    def test_score_is_computed_by_the_server(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h)
        pattern = "ccciiu"
        for q, p in zip(mcqs, pattern):
            if p == "u":
                continue
            good = _displayed_correct(fake_db, sid, q["question_id"])
            assert _answer(lab, h, sid, q["question_id"], good if p == "c" else (good + 1) % 4).status_code == 200
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        by = {q["question_id"]: q["outcome"] for q in res["questions"]}
        assert [by[q["question_id"]] for q in mcqs] == ["correct"] * 3 + ["incorrect"] * 2 + ["unanswered"]
        assert res["correct"] == 3 and res["score"] == 3 and res["unanswered"] >= 1
        assert res["accuracy"] == round(100 * 3 / res["total_questions"], 1)

    def test_client_supplied_score_or_correctness_is_ignored(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        q = mcqs[0]
        wrong = (_displayed_correct(fake_db, sid, q["question_id"]) + 1) % 4
        r = _answer(lab, h, sid, q["question_id"], wrong, is_correct=True, score=100, correct=True, outcome="correct", status="completed", correct_index=wrong)
        assert r.status_code == 200 and r.json()["data"]["feedback"]["is_correct"] is False
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h, json={"score": 100, "status": "completed"}).json()["data"]
        assert res["score"] == 0 and next(x for x in res["questions"] if x["question_id"] == q["question_id"])["outcome"] == "incorrect"

    def test_immediate_feedback_locks_and_reveals_after_answer(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        qid = mcqs[0]["question_id"]
        assert mcqs[0]["feedback"] is None and mcqs[0]["locked"] is False
        good = _displayed_correct(fake_db, sid, qid)
        r = _answer(lab, h, sid, qid, good).json()["data"]
        assert r["locked"] and r["feedback"]["is_correct"] and r["feedback"]["correct_index"] == good and r["feedback"]["explanation"]
        again = _answer(lab, h, sid, qid, (good + 1) % 4)
        assert again.status_code == 409 and again.json()["error_code"] == "ANSWER_LOCKED"
        resumed = next(q for q in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"] if q["question_id"] == qid)
        assert resumed["locked"] and resumed["feedback"]["correct_index"] == good

    def test_option_order_is_shuffled_per_session_and_mapped_back(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=4)
        for q in mcqs:
            assert sorted(q["options"]) == sorted(_doc(fake_db, q["question_id"])["options"])
            good = _displayed_correct(fake_db, sid, q["question_id"])
            assert q["options"][good] == _doc(fake_db, q["question_id"])["options"][_doc(fake_db, q["question_id"])["correct_index"]]

    def test_timed_mock_reveals_nothing_before_submission(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="timed_mock", question_count=6).json()["data"]["session_id"]
        q = next(q for q in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"] if q["interaction"] == "mcq")
        r = _answer(lab, h, sid, q["question_id"], 0).json()["data"]
        assert r["locked"] is False and r["feedback"] is None
        assert _answer(lab, h, sid, q["question_id"], 1).status_code == 200  # changeable until submission
        got = lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
        assert not (SECRET & set(_walk(got))) and all(x["hints"] == [] and x["hints_total"] == 0 and x["feedback"] is None for x in got["questions"])
        assert lab.get(f"{URL}/sessions/{sid}/result", headers=h).status_code == 409

    @pytest.mark.parametrize("body", [{"selected_index": 4}, {"selected_index": -1}, {"selected_index": "a"}, {"time_spent_seconds": -1}, {"time_spent_seconds": 99999}, {"sql": "x" * 4001}, {"text": "x" * 201}])
    def test_malformed_answers_are_422(self, lab, body):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        assert lab.put(f"{URL}/sessions/{sid}/answers/{mcqs[0]['question_id']}", json=body, headers=h).status_code == 422

    def test_answer_type_must_match_the_question(self, lab):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        r = lab.put(f"{URL}/sessions/{sid}/answers/{mcqs[0]['question_id']}", json={"sql": "SELECT 1"}, headers=h)
        assert r.status_code == 422 and r.json()["error_code"] == "WRONG_ANSWER_TYPE"

    def test_question_must_belong_to_the_session(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        outside = fake_db[Collections.DBMS_SQL_QUESTIONS].find_one({"question_id": {"$nin": [q["question_id"] for q in _qs(lab.get(f'{URL}/sessions/{sid}', headers=h))]}})
        r = _answer(lab, h, sid, outside["question_id"], 0)
        assert r.status_code == 422 and r.json()["error_code"] == "QUESTION_NOT_IN_SESSION"

    def test_marked_for_review_is_saved(self, lab):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        _answer(lab, h, sid, mcqs[0]["question_id"], marked_for_review=True)
        q = next(x for x in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"] if x["question_id"] == mcqs[0]["question_id"])
        assert q["marked_for_review"] is True and q["selected_index"] is None

    def test_time_is_clamped_to_server_elapsed(self, lab, fake_db):
        h = _auth(lab)
        sid, mcqs = self._session(lab, h, n=1)
        _answer(lab, h, sid, mcqs[0]["question_id"], 0, time_spent_seconds=3000)
        assert _raw(fake_db, sid)["answers"][mcqs[0]["question_id"]]["time_spent"] <= 5


class TestSqlExercises:
    def test_wrong_query_gives_feedback_and_can_be_retried(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        r = _check(lab, h, sid, q["question_id"], sql="SELECT 1").json()["data"]
        assert r["correct"] is False and r["locked"] is False and r["verdict"]["messages"] and r["checks"] == 1
        assert r["comparison"]["expected"]["columns"] and r["run"]["ok"]
        assert r["feedback"] is None  # no reference solution yet
        r2 = _check(lab, h, sid, q["question_id"], sql="SELECT 2").json()["data"]
        assert r2["checks"] == 2 and r2["locked"] is False

    def test_correct_query_locks_and_shows_reference(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        ref = _doc(fake_db, q["question_id"])["sql"]["reference_sql"]
        d = _check(lab, h, sid, q["question_id"], sql=ref).json()["data"]
        assert d["correct"] and d["locked"] and d["feedback"]["reference_sql"] == ref and d["feedback"]["explanation"] and d["feedback"]["is_correct"]
        again = _check(lab, h, sid, q["question_id"], sql=ref)
        assert again.status_code == 409 and again.json()["error_code"] == "ANSWER_LOCKED"
        assert _answer(lab, h, sid, q["question_id"], sql="SELECT 1").status_code == 409

    def test_an_equivalent_query_with_a_different_structure_is_accepted(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h, text="never placed an order")
        alt = "SELECT customer_name FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders) ORDER BY customer_name"
        d = _check(lab, h, sid, q["question_id"], sql=alt).json()["data"]
        assert d["correct"] is True, d["verdict"]
        sid2, q2, _ = _sql_session(lab, _auth(lab, "other@example.com"), text="never placed an order")
        alt2 = "select c.customer_name from customers c where not exists (select 1 from orders o where o.customer_id = c.customer_id) order by 1"
        assert _check(lab, {"Authorization": f"Bearer {_register_and_login(lab, email='other@example.com')}"}, sid2, q2["question_id"], sql=alt2).json()["data"]["correct"]

    def test_row_order_is_enforced_only_when_the_task_requires_it(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h, text="Return each distinct department location")
        d = _check(lab, h, sid, q["question_id"], sql="SELECT DISTINCT location FROM departments ORDER BY location DESC").json()["data"]
        assert d["correct"] is False and d["verdict"]["code"] == "order"

    def test_unsafe_sql_in_a_check_is_graded_incorrect_not_executed(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        d = _check(lab, h, sid, q["question_id"], sql="DROP TABLE employees").json()["data"]
        assert d["correct"] is False and d["run"]["ok"] is False and d["run"]["error"]["kind"] == "not_allowed" and d["comparison"] is None
        assert fake_db[Collections.USERS].count_documents({}) >= 1

    def test_hints_are_progressive_counted_and_bounded(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h, text="work on the project named Apollo")
        total = len(_doc(fake_db, q["question_id"])["hints"])
        assert q["hints"] == [] and q["hints_total"] == total
        seen = []
        for n in range(1, total + 1):
            d = lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/hint", headers=h).json()["data"]
            assert d["hint_number"] == n and d["hints"] == _doc(fake_db, q["question_id"])["hints"][:n]
            seen.append(d["hint"])
        done = lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/hint", headers=h)
        assert done.status_code == 409 and done.json()["error_code"] == "NO_MORE_HINTS"
        resumed = next(x for x in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"] if x["question_id"] == q["question_id"])
        assert resumed["hints"] == seen and resumed["hints_used"] == total

    def test_a_hint_then_a_retry_then_success_flow(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        assert _check(lab, h, sid, q["question_id"], sql="SELECT 1").json()["data"]["correct"] is False
        assert lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/hint", headers=h).status_code == 200
        assert _check(lab, h, sid, q["question_id"], sql=_doc(fake_db, q["question_id"])["sql"]["reference_sql"]).json()["data"]["correct"]
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        item = next(x for x in res["questions"] if x["question_id"] == q["question_id"])
        assert item["outcome"] == "correct" and item["sql_checks"] == 2 and item["hints_used"] == 1

    def test_reveal_locks_and_scores_zero(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        ref = _doc(fake_db, q["question_id"])["sql"]["reference_sql"]
        d = lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/reveal", headers=h).json()["data"]
        assert d["locked"] and d["feedback"]["reference_sql"] == ref and d["feedback"]["revealed"] and d["feedback"]["expected"]["rows"]
        assert _check(lab, h, sid, q["question_id"], sql=ref).status_code == 409  # cannot launder a revealed answer
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        item = next(x for x in res["questions"] if x["question_id"] == q["question_id"])
        assert item["outcome"] == "incorrect" and item["revealed"] and "revealed" in (item["note"] or "").lower()

    def test_reveal_after_solving_is_not_possible_and_score_stays(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        _check(lab, h, sid, q["question_id"], sql=_doc(fake_db, q["question_id"])["sql"]["reference_sql"])
        assert lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/reveal", headers=h).status_code == 409
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert next(x for x in res["questions"] if x["question_id"] == q["question_id"])["outcome"] == "correct"

    def test_draft_sql_is_saved_restored_and_graded_at_submit(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        ref = _doc(fake_db, q["question_id"])["sql"]["reference_sql"]
        assert _answer(lab, h, sid, q["question_id"], sql=ref).json()["data"]["locked"] is False
        got = next(x for x in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"] if x["question_id"] == q["question_id"])
        assert got["sql_answer"] == ref and got["feedback"] is None
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        item = next(x for x in res["questions"] if x["question_id"] == q["question_id"])
        assert item["outcome"] == "correct" and item["sql_answer"] == ref

    def test_wrong_final_sql_records_the_mistake_for_review(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        _answer(lab, h, sid, q["question_id"], sql="SELECT 1 AS nope")
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        item = next(x for x in res["questions"] if x["question_id"] == q["question_id"])
        assert item["outcome"] == "incorrect" and item["verdict"]["messages"] and item["actual"]["rows"] == [[1]] and item["reference_sql"] and item["expected"]["rows"]

    def test_unanswered_sql_is_unanswered(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert next(x for x in res["questions"] if x["question_id"] == q["question_id"])["outcome"] == "unanswered"

    def test_exam_mode_blocks_check_reveal_and_hint_but_allows_the_sandbox(self, lab, fake_db):
        h = _auth(lab)
        r = _start(lab, h, mode="timed_mock", question_count=50)
        sid = r.json()["data"]["session_id"]
        q = _find(r, "sql")
        for path, code in (("check", "CHECK_NOT_ALLOWED"), ("reveal", "REVEAL_NOT_ALLOWED"), ("hint", "HINT_NOT_ALLOWED")):
            resp = lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/{path}", json={"sql": "SELECT 1"}, headers=h)
            assert resp.status_code == 409 and resp.json()["error_code"] == code
        assert lab.post(f"{URL}/sandbox/run", json={"sql": "SELECT 1"}, headers=h).json()["data"]["ok"]
        ref = _doc(fake_db, q["question_id"])["sql"]["reference_sql"]
        _answer(lab, h, sid, q["question_id"], sql=ref)
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert next(x for x in res["questions"] if x["question_id"] == q["question_id"])["outcome"] == "correct"

    def test_sql_endpoints_reject_wrong_question_kinds(self, lab):
        h = _auth(lab)
        r = _start(lab, h, mode="mixed", question_count=50)
        sid = r.json()["data"]["session_id"]
        mcq = _find(r, "mcq")
        assert _check(lab, h, sid, mcq["question_id"], sql="SELECT 1").status_code == 422
        assert lab.post(f"{URL}/sessions/{sid}/questions/{mcq['question_id']}/reveal", headers=h).status_code == 422
        sql_q = _find(r, "sql")
        assert _answer(lab, h, sid, sql_q["question_id"], 0).status_code == 422
        assert _check(lab, h, sid, sql_q["question_id"], sql="  ").status_code == 422

    def test_check_is_rate_limited(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        codes = [_check(lab, h, sid, q["question_id"], sql="SELECT 1").status_code for _ in range(22)]
        assert codes[:20] == [200] * 20 and codes[20] == 429

    def test_slow_query_in_a_check_does_not_hang_or_crash(self, lab):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        d = _check(lab, h, sid, q["question_id"], sql="WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM c) SELECT count(*) FROM c").json()["data"]
        assert d["correct"] is False and d["run"]["error"]["kind"] == "timeout"


class TestShortAnswers:
    def _short(self, lab, h):
        r = _start(lab, h, mode="design_lab", question_count=50)
        return r.json()["data"]["session_id"], _find(r, "short"), r

    def test_correct_short_answer_locks_with_feedback(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = self._short(lab, h)
        assert q["short"]["kind"] in ("attrs", "keys", "number") and "value" not in q["short"]
        value = _doc(fake_db, q["question_id"])["short"]["value"]
        text = ",".join(value) if q["short"]["kind"] != "number" else str(value)
        d = _check(lab, h, sid, q["question_id"], text=text).json()["data"]
        assert d["correct"] and d["locked"] and d["feedback"]["answer"] and d["feedback"]["explanation"]
        assert _check(lab, h, sid, q["question_id"], text=text).status_code == 409

    def test_wrong_short_answer_also_locks_and_scores_zero(self, lab):
        h = _auth(lab)
        sid, q, _ = self._short(lab, h)
        d = _check(lab, h, sid, q["question_id"], text="ZZZ").json()["data"]
        assert d["correct"] is False and d["locked"] and d["feedback"]["is_correct"] is False
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        item = next(x for x in res["questions"] if x["question_id"] == q["question_id"])
        assert item["outcome"] == "incorrect" and item["correct_answer"]

    def test_draft_text_graded_at_submit(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = self._short(lab, h)
        value = _doc(fake_db, q["question_id"])["short"]["value"]
        _answer(lab, h, sid, q["question_id"], text="".join(value) if q["short"]["kind"] != "number" else str(value))
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert next(x for x in res["questions"] if x["question_id"] == q["question_id"])["outcome"] == "correct"

    def test_empty_short_check_is_422(self, lab):
        h = _auth(lab)
        sid, q, _ = self._short(lab, h)
        assert _check(lab, h, sid, q["question_id"], text="   ").status_code == 422


class TestFinalisation:
    def test_submit_is_idempotent_and_records_attempts_once(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="mixed", question_count=6).json()["data"]["session_id"]
        first = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        n = fake_db[Collections.DBMS_SQL_ATTEMPTS].count_documents({})
        for _ in range(3):
            again = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
            assert again["score"] == first["score"] and again["finished_at"] == first["finished_at"]
        assert fake_db[Collections.DBMS_SQL_ATTEMPTS].count_documents({}) == n == 6
        assert lab.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]["score"] == first["score"]

    def test_attempts_have_a_unique_index_so_a_race_cannot_double_count(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, question_count=3).json()["data"]["session_id"]
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        session = _raw(fake_db, sid)
        sessions._write_attempts(fake_db, session, session["result"])
        sessions._write_attempts(fake_db, session, session["result"])
        assert fake_db[Collections.DBMS_SQL_ATTEMPTS].count_documents({"session_id": session["_id"]}) == 3

    def test_cannot_answer_after_submission(self, lab):
        h = _auth(lab)
        r = _start(lab, h, mode="mixed", question_count=4)
        sid = r.json()["data"]["session_id"]
        q = _find(r, "mcq")
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        resp = _answer(lab, h, sid, q["question_id"], 0)
        assert resp.status_code == 409 and resp.json()["error_code"] == "SESSION_COMPLETED"
        assert lab.post(f"{URL}/sessions/{sid}/questions/{q['question_id']}/hint", headers=h).status_code == 409

    def test_result_requires_a_finished_session(self, lab):
        h = _auth(lab)
        sid = _start(lab, h).json()["data"]["session_id"]
        r = lab.get(f"{URL}/sessions/{sid}/result", headers=h)
        assert r.status_code == 409 and r.json()["error_code"] == "SESSION_NOT_FINISHED"

    def test_result_contains_the_review_material(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="mixed", question_count=20).json()["data"]["session_id"]
        res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
        assert res["status"] == "completed" and res["total_questions"] == 20 and res["scoring_policy"]
        assert all(q["explanation"] and q["outcome"] == "unanswered" for q in res["questions"])
        mcq = next(q for q in res["questions"] if q["interaction"] == "mcq")
        assert mcq["correct_index"] in range(4) and mcq["options"]
        assert res["topic_performance"] and all(t["accuracy"] == 0 for t in res["topic_performance"])

    def test_expired_timed_session_auto_submits(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="timed_mock", question_count=4, timer_minutes=5).json()["data"]["session_id"]
        fake_db[Collections.DBMS_SQL_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"started_at": datetime.now(UTC) - timedelta(minutes=20), "expires_at": datetime.now(UTC) - timedelta(minutes=15)}})
        got = lab.get(f"{URL}/sessions/{sid}", headers=h)
        assert got.status_code == 200 and got.json()["data"]["status"] == "completed"
        res = lab.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
        assert res["auto_submitted"] is True and res["time_taken_seconds"] <= 5 * 60

    def test_answers_after_expiry_are_refused_and_trigger_auto_submit(self, lab, fake_db):
        h = _auth(lab)
        r = _start(lab, h, mode="timed_mock", question_count=4, timer_minutes=5)
        sid = r.json()["data"]["session_id"]
        q = _find(r, "mcq")
        fake_db[Collections.DBMS_SQL_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(minutes=1)}})
        resp = _answer(lab, h, sid, q["question_id"], 0)
        assert resp.status_code == 409 and resp.json()["error_code"] == "SESSION_EXPIRED"
        assert _raw(fake_db, sid)["status"] == "completed"

    def test_stale_open_sessions_are_swept_on_the_next_start(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="timed_mock", question_count=3, timer_minutes=1).json()["data"]["session_id"]
        fake_db[Collections.DBMS_SQL_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(minutes=1)}})
        _start(lab, h)
        assert _raw(fake_db, sid)["status"] == "completed"


class TestOwnership:
    def test_other_users_cannot_touch_a_session(self, lab):
        a, b = _auth(lab, "a@example.com"), _auth(lab, "b@example.com")
        r = _start(lab, a, mode="mixed", question_count=50)
        sid = r.json()["data"]["session_id"]
        mcq, sql_q = _find(r, "mcq"), _find(r, "sql")
        qid = mcq["question_id"]
        probes = [
            lab.get(f"{URL}/sessions/{sid}", headers=b), lab.get(f"{URL}/sessions/{sid}/result", headers=b), lab.post(f"{URL}/sessions/{sid}/submit", headers=b),
            _answer(lab, b, sid, qid, 0), _check(lab, b, sid, sql_q["question_id"], sql="SELECT 1"),
            lab.post(f"{URL}/sessions/{sid}/questions/{sql_q['question_id']}/hint", headers=b), lab.post(f"{URL}/sessions/{sid}/questions/{sql_q['question_id']}/reveal", headers=b),
        ]
        for p in probes:
            assert p.status_code == 404 and p.json()["error_code"] == "NOT_FOUND"
        assert lab.get(f"{URL}/sessions/{sid}", headers=a).status_code == 200

    def test_missing_and_foreign_sessions_are_indistinguishable(self, lab):
        a, b = _auth(lab, "a2@example.com"), _auth(lab, "b2@example.com")
        sid = _start(lab, a).json()["data"]["session_id"]
        foreign = lab.get(f"{URL}/sessions/{sid}", headers=b)
        missing = lab.get(f"{URL}/sessions/{'0' * 24}", headers=b)
        assert foreign.status_code == missing.status_code == 404 and foreign.json() == missing.json()

    def test_history_and_progress_are_per_user(self, lab):
        a, b = _auth(lab, "a3@example.com"), _auth(lab, "b3@example.com")
        sid = _start(lab, a).json()["data"]["session_id"]
        lab.post(f"{URL}/sessions/{sid}/submit", headers=a)
        assert lab.get(f"{URL}/sessions", headers=a).json()["data"]["total"] == 1
        assert lab.get(f"{URL}/sessions", headers=b).json()["data"]["total"] == 0
        assert lab.get(f"{URL}/progress", headers=b).json()["data"]["questions_presented"] == 0

    @pytest.mark.parametrize("bad", ["abc", "g" * 24, "A" * 24, "1" * 23])
    def test_malformed_session_ids_are_422(self, lab, bad):
        assert lab.get(f"{URL}/sessions/{bad}", headers=_auth(lab)).status_code == 422

    def test_malformed_question_ids_are_422(self, lab):
        h = _auth(lab)
        assert lab.put(f"{URL}/sessions/{'a' * 24}/answers/not-a-qid", json={"selected_index": 0}, headers=h).status_code == 422
        assert lab.post(f"{URL}/sessions/{'a' * 24}/questions/dbq-XYZ/hint", headers=h).status_code == 422

    def test_history_pagination_is_bounded(self, lab):
        h = _auth(lab)
        assert lab.get(f"{URL}/sessions", params={"limit": 51}, headers=h).status_code == 422
        assert lab.get(f"{URL}/sessions", params={"page": 0}, headers=h).status_code == 422


MCQ_TOPIC = "execution-plans"  # every question in this topic is multiple choice, so scenarios below do not depend on exact content sizes


def _size(db, topic=MCQ_TOPIC):
    assert db[Collections.DBMS_SQL_QUESTIONS].count_documents({"topic_id": topic, "status": "active", "interaction": {"$ne": "mcq"}}) == 0
    return db[Collections.DBMS_SQL_QUESTIONS].count_documents({"topic_id": topic, "status": "active"})


def _play_session(lab, fake_db, h, topic, n, pattern):
    """Answer MCQs of a topic session according to a c/i/u pattern and submit. Returns the result."""
    r = _start(lab, h, mode="topic", topic_ids=[topic], question_count=n)
    sid = r.json()["data"]["session_id"]
    qs = [q for q in _qs(r) if q["interaction"] == "mcq"]
    for q, p in zip(qs, pattern):
        if p == "u":
            continue
        good = _displayed_correct(fake_db, sid, q["question_id"])
        _answer(lab, h, sid, q["question_id"], good if p == "c" else (good + 1) % 4)
    return lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]


class TestAnalytics:
    def test_empty_state_is_empty_not_invented(self, lab):
        d = lab.get(f"{URL}/progress", headers=_auth(lab)).json()["data"]
        assert d["sessions_completed"] == 0 and d["questions_answered"] == 0 and d["accuracy"] == 0 and d["topic_accuracy"] == [] and d["weak_topics"] == []
        assert d["trend"] == [] and d["improvement_points"] is None and d["mock_interviews"] == [] and d["sql"]["solved"] == 0
        rec = lab.get(f"{URL}/recommendations", headers=_auth(lab, "r@example.com")).json()["data"]
        assert rec["has_history"] is False and rec["weak_topics"] == []

    def test_accuracy_matches_the_recorded_answers(self, lab, fake_db):
        h = _auth(lab)
        res = _play_session(lab, fake_db, h, MCQ_TOPIC, 3, "cci")
        assert res["correct"] == 2
        d = lab.get(f"{URL}/progress", headers=h).json()["data"]
        assert d["sessions_completed"] == 1 and d["questions_answered"] == 3 and d["correct"] == 2 and d["accuracy"] == 66.7
        topic = next(t for t in d["topic_accuracy"] if t["topic_id"] == MCQ_TOPIC)
        assert topic["answered"] == 3 and topic["correct"] == 2 and topic["accuracy"] == 66.7
        unit = next(u for u in d["unit_accuracy"] if u["unit_id"] == "unit-c")
        assert unit["answered"] == 3 and unit["correct"] == 2
        assert sum(x["answered"] for x in d["difficulty_accuracy"]) == 3

    def test_unanswered_questions_do_not_count_toward_accuracy(self, lab, fake_db):
        h = _auth(lab)
        _play_session(lab, fake_db, h, MCQ_TOPIC, 4, "cuuu")
        d = lab.get(f"{URL}/progress", headers=h).json()["data"]
        assert d["questions_answered"] == 1 and d["unanswered"] >= 3 and d["accuracy"] == 100.0

    def test_weak_topics_use_thresholds_and_drive_weak_mode(self, lab, fake_db):
        h = _auth(lab)
        res = _play_session(lab, fake_db, h, MCQ_TOPIC, _size(fake_db), "iiiii")
        assert res["incorrect"] == 5
        weak = lab.get(f"{URL}/progress", headers=h).json()["data"]["weak_topics"]
        assert [w["topic_id"] for w in weak] == [MCQ_TOPIC] and weak[0]["accuracy"] == 0.0 and weak[0]["answered"] == 5 and weak[0]["unit_id"] == "unit-c"
        rec = lab.get(f"{URL}/recommendations", headers=h).json()["data"]
        assert rec["has_history"] and rec["weak_topics"][0]["topic_id"] == MCQ_TOPIC and rec["incorrect_question_count"] == 5
        r = _start(lab, h, mode="weak", question_count=5)
        assert r.status_code == 201 and {q["topic_id"] for q in _qs(r)} == {MCQ_TOPIC}

    def test_below_the_minimum_sample_a_topic_is_not_called_weak(self, lab, fake_db):
        h = _auth(lab)
        _play_session(lab, fake_db, h, MCQ_TOPIC, _size(fake_db), "iiii")  # only 4 answered (< 5)
        assert lab.get(f"{URL}/progress", headers=h).json()["data"]["weak_topics"] == []

    def test_a_strong_topic_is_not_weak(self, lab, fake_db):
        h = _auth(lab)
        res = _play_session(lab, fake_db, h, MCQ_TOPIC, _size(fake_db), "ccccc")
        assert res["correct"] == 5
        assert lab.get(f"{URL}/progress", headers=h).json()["data"]["weak_topics"] == []
        r = _start(lab, h, mode="weak")
        assert r.status_code == 409 and r.json()["error_code"] == "NO_WEAK_AREAS"

    def test_repeated_mistakes_are_surfaced(self, lab, fake_db):
        h = _auth(lab)
        for _ in range(2):
            _play_session(lab, fake_db, h, MCQ_TOPIC, _size(fake_db), "iiiii")
        d = lab.get(f"{URL}/progress", headers=h).json()["data"]
        # two random sets of five out of N questions overlap in at least 10 - N of them
        assert max(1, 10 - _size(fake_db)) <= len(d["repeated_mistakes"]) <= 5 and all(m["times_incorrect"] == 2 and m["topic_id"] == MCQ_TOPIC for m in d["repeated_mistakes"])

    def test_sql_stats_count_checks_and_solves(self, lab, fake_db):
        h = _auth(lab)
        sid, q, _ = _sql_session(lab, h)
        _check(lab, h, sid, q["question_id"], sql="SELECT 1")
        _check(lab, h, sid, q["question_id"], sql="SELECT 2")
        _check(lab, h, sid, q["question_id"], sql=_doc(fake_db, q["question_id"])["sql"]["reference_sql"])
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        s = lab.get(f"{URL}/progress", headers=h).json()["data"]["sql"]
        assert s["queries_checked"] == 3 and s["solved"] == 1 and s["questions_answered"] == 1 and s["success_rate"] == 100.0

    def test_mock_interview_scores_and_trend(self, lab, fake_db):
        h = _auth(lab)
        for i in range(4):
            sid = _start(lab, h, mode="timed_mock" if i % 2 == 0 else "mixed", question_count=5).json()["data"]["session_id"]
            lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        d = lab.get(f"{URL}/progress", headers=h).json()["data"]
        assert len(d["mock_interviews"]) == 2 and len(d["trend"]) == 4 and d["improvement_points"] == 0.0
        assert all(m["total"] == 5 for m in d["mock_interviews"])

    def test_results_are_recorded_only_once_even_if_a_session_is_resubmitted(self, lab, fake_db):
        h = _auth(lab)
        sid = _start(lab, h, mode="topic", topic_ids=["keys"], question_count=3).json()["data"]["session_id"]
        for _ in range(4):
            lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        assert lab.get(f"{URL}/progress", headers=h).json()["data"]["questions_presented"] == 3

    def test_time_per_question_is_reported(self, lab, fake_db):
        h = _auth(lab)
        r = _start(lab, h, mode="topic", topic_ids=[MCQ_TOPIC], question_count=2)
        sid = r.json()["data"]["session_id"]
        fake_db[Collections.DBMS_SQL_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"started_at": datetime.now(UTC) - timedelta(seconds=100)}})
        q = next(x for x in _qs(r) if x["interaction"] == "mcq")
        _answer(lab, h, sid, q["question_id"], _displayed_correct(fake_db, sid, q["question_id"]), time_spent_seconds=42)
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        assert lab.get(f"{URL}/progress", headers=h).json()["data"]["average_seconds_per_answered_question"] == 42.0


class TestHistoryIntegration:
    def test_session_appears_in_the_history_center(self, lab):
        h = _auth(lab)
        sid = _start(lab, h, mode="timed_mock", question_count=4).json()["data"]["session_id"]
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        items = lab.get("/api/v1/history", headers=h).json()["data"]["items"]
        item = next(i for i in items if i["id"] == sid)
        assert item["type"] == "dbms_sql" and item["type_label"] == "DBMS & SQL" and item["status"] == "completed" and "Timed Mock" in item["title"]
        assert item["score"] == 0 and item["metadata"]["question_count"] == 4

    def test_history_detail_returns_the_result_and_hides_other_users(self, lab):
        a, b = _auth(lab, "ha@example.com"), _auth(lab, "hb@example.com")
        sid = _start(lab, a).json()["data"]["session_id"]
        lab.post(f"{URL}/sessions/{sid}/submit", headers=a)
        d = lab.get(f"/api/v1/history/dbms_sql/{sid}", headers=a)
        assert d.status_code == 200 and "questions" in str(d.json())
        assert lab.get(f"/api/v1/history/dbms_sql/{sid}", headers=b).status_code == 404

    def test_in_progress_history_detail_is_answer_free(self, lab):
        h = _auth(lab)
        sid = _start(lab, h, mode="mixed", question_count=20).json()["data"]["session_id"]
        d = lab.get(f"/api/v1/history/dbms_sql/{sid}", headers=h)
        assert d.status_code == 200 and not (SECRET & set(_walk(d.json())))

    def test_history_type_filter(self, lab):
        h = _auth(lab)
        sid = _start(lab, h).json()["data"]["session_id"]
        lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        r = lab.get("/api/v1/history", params={"type": "dbms_sql"}, headers=h)
        assert r.status_code == 200 and all(i["type"] == "dbms_sql" for i in r.json()["data"]["items"]) and r.json()["data"]["items"]


class TestErrorFormat:
    def test_errors_are_consistent(self, lab):
        h = _auth(lab)
        r = _start(lab, h, mode="weak")
        body = r.json()
        assert body["success"] is False and body["error_code"] and body["message"]
        assert lab.get(f"{URL}/sessions/{'0' * 24}", headers=h).json()["error_code"] == "NOT_FOUND"
        assert "Traceback" not in lab.post(f"{URL}/sessions", json={"mode": "x"}, headers=h).text
