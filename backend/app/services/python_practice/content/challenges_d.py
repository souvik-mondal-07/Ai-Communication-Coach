"""Debugging and code-completion exercises. A debug starter contains a real bug and a completion starter contains `____` blanks;
the verifier proves that each starter FAILS the tests while the reference passes."""

from __future__ import annotations

from collections import Counter

from app.services.python_practice.content.build import code_q as C


def average(nums):
    return sum(nums) / len(nums) if nums else None


def _avg_alt(nums):
    total, n = 0, 0
    for x in nums:
        total += x
        n += 1
    return None if n == 0 else total / n


def append_item(item, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket


def _ai_alt(item, bucket=None):
    return ([] if bucket is None else list(bucket)) + [item] if bucket is not None and False else ([item] if bucket is None else bucket + [item])


def sum_to_n(n):
    return sum(range(1, n + 1))


def _stn_alt(n):
    return n * (n + 1) // 2 if n > 0 else 0


def dedupe_keep_order(items):
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _dko_alt(items):
    return list(dict.fromkeys(items))


def is_anagram(a, b):
    return sorted(a.replace(" ", "").lower()) == sorted(b.replace(" ", "").lower())


def _ia_alt(a, b):
    return Counter(c for c in a.lower() if c != " ") == Counter(c for c in b.lower() if c != " ")


def count_words(text):
    return len(text.split())


def _cw_alt(text):
    n, inside = 0, False
    for ch in text:
        if ch.isspace():
            inside = False
        elif not inside:
            inside, n = True, n + 1
    return n


def word_lengths(words):
    return {w: len(w) for w in words}


def _wl_alt(words):
    out = {}
    for w in words:
        out[w] = len(w)
    return out


def clamp(x, lo, hi):
    return max(lo, min(x, hi))


def _clamp_alt(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def char_frequency(s):
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    return freq


def _cf_alt(s):
    return {ch: s.count(ch) for ch in set(s)}


def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _fib_alt(n):
    seq = [0, 1]
    while len(seq) <= n:
        seq.append(seq[-1] + seq[-2])
    return seq[n]


class Stack:
    def __init__(self):
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        return self._items.pop()

    def peek(self):
        return self._items[-1]

    def size(self):
        return len(self._items)


class _StackAlt:
    def __init__(self):
        self.d = []

    def push(self, x):
        self.d = self.d + [x]

    def pop(self):
        v = self.d[-1]
        self.d = self.d[:-1]
        return v

    def peek(self):
        return self.d[-1]

    def size(self):
        return len(self.d)


def questions() -> list[dict]:
    return [
        C("debugging-function", "easy", "debug", "Fix: Average of an Empty List", "`average(nums)` should return the mean of a list, or `None` for an empty list. It currently crashes on empty input. Fix the bug without changing the other behaviour.",
          "average", "def average(nums):", "def average(nums):\n    return sum(nums) / len(nums)\n", average, _avg_alt, [([2, 4, 6],), ([5],), ([],), ([1, 2],), ([-3, 3],), ([0, 0, 0],)], constraints=("Return None for an empty list",), time_c="O(n)", space_c="O(1)",
          expl="Dividing by len(nums) == 0 raises ZeroDivisionError. Decide the contract for the empty case (here None) and check it explicitly instead of catching the error everywhere.", hints=("What is len([])?", "Guard the empty case first.")),
        C("default-arguments", "medium", "debug", "Fix: Shared Default List", "`append_item(item, bucket=None)` should return a NEW list containing `item` when no bucket is given, otherwise append to the given bucket and return it. Repeated calls without `bucket` currently share one list. Find and fix the bug.",
          "append_item", "def append_item(item, bucket=None):", "def append_item(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n", append_item, _ai_alt, [(1,), (2,), (3,), (4, [9]), ("x",), (5,)], constraints=("Calls may run one after another in the same process",), time_c="O(1)", space_c="O(1)",
          expl="A default value is evaluated once, when the function is defined, so `bucket=[]` is shared by every call that omits it. Use None as the default and create the list inside.", hints=("Where is the default list created, and how many times?", "Use `if bucket is None:`.")),
        C("loops", "easy", "debug", "Fix: Sum 1 to n", "`sum_to_n(n)` should return 1 + 2 + ... + n (and 0 when n <= 0). It is off by one. Fix it.",
          "sum_to_n", "def sum_to_n(n):", "def sum_to_n(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n", sum_to_n, _stn_alt, [(5,), (1,), (0,), (10,), (100,), (-3,)], constraints=("n may be zero or negative",), time_c="O(n)", space_c="O(1)",
          expl="range(n) stops at n - 1 and starts at 0, so n itself is never added. Use range(1, n + 1), or the closed form n * (n + 1) // 2.", hints=("What are the first and last values of range(n)?",)),
        C("duplicate-detection", "medium", "debug", "Fix: Remove Duplicates, Keep Order", "`dedupe_keep_order(items)` must return the unique items in the order they FIRST appeared. The current version loses the order. Fix it.",
          "dedupe_keep_order", "def dedupe_keep_order(items):", "def dedupe_keep_order(items):\n    return list(set(items))\n", dedupe_keep_order, _dko_alt, [([3, 1, 3, 2],), ([1, 1, 1],), ([],), (["b", "a", "b"],), ([5, 4, 3, 2, 1],), ([9, 7, 9, 8, 7],)], constraints=("Items are hashable",), time_c="O(n)", space_c="O(n)",
          expl="A set has no useful order. Track seen items in a set while appending first occurrences to a result list, or use list(dict.fromkeys(items)) (dicts keep insertion order).", hints=("Sets do not preserve order.",)),
        C("string-methods", "medium", "debug", "Fix: Anagram Check", "`is_anagram(a, b)` should ignore case and spaces: 'Dormitory' and 'dirty room' are anagrams. The current version treats them as different.",
          "is_anagram", "def is_anagram(a, b):", "def is_anagram(a, b):\n    return sorted(a) == sorted(b)\n", is_anagram, _ia_alt, [("listen", "silent"), ("Dormitory", "dirty room"), ("abc", "abd"), ("", ""), ("A gentleman", "Elegant man"), ("aa", "a")], constraints=("Ignore case and spaces only",), time_c="O(n log n)", space_c="O(n)",
          expl="Normalise both strings first: lower-case them and remove spaces, then compare their sorted letters (or their Counters).", hints=("What differs between 'Dormitory' and 'dormitory'?",)),
        C("string-methods", "easy", "debug", "Fix: Count Words", "`count_words(text)` should return the number of words, where words are separated by any amount of whitespace. Extra spaces currently inflate the count.",
          "count_words", "def count_words(text):", "def count_words(text):\n    return len(text.split(' '))\n", count_words, _cw_alt, [("hello world",), ("  many   spaces here ",), ("",), ("one",), ("a\tb\nc",), ("   ",)], constraints=("Whitespace includes tabs and newlines",), time_c="O(n)", space_c="O(n)",
          expl="split(' ') splits on every single space and keeps empty strings; split() with no argument splits on runs of any whitespace and drops empties.", hints=("Compare 'a  b'.split(' ') with 'a  b'.split().",)),
        C("dicts", "easy", "complete", "Complete: Word Lengths", "Fill in the blank so `word_lengths(words)` returns a dictionary mapping each word to its length, using a dict comprehension.",
          "word_lengths", "def word_lengths(words):", "def word_lengths(words):\n    return {____: ____ for w in words}\n", word_lengths, _wl_alt, [(["a", "bb"],), ([],), (["hello"],), (["x", "x"],), (["py", "thon", ""],), (["alpha", "be", "gam"],)], time_c="O(n)", space_c="O(n)",
          expl="A dict comprehension is {key_expr: value_expr for item in iterable}; here both expressions use w.", hints=("The key is the word itself.",)),
        C("function-basics", "easy", "complete", "Complete: Clamp", "Fill in the blanks so `clamp(x, lo, hi)` returns x limited to the range [lo, hi], using the built-ins min and max.",
          "clamp", "def clamp(x, lo, hi):", "def clamp(x, lo, hi):\n    return ____(lo, ____(x, hi))\n", clamp, _clamp_alt, [(5, 0, 10), (-3, 0, 10), (42, 0, 10), (0, 0, 10), (10, 0, 10), (2.5, 1, 2)], time_c="O(1)", space_c="O(1)",
          expl="min(x, hi) caps the upper side, then max(lo, ...) raises anything below lo.", hints=("Cap at hi with min, then floor at lo with max.",)),
        C("frequency-counting", "easy", "complete", "Complete: Character Frequency", "Fill in the blank so `char_frequency(s)` returns a dictionary of how many times each character occurs.",
          "char_frequency", "def char_frequency(s):", "def char_frequency(s):\n    freq = {}\n    for ch in s:\n        freq[ch] = freq.get(ch, ____) + 1\n    return freq\n", char_frequency, _cf_alt, [("hello",), ("",), ("aaa",), ("abcabc",), ("a b",), ("Aa",)], time_c="O(n)", space_c="O(k)",
          expl="dict.get(key, default) returns the default when the key is missing; starting from 0 lets the first occurrence become 1.", hints=("What count does a character that was never seen have?",)),
        C("recursion", "easy", "complete", "Complete: Iterative Fibonacci", "Fill in the blanks so `fibonacci(n)` returns the n-th Fibonacci number (fibonacci(0) = 0, fibonacci(1) = 1) using two running values.",
          "fibonacci", "def fibonacci(n):", "def fibonacci(n):\n    a, b = ____, ____\n    for _ in range(n):\n        a, b = b, ____\n    return a\n", fibonacci, _fib_alt, [(0,), (1,), (2,), (10,), (30,), (50,)], time_c="O(n)", space_c="O(1)",
          expl="Start with (F0, F1) = (0, 1). Each step shifts the pair: the new b is the sum of the old a and b.", hints=("The pair starts at (0, 1).",)),
        C("classes-objects", "medium", "complete", "Complete: A Stack Class", "Fill in the blanks so `Stack` supports `push(x)`, `pop()`, `peek()` and `size()` using a list.",
          "Stack", "class Stack:", "class Stack:\n    def __init__(self):\n        self._items = []\n\n    def push(self, x):\n        self._items.____(x)\n\n    def pop(self):\n        return self._items.____()\n\n    def peek(self):\n        return self._items[____]\n\n    def size(self):\n        return len(self._items)\n", Stack, _StackAlt,
          [([], [("push", [1]), ("push", [2]), ("peek", []), ("pop", []), ("size", [])]), ([], [("size", [])]), ([], [("push", ["a"]), ("pop", []), ("size", [])]), ([], [("push", [1]), ("push", [2]), ("push", [3]), ("pop", []), ("pop", []), ("peek", [])]), ([], [("push", [None]), ("size", []), ("peek", [])]), ([], [("push", [i]) for i in range(10)] + [("size", []), ("pop", []), ("peek", [])])], mode="class", time_c="O(1) per operation", space_c="O(n)",
          expl="list.append and list.pop work at the end of a list, which is the top of the stack; index -1 reads the last item without removing it.", hints=("The top of the stack is the end of the list.",)),
    ]
