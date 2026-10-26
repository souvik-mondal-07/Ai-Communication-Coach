"""Phase 25 -- normalization / transaction algorithms (against textbook results), SQL result comparison and short-answer grading."""

from __future__ import annotations

import pytest

from app.services.dbms_sql import design_algos as D
from app.services.dbms_sql import sql_compare as C
from app.services.dbms_sql import txn_algos as T
from app.services.dbms_sql.references import UnknownReference, run_reference


def fds(text):
    return D.parse_fds(text)


class TestFunctionalDependencies:
    def test_closure_chain(self):
        assert D.closure(D.attrs("A"), fds("A->B, B->C")) == D.attrs("ABC")

    def test_closure_needs_combined_lhs(self):
        assert D.closure(D.attrs("A"), fds("AB->C")) == D.attrs("A")
        assert D.closure(D.attrs("AB"), fds("AB->C, C->D")) == D.attrs("ABCD")

    def test_textbook_keys_ABCDE(self):
        # R(A,B,C,D,E), F = {A->B, BC->D, E->C, D->A}: keys are AE, BE, DE (E is never derived so it is in every key).
        keys = D.candidate_keys(D.attrs("ABCDE"), fds("A->B, BC->D, E->C, D->A"))
        assert sorted("".join(sorted(k)) for k in keys) == ["AE", "BE", "DE"]

    def test_keys_are_minimal(self):
        keys = D.candidate_keys(D.attrs("ABC"), fds("A->B, B->C"))
        assert keys == [D.attrs("A")]

    def test_no_dependencies_means_all_attributes_are_the_key(self):
        assert D.candidate_keys(D.attrs("ABC"), []) == [D.attrs("ABC")]

    def test_superkey(self):
        assert D.is_superkey(D.attrs("AD"), D.attrs("ABCD"), fds("A->B, B->C"))
        assert not D.is_superkey(D.attrs("A"), D.attrs("ABCD"), fds("A->B, B->C"))

    def test_parse_ignores_noise(self):
        assert D.parse_fds("A->B; B->C , ab -> d") == [(D.attrs("A"), D.attrs("B")), (D.attrs("B"), D.attrs("C")), (D.attrs("AB"), D.attrs("D"))]


class TestNormalForms:
    @pytest.mark.parametrize("attrs,fd,expected", [
        ("ABC", "A->B, B->C", "2NF"),           # transitive dependency
        ("ABC", "AB->C, C->B", "3NF"),          # 3NF but not BCNF
        ("ABC", "A->B, A->C", "BCNF"),
        ("ABCD", "AB->C, B->D", "1NF"),         # partial dependency
        ("ABCD", "A->B, B->C, C->D", "2NF"),
        ("ABC", "AB->C", "BCNF"),
        ("ABCDE", "A->B, BC->D, E->C, D->A", "1NF"),
    ])
    def test_highest_normal_form(self, attrs, fd, expected):
        assert D.highest_normal_form(D.attrs(attrs), fds(fd)) == expected

    def test_bcnf_implies_3nf_implies_2nf(self):
        for attrs, fd in [("ABC", "A->B, A->C"), ("ABC", "AB->C"), ("ABCD", "A->BCD")]:
            r, f = D.attrs(attrs), fds(fd)
            assert D.is_bcnf(r, f) and D.is_3nf(r, f) and D.is_2nf(r, f)

    def test_trivial_dependencies_never_violate(self):
        assert D.is_bcnf(D.attrs("AB"), fds("AB->A"))


class TestDecomposition:
    def test_binary_lossless_when_common_attrs_determine_one_side(self):
        assert D.is_lossless(D.attrs("ABC"), [D.attrs("AB"), D.attrs("AC")], fds("A->B"))

    def test_lossy_when_they_do_not(self):
        assert not D.is_lossless(D.attrs("ABC"), [D.attrs("AB"), D.attrs("BC")], fds("A->B"))

    def test_textbook_three_way_chase(self):
        # R(A,B,C,D,E), F = {A->C, B->C, C->D, DE->C, CE->A}; the classic decomposition is lossless.
        f = fds("A->C, B->C, C->D, DE->C, CE->A")
        assert D.is_lossless(D.attrs("ABCDE"), [D.attrs("AD"), D.attrs("AB"), D.attrs("BE"), D.attrs("CDE"), D.attrs("AE")], f)

    def test_dependency_preservation(self):
        assert not D.preserves_dependencies(D.attrs("ABC"), [D.attrs("AB"), D.attrs("AC")], fds("A->B, B->C"))
        assert D.preserves_dependencies(D.attrs("ABC"), [D.attrs("AB"), D.attrs("BC")], fds("A->B, B->C"))

    def test_projected_dependencies(self):
        projected = D.project_fds(D.attrs("AC"), fds("A->B, B->C"))
        assert (D.attrs("A"), D.attrs("C")) in projected


class TestMultivaluedDependencies:
    COLS = ["C", "T", "B"]
    FULL = [("DB", "Rao", "Korth"), ("DB", "Rao", "Date"), ("DB", "Sen", "Korth"), ("DB", "Sen", "Date")]

    def test_mvd_holds_on_full_cross_product(self):
        assert D.mvd_holds(self.COLS, self.FULL, D.attrs("C"), D.attrs("T"))
        assert D.mvd_holds(self.COLS, self.FULL, D.attrs("C"), D.attrs("B"))

    def test_mvd_fails_when_a_combination_is_missing(self):
        assert not D.mvd_holds(self.COLS, self.FULL[:3], D.attrs("C"), D.attrs("T"))

    def test_fourth_nf(self):
        r = D.attrs("CTB")
        assert D.fourth_nf_violations(r, [], D.parse_fds("C->T"))
        assert not D.fourth_nf_violations(D.attrs("ABC"), fds("A->BC"), D.parse_fds("A->B"))


class TestSchedules:
    def test_parse_and_errors(self):
        assert T.parse("R1(A) W2(B) C1 A2") == [("R", 1, "A"), ("W", 2, "B"), ("C", 1, None), ("A", 2, None)]
        with pytest.raises(ValueError):
            T.parse("R1 A")

    def test_conflict_serializability(self):
        assert not T.is_conflict_serializable(T.parse("R1(A) W2(A) W1(A) C1 C2"))
        assert T.is_conflict_serializable(T.parse("R1(A) W1(A) R2(A) W2(A) C1 C2"))
        assert T.serial_order(T.parse("R2(A) W2(A) R1(A) W1(A) C1 C2")) == [2, 1]

    def test_textbook_nonserializable_lost_update(self):
        assert not T.is_conflict_serializable(T.parse("R1(A) R2(A) W1(A) W2(A) C1 C2"))

    def test_view_serializable_but_not_conflict_serializable(self):
        s = T.parse("R1(A) W2(A) W1(A) W3(A) C1 C2 C3")
        assert not T.is_conflict_serializable(s) and T.is_view_serializable(s)

    def test_not_view_serializable(self):
        assert not T.is_view_serializable(T.parse("R1(A) R2(A) W1(A) W2(A)"))

    @pytest.mark.parametrize("sched,expected", [
        ("W1(A) R2(A) C2 C1", "Not recoverable"),
        ("W1(A) R2(A) C1 C2", "Recoverable but not cascadeless"),
        ("W1(A) C1 R2(A) W2(A) C2", "Strict"),
        ("W1(A) W2(A) C1 C2", "Cascadeless but not strict"),
        ("R1(A) R2(A) C1 C2", "Strict"),
        ("W1(A) R2(A) A1 C2", "Not recoverable"),
    ])
    def test_recoverability_classes(self, sched, expected):
        assert T.recoverability_class(T.parse(sched)) == expected

    def test_cascading_rollback_is_transitive(self):
        assert T.cascade_victims(T.parse("W1(A) R2(A) W2(B) R3(B) A1"), 1) == [2, 3]
        assert T.cascade_victims(T.parse("W1(A) C1 R2(A) A1"), 1) == []
        assert T.cascade_victims(T.parse("W1(A) R2(A) C1 A2"), 2) == []

    def test_two_phase_locking(self):
        assert T.is_two_phase(T.parse("X1(A) S1(B) U1(A) U1(B)"))
        assert not T.is_two_phase(T.parse("X1(A) U1(A) S1(B) U1(B)"))

    def test_deadlock_detection(self):
        assert T.lock_deadlock(T.parse("X1(A) X2(B) X1(B) X2(A)")) == [1, 2]
        assert T.lock_deadlock(T.parse("X1(A) S2(A) U1(A) X2(B)")) is None
        assert T.lock_deadlock(T.parse("S1(A) S2(A) X1(B) X2(C)")) is None
        assert T.lock_deadlock(T.parse("X1(A) X2(B) X3(C) X1(B) X2(C) X3(A)")) == [1, 2, 3]

    def test_shared_locks_do_not_block_each_other(self):
        assert T.lock_deadlock(T.parse("S1(A) S2(B) S1(B) S2(A)")) is None

    def test_isolation_matrix_follows_the_sql_standard(self):
        assert T.isolation_allows("read uncommitted", "dirty read")
        assert not T.isolation_allows("read committed", "dirty read")
        assert T.isolation_allows("read committed", "non-repeatable read")
        assert not T.isolation_allows("repeatable read", "non-repeatable read")
        assert T.isolation_allows("repeatable read", "phantom read")
        assert not any(T.ISOLATION["serializable"].values())

    def test_counting(self):
        assert T.serial_schedule_count(4) == 24
        assert T.interleaving_count([2, 3]) == 10
        assert T.interleaving_count([2, 2, 2]) == 90


class TestReferences:
    def test_registry_matches_algorithms(self):
        assert run_reference("closure", {"fds": "A->B, B->C", "x": "A"}) == "{A, B, C}"
        assert run_reference("candidate_keys", {"attrs": "ABC", "fds": "AB->C, C->B"}) == "{A, B}, {A, C}"
        assert run_reference("highest_nf", {"attrs": "ABC", "fds": "A->B, B->C"}) == "2NF"
        assert run_reference("deadlock", {"schedule": "X1(A) X2(B) X1(B) X2(A)"}) == "Deadlock: T1, T2"
        assert run_reference("hash_slot", {"size": 7, "keys": [15, 22, 8, 29], "probe": "linear", "key": 29}) == "4"
        assert run_reference("hash_slot", {"size": 5, "keys": [12, 17], "probe": "chain", "key": 12}) == "bucket 2"

    def test_unknown_kind_and_bad_params_are_errors(self):
        with pytest.raises(UnknownReference):
            run_reference("nope", {})
        with pytest.raises(UnknownReference):
            run_reference("closure", {})


class TestResultComparison:
    EC, ER = ["name", "salary"], [["Asha", 150000], ["Bilal", 95000]]

    def cmp(self, cols, rows, **kw):
        return C.compare(cols, rows, self.EC, self.ER, **kw)

    def test_identical_is_correct(self):
        assert self.cmp(self.EC, self.ER).correct

    def test_row_order_is_ignored_unless_required(self):
        flipped = list(reversed(self.ER))
        assert self.cmp(self.EC, flipped).correct
        v = self.cmp(self.EC, flipped, ordered=True)
        assert not v.correct and v.code == "order" and "ORDER BY" in " ".join(v.messages)

    def test_duplicates_matter(self):
        v = self.cmp(self.EC, self.ER + [self.ER[0]])
        assert not v.correct and v.code == "row_count"
        assert any("duplicate" in m.lower() for m in v.messages)

    def test_column_count_mismatch(self):
        v = self.cmp(["name"], [["Asha"], ["Bilal"]])
        assert not v.correct and v.code == "column_count" and "2" in v.messages[0]

    def test_column_names_only_checked_when_required(self):
        assert self.cmp(["n", "s"], self.ER).correct
        v = self.cmp(["n", "s"], self.ER, check_column_names=True)
        assert not v.correct and v.code == "column_names" and "only the column names" in v.messages[0]

    def test_column_names_are_case_insensitive(self):
        assert self.cmp(["NAME", "Salary"], self.ER, check_column_names=True).correct

    def test_wrong_column_order_is_wrong(self):
        assert not self.cmp(["salary", "name"], [[150000, "Asha"], [95000, "Bilal"]]).correct

    def test_int_and_float_are_equal(self):
        assert self.cmp(self.EC, [["Asha", 150000.0], ["Bilal", 95000.0]]).correct

    def test_float_precision(self):
        assert C.compare(["x"], [[1.001]], ["x"], [[1.0]], precision=2).correct
        assert not C.compare(["x"], [[1.01]], ["x"], [[1.0]], precision=2).correct
        assert C.compare(["x"], [[0.1 + 0.2]], ["x"], [[0.3]], precision=2).correct

    def test_null_equals_null_only(self):
        assert C.compare(["x"], [[None]], ["x"], [[None]]).correct
        assert not C.compare(["x"], [[None]], ["x"], [[0]]).correct
        assert not C.compare(["x"], [[""]], ["x"], [[None]]).correct

    def test_strings_are_case_sensitive(self):
        assert not C.compare(["x"], [["asha"]], ["x"], [["Asha"]]).correct

    def test_number_text_are_different_types(self):
        assert not C.compare(["x"], [["1"]], ["x"], [[1]]).correct

    def test_missing_and_extra_rows_are_reported(self):
        v = self.cmp(self.EC, [["Asha", 150000], ["Zed", 1]])
        assert not v.correct and v.code == "values"
        text = " ".join(v.messages)
        assert "Unexpected rows" in text and "Missing rows" in text and "Zed" in text

    def test_inner_join_hint(self):
        v = C.compare(["a"], [[1]], ["a"], [[1], [2]], sql="SELECT a FROM t JOIN u ON t.k = u.k")
        assert any("LEFT JOIN" in m for m in v.messages)

    def test_null_hint(self):
        v = C.compare(["a"], [[1]], ["a"], [[None]], sql="SELECT a FROM t")
        assert any("NULL" in m for m in v.messages)

    def test_different_valid_query_shapes_are_equivalent_by_result(self):
        # Equivalence is judged on results, so the SQL text is irrelevant when the rows match.
        a = C.compare(["n"], [["x"], ["y"]], ["n"], [["y"], ["x"]], sql="SELECT n FROM a JOIN b USING (k)")
        b = C.compare(["n"], [["x"], ["y"]], ["n"], [["y"], ["x"]], sql="SELECT n FROM a WHERE k IN (SELECT k FROM b)")
        assert a.correct and b.correct

    def test_messages_are_bounded(self):
        v = C.compare(["a"], [[i] for i in range(100)], ["a"], [[1000 + i] for i in range(100)])
        assert len(v.messages) <= 8 and all(len(m) < 400 for m in v.messages)

    def test_payload_is_truncated(self):
        p = C.result_payload(["a"], [[i] for i in range(50)])
        assert len(p["rows"]) == C.MAX_SHOWN_ROWS and p["row_count"] == 50 and p["truncated"]


class TestShortAnswers:
    @pytest.mark.parametrize("given", ["ABC", "a b c", "C,B,A", "{A, B, C}", "cba"])
    def test_attr_sets_ignore_order_case_and_punctuation(self, given):
        assert C.grade_short("attrs", ["A", "B", "C"], given)

    @pytest.mark.parametrize("given", ["AB", "ABCD", "", "   ", "123"])
    def test_attr_sets_wrong(self, given):
        assert not C.grade_short("attrs", ["A", "B", "C"], given)

    def test_keys(self):
        assert C.grade_short("keys", ["AB", "CD"], "ba, DC")
        assert C.grade_short("keys", ["AB", "CD"], "CD; AB")
        assert not C.grade_short("keys", ["AB", "CD"], "AB")
        assert not C.grade_short("keys", ["AB"], "A, B")

    def test_numbers(self):
        assert C.grade_short("number", 6, "6") and C.grade_short("number", 6, " 6.0 ") and C.grade_short("number", 1000, "1,000")
        assert not C.grade_short("number", 6, "six") and not C.grade_short("number", 6, "7")

    def test_unknown_kind_or_none_is_never_correct(self):
        assert not C.grade_short("weird", "x", "x")
        assert not C.grade_short("attrs", ["A"], None)

    def test_canonical_forms(self):
        assert C.canonical_short("attrs", ["B", "A"]) == "{A, B}"
        assert C.canonical_short("keys", ["BA", "C"]) == "{A, B}, {C}"
        assert C.canonical_short("number", 6) == "6"
