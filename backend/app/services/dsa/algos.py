"""
Reference implementations of the syllabus algorithms (Phase 24).

Pure, deterministic, side-effect free. They produce the intermediate states that trace questions show
and the answers that validation re-derives. Conventions are fixed and stated in each question:
  * sorts are ascending; bubble sort stops early when a pass makes no swap;
  * quick sort uses the Lomuto partition with the LAST element as pivot;
  * heaps are max-heaps stored 0-indexed (children of i: 2i+1, 2i+2);
  * graph algorithms visit neighbours in ascending vertex order.
Their own correctness is pinned by hand-computed cases in tests/test_dsa_algorithms.py.
"""

from __future__ import annotations

import heapq
from collections import deque

INF = float("inf")


# --- Sorting ---------------------------------------------------------------------------------


def bubble_sort(arr):
    """Returns (states after each pass, comparisons, swaps). The first pass that swaps nothing ends the sort."""
    a, states, comps, swaps = list(arr), [], 0, 0
    for end in range(len(a) - 1, 0, -1):
        swapped = False
        for i in range(end):
            comps += 1
            if a[i] > a[i + 1]:
                a[i], a[i + 1] = a[i + 1], a[i]
                swaps += 1
                swapped = True
        states.append(list(a))
        if not swapped:
            break
    return states, comps, swaps


def insertion_sort(arr):
    """Returns (state after inserting each element from index 1, comparisons, shifts)."""
    a, states, comps, shifts = list(arr), [], 0, 0
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        while j >= 0:
            comps += 1
            if a[j] > key:
                a[j + 1] = a[j]
                shifts += 1
                j -= 1
            else:
                break
        a[j + 1] = key
        states.append(list(a))
    return states, comps, shifts


def selection_sort(arr):
    """Returns (state after each pass, comparisons, swaps). A swap happens only when the minimum is elsewhere."""
    a, states, comps, swaps = list(arr), [], 0, 0
    for i in range(len(a) - 1):
        m = i
        for j in range(i + 1, len(a)):
            comps += 1
            if a[j] < a[m]:
                m = j
        if m != i:
            a[i], a[m] = a[m], a[i]
            swaps += 1
        states.append(list(a))
    return states, comps, swaps


def linear_search(arr, target):
    """Returns (index or -1, comparisons)."""
    for i, v in enumerate(arr):
        if v == target:
            return i, i + 1
    return -1, len(arr)


def binary_search(arr, target):
    """Returns (index or -1, list of probed indices). arr must be sorted ascending; floor midpoint."""
    lo, hi, probes = 0, len(arr) - 1, []
    while lo <= hi:
        mid = (lo + hi) // 2
        probes.append(mid)
        if arr[mid] == target:
            return mid, probes
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1, probes


def merge(left, right):
    out, i, j, comps = [], 0, 0, 0
    while i < len(left) and j < len(right):
        comps += 1
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out, comps


def merge_sort(arr):
    """Returns (sorted list, ordered list of merge steps [(left, right, merged)], total comparisons)."""
    steps, total = [], [0]

    def rec(a):
        if len(a) <= 1:
            return list(a)
        mid = len(a) // 2
        left, right = rec(a[:mid]), rec(a[mid:])
        merged, c = merge(left, right)
        total[0] += c
        steps.append((left, right, merged))
        return merged

    return rec(list(arr)), steps, total[0]


def lomuto_partition(a, lo, hi):
    pivot, i = a[hi], lo - 1
    for j in range(lo, hi):
        if a[j] <= pivot:
            i += 1
            a[i], a[j] = a[j], a[i]
    a[i + 1], a[hi] = a[hi], a[i + 1]
    return i + 1


def quick_sort_first_partition(arr):
    """Array after ONE Lomuto partition of the whole array (pivot = last), plus the pivot's final index."""
    a = list(arr)
    p = lomuto_partition(a, 0, len(a) - 1)
    return a, p


def quick_sort(arr):
    """Returns (sorted list, number of partition calls)."""
    a, calls = list(arr), [0]

    def rec(lo, hi):
        if lo < hi:
            calls[0] += 1
            p = lomuto_partition(a, lo, hi)
            rec(lo, p - 1)
            rec(p + 1, hi)

    rec(0, len(a) - 1)
    return a, calls[0]


# --- Stacks / expressions ---------------------------------------------------------------------

_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
_RIGHT = {"^"}


def tokenize(expr):
    return [t for t in expr.replace("(", " ( ").replace(")", " ) ").split() if t]


def infix_to_postfix(expr):
    out, stack = [], []
    for t in tokenize(expr):
        if t == "(":
            stack.append(t)
        elif t == ")":
            while stack and stack[-1] != "(":
                out.append(stack.pop())
            stack.pop()
        elif t in _PREC:
            while stack and stack[-1] != "(" and (_PREC[stack[-1]] > _PREC[t] or (_PREC[stack[-1]] == _PREC[t] and t not in _RIGHT)):
                out.append(stack.pop())
            stack.append(t)
        else:
            out.append(t)
    while stack:
        out.append(stack.pop())
    return " ".join(out)


def infix_to_prefix(expr):
    """Reverse, swap brackets, convert with the 'pop while strictly higher' rule, reverse again."""
    toks = tokenize(expr)[::-1]
    toks = [")" if t == "(" else "(" if t == ")" else t for t in toks]
    out, stack = [], []
    for t in toks:
        if t == "(":
            stack.append(t)
        elif t == ")":
            while stack and stack[-1] != "(":
                out.append(stack.pop())
            stack.pop()
        elif t in _PREC:
            while stack and stack[-1] != "(" and (_PREC[stack[-1]] > _PREC[t] or (_PREC[stack[-1]] == _PREC[t] and t in _RIGHT)):
                out.append(stack.pop())
            stack.append(t)
        else:
            out.append(t)
    while stack:
        out.append(stack.pop())
    return " ".join(out[::-1])


def _apply(op, a, b):
    return {"+": a + b, "-": a - b, "*": a * b, "/": a // b if b else 0, "^": a ** b}[op]


def eval_postfix(expr):
    """Returns (value, list of stack snapshots after each token)."""
    st, snaps = [], []
    for t in expr.split():
        if t in _PREC:
            b, a = st.pop(), st.pop()
            st.append(_apply(t, a, b))
        else:
            st.append(int(t))
        snaps.append(list(st))
    return st[0], snaps


def eval_prefix(expr):
    st = []
    for t in reversed(expr.split()):
        if t in _PREC:
            a, b = st.pop(), st.pop()
            st.append(_apply(t, a, b))
        else:
            st.append(int(t))
    return st[0]


def balanced(s):
    pairs, st = {")": "(", "]": "[", "}": "{"}, []
    for c in s:
        if c in "([{":
            st.append(c)
        elif c in pairs:
            if not st or st.pop() != pairs[c]:
                return False
    return not st


# --- Queues -----------------------------------------------------------------------------------


def circular_queue(capacity, ops):
    """ops: ('enq', x) | ('deq',). Returns (final front->rear list, outputs, array slots)."""
    slots, front, size, outputs = [None] * capacity, 0, 0, []
    for op in ops:
        if op[0] == "enq":
            if size == capacity:
                outputs.append("overflow")
            else:
                slots[(front + size) % capacity] = op[1]
                size += 1
        else:
            if size == 0:
                outputs.append("underflow")
            else:
                outputs.append(slots[front])
                slots[front] = None
                front = (front + 1) % capacity
                size -= 1
    return [slots[(front + i) % capacity] for i in range(size)], outputs, slots


def priority_queue_order(items):
    """items: [(priority, label)] -> labels in service order (lowest number first, FIFO on ties)."""
    h = [(p, i, lab) for i, (p, lab) in enumerate(items)]
    heapq.heapify(h)
    return [heapq.heappop(h)[2] for _ in range(len(h))]


def deque_ops(ops):
    """ops: ('pf',x) push-front, ('pb',x) push-back, ('ef',) pop-front, ('eb',) pop-back. Returns (list, popped)."""
    d, popped = deque(), []
    for op in ops:
        if op[0] == "pf":
            d.appendleft(op[1])
        elif op[0] == "pb":
            d.append(op[1])
        elif op[0] == "ef":
            popped.append(d.popleft() if d else "empty")
        else:
            popped.append(d.pop() if d else "empty")
    return list(d), popped


# --- Trees ------------------------------------------------------------------------------------


class Node:
    __slots__ = ("key", "left", "right")

    def __init__(self, key):
        self.key, self.left, self.right = key, None, None


def bst_insert(root, key):
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = bst_insert(root.left, key)
    elif key > root.key:
        root.right = bst_insert(root.right, key)
    return root


def build_bst(keys):
    root = None
    for k in keys:
        root = bst_insert(root, k)
    return root


def bst_delete(root, key):
    """Deletion replaces a two-child node with its inorder SUCCESSOR."""
    if root is None:
        return None
    if key < root.key:
        root.left = bst_delete(root.left, key)
    elif key > root.key:
        root.right = bst_delete(root.right, key)
    else:
        if root.left is None:
            return root.right
        if root.right is None:
            return root.left
        s = root.right
        while s.left:
            s = s.left
        root.key = s.key
        root.right = bst_delete(root.right, s.key)
    return root


def inorder(n):
    return inorder(n.left) + [n.key] + inorder(n.right) if n else []


def preorder(n):
    return [n.key] + preorder(n.left) + preorder(n.right) if n else []


def postorder(n):
    return postorder(n.left) + postorder(n.right) + [n.key] if n else []


def height(n):
    """Height in edges; an empty tree is -1 and a single node is 0."""
    return -1 if n is None else 1 + max(height(n.left), height(n.right))


def count_leaves(n):
    if n is None:
        return 0
    return 1 if n.left is None and n.right is None else count_leaves(n.left) + count_leaves(n.right)


def bst_search_path(root, key):
    path, n = [], root
    while n:
        path.append(n.key)
        if key == n.key:
            return path, True
        n = n.left if key < n.key else n.right
    return path, False


def level_order(n):
    out, q = [], deque([n] if n else [])
    while q:
        c = q.popleft()
        out.append(c.key)
        q.extend(x for x in (c.left, c.right) if x)
    return out


def tree_from_inorder_preorder(inord, pre):
    if not pre:
        return None
    root = Node(pre[0])
    i = inord.index(pre[0])
    root.left = tree_from_inorder_preorder(inord[:i], pre[1 : 1 + i])
    root.right = tree_from_inorder_preorder(inord[i + 1 :], pre[1 + i :])
    return root


def extended_tree_counts(internal):
    """A binary tree with n internal nodes has n+1 external nodes when extended (2-tree)."""
    return {"internal": internal, "external": internal + 1, "total": 2 * internal + 1}


# --- Recursion --------------------------------------------------------------------------------


def hanoi_moves(n, a="A", b="B", c="C"):
    """Move n disks from a to c using b. Returns the list of (disk, from, to)."""
    if n == 0:
        return []
    return hanoi_moves(n - 1, a, c, b) + [(n, a, c)] + hanoi_moves(n - 1, b, a, c)


def fib_calls(n):
    """Number of calls made by the naive recursive fib(n) (fib(0)=0, fib(1)=1)."""
    return 1 if n < 2 else 1 + fib_calls(n - 1) + fib_calls(n - 2)


# --- Heaps ------------------------------------------------------------------------------------


def heap_insert(heap, x):
    h = list(heap) + [x]
    i = len(h) - 1
    while i > 0 and h[(i - 1) // 2] < h[i]:
        h[(i - 1) // 2], h[i] = h[i], h[(i - 1) // 2]
        i = (i - 1) // 2
    return h


def build_heap_by_insertion(items):
    h = []
    for x in items:
        h = heap_insert(h, x)
    return h


def _sift_down(h, i, n):
    while True:
        l, r, m = 2 * i + 1, 2 * i + 2, i
        if l < n and h[l] > h[m]:
            m = l
        if r < n and h[r] > h[m]:
            m = r
        if m == i:
            return
        h[i], h[m] = h[m], h[i]
        i = m


def heap_delete_max(heap):
    h = list(heap)
    top = h[0]
    h[0] = h[-1]
    h.pop()
    _sift_down(h, 0, len(h))
    return top, h


def build_heap_bottom_up(items):
    h = list(items)
    for i in range(len(h) // 2 - 1, -1, -1):
        _sift_down(h, i, len(h))
    return h


def heapsort_states(items):
    """Returns (max-heap after build, array after each extraction pass, final sorted)."""
    h = build_heap_bottom_up(items)
    built, states, n = list(h), [], len(h)
    for end in range(n - 1, 0, -1):
        h[0], h[end] = h[end], h[0]
        _sift_down(h, 0, end)
        states.append(list(h))
    return built, states, h


# --- Hashing ----------------------------------------------------------------------------------


def hash_chaining(keys, m, h=lambda k, m: k % m):
    t = [[] for _ in range(m)]
    for k in keys:
        t[h(k, m)].append(k)
    return t


def hash_open(keys, m, scheme="linear", h2=None):
    """Open addressing. scheme: linear | quadratic (h+i^2) | double (h + i*h2(k)). Returns (table, probe counts, failed keys)."""
    t, probes, failed = [None] * m, {}, []
    for k in keys:
        for i in range(m):
            if scheme == "linear":
                idx = (k % m + i) % m
            elif scheme == "quadratic":
                idx = (k % m + i * i) % m
            else:
                idx = (k % m + i * h2(k)) % m
            if t[idx] is None:
                t[idx] = k
                probes[k] = i + 1
                break
        else:
            failed.append(k)
    return t, probes, failed


# --- Graphs -----------------------------------------------------------------------------------


def adjacency(n, edges, directed=False):
    adj = {v: [] for v in range(n)}
    for e in edges:
        u, v = e[0], e[1]
        w = e[2] if len(e) > 2 else 1
        adj[u].append((v, w))
        if not directed:
            adj[v].append((u, w))
    for v in adj:
        adj[v].sort()
    return adj


def bfs_order(n, edges, start, directed=False):
    adj, seen, order, q = adjacency(n, edges, directed), {start}, [], deque([start])
    while q:
        u = q.popleft()
        order.append(u)
        for v, _ in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return order


def dfs_order(n, edges, start, directed=False):
    adj, seen, order = adjacency(n, edges, directed), set(), []

    def rec(u):
        seen.add(u)
        order.append(u)
        for v, _ in adj[u]:
            if v not in seen:
                rec(v)

    rec(start)
    return order


def dijkstra(n, edges, src, directed=False):
    adj, dist, pq = adjacency(n, edges, directed), {v: INF for v in range(n)}, [(0, src)]
    dist[src] = 0
    order = []
    done = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        order.append(u)
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return [dist[v] for v in range(n)], order


def bellman_ford(n, edges, src):
    """Directed edges. Returns (distances, negative_cycle_reachable, relaxation rounds that changed something)."""
    dist = [INF] * n
    dist[src] = 0
    changed_rounds = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
        changed_rounds += 1
    neg = any(dist[u] != INF and dist[u] + w < dist[v] for u, v, w in edges)
    return dist, neg, changed_rounds


def floyd_warshall(n, edges, directed=True):
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for e in edges:
        u, v, w = e
        d[u][v] = min(d[u][v], w)
        if not directed:
            d[v][u] = min(d[v][u], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def has_path_matrix_after_k(n, edges, k_limit):
    """Distance matrix after allowing only intermediates 0..k_limit-1 (k_limit rounds of Floyd–Warshall)."""
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in edges:
        d[u][v] = min(d[u][v], w)
    for k in range(k_limit):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d
