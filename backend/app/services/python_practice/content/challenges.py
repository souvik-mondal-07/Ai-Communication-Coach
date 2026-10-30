"""Coding challenges (algorithms and data structures). Every problem has a reference solution AND an independent alternative that must agree on all tests."""

from __future__ import annotations

import heapq
import itertools
from collections import Counter, OrderedDict, deque

from app.services.python_practice import compare
from app.services.python_practice.content.build import code_q as C


def _sig(entry: str, args: str = "") -> str:
    return f"def {entry}({args}):"


def _st(entry: str, args: str, doc: str) -> str:
    return f'def {entry}({args}):\n    """{doc}"""\n    # your code here\n    pass'


# ---------------------------------------------------------------- references (trusted code, also shown after the reveal) ----------
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
    return []


def _two_sum_alt(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []


def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]


def _is_pal_alt(s):
    t = "".join(ch for ch in s.lower() if ch.isalnum())
    i, j = 0, len(t) - 1
    while i < j:
        if t[i] != t[j]:
            return False
        i, j = i + 1, j - 1
    return True


def first_unique_char(s):
    counts = Counter(s)
    for i, ch in enumerate(s):
        if counts[ch] == 1:
            return i
    return -1


def _fuc_alt(s):
    for i, ch in enumerate(s):
        if s.count(ch) == 1:
            return i
    return -1


def valid_parentheses(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def _vp_alt(s):
    s = "".join(ch for ch in s if ch in "()[]{}")
    prev = None
    while prev != s:
        prev = s
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""


def merge_sorted(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    return out + a[i:] + b[j:]


def _ms_alt(a, b):
    return sorted(a + b)


def has_duplicates(items):
    seen = set()
    for x in items:
        if x in seen:
            return True
        seen.add(x)
    return False


def _hd_alt(items):
    return len(set(items)) != len(items)


def top_words(text, k):
    words = [w for w in text.lower().split() if w]
    counts = Counter(words)
    return sorted(counts.items(), key=lambda p: (-p[1], p[0]))[:k]


def _tw_alt(text, k):
    freq = {}
    for w in text.lower().split():
        freq[w] = freq.get(w, 0) + 1
    pairs = [(w, n) for w, n in freq.items()]
    pairs.sort(key=lambda p: p[0])
    pairs.sort(key=lambda p: p[1], reverse=True)
    return pairs[:k]


def flatten(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def _flat_alt(nested):
    stack, out = [list(nested)[::-1]], []
    while stack:
        top = stack[-1]
        if not top:
            stack.pop(); continue
        item = top.pop()
        if isinstance(item, list):
            stack.append(item[::-1])
        else:
            out.append(item)
    return out


def longest_unique_substring(s):
    last, start, best = {}, 0, 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best


def _lus_alt(s):
    best = 0
    for i in range(len(s)):
        seen = set()
        for ch in s[i:]:
            if ch in seen:
                break
            seen.add(ch)
        best = max(best, len(seen))
    return best


def max_window_sum(nums, k):
    if k <= 0 or k > len(nums):
        return None
    cur = sum(nums[:k])
    best = cur
    for i in range(k, len(nums)):
        cur += nums[i] - nums[i - k]
        best = max(best, cur)
    return best


def _mws_alt(nums, k):
    if k <= 0 or k > len(nums):
        return None
    return max(sum(nums[i:i + k]) for i in range(len(nums) - k + 1))


def binary_search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def _bs_alt(nums, target):
    return nums.index(target) if target in nums else -1


def group_anagrams(words):
    groups = {}
    for w in words:
        groups.setdefault("".join(sorted(w)), []).append(w)
    return [sorted(g) for g in groups.values()]


def _ga_alt(words):
    used, out = [False] * len(words), []
    for i, w in enumerate(words):
        if used[i]:
            continue
        g = [w]
        used[i] = True
        for j in range(i + 1, len(words)):
            if not used[j] and sorted(words[j]) == sorted(w):
                g.append(words[j]); used[j] = True
        out.append(sorted(g))
    return out


def eval_rpn(tokens):
    st = []
    for t in tokens:
        if t in ("+", "-", "*", "/"):
            b, a = st.pop(), st.pop()
            st.append(a + b if t == "+" else a - b if t == "-" else a * b if t == "*" else int(a / b))
        else:
            st.append(int(t))
    return st[0]


def _rpn_alt(tokens):
    ops = {"+": lambda a, b: a + b, "-": lambda a, b: a - b, "*": lambda a, b: a * b, "/": lambda a, b: int(a / b)}
    st = deque()
    for t in tokens:
        if t in ops:
            b = st.pop(); a = st.pop()
            st.append(ops[t](a, b))
        else:
            st.append(int(t))
    return st.pop()


class MinStack:
    def __init__(self):
        self._items = []
        self._mins = []

    def push(self, x):
        self._items.append(x)
        self._mins.append(x if not self._mins else min(x, self._mins[-1]))

    def pop(self):
        self._mins.pop()
        return self._items.pop()

    def get_min(self):
        return self._mins[-1]


class _MinStackAlt:
    def __init__(self):
        self.a = []

    def push(self, x):
        self.a.append(x)

    def pop(self):
        return self.a.pop()

    def get_min(self):
        return min(self.a)


class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.cap:
            self.data.popitem(last=False)


class _LRUAlt:
    def __init__(self, capacity):
        self.cap, self.keys, self.vals = capacity, [], {}

    def get(self, key):
        if key not in self.vals:
            return -1
        self.keys.remove(key); self.keys.append(key)
        return self.vals[key]

    def put(self, key, value):
        if key in self.vals:
            self.keys.remove(key)
        elif len(self.keys) >= self.cap:
            del self.vals[self.keys.pop(0)]
        self.keys.append(key); self.vals[key] = value


class LinkedList:
    class _Node:
        def __init__(self, value, nxt=None):
            self.value, self.next = value, nxt

    def __init__(self):
        self.head = None

    def append(self, value):
        node = LinkedList._Node(value)
        if self.head is None:
            self.head = node
            return
        cur = self.head
        while cur.next:
            cur = cur.next
        cur.next = node

    def reverse(self):
        prev, cur = None, self.head
        while cur:
            cur.next, prev, cur = prev, cur, cur.next
        self.head = prev

    def to_list(self):
        out, cur = [], self.head
        while cur:
            out.append(cur.value)
            cur = cur.next
        return out


class _LLAlt:
    def __init__(self):
        self.items = []

    def append(self, v):
        self.items.append(v)

    def reverse(self):
        self.items.reverse()

    def to_list(self):
        return list(self.items)


def inorder(tree):
    if tree is None:
        return []
    value, left, right = tree
    return inorder(left) + [value] + inorder(right)


def _inorder_alt(tree):
    out, stack, cur = [], [], tree
    while stack or cur is not None:
        while cur is not None:
            stack.append(cur); cur = cur[1]
        cur = stack.pop()
        out.append(cur[0])
        cur = cur[2]
    return out


def coin_change(coins, amount):
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] != INF else -1


def _cc_alt(coins, amount):
    best = {0: 0}
    frontier = deque([0])
    while frontier:
        cur = frontier.popleft()
        for c in coins:
            nxt = cur + c
            if nxt <= amount and nxt not in best:
                best[nxt] = best[cur] + 1
                frontier.append(nxt)
    return best.get(amount, -1)


def permutations(items):
    if len(items) <= 1:
        return [list(items)]
    out = []
    for i, x in enumerate(items):
        for rest in permutations(items[:i] + items[i + 1:]):
            out.append([x] + rest)
    return out


def _perm_alt(items):
    return [list(p) for p in itertools.permutations(items)]


def lcs_length(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _lcs_alt(a, b):
    from functools import lru_cache

    @lru_cache(None)
    def go(i, j):
        if i == len(a) or j == len(b):
            return 0
        return 1 + go(i + 1, j + 1) if a[i] == b[j] else max(go(i + 1, j), go(i, j + 1))
    return go(0, 0)


def count_islands(grid):
    if not grid:
        return 0
    rows, cols, seen, count = len(grid), len(grid[0]), set(), 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                stack = [(r, c)]
                seen.add((r, c))
                while stack:
                    y, x = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == "1" and (ny, nx) not in seen:
                            seen.add((ny, nx)); stack.append((ny, nx))
    return count


def _isl_alt(grid):
    g = [list(row) for row in grid]
    def sink(r, c):
        if 0 <= r < len(g) and 0 <= c < len(g[0]) and g[r][c] == "1":
            g[r][c] = "0"
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sink(r + dr, c + dc)
    n = 0
    for r in range(len(g)):
        for c in range(len(g[0]) if g else 0):
            if g[r][c] == "1":
                n += 1
                sink(r, c)
    return n


def three_sum(nums):
    nums = sorted(nums)
    out = []
    for i in range(len(nums) - 2):
        if i and nums[i] == nums[i - 1]:
            continue
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                out.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                while lo < hi and nums[lo] == nums[lo - 1]:
                    lo += 1
    return out


def _3s_alt(nums):
    return sorted([list(t) for t in {tuple(sorted(c)) for c in itertools.combinations(nums, 3) if sum(c) == 0}])


def rearrange_no_adjacent(s):
    counts = Counter(s)
    heap = [(-n, ch) for ch, n in counts.items()]
    heapq.heapify(heap)
    out, prev = [], (0, "")
    while heap:
        n, ch = heapq.heappop(heap)
        out.append(ch)
        if prev[0] < 0:
            heapq.heappush(heap, prev)
        prev = (n + 1, ch)
    return "".join(out) if len(out) == len(s) else ""


@compare.register_validator("no_adjacent_rearrangement")
def _val_rearr(inp, actual):
    s = inp["args"][0]
    expected_possible = rearrange_no_adjacent(s) != ""
    if not isinstance(actual, str):
        return False
    if not expected_possible:
        return actual == ""
    return sorted(actual) == sorted(s) and all(a != b for a, b in zip(actual, actual[1:]))


def questions() -> list[dict]:
    big = list(range(1500))
    return [
        C("hash-maps", "easy", "coding", "Two Sum", "Given a list of integers `nums` and an integer `target`, return the indices `[i, j]` (i < j) of the two numbers that add up to `target`. Exactly one solution exists in the visible examples; if none exists return `[]`. Aim for one pass.",
          "two_sum", _sig("two_sum", "nums, target"), _st("two_sum", "nums, target", "Return [i, j] with nums[i] + nums[j] == target."), two_sum, _two_sum_alt,
          [([2, 7, 11, 15], 9), ([3, 2, 4], 6), ([3, 3], 6), ([1, 2, 3], 7), ([-1, -2, -3, -4], -6), ([0, 4, 3, 0], 0), (list(range(2000)) + [5000, 7000], 12000)],
          constraints=("0 <= len(nums) <= 10**4", "Return the pair with the smallest second index"), time_c="O(n)", space_c="O(n)",
          expl="Store each value's index in a dict. For every n, the complement target - n is a constant-time lookup, so one pass suffices. The nested-loop version is O(n^2).", hints=("What do you need to remember about the numbers you have already seen?", "A dict from value to index gives O(1) lookups.")),
        C("string-manipulation", "easy", "coding", "Valid Palindrome", "Return True if `s` reads the same forwards and backwards after removing every character that is not a letter or digit and ignoring case; otherwise False. An empty cleaned string counts as a palindrome.",
          "is_palindrome", _sig("is_palindrome", "s"), _st("is_palindrome", "s", "Return True if s is a palindrome ignoring case and punctuation."), is_palindrome, _is_pal_alt,
          [("A man, a plan, a canal: Panama",), ("race a car",), ("",), (" ",), ("a.",), ("0P",), ("No 'x' in Nixon",)], constraints=("0 <= len(s) <= 2 * 10**5",), time_c="O(n)", space_c="O(n)",
          expl="Filter with str.isalnum, lower-case, and compare with the reverse. A two-pointer scan does the same in O(1) extra space after cleaning.", hints=("str.isalnum() tells you whether a character is a letter or digit.",)),
        C("frequency-counting", "easy", "coding", "First Unique Character", "Return the index of the first character in `s` that appears exactly once, or -1 if there is none.",
          "first_unique_char", _sig("first_unique_char", "s"), _st("first_unique_char", "s", "Return the index of the first non-repeating character, or -1."), first_unique_char, _fuc_alt,
          [("leetcode",), ("loveleetcode",), ("aabb",), ("",), ("z",), ("abcabcd",), ("a" * 3000 + "b",)], constraints=("0 <= len(s) <= 10**5",), time_c="O(n)", space_c="O(1) for a fixed alphabet",
          expl="Count characters with Counter (or a dict), then scan again for the first count of 1. Calling s.count in a loop is O(n^2).", hints=("Two passes: count first, then find.",), imports=("from collections import Counter",)),
        C("stack-queue", "easy", "coding", "Valid Brackets", "Given a string of `()[]{}` and possibly other characters, return True if every opening bracket is closed by the matching type in the correct order. Ignore other characters.",
          "valid_parentheses", _sig("valid_parentheses", "s"), _st("valid_parentheses", "s", "Return True if the brackets are balanced and correctly nested."), valid_parentheses, _vp_alt,
          [("()[]{}",), ("(]",), ("",), ("([)]",), ("{[]}",), ("(((",), (")",), ("a(b)c[d]",)], constraints=("0 <= len(s) <= 10**4",), time_c="O(n)", space_c="O(n)",
          expl="Push openers on a stack. On a closer, the top of the stack must be its matching opener. At the end the stack must be empty.", hints=("Use a list as a stack.", "Check for an empty stack before popping.")),
        C("two-pointers", "easy", "coding", "Merge Two Sorted Lists", "Given two sorted lists of integers, return one new sorted list containing all their elements. Do not simply call sorted() on the concatenation: use the fact that both inputs are already sorted.",
          "merge_sorted", _sig("merge_sorted", "a, b"), _st("merge_sorted", "a, b", "Merge two sorted lists into one sorted list."), merge_sorted, _ms_alt,
          [([1, 3, 5], [2, 4, 6]), ([], [1]), ([], []), ([1, 1], [1]), ([5, 6], [1, 2]), ([-3, 0], [-2, 4]), (list(range(0, 3000, 2)), list(range(1, 3000, 2)))], constraints=("Both inputs are sorted ascending",), time_c="O(n + m)", space_c="O(n + m)",
          expl="Keep one pointer in each list and always take the smaller current element; append whatever remains. This is the merge step of merge sort.", hints=("Compare a[i] and b[j].", "After the loop one list may still have elements left.")),
        C("duplicate-detection", "easy", "coding", "Contains Duplicate", "Return True if any value appears at least twice in `items`, otherwise False. Elements are hashable (ints or strings).",
          "has_duplicates", _sig("has_duplicates", "items"), _st("has_duplicates", "items", "Return True if any value occurs more than once."), has_duplicates, _hd_alt,
          [([1, 2, 3, 1],), ([1, 2, 3],), ([],), (["a", "b", "a"],), ([7],), ([1, "1"],), (list(range(5000)) + [4999],)], constraints=("0 <= len(items) <= 10**5",), time_c="O(n)", space_c="O(n)",
          expl="A set gives O(1) membership. Stop at the first repeat; comparing len(set(items)) with len(items) is a compact alternative.", hints=("A set remembers what you have seen.",)),
        C("frequency-counting", "medium", "coding", "Top K Words", "Return the `k` most frequent words in `text` (split on whitespace, lower-cased) as a list of `(word, count)` tuples, ordered by count descending and then alphabetically. Return fewer than `k` items if there are fewer distinct words.",
          "top_words", _sig("top_words", "text, k"), _st("top_words", "text, k", "Return the k most common (word, count) pairs."), top_words, _tw_alt,
          [("a b a c b a", 2), ("the cat the Cat", 1), ("x y z", 5), ("", 3), ("b a b a c", 2), ("One one ONE two", 2), (" ".join(["w%d" % (i % 50) for i in range(3000)]), 3)], constraints=("k >= 1",), time_c="O(n + d log d)", space_c="O(d)",
          expl="Count with Counter, then sort by the key (-count, word) so ties break alphabetically, and slice to k. Python's sort is stable, and a tuple key handles both criteria at once.", hints=("sorted(..., key=lambda p: (-p[1], p[0])).",), imports=("from collections import Counter",)),
        C("nested-collections", "medium", "coding", "Flatten Nested Lists", "Given a list that may contain integers and arbitrarily nested lists of integers, return a flat list of all integers in their original left-to-right order.",
          "flatten", _sig("flatten", "nested"), _st("flatten", "nested", "Flatten arbitrarily nested lists."), flatten, _flat_alt,
          [([1, [2, [3, 4]], 5],), ([],), ([[], [[]]],), ([[1], [2], [3]],), ([1, 2, 3],), ([[[[7]]]],), ([[1, [2]], [[3], 4], 5, [[[6]]]],)], constraints=("Nesting depth is below 100",), time_c="O(n)", space_c="O(depth)",
          expl="Recurse: for each item, extend the result with flatten(item) if it is a list, else append it. An explicit stack avoids recursion limits.", hints=("isinstance(item, list) detects nesting.",)),
        C("sliding-window", "medium", "coding", "Longest Substring Without Repeats", "Return the length of the longest substring of `s` that contains no repeated characters.",
          "longest_unique_substring", _sig("longest_unique_substring", "s"), _st("longest_unique_substring", "s", "Return the length of the longest substring without repeating characters."), longest_unique_substring, _lus_alt,
          [("abcabcbb",), ("bbbbb",), ("",), ("pwwkew",), ("abba",), ("dvdf",), ("a",), ("abcdefghijklmnopqrstuvwxyz" * 120,)], constraints=("0 <= len(s) <= 5 * 10**4",), time_c="O(n)", space_c="O(min(n, alphabet))",
          expl="Slide a window [start, i]. Record each character's last index; if the current character was seen inside the window, move start just past that index. The window length never shrinks the best answer. Restarting from every index is O(n^2).", hints=("Remember the last index of each character in a dict.", "Only move `start` forward, never backward (see 'abba').")),
        C("sliding-window", "medium", "coding", "Maximum Window Sum", "Return the maximum sum of any `k` consecutive elements of `nums`. If `k` is not between 1 and len(nums), return None.",
          "max_window_sum", _sig("max_window_sum", "nums, k"), _st("max_window_sum", "nums, k", "Return the largest sum of k consecutive elements, or None."), max_window_sum, _mws_alt,
          [([1, 3, 2, 6, -1, 4], 3), ([5], 1), ([1, 2], 3), ([1, 2], 0), ([-5, -2, -9], 2), ([4, 4, 4, 4], 4), (big, 700)], constraints=("Values may be negative",), time_c="O(n)", space_c="O(1)",
          expl="Compute the first window's sum, then slide: add the entering element and subtract the leaving one. Recomputing sum(nums[i:i+k]) each time is O(n*k).", hints=("Update the running sum instead of recalculating it.",)),
        C("binary-search", "medium", "coding", "Binary Search", "Given a sorted list of distinct integers and a `target`, return the index of `target`, or -1 if it is absent. Aim for O(log n): halve the search range each step (a hidden test uses a list of 5,000 items).",
          "binary_search", _sig("binary_search", "nums, target"), _st("binary_search", "nums, target", "Return the index of target in sorted nums, or -1."), binary_search, _bs_alt,
          [([-1, 0, 3, 5, 9, 12], 9), ([-1, 0, 3, 5, 9, 12], 2), ([], 1), ([5], 5), ([5], 4), ([1, 3], 3), (list(range(0, 10000, 2)), 9998), (list(range(0, 10000, 2)), 9999)], constraints=("nums is sorted ascending with distinct values",), time_c="O(log n)", space_c="O(1)",
          expl="Keep lo and hi; test the midpoint and discard the half that cannot contain the target. Loop while lo <= hi so a single remaining element is still checked.", hints=("mid = (lo + hi) // 2", "Which half do you discard when nums[mid] < target?")),
        C("hash-maps", "medium", "coding", "Group Anagrams", "Group words that are anagrams of each other. Return a list of groups; inside each group sort the words alphabetically. The order of the groups does not matter.",
          "group_anagrams", _sig("group_anagrams", "words"), _st("group_anagrams", "words", "Return groups of anagrams (each group sorted)."), group_anagrams, _ga_alt,
          [(["eat", "tea", "tan", "ate", "nat", "bat"],), ([""],), (["a"],), (["ab", "ba", "abc"],), ([],), (["listen", "silent", "enlist", "google", "gogole"],), (["a", "a"],)], compare_mode="unordered", constraints=("Words are lower-case letters",), time_c="O(n * k log k)", space_c="O(n * k)",
          expl="Words are anagrams exactly when their sorted letters match, so use the sorted string as a dictionary key and collect the words under it.", hints=("''.join(sorted(word)) is a canonical key.",)),
        C("stack-queue", "medium", "coding", "Evaluate Reverse Polish Notation", "Evaluate an arithmetic expression given in Reverse Polish Notation as a list of string tokens (`+ - * /` and integers). Division truncates toward zero. The expression is always valid.",
          "eval_rpn", _sig("eval_rpn", "tokens"), _st("eval_rpn", "tokens", "Evaluate the RPN expression and return an int."), eval_rpn, _rpn_alt,
          [(["2", "1", "+", "3", "*"],), (["4", "13", "5", "/", "+"],), (["7"],), (["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"],), (["-7", "2", "/"],), (["3", "-4", "*"],), (["5", "1", "2", "+", "4", "*", "+", "3", "-"],)], constraints=("Use int(a / b) so division truncates toward zero",), time_c="O(n)", space_c="O(n)",
          expl="Push numbers; on an operator pop the right operand first, then the left, apply it and push the result. Python's // floors toward negative infinity, so use int(a / b) to truncate toward zero.", hints=("Pop b first, then a.", "-7 // 2 is -4 but the expected result is -3.")),
        C("stack-queue", "medium", "coding", "Min Stack", "Implement a class `MinStack` with `push(x)`, `pop()` (returns the removed value) and `get_min()` (returns the current minimum). Every operation must be O(1).",
          "MinStack", "class MinStack:", "class MinStack:\n    def __init__(self):\n        pass\n\n    def push(self, x):\n        pass\n\n    def pop(self):\n        pass\n\n    def get_min(self):\n        pass", MinStack, _MinStackAlt,
          [([], [("push", [3]), ("push", [1]), ("push", [2]), ("get_min", []), ("pop", []), ("get_min", []), ("pop", []), ("get_min", [])]),
           ([], [("push", [-2]), ("push", [0]), ("push", [-3]), ("get_min", []), ("pop", []), ("pop", []), ("get_min", [])]),
           ([], [("push", [5]), ("get_min", [])]), ([], [("push", [2]), ("push", [2]), ("pop", []), ("get_min", [])]),
           ([], [("push", [4]), ("push", [9]), ("push", [1]), ("push", [1]), ("pop", []), ("get_min", []), ("pop", []), ("get_min", [])]),
           ([], [("push", [i]) for i in range(40, 0, -1)] + [("get_min", [])] + [("pop", [])] * 20 + [("get_min", [])])], mode="class", constraints=("get_min is only called on a non-empty stack",), time_c="O(1) per operation", space_c="O(n)",
          expl="Keep a second stack of running minimums, pushing min(x, current_min) with every push, so the minimum is always at the top of the helper stack. Scanning with min() would make get_min O(n).", hints=("Store the minimum alongside each element.",)),
        C("data-structure-choice", "hard", "coding", "LRU Cache", "Implement `LRUCache(capacity)` with `get(key)` (returns the value or -1) and `put(key, value)`. When the cache exceeds its capacity, evict the least recently used key. Both `get` and `put` count as a use. Aim for O(1) per operation (hint: collections.OrderedDict).",
          "LRUCache", "class LRUCache:", "class LRUCache:\n    def __init__(self, capacity):\n        pass\n\n    def get(self, key):\n        pass\n\n    def put(self, key, value):\n        pass", LRUCache, _LRUAlt,
          [([2], [("put", [1, 1]), ("put", [2, 2]), ("get", [1]), ("put", [3, 3]), ("get", [2]), ("put", [4, 4]), ("get", [1]), ("get", [3]), ("get", [4])]),
           ([1], [("put", [2, 1]), ("get", [2]), ("put", [3, 2]), ("get", [2]), ("get", [3])]),
           ([2], [("put", [2, 1]), ("put", [2, 2]), ("get", [2]), ("put", [1, 1]), ("put", [4, 1]), ("get", [2])]),
           ([3], [("put", [1, 1]), ("put", [2, 2]), ("put", [3, 3]), ("get", [1]), ("put", [4, 4]), ("get", [2]), ("get", [1]), ("get", [3])]),
           ([2], [("get", [9]), ("put", [9, 5]), ("put", [9, 6]), ("get", [9])]),
           ([50], [("put", [i, i * 2]) for i in range(200)] + [("get", [i]) for i in range(145, 155)])], mode="class", constraints=("capacity >= 1",), time_c="O(1) per operation", space_c="O(capacity)",
          expl="OrderedDict keeps keys in usage order: move_to_end marks a key as most recent and popitem(last=False) evicts the oldest. A plain list makes every operation O(n).", hints=("OrderedDict.move_to_end(key)", "popitem(last=False) removes the oldest entry.",), imports=("from collections import OrderedDict",)),
        C("linked-lists", "medium", "coding", "Singly Linked List with Reverse", "Implement a singly linked list class `LinkedList` with `append(value)`, `reverse()` (in place, by re-pointing `next` links) and `to_list()` returning the values head to tail. Do not store the values in a Python list.",
          "LinkedList", "class LinkedList:", "class LinkedList:\n    def __init__(self):\n        self.head = None\n\n    def append(self, value):\n        pass\n\n    def reverse(self):\n        pass\n\n    def to_list(self):\n        pass", LinkedList, _LLAlt,
          [([], [("append", [1]), ("append", [2]), ("append", [3]), ("to_list", []), ("reverse", []), ("to_list", [])]), ([], [("to_list", []), ("reverse", []), ("to_list", [])]),
           ([], [("append", [7]), ("reverse", []), ("to_list", [])]), ([], [("append", [1]), ("append", [2]), ("reverse", []), ("append", [3]), ("to_list", [])]),
           ([], [("append", [i]) for i in range(30)] + [("reverse", []), ("reverse", []), ("to_list", [])]), ([], [("append", [None]), ("append", [0]), ("reverse", []), ("to_list", [])])], mode="class", constraints=("Values can be any hashable value, including 0 and None",), time_c="append O(n), reverse O(n)", space_c="O(1) extra",
          expl="Reverse by walking the list once and flipping each node's `next` pointer: keep `prev`, `cur`; set cur.next = prev, then advance. Finish by making `prev` the new head.", hints=("Track prev and cur; save cur.next before overwriting it.",)),
        C("trees-graphs", "medium", "coding", "In-order Traversal", "A binary tree is given as nested lists `[value, left, right]` where an empty child is `None` (and an empty tree is `None`). Return the values in in-order (left, node, right).",
          "inorder", _sig("inorder", "tree"), _st("inorder", "tree", "Return the in-order list of values."), inorder, _inorder_alt,
          [([2, [1, None, None], [3, None, None]],), (None,), ([1, None, None],), ([4, [2, [1, None, None], [3, None, None]], [6, [5, None, None], [7, None, None]]],), ([1, None, [2, [3, None, None], None]],), ([3, [2, [1, None, None], None], None],)], constraints=("Up to 10**4 nodes",), time_c="O(n)", space_c="O(h)",
          expl="Visit the left subtree, then the node, then the right subtree. For a binary search tree this produces sorted order.", hints=("Base case: None gives an empty list.",)),
        C("dynamic-programming", "medium", "coding", "Coin Change", "Given coin denominations `coins` and a target `amount`, return the fewest coins needed to make the amount, or -1 if it is impossible. You may use each coin any number of times.",
          "coin_change", _sig("coin_change", "coins, amount"), _st("coin_change", "coins, amount", "Return the minimum number of coins, or -1."), coin_change, _cc_alt,
          [([1, 2, 5], 11), ([2], 3), ([1], 0), ([186, 419, 83, 408], 6249), ([2, 5, 10], 27), ([5], 5), ([1, 3, 4], 6), ([7, 13], 1000)], constraints=("0 <= amount <= 10**4",), time_c="O(amount * len(coins))", space_c="O(amount)",
          expl="Let dp[a] be the fewest coins for amount a: dp[a] = 1 + min(dp[a - c]). A greedy 'largest coin first' strategy is wrong ([1, 3, 4] with 6: greedy gives 4+1+1 = 3 coins, optimal is 3+3 = 2).", hints=("Build answers for amounts 0..amount in order.", "Greedy does not work here.")),
        C("backtracking", "medium", "coding", "All Permutations", "Return every permutation of a list of distinct items as a list of lists. The order of the permutations does not matter.",
          "permutations", _sig("permutations", "items"), _st("permutations", "items", "Return all permutations as lists."), permutations, _perm_alt,
          [([1, 2, 3],), ([0, 1],), ([1],), ([],), (["a", "b", "c", "d"],), ([3, 1, 2],)], compare_mode="unordered", constraints=("0 <= len(items) <= 6", "Do not use itertools.permutations to solve it"), time_c="O(n * n!)", space_c="O(n * n!)",
          expl="Fix each element in turn as the first and recurse on the rest (choose, explore, un-choose). There are n! results, so the time is inherently factorial.", hints=("Pick one item, permute the remaining ones, prepend.",), imports=()),
        C("dynamic-programming", "hard", "coding", "Longest Common Subsequence", "Return the length of the longest common subsequence of strings `a` and `b` (characters in order, not necessarily adjacent).",
          "lcs_length", _sig("lcs_length", "a, b"), _st("lcs_length", "a, b", "Return the LCS length."), lcs_length, _lcs_alt,
          [("abcde", "ace"), ("abc", "abc"), ("abc", "def"), ("", "abc"), ("aggtab", "gxtxayb"), ("a", "a"), ("abcbdab", "bdcaba")], constraints=("0 <= len(a), len(b) <= 500",), time_c="O(len(a) * len(b))", space_c="O(len(a) * len(b))",
          expl="dp[i][j] = dp[i-1][j-1] + 1 when a[i-1] == b[j-1], otherwise max(dp[i-1][j], dp[i][j-1]). The table can be reduced to two rows.", hints=("Think of a table indexed by prefix lengths of a and b.",)),
        C("trees-graphs", "hard", "coding", "Count Islands", "A grid is a list of strings of '1' (land) and '0' (water). Count the islands: groups of land cells connected horizontally or vertically.",
          "count_islands", _sig("count_islands", "grid"), _st("count_islands", "grid", "Return the number of islands."), count_islands, _isl_alt,
          [(["11000", "11000", "00100", "00011"],), (["111", "010", "111"],), ([],), (["0"],), (["1"],), (["101", "010", "101"],), (["1" * 25] * 25,)], constraints=("Cells are connected only up, down, left or right",), time_c="O(rows * cols)", space_c="O(rows * cols)",
          expl="Scan the grid; on each unvisited land cell start a flood fill (DFS/BFS) marking the whole island visited and increment the count. Use an explicit stack to stay clear of the recursion limit on large grids.", hints=("Mark cells visited so you never count an island twice.",)),
        C("two-pointers", "hard", "coding", "Three Sum", "Return all unique triplets `[a, b, c]` (sorted ascending inside each triplet) from `nums` that sum to zero. The order of the triplets does not matter and duplicate triplets must not appear.",
          "three_sum", _sig("three_sum", "nums"), _st("three_sum", "nums", "Return unique zero-sum triplets."), three_sum, _3s_alt,
          [([-1, 0, 1, 2, -1, -4],), ([0, 1, 1],), ([0, 0, 0],), ([],), ([0, 0, 0, 0],), ([-2, 0, 1, 1, 2],), ([3, -1, -2, 0, 1, 2, -3, -1],)], compare_mode="unordered", constraints=("0 <= len(nums) <= 3000",), time_c="O(n^2)", space_c="O(1) extra",
          expl="Sort, then fix one number and use two pointers on the rest to find pairs that cancel it, skipping equal neighbours to avoid duplicates. Trying every triple is O(n^3).", hints=("Sorting enables the two-pointer scan.", "Skip duplicate values for the fixed element and for the pointers.")),
        C("array-problems", "hard", "coding", "Rearrange With No Adjacent Repeats", "Rearrange the characters of `s` so that no two adjacent characters are equal and return any valid arrangement, or an empty string if it is impossible. (Several answers can be valid, and any valid one is accepted.)",
          "rearrange_no_adjacent", _sig("rearrange_no_adjacent", "s"), _st("rearrange_no_adjacent", "s", "Return a rearrangement with no equal neighbours, or ''."), rearrange_no_adjacent, None,
          [("aab",), ("aaab",), ("abc",), ("a",), ("",), ("aabbcc",), ("aaaabbbcc",)], compare_mode="validator", validator="no_adjacent_rearrangement", constraints=("1 <= len(s) <= 500 in the hidden tests",), time_c="O(n log k)", space_c="O(k)",
          expl="Greedy with a max-heap: repeatedly place the most frequent remaining character that differs from the one just placed. If the heap runs out early, the most frequent letter was too common (more than ceil(n / 2)) and the answer is ''. Because many arrangements are valid, the grader checks the properties (same letters, no equal neighbours) instead of comparing text.", hints=("The most frequent character is the hardest to place.", "A max-heap of (count, char) works.",), imports=("import heapq", "from collections import Counter")),
    ]
