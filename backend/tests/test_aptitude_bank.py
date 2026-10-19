"""Phase 23 -- syllabus coverage, question validation, independent answer verification, seeding."""

from __future__ import annotations

import copy

import mongomock
import pytest

from app.db.collections import Collections
from app.services.aptitude import bank, verifiers
from app.services.aptitude.content import all_seed_questions
from app.services.aptitude.safe_eval import UnsafeExpressionError, parse_number, safe_eval
from app.services.aptitude.syllabus import MIN_QUESTIONS_PER_SUBTOPIC, SUBTOPIC_TO_TOPIC, TOPICS
from app.services.aptitude.validation import fingerprint, normalize, question_id_for, validate_question, verify_question

LEAK_KEYS = {"correct_index", "explanation", "formula", "verification", "fingerprint", "review_status", "content_hash"}


@pytest.fixture(scope="module")
def seeds():
    valid, rejected = bank.build_valid_seed_bank()
    return valid, rejected


@pytest.fixture()
def db():
    d = mongomock.MongoClient()["apt_unit"]
    bank.ensure_indexes(d)
    bank.ensure_seeded(d)
    return d


def _good() -> dict:
    """A fresh valid question to mutate in negative tests."""
    doc = copy.deepcopy(next(q for q in all_seed_questions() if q["subtopic_id"] == "unit-digit"))
    doc["review_status"] = "verified"
    assert validate_question(doc) == []
    return doc


def _renumber(doc):
    doc["question_id"] = question_id_for(doc["subtopic_id"], doc["statement"], doc.get("data"))
    return doc


# --- Syllabus -----------------------------------------------------------------------------------


class TestSyllabus:
    def test_has_26_topics_lettered_a_to_z(self):
        assert [t.code for t in TOPICS] == [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        assert len({t.id for t in TOPICS}) == 26

    def test_subtopic_ids_are_unique_and_belong_to_one_topic(self):
        all_ids = [s.id for t in TOPICS for s in t.subtopics]
        assert len(all_ids) == len(set(all_ids)) == 88
        assert all(SUBTOPIC_TO_TOPIC[s.id] == t.id for t in TOPICS for s in t.subtopics)

    def test_every_syllabus_item_maps_to_real_subtopics_and_every_subtopic_is_referenced(self):
        for t in TOPICS:
            own = {s.id for s in t.subtopics}
            referenced = set()
            for item in t.items:
                assert item.subtopic_ids, item.text
                assert set(item.subtopic_ids) <= own, item.text
                referenced |= set(item.subtopic_ids)
            assert referenced == own, t.id

    def test_every_syllabus_item_has_enough_questions(self, seeds):
        valid, _ = seeds
        counts = {}
        for q in valid:
            counts[q["subtopic_id"]] = counts.get(q["subtopic_id"], 0) + 1
        for t in TOPICS:
            for item in t.items:
                for sub in item.subtopic_ids:
                    assert counts.get(sub, 0) >= MIN_QUESTIONS_PER_SUBTOPIC, f"{t.id}/{sub} ({item.text}) has {counts.get(sub, 0)}"

    def test_syllabus_payload_reflects_real_counts(self, db):
        payload = bank.syllabus_payload(db)
        assert payload["totals"]["topics"] == 26 and payload["totals"]["subtopics"] == 88
        assert payload["totals"]["questions"] == db[Collections.APTITUDE_QUESTIONS].count_documents({"status": "active"})
        # an emptied subtopic must be reported as missing, not implemented
        db[Collections.APTITUDE_QUESTIONS].update_many({"subtopic_id": "unit-digit"}, {"$set": {"status": "inactive"}})
        topic = next(t for t in bank.syllabus_payload(db)["topics"] if t["id"] == "number-system")
        sub = next(s for s in topic["subtopics"] if s["id"] == "unit-digit")
        assert sub["status"] == "missing" and sub["question_count"] == 0 and topic["status"] == "partial"


# --- Seed content quality -------------------------------------------------------------------


class TestSeedQuality:
    def test_no_seed_is_rejected(self, seeds):
        _, rejected = seeds
        assert rejected == []

    def test_ids_and_fingerprints_are_unique(self, seeds):
        valid, _ = seeds
        assert len({q["question_id"] for q in valid}) == len(valid)
        assert len({q["fingerprint"] for q in valid}) == len(valid)
        assert len({normalize(q["statement"]) for q in valid}) == len(valid)

    def test_every_mcq_has_four_distinct_options_and_a_valid_key(self, seeds):
        for q in seeds[0]:
            assert len(q["options"]) == 4 and len({normalize(o) for o in q["options"]}) == 4, q["statement"]
            assert 0 <= q["correct_index"] <= 3
            assert q["difficulty"] in {"easy", "medium", "hard"} and q["est_time_seconds"] >= 10
            assert q["explanation"].strip()

    def test_explanations_state_the_answer(self, seeds):
        for q in seeds[0]:
            assert normalize(q["options"][q["correct_index"]]) in normalize(q["explanation"]), q["statement"]

    def test_every_answer_key_is_independently_reproduced(self, seeds):
        """Re-derive every machine-checkable answer from scratch (formula or enumeration)."""
        checked = 0
        for q in seeds[0]:
            status, problems = verify_question(q)
            assert problems == [], (q["statement"], problems)
            assert status in {"verified", "manual_review"}
            checked += status == "verified"
        assert checked / len(seeds[0]) > 0.9

    def test_manual_review_questions_are_a_small_minority_and_documented(self, seeds):
        manual = [q for q in seeds[0] if q["verification"]["method"] == "manual_review"]
        assert len(manual) < 0.1 * len(seeds[0])
        assert all(q["verification"]["note"].strip() for q in manual)

    def test_data_interpretation_questions_carry_data(self, seeds):
        di = [q for q in seeds[0] if q["question_type"] == "data_interpretation"]
        assert di and all(q["data"] and q["data"]["kind"] in {"table", "bar", "pie", "line"} for q in di)
        pies = [q["data"] for q in di if q["data"]["kind"] == "pie"]
        assert all(sum(s["value"] for s in p["slices"]) == 100 for p in pies)

    def test_all_question_types_and_difficulties_are_present(self, seeds):
        assert {q["question_type"] for q in seeds[0]} == {"direct", "scenario", "multi_step", "data_interpretation", "time_pressure"}
        assert {q["difficulty"] for q in seeds[0]} == {"easy", "medium", "hard"}

    def test_no_claim_of_real_company_exam_origin(self, seeds):
        for q in seeds[0]:
            assert "previous year" not in (q["statement"] + q["explanation"]).lower()


# --- Validator (negative cases) -------------------------------------------------------------


class TestValidator:
    def test_duplicate_options_are_rejected(self):
        doc = _good()
        doc["options"][1] = doc["options"][0].upper() + " "
        assert any("distinct" in p for p in validate_question(doc))

    def test_wrong_answer_key_is_caught_by_independent_check(self):
        doc = _good()
        doc["correct_index"] = (doc["correct_index"] + 1) % 4
        problems = validate_question(doc)
        assert any("independent result" in p or "does not state" in p for p in problems)

    def test_declared_answer_that_disagrees_with_computation_is_rejected(self):
        doc = _good()
        doc["verification"]["expected"] = float(doc["verification"]["expected"]) + 1
        assert any("independent result" in p for p in validate_question(doc))

    def test_option_ambiguity_is_rejected(self):
        doc = next(q for q in all_seed_questions() if q["subtopic_id"] == "percentage-calculations")
        doc = copy.deepcopy(doc)
        doc["review_status"] = "verified"
        other = (doc["correct_index"] + 1) % 4
        doc["options"][other] = doc["options"][doc["correct_index"]].replace(" ", "") + "."  # same number, different text
        assert any("ambiguous" in p or "distinct" in p for p in validate_question(doc))

    def test_missing_verification_is_rejected(self):
        doc = _good()
        doc["verification"] = None
        assert validate_question(doc)

    def test_manual_review_requires_a_note(self):
        doc = _good()
        doc["verification"] = {"method": "manual_review", "note": " "}
        assert validate_question(doc)

    def test_all_of_the_above_is_rejected(self):
        doc = _good()
        i = (doc["correct_index"] + 1) % 4
        doc["options"][i] = "All of the above"
        assert any("above" in p for p in validate_question(doc))

    def test_real_exam_claims_are_rejected(self):
        doc = _good()
        doc["statement"] += " This question was asked in a previous year campus test."
        assert any("real exam" in p for p in validate_question(_renumber(doc)))

    def test_unstable_id_is_rejected(self):
        doc = _good()
        doc["question_id"] = "apt-0000000000"
        assert any("stable id" in p for p in validate_question(doc))

    def test_bad_topic_subtopic_pairing_is_rejected(self):
        doc = _good()
        doc["topic_id"] = "calendar"
        assert any("subtopic" in p for p in validate_question(doc))

    def test_data_interpretation_without_data_is_rejected(self):
        doc = _good()
        doc["question_type"] = "data_interpretation"
        assert any("data" in p for p in validate_question(doc))

    def test_explanation_must_state_the_answer(self):
        doc = _good()
        doc["explanation"] = "The unit digit repeats in a cycle, so use the remainder of the exponent."
        assert any("does not state" in p for p in validate_question(doc))

    def test_wrong_option_count_is_rejected(self):
        doc = _good()
        doc["options"] = doc["options"][:3]
        assert validate_question(doc)

    def test_out_of_range_key_is_rejected(self):
        doc = _good()
        doc["correct_index"] = 4
        assert validate_question(doc)

    def test_active_unverified_question_is_rejected(self):
        doc = _good()
        doc["verification"] = {"method": "enumeration", "kind": "unit_digit", "params": {"base": 1}, "expected": 7}
        assert validate_question(doc)


# --- Safe evaluator ----------------------------------------------------------------------------


class TestSafeEval:
    @pytest.mark.parametrize("expr,expected", [("1200*(1+10/100)**2", 1452), ("comb(8,3)", 56), ("sqrt(144)", 12), ("2**10 % 7", 2), ("-3 + 5", 2), ("factorial(5)/factorial(3)", 20)])
    def test_valid_expressions(self, expr, expected):
        assert safe_eval(expr) == pytest.approx(expected)

    @pytest.mark.parametrize("expr", [
        "__import__('os').system('echo hi')", "().__class__", "open('/etc/passwd')", "lambda: 1", "[1,2][0]", "x + 1", "'a' * 3", "True + 1",
        "2**100000", "9**9**9", "factorial(100000)", "comb(10**9, 5)", "", "1/0", "sqrt(-1)", "abs(1,2,3,4,5)", "round(1, ndigits=2)", "a.b", "1 if 1 else 2",
    ])
    def test_unsafe_or_malformed_expressions_are_rejected(self, expr):
        with pytest.raises(UnsafeExpressionError):
            safe_eval(expr)

    def test_overlong_expression_is_rejected(self):
        with pytest.raises(UnsafeExpressionError):
            safe_eval("1+" * 400 + "1")

    @pytest.mark.parametrize("text,value", [("₹1,200", 1200), ("16.67%", 16.67), ("3/8", 0.375), ("7 1/5 days", 7.2), ("-4", -4), ("no digits", None)])
    def test_parse_number(self, text, value):
        assert parse_number(text) == (pytest.approx(value) if value is not None else None)


# --- Verifier behaviour ------------------------------------------------------------------------


class TestVerifiers:
    def test_calendar_matches_known_dates(self):
        assert verifiers.run_verifier("calendar_day", dict(year=2000, month=1, day=1)) == "Saturday"
        assert verifiers.run_verifier("calendar_day", dict(year=1947, month=8, day=15)) == "Friday"

    def test_odd_days_cycle(self):
        assert [verifiers.run_verifier("odd_days", dict(years=n)) for n in (100, 200, 300, 400)] == [5, 3, 1, 0]

    def test_probability_by_enumeration(self):
        assert verifiers.run_verifier("dice", dict(event="sum_eq", v=7)) == pytest.approx(1 / 6)
        assert verifiers.run_verifier("coins", dict(n=3, event="exactly_heads", k=3)) == pytest.approx(1 / 8)

    def test_syllogism_follows_vs_possible(self):
        base = dict(sets=["A", "B", "C"], premises=[["A", "A", "B"], ["I", "B", "C"]])
        assert verifiers.run_verifier("syllogism", {**base, "conclusions": [["I", "A", "C"], ["I", "C", "B"]], "mode": "follows"}) == "Only conclusion II follows"
        assert verifiers.run_verifier("syllogism", {**base, "conclusions": [["I", "A", "C"], ["E", "A", "C"]], "mode": "possible"}) == "Both conclusions I and II are possible"

    def test_contradictory_premises_are_reported(self):
        with pytest.raises(verifiers.VerificationError):
            verifiers.run_verifier("syllogism", dict(sets=["A", "B", "C"], premises=[["A", "A", "B"], ["E", "A", "B"]], conclusions=[["I", "A", "C"]], mode="follows"))

    def test_non_unique_seating_is_rejected(self):
        with pytest.raises(verifiers.VerificationError):
            verifiers.run_verifier("seating_linear", dict(people=["P", "Q", "R"], constraints=[["pos", "P", 0]], ask={"type": "who_at", "pos": 1}))

    def test_non_unique_language_code_is_rejected(self):
        with pytest.raises(verifiers.VerificationError):
            verifiers.run_verifier("language_code", dict(statements=[[["a", "b"], ["x", "y"]]], query="x"))

    def test_data_sufficiency_cases(self):
        lin = lambda c, r: {"kind": "linear", "coeffs": c, "op": "==", "rhs": r}
        base = {"vars": ["x", "y"], "domain": [1, 20], "target": {"type": "value", "var": "x"}}
        assert verifiers.run_verifier("data_sufficiency", {**base, "statements": [lin({"x": 1, "y": 1}, 10), lin({"x": 1, "y": -1}, 2)]}).startswith("Both")
        assert verifiers.run_verifier("data_sufficiency", {**base, "statements": [lin({"x": 2}, 12), lin({"x": 1, "y": 1}, 10)]}) == "Statement I alone is sufficient"
        with pytest.raises(verifiers.VerificationError):  # both alone sufficient is not one of the four supported answers
            verifiers.run_verifier("data_sufficiency", {**base, "statements": [lin({"x": 2}, 12), lin({"x": 3}, 18)]})
        with pytest.raises(verifiers.VerificationError):  # contradictory
            verifiers.run_verifier("data_sufficiency", {**base, "statements": [lin({"x": 1, "y": -1}, 3), lin({"x": 1, "y": 1}, 8)]})

    def test_unknown_kind(self):
        with pytest.raises(verifiers.VerificationError):
            verifiers.run_verifier("nope", {})


# --- Seeding and listing -------------------------------------------------------------------------


class TestSeeding:
    def test_seeding_is_idempotent(self, db):
        before = db[Collections.APTITUDE_QUESTIONS].count_documents({})
        report = bank.ensure_seeded(db)
        assert report["added"] == 0 and report["updated"] == 0 and report["rejected"] == 0
        assert db[Collections.APTITUDE_QUESTIONS].count_documents({}) == before

    def test_unique_indexes_block_duplicates(self, db):
        doc = db[Collections.APTITUDE_QUESTIONS].find_one({})
        clone = {k: v for k, v in doc.items() if k != "_id"}
        with pytest.raises(Exception):
            db[Collections.APTITUDE_QUESTIONS].insert_one(clone)

    def test_invalid_seed_is_never_stored(self, monkeypatch):
        bad = copy.deepcopy(all_seed_questions()[0])
        bad["options"][1] = bad["options"][0]  # duplicate option
        monkeypatch.setattr(bank, "all_seed_questions", lambda: [bad])
        bank._validated_seed_bank.cache_clear()
        try:
            fresh = mongomock.MongoClient()["apt_bad"]
            bank.ensure_indexes(fresh)
            report = bank.ensure_seeded(fresh)
            assert report["rejected"] == 1 and fresh[Collections.APTITUDE_QUESTIONS].count_documents({}) == 0
        finally:
            bank._validated_seed_bank.cache_clear()

    def test_duplicate_seed_content_is_rejected(self, monkeypatch):
        first = all_seed_questions()[0]
        monkeypatch.setattr(bank, "all_seed_questions", lambda: [copy.deepcopy(first), copy.deepcopy(first)])
        bank._validated_seed_bank.cache_clear()
        try:
            valid, rejected = bank.build_valid_seed_bank()
            assert len(valid) == 1 and len(rejected) == 1 and "duplicate" in rejected[0]["problems"][-1]
        finally:
            bank._validated_seed_bank.cache_clear()

    def test_removed_seed_is_retired_and_edited_seed_bumps_version(self, db, monkeypatch):
        coll = db[Collections.APTITUDE_QUESTIONS]
        victim = coll.find_one({"subtopic_id": "hcf-lcm"})
        remaining = [q for q in all_seed_questions() if q["question_id"] != victim["question_id"]]
        edited = next(q for q in remaining if q["subtopic_id"] == "average-calculations")
        edited["est_time_seconds"] += 5
        monkeypatch.setattr(bank, "all_seed_questions", lambda: remaining)
        bank._validated_seed_bank.cache_clear()
        try:
            report = bank.ensure_seeded(db)
        finally:
            bank._validated_seed_bank.cache_clear()
        assert report["retired"] == 1 and coll.find_one({"question_id": victim["question_id"]})["status"] == "inactive"
        assert coll.find_one({"question_id": edited["question_id"]})["version"] == 2

    def test_public_listing_never_contains_answers(self, db):
        page = bank.list_public_questions(db, limit=50)
        assert page["items"] and all(not (set(i) & LEAK_KEYS) for i in page["items"])

    def test_listing_filters_and_pagination(self, db):
        res = bank.list_public_questions(db, topic_id="calendar", difficulty="hard", limit=3)
        assert all(i["topic_id"] == "calendar" and i["difficulty"] == "hard" for i in res["items"])
        p1 = bank.list_public_questions(db, topic_id="number-system", page=1, limit=5)
        p2 = bank.list_public_questions(db, topic_id="number-system", page=2, limit=5)
        assert p1["has_next"] and not ({i["question_id"] for i in p1["items"]} & {i["question_id"] for i in p2["items"]})
        assert bank.list_public_questions(db, topic_id="no-such-topic")["total"] == 0

    def test_inactive_and_draft_questions_are_not_listed(self, db):
        coll = db[Collections.APTITUDE_QUESTIONS]
        qid = coll.find_one({"topic_id": "clocks"})["question_id"]
        coll.update_one({"question_id": qid}, {"$set": {"status": "draft"}})
        assert qid not in {i["question_id"] for i in bank.list_public_questions(db, topic_id="clocks", limit=50)["items"]}

    def test_fingerprint_ignores_option_order_and_case(self):
        a = _good()
        b = copy.deepcopy(a)
        b["options"] = [o.upper() for o in reversed(b["options"])]
        b["statement"] = "  " + b["statement"].upper() + " "
        assert fingerprint(a) == fingerprint(b)
