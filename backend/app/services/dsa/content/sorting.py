"""Topic C (Sorting and Searching) and the recursive-sort subtopics of Topic H."""

from __future__ import annotations

from app.services.dsa import algos as A
from app.services.dsa.references import _s

from .build import M, S, mk, mk_ref, states_trace


def _others(states, k, arr):
    """Distractors for 'state after pass k': other passes, the input and the final order."""
    pick = [_s(x) for i, x in enumerate(states) if i != k - 1] + [_s(arr), _s(sorted(arr))]
    return pick


def _partition_trace(arr):
    """Step-by-step Lomuto partition (pivot = last element) for the trace viewer."""
    a, lo, hi = list(arr), 0, len(arr) - 1
    pivot, i, steps = a[hi], lo - 1, [{"label": f"pivot = {a[hi]}", "state": _s(a)}]
    for j in range(lo, hi):
        if a[j] <= pivot:
            i += 1
            a[i], a[j] = a[j], a[i]
            steps.append({"label": f"a[{j}]={a[i]} ≤ pivot → swap into index {i}", "state": _s(a)})
        else:
            steps.append({"label": f"a[{j}]={a[j]} > pivot → skip", "state": _s(a)})
    a[i + 1], a[hi] = a[hi], a[i + 1]
    steps.append({"label": f"place pivot at index {i + 1}", "state": _s(a)})
    return steps


def bubble():
    s = "bubble-sort"
    a1 = [64, 34, 25, 12, 22, 11, 90]
    st1 = A.bubble_sort(a1)[0]
    a2 = [5, 1, 4, 2, 8]
    a3 = [7, 3, 9, 2, 6]
    st3 = A.bubble_sort(a3)[0]
    return [
        mk_ref(s, "trace", "Bubble sort (ascending, adjacent swaps, left to right) is run on [64, 34, 25, 12, 22, 11, 90]. What does the array look like after the FIRST pass?", "bubble_pass",
               {"arr": a1, "k": 1}, _others(st1, 1, a1), "In pass 1 each larger value bubbles right until it meets a bigger one; 64 travels to just before 90.", d="easy", t=75,
               trace=states_trace(st1), hints=["Compare neighbours left to right and swap when the left one is larger."]),
        mk_ref(s, "trace", "Bubble sort is run on [7, 3, 9, 2, 6]. What is the array after the SECOND pass?", "bubble_pass", {"arr": a3, "k": 2}, _others(st3, 2, a3),
               "After pass 2 the two largest values are in their final positions at the right end.", d="medium", t=90, trace=states_trace(st3)),
        mk_ref(s, "complexity", "How many swaps does bubble sort perform on [5, 1, 4, 2, 8]? (A swap occurs each time an adjacent pair is out of order.)", "bubble_swaps", {"arr": a2},
               ["3", "5", "9"], "The number of swaps equals the number of inversions in the input.", d="medium", t=75, complexity={"time": "O(n²)", "space": "O(1)"}, trace=states_trace(A.bubble_sort(a2)[0])),
        mk_ref(s, "complexity", "An optimised bubble sort stops after a pass that makes no swap. How many passes (including the final check pass) does it make on [2, 1, 3, 4, 5]?", "bubble_passes",
               {"arr": [2, 1, 3, 4, 5]}, ["1", "3", "4"], "Pass 1 fixes the only inversion; pass 2 finds nothing to swap and stops.", d="medium", t=60, complexity={"time": "O(n) best case with the early-exit flag"}),
        mk(s, "complexity", "What are the best- and worst-case time complexities of bubble sort WITH the early-exit flag?", "Best O(n), worst O(n²)", ["Best O(n log n), worst O(n²)", "Best O(n²), worst O(n²)", "Best O(1), worst O(n)"],
           "An already-sorted array needs a single pass of n − 1 comparisons; a reversed array needs about n²/2.", d="easy", t=45, complexity={"time": "O(n²)", "best": "O(n)", "average": "O(n²)", "worst": "O(n²)", "space": "O(1)"},
           ver=M("Standard analysis of optimised bubble sort.")),
        mk(s, "output", "What does this code print?", "[1, 3, 2, 4]", ["[1, 2, 3, 4]", "[3, 1, 2, 4]", "[1, 3, 4, 2]"], "A single left-to-right pass: 3 and 1 swap, 3 and 4 stay, then 4 and 2 swap, leaving [1, 3, 2, 4].",
           d="medium", t=70, code="a = [3, 1, 4, 2]\nfor i in range(len(a) - 1):\n    if a[i] > a[i + 1]:\n        a[i], a[i + 1] = a[i + 1], a[i]\nprint(a)", ver=S("[1, 3, 2, 4]"),
           trace=[{"label": "i=0: 3>1 swap", "state": "[1, 3, 4, 2]"}, {"label": "i=1: 3>4? no", "state": "[1, 3, 4, 2]"}, {"label": "i=2: 4>2 swap", "state": "[1, 3, 2, 4]"}]),
    ]


def insertion():
    s = "insertion-sort"
    a1 = [5, 2, 4, 6, 1, 3]
    st1 = A.insertion_sort(a1)[0]
    a2 = [12, 11, 13, 5, 6]
    st2 = A.insertion_sort(a2)[0]
    return [
        mk_ref(s, "trace", "Insertion sort runs on [5, 2, 4, 6, 1, 3]. What is the array after the 4th element (index 4, value 1) has been inserted into the sorted prefix?", "insertion_state",
               {"arr": a1, "k": 4}, _others(st1, 4, a1), "Value 1 is smaller than all four sorted elements, so they all shift right and 1 lands at index 0.", d="medium", t=90,
               trace=states_trace(st1, "After inserting element")),
        mk_ref(s, "trace", "Insertion sort runs on [12, 11, 13, 5, 6]. What is the array after the SECOND insertion step (inserting 13)?", "insertion_state", {"arr": a2, "k": 2}, _others(st2, 2, a2),
               "13 is already larger than the sorted prefix [11, 12], so nothing moves.", d="easy", t=60, trace=states_trace(st2, "After inserting element")),
        mk_ref(s, "complexity", "How many element shifts does insertion sort make on [5, 2, 4, 6, 1, 3]?", "insertion_shifts", {"arr": a1}, ["6", "12", "15"],
               "Shifts equal the number of inversions in the input.", d="medium", t=80, complexity={"time": "O(n²)", "space": "O(1)"}),
        mk(s, "complexity", "On which input does insertion sort run fastest, and in what time?", "Already sorted input, in O(n)", ["Reverse-sorted input, in O(n)", "Reverse-sorted input, in O(log n)", "Already sorted input, in O(1)"],
           "With sorted input each new element needs a single comparison.", d="easy", t=45, complexity={"time": "O(n²)", "best": "O(n)", "average": "O(n²)", "worst": "O(n²)", "space": "O(1)"},
           ver=M("Best case n-1 comparisons.")),
        mk(s, "scenario", "A log file is already almost sorted by timestamp; only a few entries are slightly out of place. Which of these simple sorts is the best fit?", "Insertion sort",
           ["Selection sort", "Bubble sort without early exit", "Linear search then swap"], "Insertion sort does work proportional to the number of inversions, so it is close to linear here; selection sort always does ~n²/2 comparisons.", d="medium", t=60,
           ver=M("Insertion sort is adaptive: cost = n + inversions.")),
        mk(s, "conceptual", "Which statement about insertion sort is TRUE?", "It is stable and sorts in place", ["It is unstable and needs O(n) extra space", "It is stable but needs O(n) extra space", "It always makes exactly n(n−1)/2 comparisons"],
           "Elements equal to the key are not moved past it, so order of equals is preserved; only O(1) extra space is used.", d="medium", t=45, ver=M("Insertion sort with strict > comparison is stable, in-place.")),
    ]


def selection():
    s = "selection-sort"
    a1 = [64, 25, 12, 22, 11]
    st1 = A.selection_sort(a1)[0]
    a2 = [29, 10, 14, 37, 13]
    st2 = A.selection_sort(a2)[0]
    return [
        mk_ref(s, "trace", "Selection sort (find the minimum of the unsorted part, swap it to the front) runs on [64, 25, 12, 22, 11]. What is the array after the SECOND pass?", "selection_state",
               {"arr": a1, "k": 2}, _others(st1, 2, a1), "Pass 1 puts 11 first; pass 2 finds 12 in the rest and swaps it into index 1.", d="easy", t=70, trace=states_trace(st1)),
        mk_ref(s, "trace", "Selection sort runs on [29, 10, 14, 37, 13]. What is the array after the THIRD pass?", "selection_state", {"arr": a2, "k": 3}, _others(st2, 3, a2),
               "Each pass fixes the next smallest value at the front of the unsorted part.", d="medium", t=80, trace=states_trace(st2)),
        mk_ref(s, "complexity", "How many comparisons does selection sort make on ANY array of 5 elements?", "selection_comps", {"arr": a1}, ["4", "5", "15"],
               "It always scans the whole unsorted part: 4 + 3 + 2 + 1 = n(n−1)/2, regardless of order.", d="medium", t=60, complexity={"time": "Θ(n²) in every case", "space": "O(1)"}),
        mk_ref(s, "complexity", "How many swaps does selection sort make on [64, 25, 12, 22, 11]? (A swap happens only when the minimum is not already in place.)", "selection_swaps", {"arr": a1},
               ["2", "5", "10"], "At most n − 1 swaps; here every pass but the last moves something.", d="medium", t=70, complexity={"time": "O(n²) comparisons, O(n) swaps", "space": "O(1)"}),
        mk(s, "scenario", "Writing to flash memory is very expensive but reading is cheap. Which simple sort minimises the number of writes?", "Selection sort",
           ["Bubble sort", "Insertion sort", "Linear search"], "Selection sort performs at most n − 1 swaps, far fewer writes than bubble or insertion sort.", d="medium", t=60,
           ver=M("Selection sort does O(n) swaps; bubble/insertion do O(n^2) writes in the worst case.")),
        mk(s, "conceptual", "Why is the usual swap-based selection sort NOT stable?", "A long-distance swap can move an element past an equal one",
           ["It uses recursion", "It compares with ≥ instead of >", "It needs extra memory proportional to n"], "Example: [2a, 2b, 1] becomes [1, 2b, 2a] after the first swap.", d="hard", t=75,
           ver=M("Counter-example [2a,2b,1] -> [1,2b,2a] shows equal elements reorder.")),
    ]


def linear():
    s = "linear-search"
    arr = [14, 3, 9, 27, 5, 18]
    return [
        mk_ref(s, "complexity", "How many comparisons does linear search make to find 27 in [14, 3, 9, 27, 5, 18]?", "linear_comps", {"arr": arr, "target": 27}, ["3", "6", "5"],
               "It checks 14, 3, 9, then 27 on the fourth comparison.", d="easy", t=30, complexity={"time": "O(n)", "best": "O(1)", "worst": "O(n)"}),
        mk_ref(s, "complexity", "How many comparisons does linear search make for an UNSUCCESSFUL search of 99 in [14, 3, 9, 27, 5, 18]?", "linear_comps", {"arr": arr, "target": 99}, ["1", "5", "7"],
               "Every element is examined once before concluding the value is absent.", d="easy", t=30, complexity={"time": "O(n)"}),
        mk(s, "scenario", "Which situation makes linear search a perfectly reasonable choice?", "A small, unsorted list that is searched only once",
           ["A sorted list of ten million records searched millions of times", "A hash table with no collisions", "A balanced search tree"], "With little data or a single search, the O(n) cost is negligible and no preparation is needed.", d="easy", t=45,
           ver=M("Linear search needs no ordering or preprocessing.")),
        mk(s, "output", "What does this code print?", "-1", ["0", "None", "3"], "No element equals 7, so the function falls through to return -1.", d="easy", t=30,
           code="def find(a, x):\n    for i, v in enumerate(a):\n        if v == x:\n            return i\n    return -1\n\nprint(find([4, 8, 15], 7))", ver=S("-1")),
        mk(s, "output", "What does this code print? (note which occurrence is returned)", "1", ["3", "0", "2"], "The loop returns as soon as it finds the FIRST match, at index 1.", d="medium", t=40,
           code="a = [5, 9, 2, 9]\nfor i in range(len(a)):\n    if a[i] == 9:\n        print(i)\n        break", ver=S("1")),
    ]


def binary():
    s = "binary-search"
    arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    arr2 = [3, 6, 9, 12, 15, 18, 21, 24, 27]
    return [
        mk_ref(s, "trace", "Binary search (mid = (lo + hi) // 2) looks for 23 in [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]. Which indices are probed, in order?", "binary_probes", {"arr": arr, "target": 23},
               ["4, 6, 5", "5", "4, 8, 5"], "mid=4 (16<23) → search 5..9, mid=7 (56>23) → search 5..6, mid=5 (23) found.", d="medium", t=75,
               trace=[{"label": "lo=0, hi=9", "state": "mid=4 → 16 < 23, lo=5"}, {"label": "lo=5, hi=9", "state": "mid=7 → 56 > 23, hi=6"}, {"label": "lo=5, hi=6", "state": "mid=5 → 23 found"}]),
        mk_ref(s, "trace", "Binary search for 10 in [3, 6, 9, 12, 15, 18, 21, 24, 27] (mid = (lo + hi) // 2). Which indices are probed before it reports 'not found'?", "binary_probes", {"arr": arr2, "target": 10},
               ["4, 1, 2", "4, 2, 3", "4, 1, 3, 2"], "mid=4 (15>10) → hi=3; mid=1 (6<10) → lo=2; mid=2 (9<10) → lo=3; mid=3 (12>10) → hi=2; stop.", d="hard", t=100,
               trace=[{"label": "lo=0, hi=8", "state": "mid=4 → 15 > 10, hi=3"}, {"label": "lo=0, hi=3", "state": "mid=1 → 6 < 10, lo=2"}, {"label": "lo=2, hi=3", "state": "mid=2 → 9 < 10, lo=3"}, {"label": "lo=3, hi=3", "state": "mid=3 → 12 > 10, hi=2"}, {"label": "lo=3, hi=2", "state": "lo > hi → not found"}]),
        mk(s, "complexity", "Roughly how many comparisons does binary search need, at most, on a sorted array of 1000 elements?", "10", ["1000", "500", "100"], "⌊log₂ 1000⌋ + 1 = 10.", d="medium", t=45,
           complexity={"time": "O(log n)", "best": "O(1)", "worst": "O(log n)", "space": "O(1) iterative"}, ver=M("2^10 = 1024 > 1000, so at most 10 probes.")),
        mk(s, "conceptual", "What precondition must hold for binary search to be correct?", "The array must be sorted", ["The array must have distinct elements", "The array length must be a power of two", "The array must contain the target"],
           "Binary search discards half the range based on order, which only works on sorted data.", d="easy", t=30, ver=M("Sortedness is the precondition; duplicates are allowed.")),
        mk(s, "output", "What does this code print?", "4", ["3", "5", "-1"], "mid goes 3 → (value 8 < 9, lo=4) → mid 4, a[4] = 9 found.", d="medium", t=60,
           code="a = [1, 3, 5, 8, 9, 12, 14]\nlo, hi = 0, len(a) - 1\nwhile lo <= hi:\n    mid = (lo + hi) // 2\n    if a[mid] == 9:\n        print(mid)\n        break\n    elif a[mid] < 9:\n        lo = mid + 1\n    else:\n        hi = mid - 1", ver=S("4")),
        mk(s, "scenario", "A sorted array of 10⁶ elements is searched 10⁶ times. Which total cost is closest?", "About 2 × 10⁷ comparisons with binary search", ["About 10⁶ comparisons with binary search", "About 10¹² comparisons with binary search", "About 2 × 10⁷ comparisons with linear search"],
           "Each binary search needs about 20 probes, so 10⁶ searches cost about 2 × 10⁷; linear search would cost up to 10¹².", d="hard", t=75, ver=M("log2(10^6) ~ 20 probes per search.")),
    ]


# --- H. recursive sorts -------------------------------------------------------------------------


def merge_sort_q():
    s = "recursive-merge-sort"
    a1 = [38, 27, 43, 3, 9, 82, 10]
    ms, steps, comps = A.merge_sort(a1)
    return [
        mk_ref(s, "trace", "Merge sort splits at mid = len // 2 (left half is the shorter one for odd lengths). For [38, 27, 43, 3, 9, 82, 10], what is the FIRST merge performed (the first time two sorted halves are combined)?", "mergesort_first_merge",
               {"arr": a1}, ["[27, 38, 43]", "[3, 9]", "[3, 27, 38, 43]"], "The recursion goes left until single elements: [38] and [27] are merged first, giving [27, 38].", d="hard", t=100,
               trace=[{"label": f"merge {i + 1}", "state": f"{l} + {r} → {m}"} for i, (l, r, m) in enumerate(steps)]),
        mk_ref(s, "complexity", "How many merge operations (calls that combine two sorted halves) does merge sort perform on an array of 8 distinct elements?", "mergesort_merge_count", {"arr": [8, 7, 6, 5, 4, 3, 2, 1]},
               ["3", "8", "4"], "A merge happens for every internal node of the recursion tree: n − 1 = 7.", d="medium", t=60, complexity={"time": "O(n log n)", "space": "O(n)"}),
        mk(s, "complexity", "What are merge sort's time and auxiliary space complexities?", "Time O(n log n) in every case; space O(n)", ["Time O(n²) worst case; space O(1)", "Time O(n log n) average, O(n²) worst; space O(log n)", "Time O(n) best case; space O(n)"],
           "The recursion has log n levels, each doing O(n) merging work, using an O(n) buffer.", d="medium", t=45, complexity={"time": "O(n log n)", "best": "O(n log n)", "worst": "O(n log n)", "space": "O(n)"},
           ver=M("Standard top-down merge sort with temporary arrays.")),
        mk_ref(s, "conceptual", "Merge the sorted halves [4, 9, 15] and [1, 9, 20]. What does the merge step produce?", "merge_result", {"left": [4, 9, 15], "right": [1, 9, 20]},
               ["[1, 4, 9, 15, 20]", "[1, 4, 9, 9, 20, 15]", "[4, 9, 15, 1, 9, 20]"], "Take the smaller front element each time; both 9s are kept, taking the left one first (stability).", d="easy", t=55),
        mk(s, "scenario", "Which property makes merge sort attractive for sorting records by one key while preserving the earlier order of equal keys?", "It is stable", ["It sorts in place", "It needs no recursion", "It has O(n) worst-case time"],
           "Taking from the left half on ties keeps equal keys in their original order.", d="medium", t=45, ver=M("Merge sort with <= on ties is stable.")),
        mk(s, "output", "What does this code print?", "[1, 2, 3, 5, 8]", ["[8, 5, 3, 2, 1]", "[1, 2, 3, 8, 5]", "[5, 8, 1, 2, 3]"], "ms returns the sorted merge of its recursively sorted halves.", d="medium", t=60,
           code="def merge(l, r):\n    out = []\n    while l and r:\n        out.append(l.pop(0) if l[0] <= r[0] else r.pop(0))\n    return out + l + r\n\ndef ms(a):\n    if len(a) <= 1:\n        return a\n    m = len(a) // 2\n    return merge(ms(a[:m]), ms(a[m:]))\n\nprint(ms([5, 2, 8, 1, 3]))", ver=S("[1, 2, 3, 5, 8]")),
    ]


def quick_sort_q():
    s = "recursive-quick-sort"
    a1 = [10, 80, 30, 90, 40, 50, 70]
    a2 = [8, 3, 7, 1, 6, 5]
    return [
        mk_ref(s, "trace", "Quick sort uses Lomuto partition with the LAST element as pivot. On [10, 80, 30, 90, 40, 50, 70], what is the array after the first partition?", "quick_partition", {"arr": a1},
               ["[10, 30, 40, 50, 70, 80, 90]", "[10, 80, 30, 90, 40, 50, 70]", "[70, 10, 30, 40, 50, 80, 90]"], "Elements ≤ 70 are gathered on the left in order (10, 30, 40, 50), then the pivot 70 swaps with the first larger element (80).", d="hard", t=110,
               trace=_partition_trace(a1)),
        mk_ref(s, "trace", "Quick sort (Lomuto, pivot = last element) runs on [8, 3, 7, 1, 6, 5]. At which index does the pivot end up after the first partition?", "quick_pivot_index", {"arr": a2},
               ["0", "3", "5"], "Elements ≤ 5 are 3 and 1; so the pivot 5 is placed at index 2.", d="medium", t=80, trace=_partition_trace(a2)),
        mk(s, "complexity", "What is quick sort's time complexity when it always picks the last element as pivot and the input is already sorted?", "O(n²)", ["O(n log n)", "O(n)", "O(log n)"],
           "Each partition removes only the pivot, so there are n levels of O(n) work.", d="medium", t=60, complexity={"time": "O(n²) worst case", "best": "O(n log n)", "average": "O(n log n)", "worst": "O(n²)", "space": "O(log n) average recursion stack"},
           ver=M("Sorted input with last-element pivot is the textbook worst case.")),
        mk(s, "conceptual", "Which statement about quick sort is correct?", "Average time is O(n log n) and it sorts in place apart from the recursion stack", ["It is always O(n log n) and stable", "It needs O(n) auxiliary space like merge sort", "It cannot be written recursively"],
           "Partitioning swaps in place; only the recursion stack uses extra space (O(log n) on average).", d="medium", t=50, ver=M("Standard properties of quick sort.")),
        mk_ref(s, "complexity", "How many partition calls does quick sort (Lomuto, last pivot) make on [3, 1, 2]?", "quick_calls", {"arr": [3, 1, 2]}, ["2", "3", "4"],
               "Partition [3,1,2] with pivot 2 → [1,2,3] (pivot at 1); the left part [1] and right part [3] have size 1 and need no partition: 1 call.", d="medium", t=70, complexity={"time": "O(n²) worst, O(n log n) average"}),
        mk(s, "scenario", "To avoid quick sort's worst case on already-sorted input, which pivot strategy helps most?", "Pick a random element or the median of three", ["Always pick the first element", "Always pick the last element", "Pick the maximum element"],
           "Randomised or median-of-three pivots make badly unbalanced splits unlikely on sorted input.", d="medium", t=50, ver=M("Standard pivot-selection mitigation.")),
    ]


def all_questions():
    out = []
    for f in (bubble, insertion, selection, linear, binary, merge_sort_q, quick_sort_q):
        out.extend(f())
    return out
