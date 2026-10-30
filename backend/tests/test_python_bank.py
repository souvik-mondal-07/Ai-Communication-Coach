"""Phase 26 -- Python practice question bank: validation gate, seeding, key separation, coverage, and execution re-verification."""

from __future__ import annotations

import copy

import pytest

from app.db.collections import Collections
from app.services.python_practice import bank, compare
from app.services.python_practice.content import all_seed_questions
from app.services.python_practice.content import build as B
from app.services.python_practice.sandbox import runner
from app.services.python_practice.syllabus import MIN_QUESTIONS_PER_TOPIC, TOPIC_BY_ID, UNITS
from app.services.python_practice.validation import fingerprint, validate_question, verify_question

SECRET_KEYS = {"correct_index", "explanation", "hints", "verification", "fingerprint", "content_hash", "review_status", "reference_source", "reference", "expected", "tests",
               "is_correct", "value", "time_complexity", "space_complexity"}


@pytest.fixture(scope="module")
def seeds():
    valid, rejected = bank.build_valid_seed_bank()
    return valid, rejected


def _mcq():
    return B.mcq("lists", "easy", "Which method appends one item to the end of a list?", "append", ["add", "push", "extend_one"], "list.append(x) adds x at the end of the list.")


def _problems(doc):
    doc = copy.deepcopy(doc)
    doc["review_status"] = verify_question(doc)
    return validate_question(doc)


def test_every_seed_is_accepted_and_none_rejected(seeds):
    valid, rejected = seeds
    assert rejected == [], rejected[:3]
    assert len(valid) >= 300


def test_every_topic_meets_the_minimum_and_every_unit_has_all_three_difficulties(seeds):
    valid, _ = seeds
    per_topic: dict[str, int] = {}
    per_unit: dict[str, set] = {}
    for q in valid:
        per_topic[q["topic_id"]] = per_topic.get(q["topic_id"], 0) + 1
        per_unit.setdefault(q["unit_id"], set()).add(q["difficulty"])
    assert [t for t in TOPIC_BY_ID if per_topic.get(t, 0) < MIN_QUESTIONS_PER_TOPIC] == []
    assert all(levels == {"easy", "medium", "hard"} for levels in per_unit.values()) and len(per_unit) == len(UNITS)


def test_all_exercise_types_are_present(seeds):
    valid, _ = seeds
    assert {q["format"] for q in valid} == {"concept", "output", "trace", "debug", "complete", "coding", "complexity", "scenario"}
    assert {q["interaction"] for q in valid} == {"mcq", "code"}


def test_ids_and_fingerprints_are_unique_and_stable(seeds):
    valid, _ = seeds
    assert len({q["question_id"] for q in valid}) == len(valid) == len({q["fingerprint"] for q in valid})
    again = {q["question_id"] for q in all_seed_questions()}
    assert again == {q["question_id"] for q in valid}


def test_mcq_options_are_distinct_with_exactly_one_correct(seeds):
    for q in seeds[0]:
        if q["interaction"] == "mcq":
            opts = [B.norm(o) for o in q["options"]]
            assert len(opts) == 4 and len(set(opts)) == 4, q["statement"]
            assert 0 <= q["correct_index"] <= 3


def test_correct_option_position_is_not_constant(seeds):
    positions = {q["correct_index"] for q in seeds[0] if q["interaction"] == "mcq"}
    assert positions == {0, 1, 2, 3}


def test_public_projection_never_contains_secrets(seeds):
    for q in seeds[0]:
        pub = bank.to_public(q)
        assert not (set(pub) & SECRET_KEYS), set(pub) & SECRET_KEYS
        if pub["code_spec"]:
            assert not (set(pub["code_spec"]) & SECRET_KEYS)
            for ex in pub["code_spec"]["examples"]:
                assert set(ex) == {"id", "label", "input", "expected"}
        flat = repr(pub)
        if q["interaction"] == "code":
            assert q["spec"]["reference_source"] not in flat
            hidden = [t for t in q["spec"]["tests"] if not t["visible"]]
            assert pub["code_spec"]["hidden_count"] == len(hidden) > 0
        if q["interaction"] == "mcq":
            assert q["explanation"] not in flat


def test_coding_problems_have_visible_and_hidden_tests_with_edge_cases(seeds):
    code = [q for q in seeds[0] if q["interaction"] == "code"]
    assert len(code) >= 40
    for q in code:
        tests = q["spec"]["tests"]
        assert len(tests) >= 6 and any(t["visible"] for t in tests) and sum(1 for t in tests if not t["visible"]) >= 3
        assert q["verification"]["method"] == "reference" and q["verification"]["independent_solution"] is True
        assert q["hints"], q["title"]


def test_expected_values_are_consistent_with_two_independent_solutions():
    """The builder refuses a problem whose reference and independent solution disagree."""
    def ref(a): return a + 1
    def alt_wrong(a): return a + 2
    doc = B.code_q("loops", "easy", "coding", "T", "Add one to the number, a long enough statement.", "ref", "def ref(a):", "def ref(a):\n    pass", ref, alt_wrong, [(1,), (2,), (3,), (4,), (5,), (6,)], time_c="O(1)", space_c="O(1)", expl="Because adding one is the point.", hints=("h",))
    assert doc["verification"]["method"] == "failed"
    assert any("disagree" in p for p in _problems(doc))


def test_problem_without_an_independent_solution_is_rejected():
    def ref(a): return a
    doc = B.code_q("loops", "easy", "coding", "T2", "Return the number unchanged, a long enough statement.", "ref", "def ref(a):", "def ref(a):\n    pass", ref, None, [(1,), (2,), (3,), (4,), (5,), (6,)], time_c="O(1)", space_c="O(1)", expl="Identity function explanation.", hints=("h",))
    assert doc["verification"]["method"] == "failed"


def test_validation_rejects_bad_questions():
    good = _mcq()
    assert _problems(good) == ["question is not verified (run tools.verify_python_bank for execution-checked questions)"] or _problems(good) == []
    dup = copy.deepcopy(good); dup["options"][1] = dup["options"][0]
    assert any("distinct" in p for p in _problems(dup))
    amb = copy.deepcopy(good); amb["options"][(good["correct_index"] + 1) % 4] = "all of the above"
    assert any("above" in p for p in _problems(amb))
    exam = copy.deepcopy(good); exam["statement"] += " This was asked in TCS last year."
    assert any("real company" in p for p in _problems(exam))
    ver = copy.deepcopy(good); ver["statement"] = "In Python 3.12 which method appends one item to the end of a list?"
    assert any("python_version" in p for p in _problems(ver))
    wrong_unit = copy.deepcopy(good); wrong_unit["unit_id"] = "unit-h"
    assert any("topic and unit" in p for p in _problems(wrong_unit))
    two_correct = copy.deepcopy(good); two_correct["options"] = good["options"][:3]
    assert _problems(two_correct)


@pytest.mark.parametrize("snippet", ["import socket\nsocket.create_connection(('1.1.1.1', 80))", "import subprocess\nsubprocess.run(['ls'])", "eval('1+1')", "import os\nos.system('id')",
                                     "import urllib.request\nurllib.request.urlopen('http://x')", "open('/etc/passwd').read()", "exec('x=1')"])
def test_executable_questions_cannot_touch_network_processes_or_real_files(snippet):
    doc = B.out("input-output", "easy", "What is printed by this program?", snippet, "x", ["a", "b", "c"], "Because the code is forbidden anyway.")
    doc["review_status"] = "execution_verified"
    assert any("forbidden facility" in p for p in validate_question(doc))


def test_display_only_concept_code_may_show_subprocess():
    doc = B.mcq("secure-subprocess", "medium", "Which call is safest for running an external program with user input?", "A list of arguments without shell=True", ["shell=True with string concatenation", "os.system with an f-string", "eval of the command"],
                "A list avoids shell parsing, which prevents command injection.", code="import subprocess\nsubprocess.run(['ls', name])")
    doc["review_status"] = "manual_review"
    assert validate_question(doc) == []


def test_editing_an_output_snippet_unverifies_it():
    doc = next(q for q in all_seed_questions() if q["verification"]["method"] == "execution")
    assert verify_question(doc) == "execution_verified"
    edited = copy.deepcopy(doc); edited["code"] = edited["code"] + "\n# changed"
    assert verify_question(edited) == "unverified"
    edited2 = copy.deepcopy(doc); edited2["verification"]["expected_stdout"] = "something else"
    assert verify_question(edited2) == "unverified"


def test_review_status_cannot_be_forged_by_the_seed():
    doc = copy.deepcopy(next(q for q in all_seed_questions() if q["verification"]["method"] == "execution"))
    doc["code"] = "print('different')"; doc["review_status"] = "execution_verified"
    bank_docs = verify_question(doc)
    assert bank_docs == "unverified"


def test_verification_breakdown_is_honest(seeds):
    valid, _ = seeds
    status = {q["review_status"] for q in valid}
    assert status == {"execution_verified", "reference_verified", "manual_review"}
    assert all(q["verification"]["method"] in ("execution", "reference", "manual_review") for q in valid)


# --- seeding / persistence ------------------------------------------------------------------------------------------------------------


def test_seeding_is_idempotent_and_stores_everything(fake_db):
    bank.ensure_indexes(fake_db)
    first = bank.ensure_seeded(fake_db)
    total = fake_db[Collections.PYTHON_QUESTIONS].count_documents({})
    assert first["added"] == total == first["active_seed_total"] and first["rejected"] == 0
    second = bank.ensure_seeded(fake_db)
    assert second["added"] == 0 and second["updated"] == 0 and fake_db[Collections.PYTHON_QUESTIONS].count_documents({}) == total


def test_edited_seed_bumps_version_and_removed_seed_is_retired(fake_db):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    coll = fake_db[Collections.PYTHON_QUESTIONS]
    victim = coll.find_one({"interaction": "mcq"})
    coll.update_one({"question_id": victim["question_id"]}, {"$set": {"content_hash": "stale"}})
    ghost = dict(victim); ghost.pop("_id"); ghost.update(question_id="pyq-0000000000", fingerprint="ghost")
    coll.insert_one(ghost)
    res = bank.ensure_seeded(fake_db)
    assert res["updated"] == 1 and res["retired"] == 1
    assert coll.find_one({"question_id": victim["question_id"]})["version"] == 2
    assert coll.find_one({"question_id": "pyq-0000000000"})["status"] == "inactive"


def test_syllabus_and_coverage_are_computed_from_stored_questions(fake_db):
    bank.ensure_indexes(fake_db)
    empty = bank.syllabus_payload(fake_db)
    assert empty["question_total"] == 0 and empty["topics_implemented"] == 0
    bank.ensure_seeded(fake_db)
    full = bank.syllabus_payload(fake_db)
    assert full["topics_total"] == 144 and full["topics_implemented"] == 144 and len(full["units"]) == 9
    cov = bank.coverage_report(fake_db)
    assert cov["gaps"] == [] and cov["total_questions"] == full["question_total"]
    assert cov["machine_verified"] + cov["manual_review"] == cov["total_questions"] and cov["manual_review"] > 0
    fake_db[Collections.PYTHON_QUESTIONS].delete_many({"topic_id": "closures"})
    assert any("Closures" in g for g in bank.coverage_report(fake_db)["gaps"])


def test_listing_is_bounded_and_answer_free(fake_db):
    bank.ensure_indexes(fake_db)
    bank.ensure_seeded(fake_db)
    page = bank.list_public_questions(fake_db, limit=10)
    assert len(page["items"]) == 10 and page["has_next"] and page["total"] > 300
    for item in page["items"]:
        assert not (set(item) & SECRET_KEYS)


# --- independent execution re-verification ----------------------------------------------------------------------------------------------


@pytest.mark.skipif(not runner.capabilities()["available"], reason="isolated runner unavailable")
def test_manifest_matches_real_execution_of_every_seed():
    """Runs every output snippet, reference solution and debug/completion starter in the isolated runner (the tool a maintainer runs)."""
    from app.services.python_practice import verify
    result = verify.verify_all(write=False)
    assert result["failures"] == [], result["failures"][:3]
    assert result["checked"]["execution"] >= 150 and result["checked"]["reference"] >= 40 and result["checked"]["starters"] >= 10
