"""
Registry of named reference computations (kind -> params -> answer text).

A question's `verification` block stores `{"method": "reference", "kind": ..., "params": ...}`. Validation
re-runs the kind with the stored params and requires the result to equal the marked correct option and to
differ from every distractor. This catches key/option drift and mis-edited seeds. The algorithms themselves
are pinned by hand-computed cases in tests/test_dsa_algorithms.py.
"""

from __future__ import annotations

from . import algos as A


def _s(x):
    """Canonical display text for lists / scalars / inf."""
    if isinstance(x, float) and x == A.INF:
        return "∞"
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(_s(i) for i in x) + "]"
    return str(x)


def _tbl(t):
    return "[" + ", ".join("-" if v is None else str(v) for v in t) + "]"


def _chain(t):
    return " | ".join(f"{i}: {'→'.join(map(str, b)) if b else '—'}" for i, b in enumerate(t))


def _edges(p):
    return [tuple(e) for e in p["edges"]]


def _hash2(q):
    return lambda k: q - (k % q)


REFS = {
    # sorting & searching
    "bubble_pass": lambda p: _s(A.bubble_sort(p["arr"])[0][p["k"] - 1]),
    "bubble_swaps": lambda p: str(A.bubble_sort(p["arr"])[2]),
    "bubble_comps": lambda p: str(A.bubble_sort(p["arr"])[1]),
    "bubble_passes": lambda p: str(len(A.bubble_sort(p["arr"])[0])),
    "insertion_state": lambda p: _s(A.insertion_sort(p["arr"])[0][p["k"] - 1]),
    "insertion_shifts": lambda p: str(A.insertion_sort(p["arr"])[2]),
    "insertion_comps": lambda p: str(A.insertion_sort(p["arr"])[1]),
    "selection_state": lambda p: _s(A.selection_sort(p["arr"])[0][p["k"] - 1]),
    "selection_swaps": lambda p: str(A.selection_sort(p["arr"])[2]),
    "selection_comps": lambda p: str(A.selection_sort(p["arr"])[1]),
    "linear_comps": lambda p: str(A.linear_search(p["arr"], p["target"])[1]),
    "linear_index": lambda p: str(A.linear_search(p["arr"], p["target"])[0]),
    "binary_probes": lambda p: ", ".join(map(str, A.binary_search(p["arr"], p["target"])[1])),
    "binary_probe_count": lambda p: str(len(A.binary_search(p["arr"], p["target"])[1])),
    "binary_index": lambda p: str(A.binary_search(p["arr"], p["target"])[0]),
    "merge_result": lambda p: _s(A.merge(p["left"], p["right"])[0]),
    "merge_comps": lambda p: str(A.merge(p["left"], p["right"])[1]),
    "mergesort_merge_count": lambda p: str(len(A.merge_sort(p["arr"])[1])),
    "mergesort_comps": lambda p: str(A.merge_sort(p["arr"])[2]),
    "mergesort_first_merge": lambda p: _s(A.merge_sort(p["arr"])[1][0][2]),
    "quick_partition": lambda p: _s(A.quick_sort_first_partition(p["arr"])[0]),
    "quick_pivot_index": lambda p: str(A.quick_sort_first_partition(p["arr"])[1]),
    "quick_calls": lambda p: str(A.quick_sort(p["arr"])[1]),
    # arrays
    "array_address": lambda p: str(p["base"] + p["i"] * p["w"]),
    "array_shift_insert": lambda p: str(len(p["arr"]) - p["pos"]),
    "array_shift_delete": lambda p: str(len(p["arr"]) - p["pos"] - 1),
    "array_insert_result": lambda p: _s(p["arr"][: p["pos"]] + [p["x"]] + p["arr"][p["pos"] :]),
    "array_delete_result": lambda p: _s(p["arr"][: p["pos"]] + p["arr"][p["pos"] + 1 :]),
    "array_merge_sorted": lambda p: _s(A.merge(p["left"], p["right"])[0]),
    "array_len": lambda p: str(p["ub"] - p["lb"] + 1),
    # stacks / expressions
    "postfix": lambda p: A.infix_to_postfix(p["expr"]),
    "prefix": lambda p: A.infix_to_prefix(p["expr"]),
    "eval_postfix": lambda p: str(A.eval_postfix(p["expr"])[0]),
    "eval_prefix": lambda p: str(A.eval_prefix(p["expr"])),
    "postfix_max_depth": lambda p: str(max(len(s) for s in A.eval_postfix(p["expr"])[1])),
    "balanced": lambda p: "Balanced" if A.balanced(p["s"]) else "Not balanced",
    "stack_final": lambda p: _s(_stack_run(p["ops"])[0]),
    "stack_popped": lambda p: _s(_stack_run(p["ops"])[1]),
    # queues
    "cq_final": lambda p: _s(A.circular_queue(p["cap"], [tuple(o) for o in p["ops"]])[0]),
    "cq_outputs": lambda p: _s(A.circular_queue(p["cap"], [tuple(o) for o in p["ops"]])[1]),
    "cq_slots": lambda p: _tbl(A.circular_queue(p["cap"], [tuple(o) for o in p["ops"]])[2]),
    "pq_order": lambda p: _s(A.priority_queue_order([tuple(i) for i in p["items"]])),
    "deque_final": lambda p: _s(A.deque_ops([tuple(o) for o in p["ops"]])[0]),
    "deque_popped": lambda p: _s(A.deque_ops([tuple(o) for o in p["ops"]])[1]),
    # trees
    "bst_inorder": lambda p: _s(A.inorder(A.build_bst(p["keys"]))),
    "bst_preorder": lambda p: _s(A.preorder(A.build_bst(p["keys"]))),
    "bst_postorder": lambda p: _s(A.postorder(A.build_bst(p["keys"]))),
    "bst_levelorder": lambda p: _s(A.level_order(A.build_bst(p["keys"]))),
    "bst_height": lambda p: str(A.height(A.build_bst(p["keys"]))),
    "bst_leaves": lambda p: str(A.count_leaves(A.build_bst(p["keys"]))),
    "bst_search_path": lambda p: ", ".join(map(str, A.bst_search_path(A.build_bst(p["keys"]), p["key"])[0])),
    "bst_delete_preorder": lambda p: _s(A.preorder(A.bst_delete(A.build_bst(p["keys"]), p["key"]))),
    "bst_delete_inorder": lambda p: _s(A.inorder(A.bst_delete(A.build_bst(p["keys"]), p["key"]))),
    "bst_root_after_delete": lambda p: str(A.bst_delete(A.build_bst(p["keys"]), p["key"]).key),
    "postorder_from_in_pre": lambda p: _s(A.postorder(A.tree_from_inorder_preorder(p["inorder"], p["preorder"]))),
    "heap_children": lambda p: f"{2 * p['i'] + 1} and {2 * p['i'] + 2}",
    "heap_parent": lambda p: str((p["i"] - 1) // 2),
    "extended_external": lambda p: str(A.extended_tree_counts(p["internal"])["external"]),
    "extended_total": lambda p: str(A.extended_tree_counts(p["internal"])["total"]),
    "complete_array_size": lambda p: str(2 ** (p["h"] + 1) - 1),
    "max_nodes_height": lambda p: str(2 ** (p["h"] + 1) - 1),
    "max_nodes_level": lambda p: str(2 ** p["level"]),
    # recursion
    "hanoi_count": lambda p: str(len(A.hanoi_moves(p["n"]))),
    "hanoi_move": lambda p: "disk {} from {} to {}".format(*A.hanoi_moves(p["n"])[p["k"] - 1]),
    "hanoi_sequence": lambda p: ", ".join(f"{a}→{c}" for _, a, c in A.hanoi_moves(p["n"])),
    "fib_calls": lambda p: str(A.fib_calls(p["n"])),
    # heaps
    "heap_by_insertion": lambda p: _s(A.build_heap_by_insertion(p["items"])),
    "heap_bottom_up": lambda p: _s(A.build_heap_bottom_up(p["items"])),
    "heap_after_delete": lambda p: _s(A.heap_delete_max(p["heap"])[1]),
    "heap_deleted_value": lambda p: str(A.heap_delete_max(p["heap"])[0]),
    "heapsort_built": lambda p: _s(A.heapsort_states(p["items"])[0]),
    "heapsort_pass": lambda p: _s(A.heapsort_states(p["items"])[1][p["k"] - 1]),
    # hashing
    "hash_chain": lambda p: _chain(A.hash_chaining(p["keys"], p["m"])),
    "hash_chain_longest": lambda p: str(max(len(b) for b in A.hash_chaining(p["keys"], p["m"]))),
    "hash_linear": lambda p: _tbl(A.hash_open(p["keys"], p["m"], "linear")[0]),
    "hash_quadratic": lambda p: _tbl(A.hash_open(p["keys"], p["m"], "quadratic")[0]),
    "hash_double": lambda p: _tbl(A.hash_open(p["keys"], p["m"], "double", _hash2(p["q"]))[0]),
    "hash_linear_probes": lambda p: str(A.hash_open(p["keys"], p["m"], "linear")[1][p["key"]]),
    "hash_quadratic_probes": lambda p: str(A.hash_open(p["keys"], p["m"], "quadratic")[1][p["key"]]),
    "hash_double_probes": lambda p: str(A.hash_open(p["keys"], p["m"], "double", _hash2(p["q"]))[1][p["key"]]),
    "hash_quadratic_failed": lambda p: _s(A.hash_open(p["keys"], p["m"], "quadratic")[2]),
    "hash_load_factor": lambda p: f"{p['n'] / p['m']:g}",
    "hash_index": lambda p: str(p["key"] % p["m"]),
    # graphs
    "bfs": lambda p: ", ".join(map(str, A.bfs_order(p["n"], _edges(p), p["start"], p.get("directed", False)))),
    "dfs": lambda p: ", ".join(map(str, A.dfs_order(p["n"], _edges(p), p["start"], p.get("directed", False)))),
    "dijkstra_dist": lambda p: _s(A.dijkstra(p["n"], _edges(p), p["src"], p.get("directed", False))[0][p["target"]]),
    "dijkstra_all": lambda p: _s(A.dijkstra(p["n"], _edges(p), p["src"], p.get("directed", False))[0]),
    "dijkstra_order": lambda p: ", ".join(map(str, A.dijkstra(p["n"], _edges(p), p["src"], p.get("directed", False))[1])),
    "bf_all": lambda p: _s(A.bellman_ford(p["n"], _edges(p), p["src"])[0]),
    "bf_negative_cycle": lambda p: "Yes" if A.bellman_ford(p["n"], _edges(p), p["src"])[1] else "No",
    "bf_rounds": lambda p: str(A.bellman_ford(p["n"], _edges(p), p["src"])[2]),
    "fw_entry": lambda p: _s(A.floyd_warshall(p["n"], _edges(p))[p["i"]][p["j"]]),
    "fw_after_k": lambda p: _s(A.has_path_matrix_after_k(p["n"], _edges(p), p["k"])[p["i"]][p["j"]]),
    "fw_row": lambda p: _s(A.floyd_warshall(p["n"], _edges(p))[p["i"]]),
    "graph_edge_count_complete": lambda p: str(p["n"] * (p["n"] - 1) // 2),
}


def _stack_run(ops):
    st, popped = [], []
    for op in ops:
        if op[0] == "push":
            st.append(op[1])
        else:
            popped.append(st.pop() if st else "underflow")
    return st, popped


class UnknownReference(ValueError):
    pass


def run_reference(kind: str, params: dict) -> str:
    fn = REFS.get(kind)
    if fn is None:
        raise UnknownReference(f"unknown reference kind '{kind}'")
    try:
        return fn(params)
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise UnknownReference(f"reference '{kind}' failed: {exc}") from exc
