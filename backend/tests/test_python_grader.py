"""Phase 26 -- deterministic code grading: verdicts, hidden-test secrecy, multiple valid solutions, and answers that must NOT be accepted."""

from __future__ import annotations

import json

import pytest

from app.services.python_practice import compare, grader
from app.services.python_practice.content import all_seed_questions
from app.services.python_practice.sandbox import runner

pytestmark = pytest.mark.skipif(not runner.capabilities()["available"], reason="isolated runner unavailable on this host")


@pytest.fixture(scope="module")
def problems():
    return {q["title"]: q for q in all_seed_questions() if q["interaction"] == "code"}


def spec(problems, title):
    return problems[title]["spec"]


def test_reference_solution_is_accepted_for_every_problem(problems):
    for title, q in problems.items():
        g = grader.grade(q["spec"], q["spec"]["reference_source"], visible_only=False)
        assert g.accepted and g.passed == g.total == len(q["spec"]["tests"]), (title, g.verdict, g.message)


def test_starter_code_fails_every_coding_problem(problems):
    for title, q in problems.items():
        g = grader.grade(q["spec"], q["spec"]["starter"], visible_only=False)
        assert not g.accepted, title


def test_differently_written_correct_solutions_are_accepted(problems):
    s = spec(problems, "Two Sum")
    brute = "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n"
    assert grader.grade(s, brute, visible_only=False).accepted
    s = spec(problems, "Valid Palindrome")
    alt = "import re\ndef is_palindrome(s):\n    t = re.sub(r'[^a-z0-9]', '', s.lower())\n    return t == ''.join(reversed(t))\n"
    assert grader.grade(s, alt, visible_only=False).accepted


def test_wrong_answer_reports_failures_but_hides_hidden_test_details(problems):
    s = spec(problems, "Two Sum")
    g = grader.grade(s, "def two_sum(nums, target):\n    return [0, 1]\n", visible_only=False)
    assert g.verdict == "wrong_answer" and 0 < g.passed < g.total
    d = g.to_dict()
    for t in d["tests"]:
        if t["visible"]:
            assert t["label"].startswith("Example") or t["label"].startswith("Case")
        else:
            assert t["label"].startswith("Hidden test") and t["message"] is None and t["stdout"] is None
    hidden = [t for t in d["tests"] if not t["visible"]]
    assert hidden and all(set(t) == {"id", "label", "visible", "passed", "status", "message", "stdout", "ms"} for t in hidden)
    assert all(t["message"] is None and t["stdout"] is None for t in hidden)  # a hidden result carries a verdict and nothing else


def test_hidden_test_output_and_errors_are_never_echoed(problems):
    s = spec(problems, "Two Sum")
    hidden_ids = [t["id"] for t in s["tests"] if not t["visible"]]
    src = "def two_sum(nums, target):\n    print('LEAK', nums, target)\n    raise ValueError('LEAK-ERR ' + repr(nums))\n"
    g = grader.grade(s, src, visible_only=False)
    assert "LEAK-ERR" not in json.dumps([o.to_dict() for o in g.outcomes if o.id in hidden_ids])
    vis = [o for o in g.outcomes if o.visible]
    assert vis and all("ValueError" in (o.message or "") for o in vis)  # visible failures do get a bounded message


def test_hardcoding_the_visible_examples_does_not_pass(problems):
    s = spec(problems, "Two Sum")
    hard = "def two_sum(nums, target):\n    if nums == [2, 7, 11, 15]: return [0, 1]\n    if nums == [3, 2, 4]: return [1, 2]\n    return []\n"
    g = grader.grade(s, hard, visible_only=False)
    assert not g.accepted
    trial = grader.grade(s, hard, visible_only=True)
    assert trial.passed == trial.total  # a trial run shows only examples, so the final submission is what protects the grade


def test_expected_keywords_in_a_comment_or_string_prove_nothing(problems):
    s = spec(problems, "Valid Brackets")
    src = "# uses a stack, append, pop, and returns not stack\nNOTE = 'stack = []; stack.append(ch); stack.pop(); return not stack'\ndef valid_parentheses(s):\n    return True\n"
    assert not grader.grade(s, src, visible_only=False).accepted


def test_compile_error_missing_entry_and_runtime_error(problems):
    s = spec(problems, "Two Sum")
    g = grader.grade(s, "def two_sum(nums, target)\n    return []", visible_only=False)
    assert g.verdict == "compile_error" and g.setup_error["type"] == "SyntaxError" and g.setup_error["line"] == 1
    g = grader.grade(s, "def other(): pass", visible_only=False)
    assert g.verdict == "compile_error" and "two_sum" in g.setup_error["message"]
    g = grader.grade(s, "def two_sum(nums, target):\n    return nums[99999]", visible_only=False)
    assert g.verdict == "runtime_error"
    first = next(o for o in g.outcomes if o.visible)
    assert "IndexError" in first.message and "line 2" in first.message


def test_infinite_loop_is_a_timeout_verdict_not_a_hang(problems):
    s = spec(problems, "Two Sum")
    g = grader.grade(s, "def two_sum(nums, target):\n    while True: pass", visible_only=False)
    assert g.verdict == "timeout" and not g.accepted


def test_none_return_gets_a_helpful_hint(problems):
    s = spec(problems, "Valid Palindrome")
    g = grader.grade(s, "def is_palindrome(s):\n    t = s[::-1]\n    t == s\n", visible_only=True)
    assert any("forget `return`" in (o.message or "") for o in g.outcomes)


def test_printing_instead_of_returning_fails_function_problems(problems):
    s = spec(problems, "Two Sum")
    assert not grader.grade(s, "def two_sum(nums, target):\n    print([0, 1])\n", visible_only=True).accepted


def test_class_problem_is_graded_by_behaviour(problems):
    s = spec(problems, "Min Stack")
    wrong = "class MinStack:\n    def __init__(self): self.a = []\n    def push(self, x): self.a.append(x)\n    def pop(self): return self.a.pop()\n    def get_min(self): return self.a[0]\n"
    assert not grader.grade(s, wrong, visible_only=False).accepted
    right = "class MinStack:\n    def __init__(self): self.a = []\n    def push(self, x): self.a.append(x)\n    def pop(self): return self.a.pop()\n    def get_min(self): return min(self.a)\n"
    assert grader.grade(s, right, visible_only=False).accepted


def test_many_valid_answers_are_checked_by_properties(problems):
    s = spec(problems, "Rearrange With No Adjacent Repeats")
    other = "def rearrange_no_adjacent(s):\n    from collections import Counter\n    c = Counter(s)\n    out = []\n    prev = ''\n    for _ in range(len(s)):\n        cands = sorted([k for k in c if c[k] > 0 and k != prev], key=lambda k: (-c[k], k))\n        if not cands:\n            return ''\n        out.append(cands[0]); c[cands[0]] -= 1; prev = cands[0]\n    return ''.join(out)\n"
    assert grader.grade(s, other, visible_only=False).accepted
    assert not grader.grade(s, "def rearrange_no_adjacent(s):\n    return s\n", visible_only=False).accepted
    assert not grader.grade(s, "def rearrange_no_adjacent(s):\n    return ''\n", visible_only=False).accepted


def test_unordered_comparison_accepts_any_order_but_not_wrong_content(problems):
    s = spec(problems, "All Permutations")
    rev = "def permutations(items):\n    import itertools\n    return [list(p) for p in reversed(list(itertools.permutations(items)))]\n"
    assert grader.grade(s, rev, visible_only=False).accepted
    assert not grader.grade(s, "def permutations(items):\n    return [list(items)]\n", visible_only=False).accepted


def test_output_flood_and_print_noise_do_not_break_grading(problems):
    s = spec(problems, "Two Sum")
    noisy = "def two_sum(nums, target):\n    print('x' * 100000)\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen: return [seen[target - n], i]\n        seen[n] = i\n    return []\n"
    assert grader.grade(s, noisy, visible_only=False).accepted


def test_visible_trial_run_never_executes_hidden_tests(problems):
    s = spec(problems, "Two Sum")
    g = grader.grade(s, s["reference_source"], visible_only=True)
    assert g.total == sum(1 for t in s["tests"] if t["visible"]) and all(o.visible for o in g.outcomes)


def test_runner_unavailable_is_reported_not_graded_as_wrong(problems, monkeypatch):
    monkeypatch.setattr(runner, "capabilities", lambda force=False: {"available": False, "reason": "off for test"})
    g = grader.grade(spec(problems, "Two Sum"), "def two_sum(a, b): return []", visible_only=False)
    assert g.verdict == "runner_error" and g.passed == 0 and "off for test" in g.message


# --- comparison semantics (pure functions) -----------------------------------------------------------------------------------------------


def test_comparison_rules():
    m = compare.values_match
    assert m({"__tuple__": [1, 2]}, [1, 2]) and m(2, 2.0) and not m(True, 1) and not m(1, True) and not m("1", 1) and not m(None, 0)
    assert m([3, 1, 2], [1, 2, 3], "unordered") and not m([1, 1, 2], [1, 2, 2], "unordered")
    assert m({"__set__": [1, 2]}, {"__set__": [2, 1]}, "set_like") and m(0.1 + 0.2, 0.3, "float")
    assert not m([1, 2], [1, 2, 3]) and not m({"a": 1}, {"a": 1, "b": 2}) and not m({"a": 1}, {"a": 2})
    assert m("a\n b  \n\n", "a\n b", "text") and not m("a b", "a  b", "text")
    assert compare.grade_short({"kind": "output", "value": ["1\n2"]}, " 1 \n2\n") and compare.grade_short({"kind": "number", "value": [4]}, "4.0")
    assert not compare.grade_short({"kind": "text", "value": ["TypeError"]}, "") and compare.grade_short({"kind": "text", "value": ["TypeError"]}, "  typeerror ")


def test_unknown_validator_fails_closed(problems):
    s = dict(spec(problems, "Rearrange With No Adjacent Repeats"), validator="does_not_exist")
    assert not grader.grade(s, s["reference_source"], visible_only=False).accepted
