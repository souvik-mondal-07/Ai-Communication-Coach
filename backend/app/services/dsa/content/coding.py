"""Format F: coding exercises (write-a-function, fill-the-line, fix-the-bug) across the syllabus."""

from __future__ import annotations

from .build import M, mk, mk_code

INF_NOTE = "Use -1 for unreachable vertices."


def T(label, args, expected, visible=True, edge=False):
    return {"label": label, "args": args, "expected": expected, "visible": visible, "edge": edge}


def spec(name, template, solution, tests, sample=None):
    return {"function_name": name, "template": template, "reference_solution": solution, "test_cases": tests, "sample_io": sample}


def _lines(*lines):
    return "\n".join(lines)



# Hints and constraints for the exercises above whose call did not spell them out (every coding exercise must have both).
_GUIDANCE = {
    "selection_sort_swaps": (["Find the index of the minimum of the unsorted part first.", "Only count a swap when that index differs from i."], "O(n²) comparisons; O(n) swaps at most."),
    "find_all": (["Collect indices, not values.", "Do not stop at the first match."], "O(n) time; return indices in increasing order."),
    "service_order": (["Store (priority, arrival_index, name) tuples so ties keep arrival order."], "O(n log n) time."),
    "postorder_of": (["Insert keys with a recursive function that compares with the node key.", "Postorder = left, right, node."], "Ignore duplicate keys; O(n·h) time."),
    "power": (["Base case: exp == 0 returns 1.", "Compute half = power(base, exp // 2) once and reuse it."], "0 ≤ exp ≤ 10⁴; O(log exp) calls."),
    "hanoi_moves": (["Solve n − 1 disks first, then move the largest, then n − 1 again.", "Alternate the roles of the spare and destination pegs."], "0 ≤ n ≤ 10; the result has 2ⁿ − 1 moves."),
    "kth_largest": (["Keep a min-heap holding the k largest values so far.", "When the heap grows past k, pop its smallest."], "1 ≤ k ≤ len(nums); O(n log k) time."),
    "heap_sort": (["Build the max-heap bottom-up from index n // 2 − 1 down to 0.", "After each swap with the last element, sift the new root down within the shrunken heap."], "O(n log n) time; do not use sorted() or sort()."),
    "two_sum": (["Store value → index as you scan.", "Check for the complement before storing the current value."], "O(n) time with a hash table; return the first pair found scanning left to right."),
    "hash_insert_linear": (["Home slot is k % m.", "While the slot is taken, move to (i + 1) % m."], "len(keys) ≤ m; keys are non-negative integers."),
    "bfs_order": (["Build an adjacency list first and sort each neighbour list.", "Mark a vertex as seen when you enqueue it."], "O(V + E) time."),
    "dijkstra_dist": (["Use a min-heap of (distance, vertex).", "Skip heap entries whose distance is already stale."], "All weights ≥ 0; O((V + E) log V). Report -1 for unreachable vertices."),
    "has_negative_cycle": (["Start every vertex at distance 0 so cycles anywhere are found.", "A change during the n-th round proves a negative cycle."], "O(V · E) time."),
    "floyd_warshall": (["Initialise d[i][i] = 0 and the rest to infinity.", "The outermost loop must be the intermediate vertex k."], "O(V³) time; convert infinity to -1 only at the end."),
}


def _complete_guidance(qs):
    for q in qs:
        extra = _GUIDANCE.get(q["coding"]["function_name"])
        if extra:
            q["hints"] = q["hints"] or extra[0]
            q["constraints"] = q["constraints"] or extra[1]
    return qs


# ---- write-a-function ---------------------------------------------------------------------------------


def write_functions():
    qs = []
    qs.append(mk_code("array-traversal", "Write second_largest(nums) that returns the second-largest DISTINCT value in the list, or -1 if there are fewer than two distinct values. Traverse the list once.",
        spec("second_largest", "def second_largest(nums):\n    # your code here\n    pass\n",
             _lines("def second_largest(nums):", "    first = second = None", "    for x in nums:", "        if first is None or x > first:", "            first, second = x, first", "        elif x != first and (second is None or x > second):", "            second = x", "    return -1 if second is None else second"),
             [T("sample", [[4, 9, 2, 7]], 7), T("all equal", [[5, 5, 5]], -1, False, True), T("single element", [[1]], -1, False, True), T("duplicate maximum", [[3, 1, 3, 2]], 2, False), T("negatives", [[-4, -1, -9]], -4, False)],
             "second_largest([4, 9, 2, 7]) → 7"),
        "Track the largest and second-largest distinct values in one pass; update the second only when the value differs from the largest.", d="medium", t=420,
        hints=["Keep two variables, first and second, both initially empty.", "When a new maximum appears, the old maximum becomes the second."], constraints="0 ≤ len(nums) ≤ 10⁵; O(n) time, O(1) extra space.", complexity={"time": "O(n)", "space": "O(1)"}))
    qs.append(mk_code("array-insert-delete", "Write insert_at(arr, pos, x) that returns a NEW list with x inserted at index pos by shifting later elements right. If pos is outside 0..len(arr), return an unchanged copy.",
        spec("insert_at", "def insert_at(arr, pos, x):\n    # your code here\n    pass\n",
             _lines("def insert_at(arr, pos, x):", "    if pos < 0 or pos > len(arr):", "        return list(arr)", "    out = list(arr) + [None]", "    for i in range(len(arr), pos, -1):", "        out[i] = out[i - 1]", "    out[pos] = x", "    return out"),
             [T("middle", [[1, 2, 4], 2, 3], [1, 2, 3, 4]), T("empty list", [[], 0, 9], [9], False, True), T("append at end", [[1, 2], 2, 3], [1, 2, 3], False, True), T("insert at front", [[5, 6], 0, 4], [4, 5, 6], False), T("position out of range", [[1, 2], 5, 9], [1, 2], False, True)],
             "insert_at([1, 2, 4], 2, 3) → [1, 2, 3, 4]"),
        "Grow the array by one slot, shift elements from the end down to pos one place right, then place x.", d="easy", t=300, hints=["Loop from the last index down to pos.", "Handle the range check first."],
        constraints="O(n) time; do not modify the input list.", complexity={"time": "O(n)", "space": "O(n)"}))
    qs.append(mk_code("array-sort-search-merge", "Write merge_sorted(a, b) that merges two ascending lists into one ascending list using two pointers (do not call sorted()).",
        spec("merge_sorted", "def merge_sorted(a, b):\n    # your code here\n    pass\n",
             _lines("def merge_sorted(a, b):", "    out, i, j = [], 0, 0", "    while i < len(a) and j < len(b):", "        if a[i] <= b[j]:", "            out.append(a[i])", "            i += 1", "        else:", "            out.append(b[j])", "            j += 1", "    return out + a[i:] + b[j:]"),
             [T("interleaved", [[1, 3, 5], [2, 4, 6]], [1, 2, 3, 4, 5, 6]), T("first empty", [[], [1]], [1], False, True), T("both empty", [[], []], [], False, True), T("duplicates", [[1, 1], [1]], [1, 1, 1], False, True), T("uneven lengths", [[5], [1, 2, 3]], [1, 2, 3, 5], False)],
             "merge_sorted([1, 3], [2, 4]) → [1, 2, 3, 4]"),
        "Compare the two fronts, take the smaller, and append whatever remains once one list is exhausted.", d="easy", t=360, hints=["Keep one index per list.", "After the loop, at most one list has leftovers."],
        constraints="O(m + n) time.", complexity={"time": "O(m + n)", "space": "O(m + n)"}))
    qs.append(mk_code("binary-search", "Write binary_search(arr, target) for an ascending list. Return the index of target, or -1 if absent. Use mid = (lo + hi) // 2.",
        spec("binary_search", "def binary_search(arr, target):\n    # your code here\n    pass\n",
             _lines("def binary_search(arr, target):", "    lo, hi = 0, len(arr) - 1", "    while lo <= hi:", "        mid = (lo + hi) // 2", "        if arr[mid] == target:", "            return mid", "        if arr[mid] < target:", "            lo = mid + 1", "        else:", "            hi = mid - 1", "    return -1"),
             [T("found", [[1, 3, 5, 7, 9], 7], 3), T("missing", [[1, 3, 5, 7, 9], 4], -1, False), T("empty list", [[], 1], -1, False, True), T("single hit", [[2], 2], 0, False, True), T("single miss", [[2], 3], -1, False, True), T("last element", [[1, 2, 3, 4, 5, 6], 6], 5, False), T("first element", [[1, 2, 3, 4, 5, 6], 1], 0, False, True)],
             "binary_search([1, 3, 5], 5) → 2"),
        "Halve the search range each iteration, moving lo or hi past mid.", d="easy", t=360, hints=["Loop while lo <= hi.", "Always move past mid, never onto it."], constraints="O(log n) time, O(1) space.", complexity={"time": "O(log n)", "space": "O(1)"}))
    qs.append(mk_code("bubble-sort", "Write bubble_sort(arr) that returns a new ascending list using adjacent swaps (no sorted()/sort()).",
        spec("bubble_sort", "def bubble_sort(arr):\n    # your code here\n    pass\n",
             _lines("def bubble_sort(arr):", "    a = list(arr)", "    for end in range(len(a) - 1, 0, -1):", "        swapped = False", "        for i in range(end):", "            if a[i] > a[i + 1]:", "                a[i], a[i + 1] = a[i + 1], a[i]", "                swapped = True", "        if not swapped:", "            break", "    return a"),
             [T("sample", [[5, 1, 4, 2, 8]], [1, 2, 4, 5, 8]), T("empty", [[]], [], False, True), T("single", [[1]], [1], False, True), T("duplicates", [[3, 3, 1]], [1, 3, 3], False, True), T("already sorted", [[1, 2, 3]], [1, 2, 3], False)],
             "bubble_sort([3, 1, 2]) → [1, 2, 3]"),
        "Each pass bubbles the largest remaining value to the end; stop early when a pass swaps nothing.", d="easy", t=360, hints=["The inner loop shrinks by one each pass.", "Track whether any swap happened."],
        constraints="Do not mutate the input.", complexity={"time": "O(n²) worst, O(n) best", "space": "O(n) for the copy"}))
    qs.append(mk_code("insertion-sort", "Write insertion_sort_shifts(arr) that runs insertion sort on a copy and returns how many element SHIFTS (a[j+1] = a[j]) it performed.",
        spec("insertion_sort_shifts", "def insertion_sort_shifts(arr):\n    # your code here\n    pass\n",
             _lines("def insertion_sort_shifts(arr):", "    a, shifts = list(arr), 0", "    for i in range(1, len(a)):", "        key, j = a[i], i - 1", "        while j >= 0 and a[j] > key:", "            a[j + 1] = a[j]", "            shifts += 1", "            j -= 1", "        a[j + 1] = key", "    return shifts"),
             [T("sample", [[5, 2, 4, 6, 1, 3]], 9), T("sorted", [[1, 2, 3]], 0, False, True), T("reversed", [[3, 2, 1]], 3, False), T("empty", [[]], 0, False, True), T("two elements", [[2, 1]], 1, False)],
             "insertion_sort_shifts([2, 1]) → 1"),
        "The shift count equals the number of inversions in the input.", d="medium", t=360, hints=["Count each time an element moves one slot right."], constraints="O(n²) time worst case.", complexity={"time": "O(n²)", "space": "O(n)"}))
    qs.append(mk_code("selection-sort", "Write selection_sort_swaps(arr) that runs selection sort on a copy and returns the number of swaps performed (swap only when the minimum is not already in place).",
        spec("selection_sort_swaps", "def selection_sort_swaps(arr):\n    # your code here\n    pass\n",
             _lines("def selection_sort_swaps(arr):", "    a, swaps = list(arr), 0", "    for i in range(len(a) - 1):", "        m = i", "        for j in range(i + 1, len(a)):", "            if a[j] < a[m]:", "                m = j", "        if m != i:", "            a[i], a[m] = a[m], a[i]", "            swaps += 1", "    return swaps"),
             [T("sample", [[64, 25, 12, 22, 11]], 3), T("sorted", [[1, 2, 3]], 0, False, True), T("reversed", [[3, 2, 1]], 1, False), T("empty", [[]], 0, False, True), T("two elements", [[2, 1]], 1, False)],
             "selection_sort_swaps([2, 1]) → 1"),
        "Find the minimum of the unsorted part each pass and swap it forward only if it is elsewhere.", d="medium", t=360, constraints="O(n²) comparisons.", complexity={"time": "O(n²)", "space": "O(n)"}))
    qs.append(mk_code("linear-search", "Write find_all(arr, x) that returns the list of ALL indices where x occurs, in increasing order (empty list if none).",
        spec("find_all", "def find_all(arr, x):\n    # your code here\n    pass\n",
             _lines("def find_all(arr, x):", "    return [i for i, v in enumerate(arr) if v == x]"),
             [T("repeated", [[1, 2, 1, 3, 1], 1], [0, 2, 4]), T("absent", [[1, 2], 5], [], False, True), T("empty", [[], 1], [], False, True), T("single", [[7], 7], [0], False, True)], "find_all([1, 2, 1], 1) → [0, 2]"),
        "Scan the whole list once, recording every match.", d="easy", t=240, complexity={"time": "O(n)", "space": "O(k) for k matches"}))
    qs.append(mk_code("ll-traversal", "A linked list is stored in parallel arrays: info[i] is the value of node i and link[i] is the index of the next node (-1 means NULL). Write traverse(info, link, start) returning the values in list order, starting at node index start (start = -1 means an empty list).",
        spec("traverse", "def traverse(info, link, start):\n    # your code here\n    pass\n",
             _lines("def traverse(info, link, start):", "    out, p = [], start", "    while p != -1:", "        out.append(info[p])", "        p = link[p]", "    return out"),
             [T("scattered nodes", [[10, 20, 30, 40], [2, -1, 1, 0], 3], [40, 10, 30, 20]), T("empty list", [[10], [-1], -1], [], False, True), T("single node", [[5], [-1], 0], [5], False, True), T("in order", [[1, 2, 3], [1, 2, -1], 0], [1, 2, 3], False)],
             "traverse([10, 20], [1, -1], 0) → [10, 20]"),
        "Follow link from start until NULL (-1), collecting info values.", d="easy", t=300, hints=["Start with p = start and stop when p == -1."], constraints="O(n) time.", complexity={"time": "O(n)", "space": "O(n)"}))
    qs.append(mk_code("ll-insert-delete", "Using the same info/link array representation (-1 = NULL), write delete_value(info, link, start, value) that unlinks the FIRST node holding value. Return [new_start, new_link] (new_link is a copy; leave the removed node's own link unchanged). If value is absent, return [start, copy of link].",
        spec("delete_value", "def delete_value(info, link, start, value):\n    # your code here\n    pass\n",
             _lines("def delete_value(info, link, start, value):", "    link = list(link)", "    prev, cur = -1, start", "    while cur != -1 and info[cur] != value:", "        prev, cur = cur, link[cur]", "    if cur == -1:", "        return [start, link]", "    if prev == -1:", "        return [link[cur], link]", "    link[prev] = link[cur]", "    return [start, link]"),
             [T("middle node", [[10, 20, 30], [1, 2, -1], 0, 20], [0, [2, 2, -1]]), T("head node", [[10, 20, 30], [1, 2, -1], 0, 10], [1, [1, 2, -1]], False, True), T("last node", [[10, 20, 30], [1, 2, -1], 0, 30], [0, [1, -1, -1]], False, True), T("value absent", [[10, 20, 30], [1, 2, -1], 0, 99], [0, [1, 2, -1]], False, True), T("only node", [[7], [-1], 0, 7], [-1, [-1]], False, True)],
             "delete_value([10, 20, 30], [1, 2, -1], 0, 20) → [0, [2, 2, -1]]"),
        "Walk with a trailing pointer; deleting the head changes start, otherwise re-link the predecessor.", d="medium", t=480, hints=["Track prev and cur while searching.", "Deleting the head returns link[cur] as the new start."], constraints="O(n) time.", complexity={"time": "O(n)", "space": "O(n) for the copied link array"}))
    qs.append(mk_code("stack-operations", "Write is_balanced(s) that returns True when every bracket in s — (), [] and {} — is closed in the correct order, using a stack. Other characters are ignored.",
        spec("is_balanced", "def is_balanced(s):\n    # your code here\n    pass\n",
             _lines("def is_balanced(s):", "    pairs = {')': '(', ']': '[', '}': '{'}", "    st = []", "    for ch in s:", "        if ch in '([{':", "            st.append(ch)", "        elif ch in pairs:", "            if not st or st.pop() != pairs[ch]:", "                return False", "    return not st"),
             [T("nested", ["([]{})"], True), T("mismatched", ["(]"], False, False), T("empty string", [""], True, False, True), T("unclosed", ["(("], False, False, True), T("closer first", [")"], False, False, True), T("deep nesting", ["{[()]}"], True, False)],
             "is_balanced('([])') → True"),
        "Push openers; for each closer, the popped opener must match; the stack must end empty.", d="medium", t=420, hints=["Check for an empty stack before popping."], constraints="O(n) time and space.", complexity={"time": "O(n)", "space": "O(n)"}))
    qs.append(mk_code("expression-evaluation", "Write eval_postfix(tokens) that evaluates a postfix expression given as a list of string tokens with integer operands and operators + - * / (use integer division //; operands are non-negative where / is used).",
        spec("eval_postfix", "def eval_postfix(tokens):\n    # your code here\n    pass\n",
             _lines("def eval_postfix(tokens):", "    st = []", "    for t in tokens:", "        if t in ('+', '-', '*', '/'):", "            b, a = st.pop(), st.pop()", "            st.append({'+': a + b, '-': a - b, '*': a * b, '/': a // b}[t])", "        else:", "            st.append(int(t))", "    return st[0]"),
             [T("add", [["2", "3", "+"]], 5), T("mixed", [["5", "6", "2", "+", "*", "12", "4", "/", "-"]], 37), T("single operand", [["7"]], 7, False, True), T("operand order", [["4", "2", "-"]], 2, False), T("inexact division", [["7", "2", "/"]], 3, False, True), T("negative result", [["3", "10", "-"]], -7, False)],
             "eval_postfix(['2', '3', '+']) → 5"),
        "Push operands; for an operator pop b then a, push a op b.", d="medium", t=480, hints=["The first value popped is the RIGHT operand."], constraints="O(n) time.", complexity={"time": "O(n)", "space": "O(n)"}))
    qs.append(mk_code("queue-operations", "Write circular_queue_outputs(capacity, ops) that simulates a circular queue (fixed capacity). ops is a list of ['enq', x] and ['deq']. Return the list of results: the dequeued value for each successful dequeue, 'underflow' for a dequeue on an empty queue and 'overflow' for an enqueue on a full queue (successful enqueues produce no output).",
        spec("circular_queue_outputs", "def circular_queue_outputs(capacity, ops):\n    # your code here\n    pass\n",
             _lines("def circular_queue_outputs(capacity, ops):", "    slots, front, size, out = [None] * capacity, 0, 0, []", "    for op in ops:", "        if op[0] == 'enq':", "            if size == capacity:", "                out.append('overflow')", "            else:", "                slots[(front + size) % capacity] = op[1]", "                size += 1", "        else:", "            if size == 0:", "                out.append('underflow')", "            else:", "                out.append(slots[front])", "                front = (front + 1) % capacity", "                size -= 1", "    return out"),
             [T("overflow then underflow", [2, [["enq", 1], ["enq", 2], ["enq", 3], ["deq"], ["deq"], ["deq"]]], ["overflow", 1, 2, "underflow"]), T("dequeue empty", [1, [["deq"]]], ["underflow"], False, True), T("no operations", [3, []], [], False, True), T("wrap-around", [2, [["enq", 5], ["deq"], ["enq", 6], ["enq", 7], ["deq"]]], [5, 6], False, True)],
             "circular_queue_outputs(1, [['deq']]) → ['underflow']"),
        "Keep front and size; the next free slot is (front + size) % capacity.", d="medium", t=540, hints=["Use the size counter to distinguish full from empty."], constraints="O(1) per operation.", complexity={"time": "O(1) per op", "space": "O(capacity)"}))
    qs.append(mk_code("priority-queues", "Jobs are given as [priority, name]; a LOWER number is served first and ties are served in arrival order. Write service_order(jobs) returning the names in service order (use a heap or any priority-queue idea).",
        spec("service_order", "def service_order(jobs):\n    # your code here\n    pass\n",
             _lines("import heapq", "", "def service_order(jobs):", "    heap = [(p, i, name) for i, (p, name) in enumerate(jobs)]", "    heapq.heapify(heap)", "    return [heapq.heappop(heap)[2] for _ in range(len(heap))]"),
             [T("sample", [[[3, "a"], [1, "b"], [2, "c"], [1, "d"]]], ["b", "d", "c", "a"]), T("no jobs", [[]], [], False, True), T("single job", [[[5, "x"]]], ["x"], False, True), T("all ties", [[[2, "p"], [2, "q"], [2, "r"]]], ["p", "q", "r"], False, True)],
             "service_order([[2, 'a'], [1, 'b']]) → ['b', 'a']"),
        "Break ties with the arrival index so equal priorities stay first-come-first-served.", d="medium", t=360, hints=["Store (priority, arrival_index, name) tuples."], complexity={"time": "O(n log n)", "space": "O(n)"}))
    qs.append(mk_code("bst-insert-delete", "Build a binary search tree by inserting keys in the given order (ignore duplicates). Write bst_height(keys) returning the height in EDGES (empty tree → -1, single node → 0).",
        spec("bst_height", "def bst_height(keys):\n    # your code here\n    pass\n",
             _lines("def bst_height(keys):", "    root = None", "    def insert(node, k):", "        if node is None:", "            return [k, None, None]", "        if k < node[0]:", "            node[1] = insert(node[1], k)", "        elif k > node[0]:", "            node[2] = insert(node[2], k)", "        return node", "    def height(node):", "        return -1 if node is None else 1 + max(height(node[1]), height(node[2]))", "    for k in keys:", "        root = insert(root, k)", "    return height(root)"),
             [T("balanced", [[50, 30, 70, 20, 40, 60, 80]], 2), T("empty", [[]], -1, False, True), T("single", [[5]], 0, False, True), T("sorted input", [[1, 2, 3, 4]], 3, False), T("duplicate ignored", [[3, 1, 2, 2]], 2, False, True)],
             "bst_height([2, 1, 3]) → 1"),
        "Insert recursively by comparing with the node key, then compute the height recursively.", d="medium", t=600, hints=["Represent a node as [key, left, right].", "height(None) = -1."], constraints="O(n·h) time.", complexity={"time": "O(n·h)", "space": "O(h)"}))
    qs.append(mk_code("tree-traversals", "Build a binary search tree by inserting keys in order (ignore duplicates) and return its POSTORDER traversal as a list. Write postorder_of(keys).",
        spec("postorder_of", "def postorder_of(keys):\n    # your code here\n    pass\n",
             _lines("def postorder_of(keys):", "    def insert(node, k):", "        if node is None:", "            return [k, None, None]", "        if k < node[0]:", "            node[1] = insert(node[1], k)", "        elif k > node[0]:", "            node[2] = insert(node[2], k)", "        return node", "    def post(node):", "        return [] if node is None else post(node[1]) + post(node[2]) + [node[0]]", "    root = None", "    for k in keys:", "        root = insert(root, k)", "    return post(root)"),
             [T("balanced", [[50, 30, 70, 20, 40, 60, 80]], [20, 40, 30, 60, 80, 70, 50]), T("empty", [[]], [], False, True), T("single", [[5]], [5], False, True), T("small", [[2, 1, 3]], [1, 3, 2], False), T("left chain", [[3, 2, 1]], [1, 2, 3], False, True)],
             "postorder_of([2, 1, 3]) → [1, 3, 2]"),
        "Postorder visits the left subtree, the right subtree, then the node.", d="medium", t=600, complexity={"time": "O(n·h)", "space": "O(h)"}))
    qs.append(mk_code("recursion-intro", "Write power(base, exp) for exp ≥ 0 using recursion with fast exponentiation (square the half power) — do not use ** or pow().",
        spec("power", "def power(base, exp):\n    # your code here\n    pass\n",
             _lines("def power(base, exp):", "    if exp == 0:", "        return 1", "    half = power(base, exp // 2)", "    return half * half if exp % 2 == 0 else half * half * base"),
             [T("2^10", [2, 10], 1024), T("exponent zero", [5, 0], 1, False, True), T("exponent one", [3, 1], 3, False, True), T("odd exponent", [3, 5], 243, False), T("base one, large exponent", [1, 100], 1, False, True), T("square", [7, 2], 49, False)],
             "power(2, 10) → 1024"),
        "Base case exp == 0; otherwise square the result for exp // 2 and multiply by base once more when exp is odd.", d="medium", t=420, constraints="O(log exp) recursive calls.", complexity={"time": "O(log exp)", "space": "O(log exp) call stack"}))
    qs.append(mk_code("tower-of-hanoi", "Write hanoi_moves(n) returning the list of moves as [from_peg, to_peg] pairs that move n disks from peg 'A' to peg 'C' using 'B' (n = 0 → empty list).",
        spec("hanoi_moves", "def hanoi_moves(n):\n    # your code here\n    pass\n",
             _lines("def hanoi_moves(n):", "    def go(k, a, c, b):", "        if k == 0:", "            return []", "        return go(k - 1, a, b, c) + [[a, c]] + go(k - 1, b, c, a)", "    return go(n, 'A', 'C', 'B')"),
             [T("one disk", [1], [["A", "C"]]), T("two disks", [2], [["A", "B"], ["A", "C"], ["B", "C"]], False), T("zero disks", [0], [], False, True), T("three disks", [3], [["A", "C"], ["A", "B"], ["C", "B"], ["A", "C"], ["B", "A"], ["B", "C"], ["A", "C"]], False)],
             "hanoi_moves(1) → [['A', 'C']]"),
        "Move n−1 disks to the spare peg, move the largest disk, then move the n−1 disks on top of it.", d="medium", t=480, constraints="2ⁿ − 1 moves.", complexity={"time": "O(2ⁿ)", "space": "O(n)"}))
    qs.append(mk_code("heap-operations", "Write kth_largest(nums, k) returning the k-th largest value (counting duplicates; 1 ≤ k ≤ len(nums)). A min-heap of size k is a good approach.",
        spec("kth_largest", "def kth_largest(nums, k):\n    # your code here\n    pass\n",
             _lines("import heapq", "", "def kth_largest(nums, k):", "    heap = []", "    for x in nums:", "        heapq.heappush(heap, x)", "        if len(heap) > k:", "            heapq.heappop(heap)", "    return heap[0]"),
             [T("sample", [[3, 2, 1, 5, 6, 4], 2], 5), T("single element", [[1], 1], 1, False, True), T("duplicates count", [[2, 2, 3], 2], 2, False, True), T("k equals length", [[7, 6, 5], 3], 5, False, True)],
             "kth_largest([3, 1, 2], 1) → 3"),
        "Keep only the k largest values in a min-heap; its root is the k-th largest.", d="medium", t=480, complexity={"time": "O(n log k)", "space": "O(k)"}))
    qs.append(mk_code("heapsort", "Write heap_sort(arr) returning a new ascending list. Build a max-heap in place on a copy and repeatedly move the maximum to the end (do not use sorted()/sort()).",
        spec("heap_sort", "def heap_sort(arr):\n    # your code here\n    pass\n",
             _lines("def heap_sort(arr):", "    a = list(arr)", "    n = len(a)", "    def sift(i, size):", "        while True:", "            l, r, m = 2 * i + 1, 2 * i + 2, i", "            if l < size and a[l] > a[m]:", "                m = l", "            if r < size and a[r] > a[m]:", "                m = r", "            if m == i:", "                return", "            a[i], a[m] = a[m], a[i]", "            i = m", "    for i in range(n // 2 - 1, -1, -1):", "        sift(i, n)", "    for end in range(n - 1, 0, -1):", "        a[0], a[end] = a[end], a[0]", "        sift(0, end)", "    return a"),
             [T("sample", [[4, 10, 3, 5, 1]], [1, 3, 4, 5, 10]), T("empty", [[]], [], False, True), T("duplicates", [[2, 2, 1]], [1, 2, 2], False, True), T("single", [[1]], [1], False, True)],
             "heap_sort([3, 1, 2]) → [1, 2, 3]"),
        "Heapify bottom-up, then swap the root with the last unsorted element and sift down.", d="hard", t=720, complexity={"time": "O(n log n)", "space": "O(n) for the copy, O(1) extra"}))
    qs.append(mk_code("hash-functions", "Write two_sum(nums, target) returning [i, j] with i < j and nums[i] + nums[j] == target, using a hash table for O(n) time. If no pair exists return [].",
        spec("two_sum", "def two_sum(nums, target):\n    # your code here\n    pass\n",
             _lines("def two_sum(nums, target):", "    seen = {}", "    for j, x in enumerate(nums):", "        if target - x in seen:", "            return [seen[target - x], j]", "        seen[x] = j", "    return []"),
             [T("sample", [[2, 7, 11, 15], 9], [0, 1]), T("later pair", [[3, 2, 4], 6], [1, 2], False), T("duplicate values", [[3, 3], 6], [0, 1], False, True), T("no pair", [[1, 2], 7], [], False, True), T("empty", [[], 1], [], False, True)],
             "two_sum([2, 7], 9) → [0, 1]"),
        "Store each value's index; before storing x, check whether target − x was already seen.", d="medium", t=420, constraints="O(n) time, O(n) space.", complexity={"time": "O(n)", "space": "O(n)"}))
    qs.append(mk_code("linear-probing", "Write hash_insert_linear(keys, m) that inserts integer keys in order into a table of size m with h(k) = k mod m and linear probing, returning the table as a list (None for empty). Assume len(keys) ≤ m.",
        spec("hash_insert_linear", "def hash_insert_linear(keys, m):\n    # your code here\n    pass\n",
             _lines("def hash_insert_linear(keys, m):", "    table = [None] * m", "    for k in keys:", "        i = k % m", "        while table[i] is not None:", "            i = (i + 1) % m", "        table[i] = k", "    return table"),
             [T("with collision", [[50, 700, 76, 85], 7], [700, 50, 85, None, None, None, 76]), T("no keys", [[], 3], [None, None, None], False, True), T("wrap-around", [[1, 4, 7], 3], [7, 1, 4], False, True), T("table filled", [[0, 3, 6], 3], [0, 3, 6], False, True)],
             "hash_insert_linear([5, 10], 5) → [5, 10, None, None, None]"),
        "On a collision move to (i + 1) % m until a free slot appears.", d="medium", t=420, complexity={"time": "O(n) average with a low load factor", "space": "O(m)"}))
    qs.append(mk_code("bfs", "A graph with vertices 0..n−1 is given as an undirected edge list. Write bfs_order(n, edges, start) returning the BFS visit order, taking neighbours in ASCENDING vertex order. Only vertices reachable from start are visited.",
        spec("bfs_order", "def bfs_order(n, edges, start):\n    # your code here\n    pass\n",
             _lines("from collections import deque", "", "def bfs_order(n, edges, start):", "    adj = [[] for _ in range(n)]", "    for u, v in edges:", "        adj[u].append(v)", "        adj[v].append(u)", "    seen, order, q = {start}, [], deque([start])", "    while q:", "        u = q.popleft()", "        order.append(u)", "        for v in sorted(adj[u]):", "            if v not in seen:", "                seen.add(v)", "                q.append(v)", "    return order"),
             [T("diamond", [4, [[0, 1], [0, 2], [1, 3], [2, 3]], 0], [0, 1, 2, 3]), T("single vertex", [1, [], 0], [0], False, True), T("disconnected", [4, [[0, 1], [2, 3]], 0], [0, 1], False, True), T("ascending neighbours", [5, [[0, 2], [0, 1], [1, 3], [2, 4]], 0], [0, 1, 2, 3, 4], False)],
             "bfs_order(2, [[0, 1]], 0) → [0, 1]"),
        "Use a queue and a visited set; mark vertices when they are enqueued.", d="medium", t=600, constraints="O(V + E) time.", complexity={"time": "O(V + E)", "space": "O(V + E)"}))
    qs.append(mk_code("dijkstra", f"An undirected weighted graph on vertices 0..n−1 is given as [u, v, w] edges (w ≥ 0). Write dijkstra_dist(n, edges, src) returning the shortest distance to every vertex. {INF_NOTE}",
        spec("dijkstra_dist", "def dijkstra_dist(n, edges, src):\n    # your code here\n    pass\n",
             _lines("import heapq", "", "def dijkstra_dist(n, edges, src):", "    adj = [[] for _ in range(n)]", "    for u, v, w in edges:", "        adj[u].append((v, w))", "        adj[v].append((u, w))", "    dist = [float('inf')] * n", "    dist[src] = 0", "    pq = [(0, src)]", "    while pq:", "        d, u = heapq.heappop(pq)", "        if d > dist[u]:", "            continue", "        for v, w in adj[u]:", "            if d + w < dist[v]:", "                dist[v] = d + w", "                heapq.heappush(pq, (dist[v], v))", "    return [-1 if x == float('inf') else x for x in dist]"),
             [T("sample", [5, [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 1], [2, 3, 5], [3, 4, 3]], 0], [0, 3, 1, 4, 7]), T("single vertex", [1, [], 0], [0], False, True), T("unreachable vertex", [3, [[0, 1, 2]], 0], [0, 2, -1], False, True), T("indirect route is shorter", [3, [[0, 1, 5], [1, 2, 1], [0, 2, 10]], 0], [0, 5, 6], False)],
             "dijkstra_dist(2, [[0, 1, 3]], 0) → [0, 3]"),
        "Use a min-heap of (distance, vertex); skip stale entries and relax each edge.", d="hard", t=780, constraints="O((V + E) log V).", complexity={"time": "O((V + E) log V)", "space": "O(V + E)"}))
    qs.append(mk_code("bellman-ford", "Write has_negative_cycle(n, edges) for a DIRECTED graph with [u, v, w] edges. Return True if ANY negative-weight cycle exists (anywhere in the graph), else False. Hint: start every vertex at distance 0.",
        spec("has_negative_cycle", "def has_negative_cycle(n, edges):\n    # your code here\n    pass\n",
             _lines("def has_negative_cycle(n, edges):", "    dist = [0] * n", "    for round_no in range(n):", "        changed = False", "        for u, v, w in edges:", "            if dist[u] + w < dist[v]:", "                dist[v] = dist[u] + w", "                changed = True", "        if not changed:", "            return False", "    return True"),
             [T("cycle present", [4, [[0, 1, 1], [1, 2, -1], [2, 3, -1], [3, 1, -1]]], True), T("no cycle", [3, [[0, 1, 1], [1, 2, 1]]], False, False), T("no edges", [1, []], False, False, True), T("two-vertex negative cycle", [2, [[0, 1, -1], [1, 0, -1]]], True, False, True), T("negative edge without a cycle", [2, [[0, 1, -5]]], False, False, True)],
             "has_negative_cycle(1, []) → False"),
        "If distances still change in the n-th relaxation round, a negative cycle exists.", d="hard", t=720, constraints="O(V · E).", complexity={"time": "O(V · E)", "space": "O(V)"}))
    qs.append(mk_code("floyd-warshall", "Write floyd_warshall(n, edges) for a DIRECTED graph with [u, v, w] edges (no negative cycles). Return the n×n matrix of shortest distances; use 0 on the diagonal and -1 for unreachable pairs.",
        spec("floyd_warshall", "def floyd_warshall(n, edges):\n    # your code here\n    pass\n",
             _lines("def floyd_warshall(n, edges):", "    INF = float('inf')", "    d = [[INF] * n for _ in range(n)]", "    for i in range(n):", "        d[i][i] = 0", "    for u, v, w in edges:", "        d[u][v] = min(d[u][v], w)", "    for k in range(n):", "        for i in range(n):", "            for j in range(n):", "                if d[i][k] + d[k][j] < d[i][j]:", "                    d[i][j] = d[i][k] + d[k][j]", "    return [[-1 if x == INF else x for x in row] for row in d]"),
             [T("sample", [4, [[0, 1, 5], [0, 3, 10], [1, 2, 3], [2, 3, 1]]], [[0, 5, 8, 9], [-1, 0, 3, 4], [-1, -1, 0, 1], [-1, -1, -1, 0]]), T("single vertex", [1, []], [[0]], False, True), T("one edge", [2, [[0, 1, 4]]], [[0, 4], [-1, 0]], False, True)],
             "floyd_warshall(1, []) → [[0]]"),
        "The outer loop over k allows vertex k as an intermediate; relax every (i, j).", d="hard", t=720, constraints="O(V³).", complexity={"time": "O(V³)", "space": "O(V²)"}))
    return _complete_guidance(qs)


# ---- fill-the-line / fix-the-bug (MCQ, verified by substituting every option and running tests) ----------------------


_G_A = [[[1, 4], [2, 1]], [[3, 1]], [[1, 2], [3, 5]], []]
_G_B = [[[1, 10], [2, 1]], [], [[1, 1]]]
_G_C = [[[1, 3], [2, 2]], [], [[1, 2]]]  # w < dist[v] but d + w > dist[v]: catches the 'w < dist[v]' mistake
_DIJKSTRA_TESTS = [[[_G_A, 0], [0, 3, 1, 4]], [[_G_B, 0], [0, 2, 1]], [[_G_C, 0], [0, 3, 2]]]


def _line_q(sub, ctype, stem, code, answer, wrong, expl, function, tests, *, d, hint, t=120):
    return mk(sub, "coding", stem, answer, wrong, expl, d=d, t=t, code=code, coding_type=ctype, hints=[hint],
              ver={"method": "manual_review", "note": "Every option is substituted into the marked line and run against the tests; only the key passes (test-suite check).", "line_check": {"function": function, "tests": tests}})


def line_questions():
    qs = []
    qs.append(_line_q("binary-search", "fill_line", "Complete the marked line of this binary search so it terminates and finds every element.",
        _lines("def bsearch(a, x):", "    lo, hi = 0, len(a) - 1", "    while lo <= hi:", "        mid = (lo + hi) // 2", "        if a[mid] == x:", "            return mid", "        elif a[mid] < x:", "            ___  # <<<", "        else:", "            hi = mid - 1", "    return -1"),
        "lo = mid + 1", ["lo = mid", "lo = mid - 1", "hi = mid + 1"], "When a[mid] < x the target lies to the right, and mid itself is ruled out, so lo must move to mid + 1.", "bsearch",
        [[[[1, 3, 5, 7], 5], 2], [[[1, 3, 5, 7], 7], 3], [[[1, 3, 5, 7], 4], -1], [[[2], 3], -1], [[[], 1], -1]], d="easy", hint="The element at mid has already been rejected."))
    qs.append(_line_q("insertion-sort", "fill_line", "Complete the marked line inside the inner loop of insertion sort.",
        _lines("def insertion_sort(a):", "    a = list(a)", "    for i in range(1, len(a)):", "        key = a[i]", "        j = i - 1", "        while j >= 0 and a[j] > key:", "            ___  # <<<", "            j -= 1", "        a[j + 1] = key", "    return a"),
        "a[j + 1] = a[j]", ["a[j] = a[j + 1]", "a[j + 1] = key", "a[j - 1] = a[j]"], "Larger elements shift one place right to open a gap for the key.", "insertion_sort",
        [[[[5, 2, 4, 6, 1, 3]], [1, 2, 3, 4, 5, 6]], [[[3, 2, 1]], [1, 2, 3]], [[[1]], [1]], [[[]], []], [[[2, 2, 1]], [1, 2, 2]]], d="medium", hint="Move a[j] one slot to the right."))
    qs.append(_line_q("stack-operations", "fix_bug", "The marked line should detect a mismatched closing bracket but contains a bug in some versions. Pick the line that makes is_balanced correct.",
        _lines("def is_balanced(s):", "    pairs = {')': '(', ']': '[', '}': '{'}", "    st = []", "    for ch in s:", "        if ch in '([{':", "            st.append(ch)", "        elif ch in pairs:", "            if not st or st.pop() == pairs[ch]:  # <<<", "                return False", "    return not st"),
        "if not st or st.pop() != pairs[ch]:", ["if not st or st.pop() == pairs[ch]:", "if not st or st[-1] != ch:", "if st.pop() != ch:"], "A closer must match the opener on top of the stack; also guard against an empty stack before popping.", "is_balanced",
        [[["([]{})"], True], [["(]"], False], [[""], True], [["(("], False], [[")"], False], [["{[()]}"], True]], d="medium", hint="pop() returns the most recent opener; compare it with what this closer needs."))
    qs.append(_line_q("queue-operations", "fill_line", "Complete the function that returns the array index where the next enqueued element of a circular queue is stored.",
        _lines("def enqueue_index(front, size, capacity):", "    return ___  # <<<"),
        "return (front + size) % capacity", ["return front + size", "return (front + size - 1) % capacity", "return (front + 1) % capacity"], "The queue occupies slots front..front+size−1; the next free slot follows it, wrapping with modulo.", "enqueue_index",
        [[[0, 0, 4], 0], [[2, 3, 4], 1], [[3, 1, 4], 0], [[1, 2, 5], 3]], d="easy", hint="Add size to front, then wrap."))
    qs.append(_line_q("tree-traversals", "fill_line", "A tree is a tuple (key, left, right) or None. Complete the INORDER traversal.",
        _lines("def inorder(t):", "    if t is None:", "        return []", "    return ___  # <<<"),
        "return inorder(t[1]) + [t[0]] + inorder(t[2])", ["return [t[0]] + inorder(t[1]) + inorder(t[2])", "return inorder(t[1]) + inorder(t[2]) + [t[0]]", "return inorder(t[2]) + [t[0]] + inorder(t[1])"], "Inorder is left subtree, node, right subtree.", "inorder",
        [[[[2, [1, None, None], [3, None, None]]], [1, 2, 3]], [[None], []], [[[5, None, None]], [5]], [[[4, [2, [1, None, None], [3, None, None]], [6, None, None]]], [1, 2, 3, 4, 6]]], d="easy", hint="The node's key goes between the two recursive results."))
    qs.append(_line_q("recursion-intro", "fix_bug", "fact(n) crashes with RecursionError for n = 0. Which replacement for the marked line fixes it?",
        _lines("def fact(n):", "    if n == 1:  # <<<", "        return 1", "    return n * fact(n - 1)"),
        "if n <= 1:", ["if n == 1:", "if n == 2:", "if n < 0:"], "With `n == 1` the call fact(0) skips the base case and recurses forever; `n <= 1` covers 0 and 1.", "fact",
        [[[0], 1], [[1], 1], [[5], 120], [[3], 6]], d="easy", hint="Which inputs never reach the base case?"))
    qs.append(_line_q("tower-of-hanoi", "fill_line", "Complete the recursive return so the tower of n disks moves from src to dst via spare.",
        _lines("def hanoi(n, src, dst, spare):", "    if n == 0:", "        return []", "    return hanoi(n - 1, src, spare, dst) + [(src, dst)] + ___  # <<<"),
        "return hanoi(n - 1, src, spare, dst) + [(src, dst)] + hanoi(n - 1, spare, dst, src)", ["return hanoi(n - 1, src, spare, dst) + [(src, dst)] + hanoi(n - 1, src, dst, spare)", "return hanoi(n - 1, src, spare, dst) + [(src, dst)] + hanoi(n - 1, dst, src, spare)", "return hanoi(n - 1, src, spare, dst) + [(src, dst)] + hanoi(n - 1, spare, src, dst)"],
        "After the largest disk reaches dst, the n−1 disks parked on spare must move onto dst, with src as the new spare.", "hanoi",
        [[[1, "A", "C", "B"], [["A", "C"]]], [[2, "A", "C", "B"], [["A", "B"], ["A", "C"], ["B", "C"]]], [[0, "A", "C", "B"], []]], d="hard", hint="The second recursive call starts from where the first one ended."))
    qs.append(_line_q("recursive-quick-sort", "fill_line", "Complete the Lomuto partition (pivot = last element) condition. The function returns [array, pivot_index].",
        _lines("def partition(a, lo, hi):", "    pivot, i = a[hi], lo - 1", "    for j in range(lo, hi):", "        ___  # <<<", "            i += 1", "            a[i], a[j] = a[j], a[i]", "    a[i + 1], a[hi] = a[hi], a[i + 1]", "    return [a, i + 1]"),
        "if a[j] <= pivot:", ["if a[j] >= pivot:", "if a[j] < a[i]:", "if a[j] == pivot:"], "Elements not larger than the pivot are gathered at the front.", "partition",
        [[[[3, 1, 2], 0, 2], [[1, 2, 3], 1]], [[[8, 3, 7, 1, 6, 5], 0, 5], [[3, 1, 5, 8, 6, 7], 2]], [[[1], 0, 0], [[1], 0]], [[[3, 5, 1, 8, 6], 0, 4], [[3, 5, 1, 6, 8], 3]]], d="medium", hint="Which side of the pivot should smaller values go to?"))
    qs.append(_line_q("heap-operations", "fix_bug", "Insertion into a zero-based max-heap uses the wrong parent index. Pick the correct swap for the sift-up loop.",
        _lines("def push(heap, x):", "    heap = heap + [x]", "    i = len(heap) - 1", "    while i > 0 and heap[(i - 1) // 2] < heap[i]:", "        heap[i // 2], heap[i] = heap[i], heap[i // 2]  # <<<", "        i = (i - 1) // 2", "    return heap"),
        "heap[(i - 1) // 2], heap[i] = heap[i], heap[(i - 1) // 2]", ["heap[i // 2], heap[i] = heap[i], heap[i // 2]", "heap[i], heap[i + 1] = heap[i + 1], heap[i]", "heap[(i - 1) // 2] = heap[i]"], "The parent of index i in a zero-based heap is (i − 1) // 2, and the swap must exchange both values.", "push",
        [[[[40, 30, 15, 10, 20], 45], [45, 30, 40, 10, 20, 15]], [[[], 5], [5]], [[[9, 5], 1], [9, 5, 1]]], d="hard", hint="Use the same parent formula in the condition and the swap."))
    qs.append(_line_q("linear-probing", "fill_line", "Complete the probe step of linear probing (the table wraps around).",
        _lines("def insert(table, key):", "    m = len(table)", "    i = key % m", "    while table[i] is not None:", "        ___  # <<<", "    table[i] = key", "    return table"),
        "i = (i + 1) % m", ["i = i + 1", "i = (i + 2) % m", "i = (i - 1) % m"], "Linear probing moves to the next slot, wrapping to 0 after the last one.", "insert",
        [[[[None] * 5, 3], [None, None, None, 3, None]], [[[None, None, None, 3, None], 8], [None, None, None, 3, 8]], [[[None, None, None, None, 9], 14], [14, None, None, None, 9]]], d="medium", hint="The step is 1 and the index must wrap."))
    qs.append(_line_q("bfs", "fill_line", "Complete the BFS loop. graph is a list of neighbour lists; the function returns the visit order.",
        _lines("from collections import deque", "", "def bfs(graph, start):", "    seen, order, q = {start}, [], deque([start])", "    while q:", "        ___  # <<<", "        order.append(u)", "        for v in graph[u]:", "            if v not in seen:", "                seen.add(v)", "                q.append(v)", "    return order"),
        "u = q.popleft()", ["u = q.pop()", "u = q[0]", "u = q[-1]"], "BFS takes vertices from the FRONT of the queue and removes them.", "bfs",
        [[[[[1, 2], [3], [3], []], 0], [0, 1, 2, 3]], [[[[1, 2], [], []], 0], [0, 1, 2]], [[[[]], 0], [0]]], d="medium", hint="A queue is first in, first out — and the element must also be removed."))
    qs.append(_line_q("dijkstra", "fill_line", "Complete the relaxation test. graph[u] is a list of [v, weight] pairs and the function returns the distance list.",
        _lines("import heapq", "", "def dijkstra(graph, src):", "    dist = [float('inf')] * len(graph)", "    dist[src] = 0", "    pq = [(0, src)]", "    while pq:", "        d, u = heapq.heappop(pq)", "        if d > dist[u]:", "            continue", "        for v, w in graph[u]:", "            if ___:  # <<<", "                dist[v] = d + w", "                heapq.heappush(pq, (dist[v], v))", "    return dist"),
        "if d + w < dist[v]:", ["if w < dist[v]:", "if d + w > dist[v]:", "if dist[v] == float('inf'):"], "Relax an edge only when going through u gives a strictly shorter path to v.", "dijkstra",
        _DIJKSTRA_TESTS, d="hard", hint="Compare the new total distance with the best known."))
    qs.append(_line_q("selection-sort", "fix_bug", "This selection sort sometimes returns an unsorted list. Choose the correct comparison for the marked line.",
        _lines("def selection_sort(a):", "    a = list(a)", "    for i in range(len(a)):", "        m = i", "        for j in range(i + 1, len(a)):", "            if a[j] < a[i]:  # <<<", "                m = j", "        a[i], a[m] = a[m], a[i]", "    return a"),
        "if a[j] < a[m]:", ["if a[j] < a[i]:", "if a[j] > a[m]:", "if a[j] <= a[j - 1]:"], "Each candidate must be compared with the current minimum a[m], not with a[i].", "selection_sort",
        [[[[3, 1, 2]], [1, 2, 3]], [[[64, 25, 12, 22, 11]], [11, 12, 22, 25, 64]], [[[1]], [1]], [[[]], []], [[[2, 1]], [1, 2]], [[[8, 7, 4, 6, 5]], [4, 5, 6, 7, 8]]], d="medium", hint="Which variable remembers the smallest value found so far?"))
    qs.append(_line_q("bubble-sort", "fix_bug", "bubble_passes should stop after the first pass with no swaps, but the marked line is wrong. Which line fixes it?",
        _lines("def bubble_passes(a):", "    a, passes = list(a), 0", "    for end in range(len(a) - 1, 0, -1):", "        swapped = False", "        for i in range(end):", "            if a[i] > a[i + 1]:", "                a[i], a[i + 1] = a[i + 1], a[i]", "                swapped = True", "        passes += 1", "        if swapped: break  # <<<", "    return passes"),
        "if not swapped: break", ["if swapped: break", "if not swapped: continue", "break"], "The sort is finished only when a whole pass makes no swap.", "bubble_passes",
        [[[[2, 1, 3, 4, 5]], 2], [[[1, 2, 3]], 1], [[[5, 4, 3, 2, 1]], 4], [[[]], 0], [[[1]], 0]], d="medium", hint="Stop when nothing was swapped."))
    qs.append(_line_q("expression-evaluation", "fix_bug", "eval_postfix gives wrong answers for - and / . Choose the correct line.",
        _lines("def eval_postfix(tokens):", "    st = []", "    for t in tokens:", "        if t in ('+', '-', '*', '/'):", "            b = st.pop()", "            a = st.pop()", "            st.append({'+': a + b, '-': b - a, '*': a * b, '/': b // a}[t])  # <<<", "        else:", "            st.append(int(t))", "    return st[0]"),
        "st.append({'+': a + b, '-': a - b, '*': a * b, '/': a // b}[t])", ["st.append({'+': a + b, '-': b - a, '*': a * b, '/': b // a}[t])", "st.append({'+': a + b, '-': a - b, '*': a * b, '/': a / b}[t])", "st.append(a + b)"], "The first popped value is the RIGHT operand b, so subtraction and division are a − b and a // b.", "eval_postfix",
        [[[["2", "3", "+"]], 5], [[["4", "2", "-"]], 2], [[["7", "2", "/"]], 3], [[["5", "6", "2", "+", "*", "12", "4", "/", "-"]], 37]], d="medium", hint="Which popped value was on top?"))
    return qs


def all_questions():
    return write_functions() + line_questions()
