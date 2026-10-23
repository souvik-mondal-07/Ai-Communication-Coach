"""Topic J (Graphs)."""

from __future__ import annotations

from app.services.dsa import algos as A
from app.services.dsa.references import _s

from .build import M, S, mk, mk_ref

G1 = [[0, 1], [0, 2], [1, 3], [1, 4], [2, 4], [3, 5], [4, 5]]  # undirected, 6 vertices
G2 = [[0, 1], [0, 3], [1, 2], [3, 2], [2, 4], [4, 0]]  # directed, 5 vertices
W1 = [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 1], [2, 3, 5], [3, 4, 3]]  # undirected weighted
BF1 = [[0, 1, 6], [0, 2, 7], [1, 2, 8], [1, 3, 5], [1, 4, -4], [2, 3, -3], [2, 4, 9], [3, 1, -2], [4, 3, 7], [4, 0, 2]]
BFC = [[0, 1, 1], [1, 2, -1], [2, 3, -1], [3, 1, -1]]  # negative cycle 1→2→3→1
FW1 = [[0, 1, 5], [0, 3, 10], [1, 2, 3], [2, 3, 1]]  # directed


def _txt(edges, weighted=False):
    return ", ".join(f"{e[0]}–{e[1]}({e[2]})" if weighted else f"{e[0]}–{e[1]}" for e in edges)


def _arrows(edges, weighted=False):
    return ", ".join(f"{e[0]}→{e[1]}({e[2]})" if weighted else f"{e[0]}→{e[1]}" for e in edges)


def _progress(order, verb="visit"):
    return [{"label": f"{verb} {v}", "state": _s(order[: i + 1])} for i, v in enumerate(order)]


def bfs_q():
    s = "bfs"
    bfs1 = A.bfs_order(6, [tuple(e) for e in G1], 0)
    dfs1 = A.dfs_order(6, [tuple(e) for e in G1], 0)
    return [
        mk_ref(s, "trace", f"An undirected graph on vertices 0–5 has edges {_txt(G1)}. BFS starts at 0 and visits neighbours in ascending order. What is the visit order?", "bfs", {"n": 6, "edges": G1, "start": 0},
               [", ".join(map(str, dfs1)), "0, 2, 1, 4, 3, 5", "0, 1, 3, 5, 2, 4"], "Level by level: 0; then 1, 2; then 3, 4 (neighbours of 1 and 2); then 5.", d="medium", t=75, trace=_progress(bfs1)),
        mk_ref(s, "trace", f"A DIRECTED graph on vertices 0–4 has edges {_arrows(G2)}. BFS starts at 0 (neighbours in ascending order). What is the visit order?", "bfs", {"n": 5, "edges": G2, "start": 0, "directed": True},
               ["0, 1, 2, 3, 4", "0, 3, 1, 2, 4", "0, 1, 3, 4, 2"], "Queue: 0 → 1, 3 → 2 (first reached through 1) → 4.", d="medium", t=70, trace=_progress(A.bfs_order(5, [tuple(e) for e in G2], 0, True))),
        mk(s, "conceptual", "Which data structure drives Breadth-First Search?", "A queue", ["A stack", "A priority queue keyed by edge weight", "A hash table only"], "FIFO order makes BFS explore all vertices at distance d before distance d + 1.", d="easy", t=30, ver=M("BFS uses a FIFO queue.")),
        mk(s, "complexity", "What is the time complexity of BFS on a graph with V vertices and E edges stored as adjacency lists?", "O(V + E)", ["O(V · E)", "O(V²) always", "O(E log V)"], "Each vertex is enqueued once and each edge examined a constant number of times.", d="medium", t=40,
           complexity={"time": "O(V + E)", "space": "O(V)"}, ver=M("Standard BFS analysis with adjacency lists.")),
        mk(s, "scenario", "You need the fewest number of edges between two users in an unweighted social network. Which algorithm is the natural choice?", "BFS from one user", ["DFS from one user", "Bellman–Ford with all weights 0", "Heap sort on user IDs"], "BFS reaches vertices in nondecreasing hop distance.", d="easy", t=40, ver=M("BFS finds shortest paths in unweighted graphs.")),
        mk(s, "output", "What does this code print?", "[0, 1, 2, 3]", ["[0, 2, 1, 3]", "[0, 1, 3, 2]", "[3, 2, 1, 0]"], "The queue processes 0, then 1 and 2, then 3.", d="medium", t=60,
           code="from collections import deque\ng = {0: [1, 2], 1: [3], 2: [3], 3: []}\nseen, order, q = {0}, [], deque([0])\nwhile q:\n    u = q.popleft()\n    order.append(u)\n    for v in g[u]:\n        if v not in seen:\n            seen.add(v)\n            q.append(v)\nprint(order)", ver=S("[0, 1, 2, 3]")),
    ]


def dfs_q():
    s = "dfs"
    dfs1 = A.dfs_order(6, [tuple(e) for e in G1], 0)
    bfs1 = A.bfs_order(6, [tuple(e) for e in G1], 0)
    return [
        mk_ref(s, "trace", f"An undirected graph on vertices 0–5 has edges {_txt(G1)}. Recursive DFS starts at 0 and visits neighbours in ascending order. What is the visit order?", "dfs", {"n": 6, "edges": G1, "start": 0},
               [", ".join(map(str, bfs1)), "0, 2, 4, 1, 3, 5", "0, 1, 3, 4, 5, 2"], "Go deep first: 0 → 1 → 3 → 5 → 4, then back up and visit 2.", d="medium", t=80, trace=_progress(dfs1)),
        mk_ref(s, "trace", f"A DIRECTED graph on vertices 0–4 has edges {_arrows(G2)}. DFS starts at 0 (neighbours in ascending order). What is the visit order?", "dfs", {"n": 5, "edges": G2, "start": 0, "directed": True},
               ["0, 1, 3, 2, 4", "0, 3, 2, 4, 1", "0, 1, 2, 3, 4"], "0 → 1 → 2 → 4 (4→0 already visited), then back to 0 and its neighbour 3.", d="medium", t=75, trace=_progress(A.dfs_order(5, [tuple(e) for e in G2], 0, True))),
        mk(s, "conceptual", "Which structure does iterative DFS use explicitly (and recursive DFS uses implicitly)?", "A stack", ["A queue", "A min-heap", "A hash table"], "The most recently discovered vertex is explored first.", d="easy", t=30, ver=M("DFS explores the most recently discovered vertex first: LIFO.")),
        mk(s, "complexity", "What is the time and auxiliary space of recursive DFS on a graph with V vertices and E edges (adjacency lists)?", "Time O(V + E); space O(V) for the visited set and recursion", ["Time O(V · E); space O(1)", "Time O(E log V); space O(E)", "Time O(V²); space O(V²) always"], "Each vertex and edge is processed once; recursion depth can reach V.", d="medium", t=50,
           complexity={"time": "O(V + E)", "space": "O(V)"}, ver=M("Standard DFS analysis.")),
        mk(s, "scenario", "A build system must detect circular dependencies among modules. Which traversal is typically used?", "DFS, detecting a back edge to a vertex still on the recursion stack", ["BFS counting levels", "Binary search on module names", "Heap sort on dependencies"], "A back edge in a directed graph means a cycle.", d="hard", t=60, ver=M("Cycle detection with DFS colours/recursion stack.")),
        mk(s, "output", "What does this code print?", "[0, 1, 3, 2]", ["[0, 1, 2, 3]", "[0, 2, 3, 1]", "[0, 2, 1, 3]"], "DFS goes from 0 to 1 to 3 before backtracking to 2.", d="medium", t=60,
           code="g = {0: [1, 2], 1: [3], 2: [3], 3: []}\nseen, order = set(), []\ndef dfs(u):\n    seen.add(u)\n    order.append(u)\n    for v in g[u]:\n        if v not in seen:\n            dfs(v)\ndfs(0)\nprint(order)", ver=S("[0, 1, 3, 2]")),
    ]


def dijkstra_q():
    s = "dijkstra"
    ed = [tuple(e) for e in W1]
    dist, order = A.dijkstra(5, ed, 0)
    return [
        mk_ref(s, "trace", f"An undirected weighted graph on vertices 0–4 has edges {_txt(W1, True)} (weight in brackets). Using Dijkstra from 0, what is the shortest distance to vertex 3?", "dijkstra_dist", {"n": 5, "edges": W1, "src": 0, "target": 3},
               ["5", "6", "1"], "Best route is 0→2→1→3 = 1 + 2 + 1; going 0→1 directly costs 4, 0→2→3 costs 6.", d="medium", t=80,
               trace=[{"label": "settle 0", "state": "dist: [0, 4, 1, ∞, ∞]"}, {"label": "settle 2 (dist 1)", "state": "dist: [0, 3, 1, 6, ∞]"}, {"label": "settle 1 (dist 3)", "state": "dist: [0, 3, 1, 4, ∞]"}, {"label": "settle 3 (dist 4)", "state": "dist: [0, 3, 1, 4, 7]"}, {"label": "settle 4 (dist 7)", "state": "dist: [0, 3, 1, 4, 7]"}]),
        mk_ref(s, "trace", f"For the same graph (edges {_txt(W1, True)}), what is the final distance array from source 0?", "dijkstra_all", {"n": 5, "edges": W1, "src": 0},
               ["[0, 4, 1, 6, 9]", "[0, 3, 1, 6, 9]", "[0, 3, 1, 4, 6]"], "Distances settle in the order 0, 2, 1, 3, 4.", d="medium", t=85,
               trace=[{"label": "settle 0", "state": "[0, 4, 1, ∞, ∞]"}, {"label": "settle 2", "state": "[0, 3, 1, 6, ∞]"}, {"label": "settle 1", "state": "[0, 3, 1, 4, ∞]"}, {"label": "settle 3", "state": "[0, 3, 1, 4, 7]"}, {"label": "settle 4", "state": "[0, 3, 1, 4, 7]"}]),
        mk_ref(s, "trace", f"For the same graph and source 0, in which order does Dijkstra FINALISE (settle) the vertices?", "dijkstra_order", {"n": 5, "edges": W1, "src": 0},
               ["0, 1, 2, 3, 4", "0, 1, 3, 2, 4", "0, 2, 3, 1, 4"], "The next vertex settled is always the unsettled one with the smallest tentative distance.", d="hard", t=90,
               trace=[{"label": "tentative after 0", "state": "1:4, 2:1 → settle 2 (smallest)"}, {"label": "tentative after 2", "state": "1:3, 3:6 → settle 1"}, {"label": "tentative after 1", "state": "3:4 → settle 3, then 4"}]),
        mk(s, "conceptual", "Why does Dijkstra's algorithm fail on graphs with negative edge weights?", "Once a vertex is settled its distance is assumed final, but a later negative edge could shorten it", ["It cannot store negative numbers", "It only works on directed graphs", "It runs in exponential time"], "The greedy 'settled is final' rule needs non-negative weights.", d="medium", t=55, ver=M("Core correctness assumption of Dijkstra.")),
        mk(s, "complexity", "What is the time complexity of Dijkstra's algorithm with a binary heap and adjacency lists?", "O((V + E) log V)", ["O(V · E)", "O(V³)", "O(V + E)"], "Each edge relaxation may push to the heap at O(log V).", d="hard", t=50,
           complexity={"time": "O((V + E) log V) with a binary heap; O(V²) with an array", "space": "O(V)"}, ver=M("Standard heap-based Dijkstra analysis.")),
        mk(s, "scenario", "A navigation app computes the fastest route using non-negative travel times. Which algorithm fits best?", "Dijkstra's algorithm", ["Bellman–Ford, because it is faster", "BFS, because roads are unweighted", "Floyd–Warshall for a single route"], "Non-negative weights and a single source suit Dijkstra.", d="easy", t=40, ver=M("Dijkstra for single-source with non-negative weights.")),
    ]


def bellman_q():
    s = "bellman-ford"
    ed = [tuple(e) for e in BF1]
    return [
        mk_ref(s, "trace", f"A directed graph on vertices 0–4 has edges {_arrows(BF1, True)}. After Bellman–Ford from source 0 completes, what is the distance array?", "bf_all", {"n": 5, "edges": BF1, "src": 0},
               ["[0, 6, 7, 4, -4]", "[0, 2, 7, 4, 2]", "[0, 6, 7, 11, 2]"], "Negative edges let the path 0→2→3→1→4 reach vertex 4 with cost 7 → 4 → 2 → −2.", d="hard", t=120,
               trace=[{"label": "start", "state": "[0, ∞, ∞, ∞, ∞]"}, {"label": "path 0→2→3→1→4", "state": "dist 2 = 7, dist 3 = 4, dist 1 = 2, dist 4 = −2"}, {"label": "final distances", "state": "[0, 2, 7, 4, -2]"}]),
        mk_ref(s, "trace", f"Does the directed graph with edges {_arrows(BFC, True)} contain a negative cycle reachable from vertex 0?", "bf_negative_cycle", {"n": 4, "edges": BFC, "src": 0},
               ["No", "Only if it is undirected", "Cannot be determined"], "The cycle 1→2→3→1 has total weight −3, so a further relaxation pass still improves distances.", d="medium", t=80,
               trace=[{"label": "cycle weights", "state": "1→2 (−1) + 2→3 (−1) + 3→1 (−1) = −3"}, {"label": "extra (V-th) relaxation pass", "state": "still shortens a distance → negative cycle"}]),
        mk(s, "complexity", "What is the time complexity of Bellman–Ford on a graph with V vertices and E edges?", "O(V · E)", ["O((V + E) log V)", "O(V + E)", "O(V³) always"], "It relaxes all E edges up to V − 1 times.", d="medium", t=40, complexity={"time": "O(V · E)", "space": "O(V)"}, ver=M("Standard Bellman-Ford analysis.")),
        mk(s, "conceptual", "How does Bellman–Ford detect a negative cycle?", "If any edge can still be relaxed after V − 1 passes", ["If a distance becomes zero", "If the queue becomes empty", "If two vertices share a distance"], "With no negative cycle, all shortest paths use at most V − 1 edges, so distances stop changing.", d="medium", t=50, ver=M("Standard detection rule.")),
        mk(s, "scenario", "A currency-exchange graph may contain arbitrage opportunities (negative cycles after taking logarithms). Which shortest-path algorithm can detect them?", "Bellman–Ford", ["Dijkstra", "BFS", "Prim's algorithm"], "It tolerates negative weights and reports negative cycles.", d="hard", t=60, ver=M("Classic arbitrage detection with Bellman-Ford.")),
        mk(s, "conceptual", "Why does Bellman–Ford run exactly V − 1 relaxation passes in the absence of negative cycles?", "A shortest path has at most V − 1 edges, and each pass fixes at least the next edge along it", ["Each pass removes one vertex", "The graph has V − 1 cycles", "It stops when the queue is empty"], "After pass k, all shortest paths using at most k edges are correct.", d="hard", t=60, ver=M("Path-length argument for Bellman-Ford correctness.")),
    ]


def floyd_q():
    s = "floyd-warshall"
    return [
        mk_ref(s, "trace", f"A directed graph on vertices 0–3 has edges {_arrows(FW1, True)}. After Floyd–Warshall finishes, what is the shortest distance from 0 to 3?", "fw_entry", {"n": 4, "edges": FW1, "i": 0, "j": 3},
               ["10", "8", "6"], "The route 0→1→2→3 costs 5 + 3 + 1, which beats the direct edge of 10.", d="medium", t=75,
               trace=[{"label": "initial d[0][3]", "state": "10 (direct edge)"}, {"label": "k = 1 allowed", "state": "d[0][2] = 5 + 3 = 8"}, {"label": "k = 2 allowed", "state": "d[0][3] = min(10, 8 + 1) = 9"}]),
        mk_ref(s, "trace", f"For the same graph and Floyd–Warshall, what is the distance from 0 to 2 after ONLY k = 0 and k = 1 have been used as intermediate vertices (the first two outer-loop rounds)?", "fw_after_k", {"n": 4, "edges": FW1, "i": 0, "j": 2, "k": 2},
               ["∞", "3", "5"], "Using vertex 1 as an intermediate gives 0→1→2 = 5 + 3.", d="hard", t=90,
               trace=[{"label": "initial d[0][2]", "state": "∞ (no direct edge)"}, {"label": "k = 0", "state": "no improvement"}, {"label": "k = 1", "state": "d[0][2] = d[0][1] + d[1][2] = 8"}]),
        mk_ref(s, "trace", f"For the same graph, what is the full first row (distances from 0 to 0, 1, 2, 3) after Floyd–Warshall completes?", "fw_row", {"n": 4, "edges": FW1, "i": 0},
               ["[0, 5, 8, 10]", "[0, 5, 3, 1]", "[0, 5, ∞, 9]"], "0→2 is 8 and 0→3 is 9 via the chain 0→1→2→3.", d="medium", t=80,
               trace=[{"label": "direct edges", "state": "[0, 5, ∞, 10]"}, {"label": "after k = 1", "state": "[0, 5, 8, 10]"}, {"label": "after k = 2", "state": "[0, 5, 8, 9]"}]),
        mk(s, "complexity", "What are the time and space complexities of Floyd–Warshall on V vertices?", "Time O(V³); space O(V²)", ["Time O(V²); space O(V)", "Time O(V · E); space O(V)", "Time O(V³); space O(V)"], "Three nested loops over V vertices updating a V × V matrix.", d="easy", t=40, complexity={"time": "O(V³)", "space": "O(V²)"}, ver=M("Standard Floyd-Warshall analysis.")),
        mk(s, "conceptual", "In Floyd–Warshall, what does the outer loop variable k represent?", "The intermediate vertex that paths are currently allowed to pass through", ["The source vertex", "The destination vertex", "The number of edges in the path"], "After round k, all shortest paths using only vertices 0..k as intermediates are known.", d="medium", t=45, ver=M("Dynamic-programming definition of Floyd-Warshall.")),
        mk(s, "scenario", "A logistics team needs the shortest travel time between EVERY pair of 200 depots, with some negative adjustment edges but no negative cycles. Which algorithm is simplest?", "Floyd–Warshall", ["Dijkstra run once", "BFS", "Binary search"], "All-pairs shortest paths with negative (but cycle-free) weights suit Floyd–Warshall.", d="medium", t=50, ver=M("All-pairs shortest paths use cases.")),
        mk(s, "conceptual", "How can a negative cycle be detected after running Floyd–Warshall?", "Some diagonal entry d[i][i] is negative", ["Some off-diagonal entry is ∞", "The matrix is symmetric", "d[0][0] differs from d[1][1]"], "A negative cycle through i makes the distance from i back to itself negative.", d="hard", t=55, ver=M("Standard negative-cycle test.")),
    ]


def all_questions():
    out = []
    for f in (bfs_q, dfs_q, dijkstra_q, bellman_q, floyd_q):
        out.extend(f())
    return out
