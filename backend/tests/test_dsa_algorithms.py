"""Phase 24 -- the reference algorithms are pinned to hand-computed results (independent of the seed bank)."""

from __future__ import annotations

from app.services.dsa import algos as A


def test_bubble_sort_passes_and_counts():
    states, comps, swaps = A.bubble_sort([5, 1, 4, 2, 8])
    assert states == [[1, 4, 2, 5, 8], [1, 2, 4, 5, 8], [1, 2, 4, 5, 8]]  # pass 3 swaps nothing and stops
    assert (comps, swaps) == (9, 4)


def test_insertion_and_selection_sort_hand_traces():
    states, comps, shifts = A.insertion_sort([5, 2, 4, 6, 1, 3])
    assert states[0] == [2, 5, 4, 6, 1, 3] and states[3] == [1, 2, 4, 5, 6, 3] and states[-1] == [1, 2, 3, 4, 5, 6] and shifts == 9
    s_states, s_comps, s_swaps = A.selection_sort([64, 25, 12, 22, 11])
    assert s_states[0] == [11, 25, 12, 22, 64] and s_states[1] == [11, 12, 25, 22, 64] and s_comps == 10 and s_swaps == 3


def test_searches():
    assert A.linear_search([14, 3, 9, 27], 27) == (3, 4) and A.linear_search([1, 2], 9) == (-1, 2)
    arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    assert A.binary_search(arr, 23) == (5, [4, 7, 5]) and A.binary_search(arr, 1)[0] == -1
    assert A.binary_search([3, 6, 9, 12, 15, 18, 21, 24, 27], 10) == (-1, [4, 1, 2, 3])


def test_merge_and_quick_sort():
    assert A.merge([2, 5, 9], [1, 5, 8, 12])[0] == [1, 2, 5, 5, 8, 9, 12]
    assert A.merge([1, 3, 5, 7], [2, 4, 6, 8])[1] == 7
    assert A.merge_sort([5, 2, 8, 1, 3])[0] == [1, 2, 3, 5, 8]
    assert A.quick_sort_first_partition([8, 3, 7, 1, 6, 5]) == ([3, 1, 5, 8, 6, 7], 2)
    assert A.quick_sort([3, 1, 2]) == ([1, 2, 3], 1)


def test_expression_conversion_and_evaluation():
    assert A.infix_to_postfix("A + B * C") == "A B C * +"
    assert A.infix_to_postfix("( A + B ) * ( C - D )") == "A B + C D - *"
    assert A.infix_to_postfix("A - B - C") == "A B - C -"  # left associative
    assert A.infix_to_prefix("( A + B ) * C") == "* + A B C"
    assert A.infix_to_prefix("A - B - C") == "- - A B C"
    assert A.eval_postfix("5 6 2 + * 12 4 / -")[0] == 37 and A.eval_prefix("- * 2 3 4") == 2
    assert A.balanced("{[()]}") and not A.balanced("([)]") and not A.balanced("((")


def test_queues_and_deque():
    final, outs, slots = A.circular_queue(4, [("enq", "A"), ("enq", "B"), ("enq", "C"), ("deq",), ("deq",), ("enq", "D"), ("enq", "E")])
    assert slots == ["E", None, "C", "D"] and final == ["C", "D", "E"] and outs == ["A", "B"]
    assert A.circular_queue(2, [("enq", 1), ("enq", 2), ("enq", 3), ("deq",), ("deq",), ("deq",)])[1] == ["overflow", 1, 2, "underflow"]
    assert A.priority_queue_order([(3, "p"), (1, "a"), (2, "e"), (1, "b")]) == ["a", "b", "e", "p"]  # ties are FIFO
    assert A.deque_ops([("pb", 1), ("pb", 2), ("pf", 0), ("eb",), ("ef",)]) == ([1], [2, 0])


def test_binary_search_tree_operations():
    root = A.build_bst([50, 30, 70, 20, 40, 60, 80])
    assert A.inorder(root) == [20, 30, 40, 50, 60, 70, 80]
    assert A.preorder(root) == [50, 30, 20, 40, 70, 60, 80]
    assert A.postorder(root) == [20, 40, 30, 60, 80, 70, 50]
    assert A.level_order(root) == [50, 30, 70, 20, 40, 60, 80]
    assert A.height(root) == 2 and A.height(None) == -1 and A.count_leaves(root) == 4
    assert A.bst_search_path(root, 60) == ([50, 70, 60], True) and A.bst_search_path(root, 65)[1] is False
    assert A.preorder(A.bst_delete(A.build_bst([50, 30, 70, 20, 40, 60, 80]), 50)) == [60, 30, 20, 40, 70, 80]  # successor replaces the root
    assert A.preorder(A.bst_delete(A.build_bst([8, 3, 10, 1, 6, 14, 4, 7, 13]), 3)) == [8, 4, 1, 6, 7, 10, 14, 13]
    assert A.postorder(A.tree_from_inorder_preorder([4, 2, 5, 1, 3], [1, 2, 4, 5, 3])) == [4, 5, 2, 3, 1]
    assert A.extended_tree_counts(6) == {"internal": 6, "external": 7, "total": 13}


def test_recursion():
    assert len(A.hanoi_moves(4)) == 15 and len(A.hanoi_moves(0)) == 0
    assert A.hanoi_moves(2) == [(1, "A", "B"), (2, "A", "C"), (1, "B", "C")]
    assert [A.fib_calls(n) for n in range(6)] == [1, 1, 3, 5, 9, 15]


def test_heaps():
    assert A.build_heap_by_insertion([10, 20, 15, 30, 40]) == [40, 30, 15, 10, 20]
    assert A.build_heap_bottom_up([13, 31, 35, 36, 38, 26]) == [38, 36, 35, 13, 31, 26]
    assert A.build_heap_by_insertion([13, 31, 35, 36, 38, 26]) == [38, 36, 31, 13, 35, 26]  # the two methods really differ
    top, rest = A.heap_delete_max([40, 30, 15, 10, 20])
    assert top == 40 and rest == [30, 20, 15, 10]
    built, states, final = A.heapsort_states([4, 10, 3, 5, 1])
    assert built == [10, 5, 3, 4, 1] and states[0] == [5, 4, 3, 1, 10] and final == [1, 3, 4, 5, 10]


def test_hashing_schemes():
    assert A.hash_open([50, 700, 76, 85, 92, 73, 101], 7)[0] == [700, 50, 85, 92, 73, 101, 76]
    table, probes, _ = A.hash_open([87, 95, 99, 30, 51, 79], 11, "quadratic")
    assert probes[51] == 4 and table[5] == 51  # 7, 8, 0 taken, then 7 + 9 = 16 mod 11 = 5
    table, probes, _ = A.hash_open([34, 46, 32, 44, 47, 36], 10, "double", lambda k: 7 - k % 7)
    assert probes[44] == 2 and table[9] == 44  # home slot 4 taken, step 7 - 2 = 5
    assert A.hash_chaining([15, 53, 50, 56, 27, 58, 74, 39], 7)[4] == [53, 74, 39]


def test_graph_algorithms():
    g = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 4), (3, 5), (4, 5)]
    assert A.bfs_order(6, g, 0) == [0, 1, 2, 3, 4, 5] and A.dfs_order(6, g, 0) == [0, 1, 3, 5, 4, 2]
    w = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5), (3, 4, 3)]
    dist, order = A.dijkstra(5, w, 0)
    assert dist == [0, 3, 1, 4, 7] and order == [0, 2, 1, 3, 4]
    bf = [(0, 1, 6), (0, 2, 7), (1, 2, 8), (1, 3, 5), (1, 4, -4), (2, 3, -3), (2, 4, 9), (3, 1, -2), (4, 3, 7), (4, 0, 2)]
    assert A.bellman_ford(5, bf, 0)[:2] == ([0, 2, 7, 4, -2], False)
    assert A.bellman_ford(4, [(0, 1, 1), (1, 2, -1), (2, 3, -1), (3, 1, -1)], 0)[1] is True
    fw = A.floyd_warshall(4, [(0, 1, 5), (0, 3, 10), (1, 2, 3), (2, 3, 1)])
    assert fw[0] == [0, 5, 8, 9] and fw[1][0] == A.INF
