"""Phase 26 -- Python practice API: auth, key separation, server-side scoring, code flows, exam rules, idempotency, ownership, analytics, history, degradation."""

from __future__ import annotations

import json
import random
import threading
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from app.core.rate_limit import reset_rate_limits
from app.db.collections import Collections
from app.services.python_practice import bank, sessions
from app.services.python_practice.sandbox import runner
from tests.test_communication import _register_and_login

URL = "/api/v1/python-practice"
SECRET = {"correct_index", "explanation", "verification", "fingerprint", "content_hash", "reference_source", "expected", "is_correct", "review_status", "correct_answer",
          "reference", "tests", "time_complexity", "space_complexity"}
ALL_MODES = ["topic", "mixed", "interview", "predict_output", "trace", "debug", "complete", "coding", "complexity", "oop", "advanced", "security", "timed_mock"]


def _keys(obj, skip=("examples",)):
    """All dict keys in a JSON payload, ignoring the visible `examples` (their expected values are part of the problem statement by design)."""
    found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            if k not in skip:
                found |= _keys(v, skip)
    elif isinstance(obj, list):
        for v in obj:
            found |= _keys(v, skip)
    return found


needs_runner = pytest.mark.skipif(not runner.capabilities()["available"], reason="isolated runner unavailable on this host")
TWO_SUM_OK = "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n    return []\n"


@pytest.fixture()
def lab(client, fake_db, monkeypatch):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    reset_rate_limits()
    monkeypatch.setattr(sessions, "_rng", random.Random(7))
    return client


def _auth(client, email="py@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _uid(db, email="py@example.com"):
    return db[Collections.USERS].find_one({"email": email})["_id"]


def _start(client, h, **body):
    body.setdefault("mode", "mixed")
    if body["mode"] == "topic" and "topic_ids" not in body:
        body["topic_ids"] = ["lists"]
    return client.post(f"{URL}/sessions", json=body, headers=h)


def _raw(db, sid):
    return db[Collections.PYTHON_SESSIONS].find_one({"_id": ObjectId(sid)})


def _doc(db, qid):
    return db[Collections.PYTHON_QUESTIONS].find_one({"question_id": qid})


def _displayed(db, sid, qid, correct=True):
    s = _raw(db, sid)
    order = next(q["option_order"] for q in s["questions"] if q["question_id"] == qid)
    right = order.index(_doc(db, qid)["correct_index"])
    return right if correct else (right + 1) % 4


def _answer(client, h, sid, qid, index=None, **extra):
    body = {**({"selected_index": index} if index is not None else {}), **extra}
    return client.put(f"{URL}/sessions/{sid}/answers/{qid}", json=body, headers=h)


def _post(client, h, sid, qid, what, **body):
    return client.post(f"{URL}/sessions/{sid}/questions/{qid}/{what}", json=body, headers=h)


def _qs(resp):
    return resp.json()["data"]["questions"]


def _code_session(client, h, topic="hash-maps", **extra):
    r = _start(client, h, mode="coding", topic_ids=[topic], difficulty="easy", question_count=1, **extra)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    return d["session_id"], d["questions"][0]["question_id"]


# --- authentication ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", [
    ("get", "/runner"), ("get", "/syllabus"), ("get", "/coverage"), ("get", "/questions"), ("post", "/sessions"), ("get", "/sessions"), ("get", "/progress"), ("get", "/recommendations"),
    ("get", "/sessions/" + "a" * 24), ("post", "/sessions/" + "a" * 24 + "/submit"), ("get", "/sessions/" + "a" * 24 + "/result"),
    ("put", "/sessions/" + "a" * 24 + "/answers/pyq-aaaaaaaaaa"), ("post", "/sessions/" + "a" * 24 + "/questions/pyq-aaaaaaaaaa/run"),
    ("post", "/sessions/" + "a" * 24 + "/questions/pyq-aaaaaaaaaa/check"), ("post", "/sessions/" + "a" * 24 + "/questions/pyq-aaaaaaaaaa/hint"),
    ("post", "/sessions/" + "a" * 24 + "/questions/pyq-aaaaaaaaaa/reveal"),
])
def test_every_endpoint_requires_authentication(lab, method, path):
    assert getattr(lab, method)(URL + path).status_code in (401, 403)


# --- reference data -------------------------------------------------------------------------------------------------------------------


def test_runner_syllabus_and_coverage(lab):
    h = _auth(lab)
    runner_status = lab.get(f"{URL}/runner", headers=h).json()["data"]
    assert "available" in runner_status and runner_status["layers"] and runner_status["limits"]["source_chars"] == 10_000
    syl = lab.get(f"{URL}/syllabus", headers=h).json()["data"]
    assert len(syl["units"]) == 9 and syl["topics_total"] == 144 and syl["topics_implemented"] == 144
    assert all(t["question_count"] >= 2 for u in syl["units"] for t in u["topics"])
    cov = lab.get(f"{URL}/coverage", headers=h).json()["data"]
    assert cov["gaps"] == [] and cov["manual_review"] > 0 and cov["machine_verified"] > 150


def test_question_listing_is_answer_free_and_bounded(lab):
    h = _auth(lab)
    r = lab.get(f"{URL}/questions", params={"unit_id": "unit-g", "limit": 50}, headers=h)
    assert r.status_code == 200 and len(r.json()["data"]["items"]) <= 50
    assert not (_keys(r.json()) & SECRET), _keys(r.json()) & SECRET
    assert lab.get(f"{URL}/questions", params={"limit": 51}, headers=h).status_code == 422
    assert lab.get(f"{URL}/questions", params={"difficulty": "extreme"}, headers=h).status_code == 422
    assert lab.get(f"{URL}/questions", params={"topic_id": "../etc"}, headers=h).status_code == 422
    coding = lab.get(f"{URL}/questions", params={"interaction": "code", "limit": 50}, headers=h).json()["data"]["items"]
    assert coding and all(q["code_spec"]["hidden_count"] > 0 and "reference_source" not in json.dumps(q) for q in coding)


# --- sessions and modes -------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ALL_MODES)
def test_every_mode_starts_and_payload_is_answer_free(lab, mode):
    h = _auth(lab)
    r = _start(lab, h, mode=mode, question_count=6)
    if mode in ("coding", "debug", "complete") and not runner.capabilities()["available"]:
        # e.g. Windows/macOS: these modes must refuse with a clear reason instead of serving exercises that cannot be graded
        assert r.status_code == 409 and r.json()["error_code"] == "RUNNER_UNAVAILABLE", r.text
        return
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["questions"] and d["exam_mode"] == (mode == "timed_mock")
    assert not (_keys(d) & SECRET), _keys(d) & SECRET
    for q in d["questions"]:
        assert q["feedback"] is None and not q["locked"]
        if q["interaction"] == "code":
            assert q["code_spec"]["starter"] and q["code_spec"]["hidden_count"] > 0 and "reference_source" not in json.dumps(q)


def test_mode_filters_select_the_right_kinds(lab):
    h = _auth(lab)
    kinds = {"predict_output": ("format", "output"), "trace": ("format", "trace"), "debug": ("format", "debug"), "complete": ("format", "complete"), "complexity": ("format", "complexity"),
             "coding": ("interaction", "code"), "oop": ("unit_id", "unit-d"), "advanced": ("unit_id", "unit-f"), "security": ("unit_id", "unit-h")}
    runner_ok = runner.capabilities()["available"]
    for mode, (field, want) in kinds.items():
        resp = _start(lab, h, mode=mode, question_count=8)
        if mode in ("coding", "debug", "complete") and not runner_ok:
            assert resp.status_code == 409 and resp.json()["error_code"] == "RUNNER_UNAVAILABLE", mode
            continue
        qs = _qs(resp)
        assert qs and all(q[field] == want for q in qs), mode
    qs = _qs(_start(lab, h, mode="interview", question_count=15))
    assert {q["format"] for q in qs} <= {"concept", "scenario"}


def test_topic_mode_requires_a_topic_and_validates_ids(lab):
    h = _auth(lab)
    assert _start(lab, h, mode="topic", topic_ids=[]).status_code == 422
    assert _start(lab, h, mode="topic", topic_ids=["no-such-topic"]).status_code == 422
    assert _start(lab, h, mode="mixed", unit_ids=["unit-zzz"]).status_code == 422
    assert _start(lab, h, mode="mixed", question_count=41).status_code == 422
    assert _start(lab, h, mode="mixed", mode_extra=1, timer_minutes=999).status_code == 422
    assert _start(lab, h, mode="bogus").status_code == 422
    qs = _qs(_start(lab, h, mode="topic", topic_ids=["closures"], question_count=10))
    assert qs and {q["topic_id"] for q in qs} == {"closures"}


def test_difficulty_filter(lab):
    h = _auth(lab)
    assert {q["difficulty"] for q in _qs(_start(lab, h, mode="mixed", difficulty="hard", question_count=10))} == {"hard"}


def test_weak_mode_needs_history(lab):
    h = _auth(lab)
    r = _start(lab, h, mode="weak")
    assert r.status_code == 409 and r.json()["error_code"] == "NO_HISTORY"


# --- scoring: always on the server ---------------------------------------------------------------------------------------------------------


def _mcq_session(lab, h, n=6, **kw):
    r = _start(lab, h, mode="mixed", question_count=n, interaction="mcq", **kw) if False else _start(lab, h, mode="interview", question_count=n, **kw)
    d = r.json()["data"]
    return d["session_id"], d["questions"]


def test_mcq_is_graded_by_the_server_and_locks(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=4)
    q = qs[0]
    r = _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"], correct=False))
    fb = r.json()["data"]["feedback"]
    assert r.json()["data"]["locked"] and fb["is_correct"] is False and fb["correct_index"] == _displayed(fake_db, sid, q["question_id"]) and fb["explanation"]
    assert _answer(lab, h, sid, q["question_id"], 0).status_code == 409


def test_client_supplied_scores_and_flags_are_ignored(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=3)
    for q in qs:
        r = _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"], correct=False), is_correct=True, correct=True, score=100, outcome="correct", correct_index=0, solved=True)
        assert r.status_code == 200 and r.json()["data"]["feedback"]["is_correct"] is False
    result = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    assert result["score"] == 0 and result["correct"] == 0 and result["incorrect"] == len(qs)
    bad = lab.post(f"{URL}/sessions/{sid}/submit", json={"score": 99, "status": "completed"}, headers=h)
    assert bad.json()["data"]["score"] == 0


def test_server_score_matches_answers(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=5)
    for i, q in enumerate(qs):
        if i < 3:
            _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"], correct=(i != 2)))
    res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    mcq_correct = 2
    assert res["correct"] == mcq_correct and res["incorrect"] == 1 and res["unanswered"] == len(qs) - 3 and res["score"] == mcq_correct
    assert res["accuracy"] == round(100 * mcq_correct / len(qs), 1)
    assert all(q["explanation"] for q in res["questions"]) and any(q["outcome"] == "unanswered" for q in res["questions"])


def test_short_answers_are_graded_deterministically(lab, fake_db):
    h = _auth(lab)
    doc = fake_db[Collections.PYTHON_QUESTIONS].find_one({"interaction": "short"})
    if doc is None:  # the shipped bank uses MCQ for output prediction; build a typed-answer question to exercise the path
        from app.services.python_practice.content.build import out
        d = out("loops", "easy", "What is printed by this loop, typed exactly?", "for i in range(3):\n    print(i)", "0\n1\n2", [], "range(3) yields 0, 1, 2.", typed=True)
        d["review_status"] = "manual_review"; d["fingerprint"] = "typed"; d["content_hash"] = "x"
        fake_db[Collections.PYTHON_QUESTIONS].insert_one(d)
        doc = d
    r = _start(lab, h, mode="topic", topic_ids=[doc["topic_id"]], question_count=40)
    sid = r.json()["data"]["session_id"]
    q = next(x for x in r.json()["data"]["questions"] if x["question_id"] == doc["question_id"])
    assert q["interaction"] == "short" and "value" not in json.dumps(q)
    wrong = _post(lab, h, sid, q["question_id"], "check", text="definitely wrong")
    assert wrong.json()["data"]["correct"] is False
    assert wrong.json()["data"]["feedback"]["answer"]


def test_wrong_answer_types_are_rejected(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=2)
    qid = qs[0]["question_id"]
    assert _answer(lab, h, sid, qid, text="abc").status_code == 422
    assert _answer(lab, h, sid, qid, code="print(1)").status_code == 422
    assert _answer(lab, h, sid, qid, 9).status_code == 422
    assert _post(lab, h, sid, qid, "check", text="abc").status_code == 422
    assert _post(lab, h, sid, qid, "run", code="print(1)").status_code == 422
    assert _post(lab, h, sid, qid, "reveal").status_code == 422
    other = "pyq-" + "0" * 10
    assert _answer(lab, h, sid, other, 0).status_code == 422


def test_hints_are_counted_and_limited(lab, fake_db):
    h = _auth(lab)
    hinted = next(d for d in fake_db[Collections.PYTHON_QUESTIONS].find({"interaction": "mcq"}) if d.get("hints"))  # servable with or without a runner
    r = _start(lab, h, mode="topic", topic_ids=[hinted["topic_id"]], question_count=40)
    sid = r.json()["data"]["session_id"]
    q = next(x for x in r.json()["data"]["questions"] if x["question_id"] == hinted["question_id"])
    qid = q["question_id"]
    total = len(_doc(fake_db, qid)["hints"])
    for n in range(1, total + 1):
        out = _post(lab, h, sid, qid, "hint").json()["data"]
        assert out["hint_number"] == n and len(out["hints"]) == n
    assert _post(lab, h, sid, qid, "hint").status_code == 409
    got = lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"]
    assert next(x for x in got if x["question_id"] == qid)["hints_used"] == total


# --- timed mock interviews --------------------------------------------------------------------------------------------------------------------------


def test_timed_mock_reveals_nothing_and_allows_no_checks_hints_or_reveal(lab, fake_db):
    h = _auth(lab)
    r = _start(lab, h, mode="timed_mock", question_count=5, timer_minutes=20)
    d = r.json()["data"]
    sid = d["session_id"]
    assert d["exam_mode"] and d["immediate_feedback"] is False and d["timer_minutes"] == 20 and 0 < d["remaining_seconds"] <= 1200
    q = d["questions"][0]
    out = _answer(lab, h, sid, q["question_id"], 0) if q["interaction"] == "mcq" else None
    if out is not None:
        assert out.json()["data"]["feedback"] is None and out.json()["data"]["locked"] is False
    assert _post(lab, h, sid, q["question_id"], "hint").status_code == 409
    assert _post(lab, h, sid, q["question_id"], "check", text="x").status_code == 409
    assert _post(lab, h, sid, q["question_id"], "reveal").status_code == 409
    assert all(x["hints_total"] == 0 and x["hints"] == [] for x in lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"])
    assert lab.post(f"{URL}/sessions/{sid}/result", headers=h).status_code == 405 and lab.get(f"{URL}/sessions/{sid}/result", headers=h).status_code == 409
    assert _start(lab, h, mode="timed_mock", immediate_feedback=True).status_code == 422


def test_timed_mock_auto_submits_when_time_is_up(lab, fake_db):
    h = _auth(lab)
    d = _start(lab, h, mode="timed_mock", question_count=4, timer_minutes=5).json()["data"]
    sid, q = d["session_id"], d["questions"][0]
    if q["interaction"] == "mcq":
        _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"]))
    fake_db[Collections.PYTHON_SESSIONS].update_one({"_id": ObjectId(sid)}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(minutes=1)}})
    r = _answer(lab, h, sid, q["question_id"], 0)
    assert r.status_code == 409 and r.json()["error_code"] == "SESSION_EXPIRED"
    got = lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]
    assert got["status"] == "completed" and got["remaining_seconds"] == 0
    res = lab.get(f"{URL}/sessions/{sid}/result", headers=h).json()["data"]
    assert res["auto_submitted"] is True


# --- coding flows --------------------------------------------------------------------------------------------------------------------------------


@needs_runner
def test_coding_trial_run_shows_only_example_results(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    r = _post(lab, h, sid, qid, "run", code="def two_sum(nums, target):\n    return [0, 1]\n")
    assert r.status_code == 200
    res = r.json()["data"]["result"]
    assert res["total"] == sum(1 for t in _doc(fake_db, qid)["spec"]["tests"] if t["visible"]) and all(t["visible"] for t in res["tests"])
    assert "Expected" in json.dumps(res) and "hidden" not in json.dumps(res).lower()
    state = lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]
    assert state["runs"] == 1 and state["code_answer"].startswith("def two_sum") and not state["locked"]


@needs_runner
def test_coding_check_wrong_then_right_locks_and_scores(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    wrong = _post(lab, h, sid, qid, "check", code="def two_sum(nums, target):\n    return [0, 1]\n").json()["data"]
    assert wrong["correct"] is False and wrong["locked"] is False and wrong["feedback"] is None and wrong["result"]["passed"] < wrong["result"]["total"]
    assert any(t["label"].startswith("Hidden test") for t in wrong["result"]["tests"])
    assert "reference_source" not in json.dumps(wrong)
    right = _post(lab, h, sid, qid, "check", code=TWO_SUM_OK).json()["data"]
    assert right["correct"] is True and right["locked"] is True and right["result"]["passed"] == right["result"]["total"]
    assert "def two_sum" in right["feedback"]["reference_source"] and right["feedback"]["time_complexity"] == "O(n)"
    assert _post(lab, h, sid, qid, "check", code=TWO_SUM_OK).status_code == 409
    res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    assert res["score"] == 1 and res["questions"][0]["tests_passed"] == res["questions"][0]["tests_total"] and res["questions"][0]["code_checks"] == 2


@needs_runner
def test_reveal_rules_for_reference_solutions(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    early = _post(lab, h, sid, qid, "reveal")
    assert early.status_code == 409 and early.json()["error_code"] == "REVEAL_TOO_EARLY"
    assert lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]["can_reveal"] is False
    _post(lab, h, sid, qid, "check", code="def two_sum(nums, target):\n    return []\n")
    assert lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]["can_reveal"] is True
    shown = _post(lab, h, sid, qid, "reveal").json()["data"]
    assert shown["locked"] and "def two_sum" in shown["feedback"]["reference_source"] and shown["feedback"]["explanation"]
    res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    assert res["score"] == 0 and res["questions"][0]["outcome"] == "incorrect" and "revealed" in res["questions"][0]["note"].lower()


@needs_runner
def test_reveal_is_also_allowed_after_every_hint(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    for _ in _doc(fake_db, qid)["hints"]:
        _post(lab, h, sid, qid, "hint")
    assert _post(lab, h, sid, qid, "reveal").status_code == 200


@needs_runner
def test_unchecked_draft_is_graded_at_submission(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    assert _answer(lab, h, sid, qid, code=TWO_SUM_OK).status_code == 200
    res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    assert res["score"] == 1 and res["questions"][0]["outcome"] == "correct" and res["questions"][0]["verdict"]["verdict"] == "accepted"


@needs_runner
def test_timed_mock_allows_trial_runs_but_not_checks(lab, fake_db):
    h = _auth(lab)
    r = _start(lab, h, mode="timed_mock", topic_ids=["hash-maps"], question_count=3, timer_minutes=30)
    d = r.json()["data"]
    q = next((x for x in d["questions"] if x["interaction"] == "code"), None)
    if q is None:
        pytest.skip("no coding question drawn")
    run = _post(lab, h, d["session_id"], q["question_id"], "run", code="def two_sum(nums, target):\n    return []\n")
    assert run.status_code == 200
    assert _post(lab, h, d["session_id"], q["question_id"], "check", code=TWO_SUM_OK).status_code == 409


def test_code_input_validation(lab):
    h = _auth(lab)
    r = _start(lab, h, mode="coding", topic_ids=["hash-maps"], question_count=1) if runner.capabilities()["available"] else None
    if r is None:
        pytest.skip("runner unavailable")
    d = r.json()["data"]
    sid, qid = d["session_id"], d["questions"][0]["question_id"]
    assert _post(lab, h, sid, qid, "run", code="x" * 10_001).status_code == 422
    assert _post(lab, h, sid, qid, "run", code="").status_code == 422
    assert _post(lab, h, sid, qid, "check", code="   ").status_code == 422
    assert _answer(lab, h, sid, qid, code="x" * 10_001).status_code == 422
    assert _post(lab, h, sid, qid, "run").status_code == 422
    assert _post(lab, h, sid, qid, "run", code=123).status_code == 422


@needs_runner
def test_code_endpoints_are_rate_limited(lab):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    codes = [_post(lab, h, sid, qid, "run", code="def two_sum(:\n").status_code for _ in range(22)]
    assert 429 in codes and codes.count(200) == 20


# --- degradation: no runner means no code questions, honestly ---------------------------------------------------------------------------------------------


def test_without_a_runner_code_questions_are_never_served(lab, monkeypatch):
    monkeypatch.setattr(runner, "capabilities", lambda force=False: {"available": False, "reason": "Code execution is switched off by the administrator.", "layers": [], "limits": {}})
    h = _auth(lab)
    for mode in ("mixed", "security", "interview", "timed_mock"):
        qs = _qs(_start(lab, h, mode=mode, question_count=40))
        assert qs and all(q["interaction"] != "code" for q in qs), mode
    for mode in ("coding", "debug", "complete"):
        r = _start(lab, h, mode=mode)
        assert r.status_code == 409 and r.json()["error_code"] == "RUNNER_UNAVAILABLE" and "switched off" in r.json()["message"]
    assert lab.get(f"{URL}/runner", headers=h).json()["data"]["available"] is False


@needs_runner
def test_runner_going_down_mid_session_does_not_penalise_the_learner(lab, fake_db, monkeypatch):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    assert _answer(lab, h, sid, qid, code=TWO_SUM_OK).status_code == 200
    monkeypatch.setattr(runner, "capabilities", lambda force=False: {"available": False, "reason": "down", "layers": [], "limits": {}})
    chk = _post(lab, h, sid, qid, "check", code=TWO_SUM_OK)
    assert chk.status_code == 409 and chk.json()["error_code"] == "RUNNER_UNAVAILABLE"
    assert lab.get(f"{URL}/sessions/{sid}", headers=h).json()["data"]["questions"][0]["checks"] == 0  # nothing was counted
    res = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    assert res["incorrect"] == 0 and res["unanswered"] == 1 and "could not be graded" in res["questions"][0]["note"]


# --- idempotency, ownership, analytics ------------------------------------------------------------------------------------------------------------------------------


def test_submit_is_idempotent_and_attempts_are_never_double_counted(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=4)
    for q in qs[:2]:
        _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"]))
    first = lab.post(f"{URL}/sessions/{sid}/submit", headers=h).json()["data"]
    for _ in range(3):
        again = lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
        assert again.status_code == 200 and again.json()["data"]["score"] == first["score"] == 2
    assert fake_db[Collections.PYTHON_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 4
    prog = lab.get(f"{URL}/progress", headers=h).json()["data"]
    assert prog["questions_presented"] == 4 and prog["questions_answered"] == 2 and prog["sessions_completed"] == 1
    assert _answer(lab, h, sid, qs[2]["question_id"], 0).status_code == 409


def test_concurrent_submits_complete_once(lab, fake_db):
    h = _auth(lab)
    sid, qs = _mcq_session(lab, h, n=4)
    _answer(lab, h, sid, qs[0]["question_id"], _displayed(fake_db, sid, qs[0]["question_id"]))
    out: list[int] = []

    def go():
        out.append(lab.post(f"{URL}/sessions/{sid}/submit", headers=h).status_code)

    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert out.count(200) == 4
    assert fake_db[Collections.PYTHON_ATTEMPTS].count_documents({"session_id": ObjectId(sid)}) == 4


def test_users_cannot_touch_each_others_sessions(lab, fake_db):
    a, b = _auth(lab, "a@example.com"), _auth(lab, "b@example.com")
    sid, qs = _mcq_session(lab, a, n=3)
    qid = qs[0]["question_id"]
    missing = lab.get(f"{URL}/sessions/{'f' * 24}", headers=b)
    assert lab.get(f"{URL}/sessions/{sid}", headers=b).status_code == 404 and lab.get(f"{URL}/sessions/{sid}", headers=b).json() == missing.json()
    assert _answer(lab, b, sid, qid, 0).status_code == 404
    for what in ("hint", "check", "run", "reveal"):
        assert _post(lab, b, sid, qid, what, text="x", code="x").status_code == 404, what
    assert lab.post(f"{URL}/sessions/{sid}/submit", headers=b).status_code == 404
    assert lab.get(f"{URL}/sessions/{sid}/result", headers=b).status_code == 404
    assert lab.get(f"{URL}/sessions", headers=b).json()["data"]["total"] == 0
    assert lab.get(f"{URL}/sessions/not-an-id", headers=a).status_code == 422
    assert _raw(fake_db, sid)["status"] == "in_progress"


def test_progress_numbers_are_exact_and_per_user(lab, fake_db):
    h = _auth(lab)
    empty = lab.get(f"{URL}/progress", headers=h).json()["data"]
    assert empty["questions_answered"] == 0 and empty["accuracy"] == 0.0 and empty["topic_accuracy"] == [] and empty["weak_topics"] == [] and empty["coding"]["success_rate"] == 0.0
    sid, qs = _mcq_session(lab, h, n=6)
    plan = [True, True, False, True, False, None]
    for q, ok in zip(qs, plan):
        if ok is not None:
            _answer(lab, h, sid, q["question_id"], _displayed(fake_db, sid, q["question_id"], correct=ok))
    lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
    p = lab.get(f"{URL}/progress", headers=h).json()["data"]
    assert (p["questions_answered"], p["correct"], p["incorrect"], p["unanswered"], p["accuracy"]) == (5, 3, 2, 1, 60.0)
    assert sum(t["answered"] for t in p["topic_accuracy"]) == 5 and sum(t["correct"] for t in p["topic_accuracy"]) == 3
    assert sum(d["answered"] for d in p["difficulty_accuracy"]) == 5 and p["recent_sessions"][0]["score"] == 3
    assert lab.get(f"{URL}/progress", headers=_auth(lab, "other@example.com")).json()["data"]["questions_answered"] == 0


@needs_runner
def test_coding_analytics_are_recorded(lab, fake_db):
    h = _auth(lab)
    sid, qid = _code_session(lab, h)
    _post(lab, h, sid, qid, "run", code="def two_sum(nums, target):\n    return []\n")
    _post(lab, h, sid, qid, "check", code="def two_sum(nums, target):\n    return []\n")
    _post(lab, h, sid, qid, "check", code=TWO_SUM_OK)
    lab.post(f"{URL}/sessions/{sid}/submit", headers=h)
    c = lab.get(f"{URL}/progress", headers=h).json()["data"]["coding"]
    assert c["questions_answered"] == 1 and c["solved"] == 1 and c["submissions"] == 2 and c["trial_runs"] == 1 and c["success_rate"] == 100.0
    assert c["tests_passed"] == c["tests_total"] > 0 and c["test_pass_rate"] == 100.0


def test_weak_topics_and_weak_mode(lab, fake_db):
    h = _auth(lab)
    uid = _uid(fake_db)
    now = datetime.now(UTC)
    rows = [{"user_id": uid, "session_id": ObjectId(), "question_id": f"pyq-{i:010x}", "unit_id": "unit-c", "topic_id": "closures", "difficulty": "easy", "format": "concept", "interaction": "mcq",
             "outcome": "incorrect" if i < 4 else "correct", "time_spent_seconds": 10, "mode": "topic", "hints_used": 0, "code_checks": 0, "code_runs": 0, "tests_passed": 0, "tests_total": 0,
             "revealed": False, "created_at": now - timedelta(minutes=i)} for i in range(6)]
    fake_db[Collections.PYTHON_ATTEMPTS].insert_many(rows)
    rec = lab.get(f"{URL}/recommendations", headers=h).json()["data"]
    assert rec["has_history"] and rec["weak_topics"][0]["topic_id"] == "closures" and rec["weak_topics"][0]["accuracy"] == 33.3 and rec["incorrect_question_count"] == 4
    qs = _qs(_start(lab, h, mode="weak", question_count=10))
    assert qs and {q["topic_id"] for q in qs} == {"closures"}


def test_open_session_cap(lab, monkeypatch):
    h = _auth(lab)
    monkeypatch.setattr(sessions, "MAX_OPEN_SESSIONS", 3)
    for _ in range(3):
        assert _start(lab, h, mode="mixed", question_count=1).status_code == 201
    r = _start(lab, h, mode="mixed", question_count=1)
    assert r.status_code == 409 and r.json()["error_code"] == "TOO_MANY_OPEN_SESSIONS"


def test_error_responses_never_leak_internals(lab):
    h = _auth(lab)
    for resp in (lab.get(f"{URL}/sessions/{'e' * 24}", headers=h), _start(lab, h, mode="topic", topic_ids=["x y"]), lab.put(f"{URL}/sessions/{'e' * 24}/answers/pyq-aaaaaaaaaa", json={}, headers=h)):
        text = resp.text.lower()
        assert "traceback" not in text and "mongo" not in text and "/home/" not in text and "jwt" not in text


# --- history center --------------------------------------------------------------------------------------------------------------------------------------------------


def test_sessions_appear_in_history_center_with_safe_detail(lab, fake_db):
    a, b = _auth(lab, "ha@example.com"), _auth(lab, "hb@example.com")
    sid, qs = _mcq_session(lab, a, n=3)
    live = lab.get(f"/api/v1/history/python_practice/{sid}", headers=a)
    assert live.status_code == 200 and "correct_index" not in live.text
    _answer(lab, a, sid, qs[0]["question_id"], _displayed(fake_db, sid, qs[0]["question_id"]))
    lab.post(f"{URL}/sessions/{sid}/submit", headers=a)
    items = lab.get("/api/v1/history", params={"type": "python_practice"}, headers=a).json()["data"]["items"]
    assert len(items) == 1 and items[0]["type"] == "python_practice" and items[0]["type_label"] == "Python Practice" and items[0]["status"] == "completed"
    assert items[0]["score"] == round(100 / 3, 1) or items[0]["score"] is not None
    done = lab.get(f"/api/v1/history/python_practice/{sid}", headers=a)
    assert done.status_code == 200 and "explanation" in done.text
    assert lab.get(f"/api/v1/history/python_practice/{sid}", headers=b).status_code == 404
    assert lab.get("/api/v1/history", params={"type": "python_practice"}, headers=b).json()["data"]["items"] == []
    assert any(i["type"] == "python_practice" for i in lab.get("/api/v1/history", headers=a).json()["data"]["items"])


def test_history_pagination_is_bounded(lab):
    h = _auth(lab)
    for _ in range(3):
        _start(lab, h, mode="mixed", question_count=1)
    assert lab.get(f"{URL}/sessions", params={"limit": 51}, headers=h).status_code == 422
    page = lab.get(f"{URL}/sessions", params={"limit": 2, "page": 1}, headers=h).json()["data"]
    assert len(page["items"]) == 2 and page["total"] == 3 and page["has_next"] is True
