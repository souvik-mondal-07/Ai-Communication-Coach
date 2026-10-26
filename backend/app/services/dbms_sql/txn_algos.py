"""
Transaction & concurrency algorithms (Phase 25): schedule parsing, conflict and view serializability, recoverability
classes, cascading rollback, two-phase locking and lock-wait deadlock detection. Pure Python; used to VERIFY answer keys.

Schedule syntax (whitespace separated): R1(A) W2(A) C1 A2   -> read/write item A by T1/T2, commit T1, abort T2.
Lock syntax: S1(A) X2(B) U1(A)   -> shared lock, exclusive lock, unlock.
"""

from __future__ import annotations

import re
from itertools import permutations
from math import factorial

Op = tuple[str, int, str | None]  # (kind, txn, item) ; kind in R W C A S X U

_TOKEN = re.compile(r"^([RWSXU])(\d+)\(([A-Za-z]\w*)\)$|^([CA])(\d+)$")


def parse(schedule: str) -> list[Op]:
    ops: list[Op] = []
    for tok in schedule.split():
        m = _TOKEN.match(tok)
        if not m:
            raise ValueError(f"bad token {tok!r}")
        ops.append((m.group(1), int(m.group(2)), m.group(3)) if m.group(1) else (m.group(4), int(m.group(5)), None))
    return ops


def transactions(ops: list[Op]) -> list[int]:
    return sorted({t for _, t, _ in ops})


def _data_ops(ops: list[Op], include_aborted: bool = False) -> list[tuple[int, str, int, str]]:
    aborted = {t for k, t, _ in ops if k == "A"}
    return [(i, k, t, x) for i, (k, t, x) in enumerate(ops) if k in "RW" and (include_aborted or t not in aborted)]


def conflict_edges(ops: list[Op]) -> set[tuple[int, int]]:
    data = _data_ops(ops)
    edges: set[tuple[int, int]] = set()
    for i, (_, k1, t1, x1) in enumerate(data):
        for _, k2, t2, x2 in data[i + 1:]:
            if t1 != t2 and x1 == x2 and "W" in (k1, k2):
                edges.add((t1, t2))
    return edges


def serial_order(ops: list[Op]) -> list[int] | None:
    """A topological order of the precedence graph (smallest id first), or None if there is a cycle."""
    nodes = sorted({t for _, _, t, _ in _data_ops(ops)})
    edges = conflict_edges(ops)
    indeg = {n: 0 for n in nodes}
    for _, b in edges:
        indeg[b] += 1
    order: list[int] = []
    ready = sorted(n for n in nodes if indeg[n] == 0)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for a, b in sorted(edges):
            if a == n:
                indeg[b] -= 1
                if indeg[b] == 0:
                    ready.append(b)
        ready.sort()
    return order if len(order) == len(nodes) else None


def is_conflict_serializable(ops: list[Op]) -> bool:
    return serial_order(ops) is not None


def _view(ops: list[tuple[str, int, str]]) -> tuple[frozenset, frozenset]:
    last: dict[str, int | None] = {}
    reads: list[tuple[int, str, int | None, int]] = []
    count: dict[tuple[int, str], int] = {}
    for k, t, x in ops:
        if k == "R":
            n = count[(t, x)] = count.get((t, x), 0) + 1
            reads.append((t, x, last.get(x), n))
        else:
            last[x] = t
    return frozenset(reads), frozenset(last.items())


def is_view_serializable(ops: list[Op]) -> bool:
    data = [(k, t, x) for _, k, t, x in _data_ops(ops)]
    txns = sorted({t for _, t, _ in data})
    if len(txns) > 6:
        raise ValueError("too many transactions for the brute-force view check")
    target = _view(data)
    return any(_view([o for t in perm for o in data if o[1] == t]) == target for perm in permutations(txns))


def _positions(ops: list[Op]) -> tuple[dict[int, int], dict[int, int]]:
    commit = {t: i for i, (k, t, _) in enumerate(ops) if k == "C"}
    abort = {t: i for i, (k, t, _) in enumerate(ops) if k == "A"}
    return commit, abort


def reads_from(ops: list[Op]) -> list[tuple[int, int, int]]:
    """(reader, writer, read_position) for every read of an item last written by ANOTHER transaction."""
    last: dict[str, int] = {}
    out = []
    for i, (k, t, x) in enumerate(ops):
        if k == "W":
            last[x] = t
        elif k == "R" and x in last and last[x] != t:
            out.append((t, last[x], i))
    return out


def recoverability_class(ops: list[Op]) -> str:
    commit, abort = _positions(ops)
    rf = reads_from(ops)
    recoverable = all(not (rd in commit and (wr in abort or wr not in commit or commit[wr] > commit[rd])) for rd, wr, _ in rf)
    if not recoverable:
        return "Not recoverable"
    cascadeless = all(wr in commit and commit[wr] < pos for _, wr, pos in rf)
    if not cascadeless:
        return "Recoverable but not cascadeless"
    last: dict[str, int] = {}
    strict = True
    for i, (k, t, x) in enumerate(ops):
        if k in "RW":
            w = last.get(x)
            if w is not None and w != t:
                done = commit.get(w, 10**9) < i or abort.get(w, 10**9) < i
                strict = strict and done
            if k == "W":
                last[x] = t
    return "Strict" if strict else "Cascadeless but not strict"


def cascade_victims(ops: list[Op], aborted: int) -> list[int]:
    """Transactions that must roll back (transitively) because they read data written by `aborted` before it ended."""
    commit, abort = _positions(ops)
    cut = abort.get(aborted, len(ops))
    victims = {aborted}
    last: dict[str, int] = {}
    for i, (k, t, x) in enumerate(ops[:cut]):
        if k == "W":
            last[x] = t
        elif k == "R" and last.get(x) in victims and t not in victims and commit.get(last[x], 10**9) > i:
            victims.add(t)
    return sorted(victims - {aborted})


def is_two_phase(ops: list[Op]) -> bool:
    shrinking: set[int] = set()
    for k, t, _ in ops:
        if k == "U":
            shrinking.add(t)
        elif k in "SX" and t in shrinking:
            return False
    return True


def lock_deadlock(ops: list[Op]) -> list[int] | None:
    """Simulate S/X lock requests in order; return the transactions in a wait-for cycle, or None."""
    held: dict[str, dict[int, str]] = {}
    waiting: dict[int, tuple[str, str]] = {}  # txn -> (mode, item) pending

    def blockers(t: int, mode: str, item: str) -> set[int]:
        return {o for o, m in held.get(item, {}).items() if o != t and (mode == "X" or m == "X")}

    def retry() -> None:
        progressed = True
        while progressed:
            progressed = False
            for t, (mode, item) in list(waiting.items()):
                if not blockers(t, mode, item):
                    held.setdefault(item, {})[t] = mode if held.get(item, {}).get(t) != "X" else "X"
                    del waiting[t]
                    progressed = True

    for k, t, x in ops:
        if t in waiting:
            continue
        if k in "SX":
            if blockers(t, k, x):
                waiting[t] = (k, x)
            else:
                cur = held.setdefault(x, {})
                cur[t] = "X" if (k == "X" or cur.get(t) == "X") else "S"
        elif k == "U":
            held.get(x, {}).pop(t, None)
            retry()
    graph = {t: blockers(t, m, x) for t, (m, x) in waiting.items()}
    for start in sorted(graph):
        path, node = [], start
        seen: dict[int, int] = {}
        while node in graph and node not in seen:
            seen[node] = len(path)
            path.append(node)
            nxt = sorted(graph[node] & set(graph))
            if not nxt:
                break
            node = nxt[0]
        if node in seen:
            return sorted(path[seen[node]:])
    return None


# SQL-standard isolation levels: which anomalies are POSSIBLE (real products may be stricter; see questions' dialect notes).
ISOLATION = {
    "read uncommitted": {"dirty read": True, "non-repeatable read": True, "phantom read": True},
    "read committed": {"dirty read": False, "non-repeatable read": True, "phantom read": True},
    "repeatable read": {"dirty read": False, "non-repeatable read": False, "phantom read": True},
    "serializable": {"dirty read": False, "non-repeatable read": False, "phantom read": False},
}


def isolation_allows(level: str, anomaly: str) -> bool:
    return ISOLATION[level.lower()][anomaly.lower()]


def serial_schedule_count(n: int) -> int:
    return factorial(n)


def interleaving_count(lengths: list[int]) -> int:
    total = factorial(sum(lengths))
    for n in lengths:
        total //= factorial(n)
    return total
