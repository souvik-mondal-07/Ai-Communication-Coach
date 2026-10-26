"""Phase 25 -- question bank: syllabus coverage, structural quality, validator rejection, seeding, answer-key isolation, MongoDB checks."""

from __future__ import annotations

import copy

import mongomock
import pytest

from app.db.collections import Collections
from app.services.dbms_sql import bank, datasets, oracles, sandbox, sql_compare
from app.services.dbms_sql.content import all_seed_questions
from app.services.dbms_sql.syllabus import MIN_QUESTIONS_PER_TOPIC, TOPIC_BY_ID, UNITS
from app.services.dbms_sql.validation import content_hash, fingerprint, question_id_for, validate_question, verify_question

SECRET = {"correct_index", "explanation", "verification", "fingerprint", "content_hash", "reference_sql", "expected", "hints", "review_status", "version"}


@pytest.fixture(scope="module")
def valid_bank():
    valid, rejected = bank.build_valid_seed_bank()
    return valid, rejected


@pytest.fixture()
def db():
    d = mongomock.MongoClient()["bank_test"]
    bank.ensure_indexes(d)
    return d


def _fresh(topic="keys", **over):
    """A known-good MCQ to mutate in validator tests."""
    stmt = "Which statement about relations is true in this validator test?"
    doc = {
        "question_id": question_id_for(topic, stmt), "unit_id": "unit-b", "topic_id": topic, "format": "concept", "interaction": "mcq", "dialect": "standard", "difficulty": "easy",
        "statement": stmt, "code": None, "dataset_id": None, "options": ["alpha", "beta", "gamma", "delta"], "correct_index": 1, "explanation": "Because beta is the right answer here.",
        "hints": [], "est_time_seconds": 30, "tags": [], "requires": [], "status": "active", "version": 1, "source": "seed", "review_status": "unverified",
        "verification": {"method": "manual_review", "note": "A sufficiently long reviewer note for the test."},
    }
    doc.update(over)
    doc["question_id"] = question_id_for(doc["topic_id"], doc["statement"], doc.get("code"))
    return doc


class TestSyllabus:
    def test_every_syllabus_bullet_is_a_topic(self):
        assert len(UNITS) == 7 and [u.code for u in UNITS] == list("ABCDEFG")
        assert [len(u.topics) for u in UNITS] == [9, 7, 12, 11, 7, 13, 11]
        assert len(TOPIC_BY_ID) == 70

    def test_ids_are_unique_and_stable(self):
        ids = [t.id for u in UNITS for t in u.topics]
        assert len(ids) == len(set(ids))
        assert all(u.id == f"unit-{u.code.lower()}" for u in UNITS)


class TestSeedBank:
    def test_no_seed_is_rejected(self, valid_bank):
        valid, rejected = valid_bank
        assert rejected == [], rejected
        assert len(valid) == len(all_seed_questions())

    def test_every_topic_has_enough_validated_questions(self, valid_bank):
        valid, _ = valid_bank
        counts = {}
        for q in valid:
            counts[q["topic_id"]] = counts.get(q["topic_id"], 0) + 1
        short = {t: counts.get(t, 0) for t in TOPIC_BY_ID if counts.get(t, 0) < MIN_QUESTIONS_PER_TOPIC}
        assert short == {}, f"topics below {MIN_QUESTIONS_PER_TOPIC} questions: {short}"

    def test_every_unit_is_represented(self, valid_bank):
        assert {q["unit_id"] for q in valid_bank[0]} == {u.id for u in UNITS}

    def test_ids_and_fingerprints_are_unique(self, valid_bank):
        valid, _ = valid_bank
        assert len({q["question_id"] for q in valid}) == len(valid) == len({q["fingerprint"] for q in valid})

    def test_no_two_questions_share_a_statement_and_code(self, valid_bank):
        pairs = [(q["topic_id"], q["statement"].casefold(), (q.get("code") or "").casefold()) for q in valid_bank[0]]
        assert len(pairs) == len(set(pairs))

    def test_every_mcq_has_four_distinct_options_and_one_correct(self, valid_bank):
        for q in valid_bank[0]:
            if q["interaction"] == "mcq":
                assert len(q["options"]) == 4 and len({o.casefold() for o in q["options"]}) == 4, q["statement"]
                assert 0 <= q["correct_index"] < 4

    def test_correct_option_position_is_not_always_the_same(self, valid_bank):
        positions = [q["correct_index"] for q in valid_bank[0] if q["interaction"] == "mcq"]
        assert all(positions.count(i) > len(positions) * 0.1 for i in range(4)), "correct answers are clustered in one position"

    def test_every_question_has_explanation_and_estimate_and_verification(self, valid_bank):
        for q in valid_bank[0]:
            assert q["explanation"].strip() and q["est_time_seconds"] >= 10 and q["verification"]["method"]
            assert q["review_status"] in ("reference_checked", "sql_checked", "sql_output_checked", "manual_review")

    def test_sql_questions_have_hints_and_verified_expected_results(self, valid_bank):
        sql_qs = [q for q in valid_bank[0] if q["interaction"] == "sql"]
        assert len(sql_qs) >= 40
        for q in sql_qs:
            assert q["hints"] and q["sql"]["expected"]["rows"] and q["review_status"] == "sql_checked"
            assert q["dialect"] == "sqlite" and q["dataset_id"] == "practice"

    def test_stored_expected_result_matches_a_fresh_engine_run_and_the_independent_oracle(self, valid_bank):
        tables = datasets.python_tables()
        for q in valid_bank[0]:
            if q["interaction"] != "sql":
                continue
            spec = q["sql"]
            run = sandbox.run_query(spec["reference_sql"])
            assert run.ok, q["statement"]
            assert sql_compare.compare(run.columns, run.rows, spec["expected"]["columns"], spec["expected"]["rows"], ordered=spec["ordered"], check_column_names=True).correct
            oracle_rows = [list(r) for r in oracles.ORACLES[q["question_id"]](tables)]
            assert sql_compare.compare(run.columns, run.rows, run.columns, oracle_rows, ordered=spec["ordered"], precision=spec["precision"]).correct, q["statement"]

    def test_debug_starters_are_really_broken_and_completion_starters_really_incomplete(self, valid_bank):
        for q in valid_bank[0]:
            if q["interaction"] != "sql" or q["format"] not in ("debug", "complete"):
                continue
            spec = q["sql"]
            run = sandbox.run_query(spec["starter"])
            if q["format"] == "complete":
                assert "___" in spec["starter"] and not run.ok
            elif run.ok:
                assert not sql_compare.compare(run.columns, run.rows, spec["expected"]["columns"], spec["expected"]["rows"], ordered=spec["ordered"], check_column_names=spec["check_column_names"]).correct

    def test_reference_solutions_actually_solve_their_own_question(self, valid_bank):
        for q in valid_bank[0]:
            if q["interaction"] == "sql":
                spec = q["sql"]
                run = sandbox.run_query(spec["reference_sql"])
                assert sql_compare.compare(run.columns, run.rows, spec["expected"]["columns"], spec["expected"]["rows"], ordered=spec["ordered"], check_column_names=spec["check_column_names"]).correct

    def test_every_practice_mode_has_enough_questions(self, valid_bank):
        valid, _ = valid_bank
        by = lambda f: sum(1 for q in valid if f(q))  # noqa: E731
        assert by(lambda q: q["format"] == "query") >= 25
        assert by(lambda q: q["format"] == "output") >= 12
        assert by(lambda q: q["format"] == "debug") >= 10
        assert by(lambda q: q["format"] == "complete") >= 8
        assert by(lambda q: q["unit_id"] == "unit-d") >= 30
        assert by(lambda q: q["unit_id"] == "unit-f") >= 35
        assert by(lambda q: q["unit_id"] == "unit-g") >= 30
        assert by(lambda q: q["format"] in ("concept", "scenario")) >= 100

    def test_all_three_difficulties_exist_in_bulk(self, valid_bank):
        for d in ("easy", "medium", "hard"):
            assert sum(1 for q in valid_bank[0] if q["difficulty"] == d) >= 30

    def test_every_topic_has_all_three_difficulty_levels(self, valid_bank):
        have = {(q["topic_id"], q["difficulty"]) for q in valid_bank[0]}
        missing = sorted(f"{t}:{d}" for t in TOPIC_BY_ID for d in ("easy", "medium", "hard") if (t, d) not in have)
        assert missing == [], f"difficulty gaps: {missing}"

    def test_scenario_and_short_answer_questions_exist(self, valid_bank):
        valid = valid_bank[0]
        assert sum(1 for q in valid if q["format"] == "scenario") >= 20
        shorts = [q for q in valid if q["interaction"] == "short"]
        assert len(shorts) >= 6 and {q["short"]["kind"] for q in shorts} >= {"attrs", "keys"}
        assert all(q["review_status"] == "reference_checked" for q in shorts)

    def test_dialect_specific_questions_are_labelled(self, valid_bank):
        valid, _ = valid_bank
        labelled = {q["dialect"] for q in valid}
        assert {"standard", "sqlite", "mysql", "postgresql", "oracle", "sqlserver", "mongodb", "dynamodb"} <= labelled
        for topic in ("stored-procedures", "triggers", "exception-handling", "dialect-differences"):
            labelled_here = [q for q in valid if q["topic_id"] == topic and q["dialect"] != "standard"]
            assert len(labelled_here) >= 2, f"{topic} should contain explicitly dialect-labelled questions"

    def test_mongodb_examples_declare_mongodb_and_are_not_sql(self, valid_bank):
        for q in valid_bank[0]:
            framing = q["statement"] + (q.get("code") or "")
            if "db." in framing and "$" in framing or "createIndex" in framing:
                assert q["dialect"] == "mongodb", q["statement"]

    def test_no_question_claims_to_be_from_a_real_exam(self, valid_bank):
        import re
        for q in valid_bank[0]:
            assert not re.search(r"previous year|asked in|actual exam", q["statement"] + q["explanation"], re.I)

    def test_manual_review_is_reported_separately_never_as_machine_verified(self, valid_bank):
        statuses = {q["review_status"] for q in valid_bank[0]}
        assert "manual_review" in statuses  # honest: pure definitions have no executable check
        for q in valid_bank[0]:
            if q["review_status"] == "manual_review":
                assert q["verification"]["method"] == "manual_review" and len(q["verification"]["note"]) >= 15

    def test_design_and_transaction_answers_are_machine_verified(self, valid_bank):
        design_ref = [q for q in valid_bank[0] if q["format"] in ("design", "transaction") and q["verification"].get("method") == "reference"]
        assert len(design_ref) >= 30 and all(q["review_status"] == "reference_checked" for q in design_ref)


class TestMongoResultsRecomputed:
    """MongoDB result-prediction questions embed a spec; recompute each with mongomock (an independent engine)."""

    def _specs(self):
        return [(q, q["verification"]["mongo_check"]) for q in all_seed_questions() if q["verification"].get("mongo_check")]

    def test_there_are_mongodb_result_questions(self):
        assert len(self._specs()) >= 3

    def test_results_match_mongomock(self):
        for q, spec in self._specs():
            coll = mongomock.MongoClient()["m"]["items"]
            coll.insert_many(copy.deepcopy(spec["docs"]))
            if spec["op"] == "update_many_count":
                coll.update_many(spec["filter"], spec["update"])
                assert coll.count_documents(spec["count_filter"]) == spec["expected"] == int(q["options"][q["correct_index"]]), q["statement"]
                continue
            if spec["op"] == "find":
                got = list(coll.find(spec["filter"], spec["projection"]).sort(spec["sort"]))
            else:
                coll.update_one(spec["filter"], spec["update"])
                got = list(coll.find(spec["filter"], {"_id": 0}))
            got = [{k: v for k, v in d.items() if k != "_id"} for d in got]
            assert got == spec["expected"], q["statement"]
            rendered = ", ".join(d["name"] for d in got) if spec["render"] == "names" else str(got[0]["qty"])
            assert rendered == q["options"][q["correct_index"]], q["statement"]


class TestValidatorRejectsBadQuestions:
    def test_a_good_question_passes(self):
        assert validate_question(_fresh()) == []

    def test_unknown_topic_or_unit_mismatch(self):
        assert any("topic" in p for p in validate_question(_fresh(unit_id="unit-a")))

    def test_duplicate_options(self):
        assert any("distinct" in p for p in validate_question(_fresh(options=["a1", "a1", "b2", "c3"])))

    def test_wrong_option_count_and_correct_index(self):
        assert validate_question(_fresh(options=["a", "b", "c"]))
        assert validate_question(_fresh(correct_index=None))
        assert validate_question(_fresh(correct_index=9))

    def test_all_of_the_above_is_rejected(self):
        assert any("above" in p for p in validate_question(_fresh(options=["alpha", "beta", "gamma", "All of the above"])))

    def test_missing_or_weak_verification(self):
        assert any("verification" in p for p in validate_question(_fresh(verification=None)))
        assert validate_question(_fresh(verification={"method": "manual_review", "note": "short"}))
        assert validate_question(_fresh(verification={"method": "magic"}))

    def test_stale_id_is_rejected(self):
        d = _fresh()
        d["question_id"] = "dbq-0000000000"
        assert any("stable id" in p for p in validate_question(d))

    def test_vendor_syntax_must_declare_its_dialect(self):
        bad = _fresh(statement="In this validator test, which statement is correct: CREATE PROCEDURE p AS BEGIN SELECT 1; END?")
        assert any("dialect" in p for p in validate_question(bad))
        assert validate_question({**bad, "dialect": "sqlserver"}) == []

    def test_mongo_syntax_must_declare_mongodb(self):
        bad = _fresh(statement="In this validator test, what does db.items.find({ qty: { $gt: 2 } }) return for the sample?")
        assert any("dialect" in p for p in validate_question(bad))

    def test_real_exam_claims_are_rejected(self):
        assert any("real exam" in p for p in validate_question(_fresh(statement="This validator test question was asked in an actual exam last year.")))

    def test_wrong_reference_answer_is_rejected(self):
        wrong = _fresh(options=["{A}", "{B}", "{A, B}", "{C}"], correct_index=1, verification={"method": "reference", "kind": "candidate_keys", "params": {"attrs": "ABCD", "fds": "A->B, B->C, C->D"}})
        assert any("does not equal" in p for p in validate_question(wrong))

    def test_correct_reference_answer_is_accepted(self):
        good = _fresh(options=["{B}", "{A}", "{A, B}", "{C}"], correct_index=1, verification={"method": "reference", "kind": "candidate_keys", "params": {"attrs": "ABCD", "fds": "A->B, B->C, C->D"}})
        assert validate_question(good) == []

    def test_ambiguous_reference_distractor_is_rejected(self):
        amb = _fresh(options=["Yes", "yes", "No", "Maybe"], correct_index=0, verification={"method": "reference", "kind": "is_superkey", "params": {"attrs": "AB", "fds": "A->B", "x": "A"}})
        assert validate_question(amb)

    def test_unknown_reference_kind(self):
        assert validate_question(_fresh(verification={"method": "reference", "kind": "nope", "params": {}}))

    def test_json_validity_check(self):
        good = _fresh(options=["{'a': 1}", '{"a": 1}', "{a: 1}", '{"a": 1,}'], correct_index=1, verification={"method": "json_valid"})
        assert validate_question(good) == []
        bad = {**good, "correct_index": 0}
        assert validate_question(bad)

    def _sql_doc(self, **over):
        stmt = "Return every department name alphabetically for this validator test."
        sql = {"dataset_id": "practice", "starter": None, "reference_sql": "SELECT dept_name FROM departments ORDER BY dept_name",
               "expected": {"columns": ["dept_name"], "rows": [["Engineering"], ["HR"], ["Legal"], ["Marketing"], ["Sales"]]}, "ordered": True, "check_column_names": False, "precision": 2}
        sql.update(over.pop("sql_over", {}))
        qid = "sql-oracle-test"
        oracles.ORACLES[qid] = lambda T: [(d["dept_name"],) for d in sorted(T["departments"], key=lambda d: d["dept_name"])]
        doc = _fresh(statement=stmt, format="query", interaction="sql", dialect="sqlite", dataset_id="practice", options=[], correct_index=None, hints=["Sort by name."],
                     sql=sql, verification={"method": "sql", "oracle": qid}, topic="basic-sql-operations", unit_id="unit-b", topic_id="basic-sql-operations")
        doc.update(over)
        doc["question_id"] = question_id_for(doc["topic_id"], doc["statement"], doc.get("code"))
        return doc

    def test_a_good_sql_question_passes(self):
        assert validate_question(self._sql_doc()) == []

    def test_wrong_expected_rows_are_rejected(self):
        d = self._sql_doc(sql_over={"expected": {"columns": ["dept_name"], "rows": [["Engineering"], ["HR"]]}})
        assert any("expected result" in p for p in validate_question(d))

    def test_failing_reference_query_is_rejected(self):
        d = self._sql_doc(sql_over={"reference_sql": "SELECT nope FROM departments"})
        assert any("reference query failed" in p for p in validate_question(d))

    def test_oracle_disagreement_is_rejected(self):
        d = self._sql_doc()
        oracles.ORACLES["sql-oracle-test"] = lambda T: [("Wrong",)]
        assert any("oracle" in p for p in validate_question(d))

    def test_missing_oracle_is_rejected(self):
        d = self._sql_doc()
        d["verification"] = {"method": "sql", "oracle": "not-registered"}
        assert any("oracle" in p for p in validate_question(d))

    def test_sql_question_without_hint_is_rejected(self):
        assert any("hint" in p for p in validate_question(self._sql_doc(hints=[])))

    def test_sql_question_must_declare_sqlite(self):
        assert any("sqlite" in p for p in validate_question(self._sql_doc(dialect="standard")))

    def test_debug_starter_that_already_works_is_rejected(self):
        d = self._sql_doc(format="debug")
        d["sql"]["starter"] = "SELECT dept_name FROM departments ORDER BY dept_name"
        assert any("already produces" in p for p in validate_question(d))

    def test_completion_starter_needs_a_blank_that_stops_it_running(self):
        d = self._sql_doc(format="complete")
        d["sql"]["starter"] = "SELECT dept_name FROM departments"
        assert any("blank" in p for p in validate_question(d))

    def test_starter_that_already_solves_a_query_task_is_rejected(self):
        d = self._sql_doc()
        d["sql"]["starter"] = d["sql"]["reference_sql"]
        assert any("already solves" in p for p in validate_question(d))

    def test_sql_output_question_with_wrong_option_is_rejected(self):
        stmt = "How many rows does this return in the validator test?"
        code = "SELECT * FROM departments"
        qid = question_id_for("crud-concepts", stmt, code)
        oracles.ORACLES[qid] = lambda T: "5"
        doc = _fresh(topic="crud-concepts", statement=stmt, code=code, format="output", dialect="sqlite", dataset_id="practice", unit_id="unit-b", options=["4", "5", "6", "7"], correct_index=0,
                     verification={"method": "sql_output", "render": "count", "oracle": qid})
        assert any("engine result" in p for p in validate_question(doc))
        doc["correct_index"] = 1
        assert validate_question(doc) == []

    def test_active_question_cannot_be_unverified(self):
        assert verify_question(_fresh(verification=None))[0] == "unverified"


class TestPublicProjection:
    def test_to_public_never_contains_an_answer_key(self, valid_bank):
        for q in valid_bank[0]:
            pub = bank.to_public(q)
            assert not (SECRET & pub.keys()), q["statement"]
            if pub["sql"]:
                assert not (SECRET & pub["sql"].keys())
            if pub["short"]:
                assert set(pub["short"]) == {"kind", "help"}

    def test_public_sql_shows_only_the_expected_column_names(self, valid_bank):
        q = next(q for q in valid_bank[0] if q["interaction"] == "sql")
        pub = bank.to_public(q)
        assert pub["sql"]["expected_columns"] == q["sql"]["expected"]["columns"] and "rows" not in str(pub["sql"])

    def test_options_order_is_applied(self, valid_bank):
        q = next(q for q in valid_bank[0] if q["interaction"] == "mcq")
        assert bank.to_public(q, options_order=[3, 2, 1, 0])["options"] == list(reversed(q["options"]))


class TestSeedingInMongo:
    def test_seeding_stores_every_valid_question(self, db):
        res = bank.ensure_seeded(db)
        assert res["rejected"] == 0 and res["added"] == res["active_seed_total"] == db[Collections.DBMS_SQL_QUESTIONS].count_documents({"status": "active"})

    def test_seeding_is_idempotent(self, db):
        bank.ensure_seeded(db)
        n = db[Collections.DBMS_SQL_QUESTIONS].count_documents({})
        again = bank.ensure_seeded(db)
        assert again["added"] == 0 and again["updated"] == 0 and again["retired"] == 0
        assert db[Collections.DBMS_SQL_QUESTIONS].count_documents({}) == n

    def test_edited_seed_bumps_version_and_removed_seed_is_retired(self, db):
        bank.ensure_seeded(db)
        coll = db[Collections.DBMS_SQL_QUESTIONS]
        victim = coll.find_one({"interaction": "mcq"})
        coll.update_one({"question_id": victim["question_id"]}, {"$set": {"content_hash": "stale", "status": "active"}})
        coll.insert_one({**{k: v for k, v in victim.items() if k != "_id"}, "question_id": "dbq-ffffffffff", "fingerprint": "zzz", "source": "seed", "status": "active"})
        res = bank.ensure_seeded(db)
        assert res["updated"] == 1 and res["retired"] == 1
        assert coll.find_one({"question_id": victim["question_id"]})["version"] == 2
        assert coll.find_one({"question_id": "dbq-ffffffffff"})["status"] == "inactive"

    def test_inactive_questions_are_never_listed(self, db):
        bank.ensure_seeded(db)
        db[Collections.DBMS_SQL_QUESTIONS].update_many({}, {"$set": {"status": "inactive"}})
        assert bank.list_public_questions(db)["total"] == 0

    def test_unique_indexes_exist(self, db):
        info = db[Collections.DBMS_SQL_QUESTIONS].index_information()
        assert any(v.get("unique") and v["key"] == [("question_id", 1)] for v in info.values())

    def test_content_hash_changes_when_content_changes(self, valid_bank):
        q = copy.deepcopy(valid_bank[0][0])
        h = content_hash(q)
        q["explanation"] = q["explanation"] + " edited"
        assert content_hash(q) != h and fingerprint(q) == fingerprint(valid_bank[0][0])


class TestSyllabusAndCoverage:
    def test_empty_database_reports_missing_not_complete(self, db):
        s = bank.syllabus_payload(db)
        assert s["question_total"] == 0 and s["topics_implemented"] == 0
        assert all(t["status"] == "missing" for u in s["units"] for t in u["topics"])

    def test_counts_come_from_stored_questions(self, db):
        bank.ensure_seeded(db)
        s = bank.syllabus_payload(db)
        assert s["topics_total"] == 70 and s["topics_implemented"] == 70 and s["question_total"] == db[Collections.DBMS_SQL_QUESTIONS].count_documents({"status": "active"})
        assert s["sql_engine"]["engine"] == "SQLite"

    def test_a_topic_below_the_minimum_is_not_marked_implemented(self, db):
        bank.ensure_seeded(db)
        coll = db[Collections.DBMS_SQL_QUESTIONS]
        ids = [d["question_id"] for d in coll.find({"topic_id": "cursors"})][1:]
        coll.update_many({"question_id": {"$in": ids}}, {"$set": {"status": "inactive"}})
        row = next(t for u in bank.syllabus_payload(db)["units"] for t in u["topics"] if t["id"] == "cursors")
        assert row["status"] == "partial" and row["question_count"] == 1
        assert any("Cursors" in g and "only 1" in g for g in bank.coverage_report(db)["gaps"])

    def test_coverage_report_shape_and_honest_totals(self, db):
        bank.ensure_seeded(db)
        rep = bank.coverage_report(db)
        assert len(rep["rows"]) == 70 and rep["total_questions"] == sum(r["count"] for r in rep["rows"])
        assert rep["machine_verified"] + rep["manual_review"] == rep["total_questions"]
        assert rep["manual_review"] > 0
