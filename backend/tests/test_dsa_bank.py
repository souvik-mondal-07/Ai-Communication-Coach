"""Phase 24 -- syllabus hierarchy, question validation, seeding, listing and executed verification of the seed bank."""

from __future__ import annotations

import copy
import pathlib
import re
from collections import Counter

import pytest

from app.db.collections import Collections
from app.services.dsa import bank, validation
from app.services.dsa.content import all_seed_questions
from app.services.dsa.syllabus import MIN_QUESTIONS_PER_SUBTOPIC, SUBTOPIC_TO_TOPIC, TOPIC_BY_ID, TOPICS
from tests.test_communication import _register_and_login
from tools import dsa_seed_runner as runner

URL = "/api/v1/dsa"
LEAK = {"correct_index", "explanation", "trace", "complexity", "verification", "fingerprint", "reference_solution", "hints", "content_hash", "review_status"}

# The user's syllabus, verbatim, as (topic code, line). Every line must trace to subtopics that have real questions.
SYLLABUS = {
    "A": ["Basic concepts and notations.", "Time complexity and space complexity.", "Time-space trade-offs.", "Big O notation.", "Omega notation.", "Theta notation.", "Basic data structures."],
    "B": ["Linear arrays and memory representation.", "Traversal, insertion, deletion, sorting, searching, and merging.", "Complexity analysis of array operations."],
    "C": ["Bubble Sort.", "Insertion Sort.", "Selection Sort.", "Linear Search.", "Binary Search."],
    "D": ["Introduction, memory representation, and allocation.", "Traversal, insertion, and deletion.", "Header linked lists: grounded and circular.", "Two-way/doubly linked lists and their operations."],
    "E": ["Array and linked-list representations.", "Traversal, push, and pop.", "Polish notation.", "Arithmetic expression evaluation.", "Expression conversion and transformation."],
    "F": ["Array and linked-list representations.", "Traversal, insertion, and deletion.", "Priority queues.", "Deques."],
    "G": ["Binary trees.", "Complete and extended binary trees.", "Linked and sequential memory representations.", "Binary Search Trees; BST searching.", "BST insertion and deletion.", "Recursive inorder, preorder, and postorder traversals."],
    "H": ["Introduction to recursion.", "Tower of Hanoi.", "Recursive Merge Sort.", "Recursive Quick Sort."],
    "I": ["Heaps, insertion, and deletion.", "HeapSort.", "Hash functions and hash tables.", "Open hashing using separate chaining.", "Closed hashing/open addressing.", "Linear probing.", "Quadratic probing.", "Double hashing."],
    "J": ["Breadth-First Search (BFS).", "Depth-First Search (DFS).", "Dijkstra's shortest-path algorithm.", "Bellman–Ford algorithm.", "Floyd–Warshall algorithm."],
}


@pytest.fixture(scope="module")
def seed():
    valid, rejected = bank.build_valid_seed_bank()
    return valid, rejected


# --- Syllabus hierarchy ---------------------------------------------------------------------------------


class TestSyllabus:
    def test_ten_topics_a_to_j_in_order(self):
        assert [t.code for t in TOPICS] == list("ABCDEFGHIJ") and len(TOPICS) == 10

    def test_every_syllabus_line_is_present_and_traceable(self):
        for t in TOPICS:
            assert [i.text for i in t.items] == SYLLABUS[t.code], t.code
            for item in t.items:
                assert item.subtopic_ids and all(s in SUBTOPIC_TO_TOPIC and SUBTOPIC_TO_TOPIC[s] == t.id for s in item.subtopic_ids)

    def test_every_subtopic_is_covered_by_some_syllabus_line(self):
        covered = {s for t in TOPICS for i in t.items for s in i.subtopic_ids}
        assert covered == set(SUBTOPIC_TO_TOPIC)

    def test_ids_are_unique_and_url_safe(self):
        subs = [s.id for t in TOPICS for s in t.subtopics]
        assert len(subs) == len(set(subs)) == 54 and all(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", s) for s in subs)


# --- Seed bank ------------------------------------------------------------------------------------------


class TestSeedBank:
    def test_no_seed_is_rejected(self, seed):
        valid, rejected = seed
        assert rejected == [] and len(valid) >= 300

    def test_every_subtopic_has_enough_usable_questions(self, seed):
        counts = Counter(q["subtopic_id"] for q in seed[0])
        short = {s: counts.get(s, 0) for s in SUBTOPIC_TO_TOPIC if counts.get(s, 0) < MIN_QUESTIONS_PER_SUBTOPIC}
        assert short == {}

    def test_every_format_and_difficulty_is_present(self, seed):
        assert {q["format"] for q in seed[0]} == {"conceptual", "scenario", "output", "trace", "complexity", "coding"}
        assert {q["difficulty"] for q in seed[0]} == {"easy", "medium", "hard"}
        assert {q["coding_type"] for q in seed[0] if q["coding_type"]} == {"fill_line", "fix_bug", "write_function"}

    def test_every_mode_has_questions(self, seed):
        by_fmt = Counter(q["format"] for q in seed[0] if q["interaction"] == "mcq")
        for fmt in ("conceptual", "scenario", "output", "trace", "complexity", "coding"):
            assert by_fmt[fmt] >= 5, fmt
        assert sum(1 for q in seed[0] if q["interaction"] == "code") >= 20

    def test_ids_are_stable_unique_and_deterministic(self, seed):
        ids = [q["question_id"] for q in seed[0]]
        assert len(ids) == len(set(ids)) and all(re.fullmatch(r"dsa-[a-f0-9]{10}", i) for i in ids)
        again = {q["question_id"] for q in all_seed_questions()}
        assert again == set(ids)

    def test_no_duplicate_fingerprints(self, seed):
        fps = [q["fingerprint"] for q in seed[0]]
        assert len(fps) == len(set(fps))

    def test_mcq_shape(self, seed):
        for q in (q for q in seed[0] if q["interaction"] == "mcq"):
            assert len(q["options"]) == 4 and len({validation.normalize(o) for o in q["options"]}) == 4 and 0 <= q["correct_index"] <= 3
            assert not any(re.search(r"(all|none) of the above", o, re.I) for o in q["options"])

    def test_every_trace_question_has_intermediate_states(self, seed):
        traces = [q for q in seed[0] if q["format"] == "trace"]
        assert len(traces) >= 40 and all(len(q["trace"]) >= 1 for q in traces)

    def test_every_complexity_question_has_a_complexity_block(self, seed):
        cx = [q for q in seed[0] if q["format"] == "complexity"]
        assert len(cx) >= 30 and all(q["complexity"].get("time") for q in cx)

    def test_every_output_question_has_a_snippet(self, seed):
        out = [q for q in seed[0] if q["format"] == "output"]
        assert len(out) >= 25 and all(q["code"] for q in out)

    def test_coding_questions_have_hidden_and_edge_tests(self, seed):
        for q in (q for q in seed[0] if q["interaction"] == "code"):
            tests = q["coding"]["test_cases"]
            assert any(not t["visible"] for t in tests) and any(t["visible"] for t in tests) and any(t["edge"] for t in tests), q["statement"][:60]
            assert q["coding"]["template"].strip() and q["hints"] and q["constraints"], q["statement"][:60]  # every exercise has hints and constraints

    def test_no_claims_about_real_company_exams(self, seed):
        blob = " ".join(q["statement"] + q["explanation"] for q in seed[0]).lower()
        for phrase in ("asked in", "appeared in", "previous year", "actual exam"):
            assert phrase not in blob


# --- Validation (negative cases) ------------------------------------------------------------------------


def _mcq(seed):
    return copy.deepcopy(next(q for q in seed[0] if q["verification"]["method"] == "reference"))


class TestValidation:
    def test_wrong_key_is_rejected_by_reference_recompute(self, seed):
        q = _mcq(seed)
        q["correct_index"] = (q["correct_index"] + 1) % 4
        assert any("reference result" in p or "explanation" in p for p in validation.validate_question(q))

    def test_ambiguous_second_correct_option_is_rejected(self, seed):
        q = _mcq(seed)
        other = (q["correct_index"] + 1) % 4
        q["options"][other] = q["options"][q["correct_index"]] + " "
        assert validation.validate_question(q)

    def test_three_options_rejected(self, seed):
        q = _mcq(seed)
        q["options"] = q["options"][:3]
        assert validation.validate_question(q)

    def test_all_of_the_above_rejected(self, seed):
        q = _mcq(seed)
        q["options"][(q["correct_index"] + 1) % 4] = "All of the above"
        assert any("above" in p for p in validation.validate_question(q))

    def test_unverified_active_question_rejected(self, seed):
        q = _mcq(seed)
        q["verification"] = None
        assert validation.validate_question(q)

    def test_real_exam_claim_rejected(self, seed):
        q = _mcq(seed)
        q["statement"] += " (asked in a TCS drive)"
        q["question_id"] = validation.question_id_for(q["subtopic_id"], q["statement"], q.get("code"))
        assert any("real exam" in p for p in validation.validate_question(q))

    def test_unstable_id_rejected(self, seed):
        q = _mcq(seed)
        q["question_id"] = "dsa-0000000000"
        assert any("stable id" in p for p in validation.validate_question(q))

    def test_wrong_topic_for_subtopic_rejected(self, seed):
        q = _mcq(seed)
        q["topic_id"] = "graphs" if q["topic_id"] != "graphs" else "arrays"
        assert any("subtopic does not belong" in p for p in validation.validate_question(q))

    def test_trace_question_needs_trace(self, seed):
        q = copy.deepcopy(next(q for q in seed[0] if q["format"] == "trace"))
        q["trace"] = None
        assert validation.validate_question(q)

    def test_coding_needs_hidden_and_edge_tests(self, seed):
        q = copy.deepcopy(next(q for q in seed[0] if q["interaction"] == "code"))
        for t in q["coding"]["test_cases"]:
            t["visible"], t["edge"] = True, False
        probs = validation.validate_question(q)
        assert any("hidden" in p for p in probs) and any("edge" in p for p in probs)

    def test_coding_reference_must_define_the_function(self, seed):
        q = copy.deepcopy(next(q for q in seed[0] if q["interaction"] == "code"))
        q["coding"]["reference_solution"] = "def other(x):\n    return x + 1\n"
        assert any("does not define" in p for p in validation.validate_question(q))

    def test_snippet_expected_must_match_key(self, seed):
        q = copy.deepcopy(next(q for q in seed[0] if q["verification"]["method"] == "snippet"))
        q["verification"]["expected"] = "definitely not this"
        assert any("snippet output" in p for p in validation.validate_question(q))


# --- Database seeding -----------------------------------------------------------------------------------


class TestDatabaseSeeding:
    def test_seeding_is_idempotent_and_indexed(self, fake_db):
        bank.ensure_indexes(fake_db)
        first = bank.ensure_seeded(fake_db)
        second = bank.ensure_seeded(fake_db)
        assert first["added"] >= 300 and first["rejected"] == 0 and second["added"] == 0 and second["updated"] == 0
        assert fake_db[Collections.DSA_QUESTIONS].count_documents({"status": "active"}) == first["active_seed_total"]

    def test_removed_seed_is_retired_not_deleted(self, fake_db):
        bank.ensure_indexes(fake_db)
        bank.ensure_seeded(fake_db)
        fake_db[Collections.DSA_QUESTIONS].insert_one({"question_id": "dsa-ffffffffff", "source": "seed", "status": "active", "content_hash": "x", "version": 1})
        r = bank.ensure_seeded(fake_db)
        row = fake_db[Collections.DSA_QUESTIONS].find_one({"question_id": "dsa-ffffffffff"})
        assert r["retired"] == 1 and row["status"] == "inactive"

    def test_syllabus_counts_come_from_the_database(self, fake_db):
        bank.ensure_indexes(fake_db)
        assert bank.syllabus_payload(fake_db)["totals"]["questions"] == 0  # nothing seeded -> nothing is claimed
        assert all(t["status"] == "missing" for t in bank.syllabus_payload(fake_db)["topics"])
        bank.ensure_seeded(fake_db)
        data = bank.syllabus_payload(fake_db)
        assert data["totals"]["subtopics"] == 54 and data["totals"]["subtopics_implemented"] == 54
        assert data["execution"]["automated_code_execution"] is False

    def test_inactive_questions_are_never_listed(self, fake_db):
        bank.ensure_indexes(fake_db)
        bank.ensure_seeded(fake_db)
        fake_db[Collections.DSA_QUESTIONS].update_many({"subtopic_id": "bfs"}, {"$set": {"status": "inactive"}})
        assert bank.list_public_questions(fake_db, subtopic_id="bfs")["total"] == 0
        assert bank.syllabus_payload(fake_db)["topics"][-1]["subtopics"][0]["status"] == "missing"

    def test_public_projection_never_leaks_answers(self, fake_db):
        bank.ensure_indexes(fake_db)
        bank.ensure_seeded(fake_db)
        items = bank.list_public_questions(fake_db, limit=50)["items"]
        assert items and all(not (set(i) & LEAK) for i in items)
        code_items = bank.list_public_questions(fake_db, fmt="coding", limit=50)["items"]
        for i in (c for c in code_items if c["coding"]):
            assert "reference_solution" not in i["coding"] and i["coding"]["hidden_test_count"] >= 1
            assert all(set(t) == {"label", "args", "expected"} for t in i["coding"]["visible_tests"])

    def test_filtering_by_topic_subtopic_difficulty_and_format(self, fake_db):
        bank.ensure_indexes(fake_db)
        bank.ensure_seeded(fake_db)
        r = bank.list_public_questions(fake_db, topic_id="graphs", difficulty="hard", limit=50)
        assert r["total"] > 0 and all(i["topic_id"] == "graphs" and i["difficulty"] == "hard" for i in r["items"])
        r = bank.list_public_questions(fake_db, subtopic_id="dijkstra", fmt="trace", limit=50)
        assert r["total"] > 0 and all(i["subtopic_id"] == "dijkstra" and i["format"] == "trace" for i in r["items"])
        assert bank.list_public_questions(fake_db, topic_id="graphs", fmt="conceptual", limit=50)["total"] >= 0


# --- Execution-based verification of the seed bank ------------------------------------------------------
# These run the repository's own seed code in the isolated test runner. They are the evidence that
# reference solutions, fill-the-line keys and output-prediction answers are right.


@pytest.fixture(scope="module")
def executed(seed):
    return seed[0]


class TestSeedsAreExecutedAndVerified:
    def test_every_reference_solution_passes_every_test_case(self, executed):
        failures = []
        for q in (q for q in executed if q["interaction"] == "code"):
            failures += [(q["statement"][:50], f) for f in runner.check_solution(q["coding"])]
        assert failures == []

    def test_every_fill_and_fix_question_has_exactly_one_working_option(self, executed):
        failures, checked = [], 0
        for q in (q for q in executed if "line_check" in (q["verification"] or {})):
            checked += 1
            failures += [(q["statement"][:50], f) for f in runner.check_line_question(q)]
        assert checked >= 12 and failures == []

    def test_every_output_snippet_prints_its_declared_answer(self, executed):
        failures, checked = [], 0
        for q in (q for q in executed if (q["verification"] or {}).get("method") == "snippet"):
            checked += 1
            r = runner.check_snippet(q)
            if r:
                failures.append((q["statement"][:50], r))
        assert checked >= 25 and failures == []

    def test_boundary_cases_exist_for_each_coding_problem(self, executed):
        for q in (q for q in executed if q["interaction"] == "code"):
            labels = " ".join(t["label"] for t in q["coding"]["test_cases"] if t["edge"])
            assert labels.strip(), q["statement"][:60]


class TestRunnerIsolationAndScope:
    def test_runner_enforces_timeouts(self):
        r = runner.run_calls("def f():\n    while True:\n        pass\n", "f", [[]], timeout=1.5)
        assert r == [{"ok": False, "error": "Timeout"}]

    def test_runner_has_no_environment_secrets(self, monkeypatch):
        monkeypatch.setenv("MONGO_URI", "mongodb://secret")
        r = runner.run_calls("import os\ndef f():\n    return os.environ.get('MONGO_URI')\n", "f", [[]])
        assert r == [{"ok": True, "value": None}]

    def test_runner_cannot_write_outside_its_scratch_directory_quota(self):
        r = runner.run_calls("def f():\n    open('x', 'w').write('a' * (2 * 1024 * 1024))\n    return 1\n", "f", [[]])
        assert r[0]["ok"] is False  # RLIMIT_FSIZE stops oversized writes

    def test_application_code_never_imports_the_runner_or_tools(self):
        """User code must never run: nothing under app/ may import the trusted-seed runner or the tools package."""
        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        offenders = []
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if re.search(r"^\s*(from|import)\s+tools\b|dsa_seed_runner|coding_runner", text, re.M):
                offenders.append(str(path.relative_to(root)))
        assert offenders == []

    def test_the_deployed_package_has_no_execution_surface_for_dsa(self):
        """The runner is outside app/ (the project's security test forbids subprocess/exec there), so the app cannot run any code."""
        backend = pathlib.Path(__file__).resolve().parents[1]
        assert (backend / "tools" / "dsa_seed_runner.py").exists()
        assert not (backend / "app" / "services" / "dsa" / "coding_runner.py").exists()

    def test_dsa_services_do_not_use_exec_eval_or_subprocess(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "app"
        files = [root / "api/routes/dsa.py", *(p for p in (root / "services/dsa").rglob("*.py") if "content" not in p.parts)]
        bad = []
        for f in files:
            code = re.sub(r'""".*?"""', "", f.read_text(encoding="utf-8"), flags=re.S)
            code = "\n".join(line.split("#")[0] for line in code.splitlines())
            if re.search(r"\b(exec|eval)\s*\(|subprocess|os\.system|__import__", code):
                bad.append(f.name)
        assert bad == []
