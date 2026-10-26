"""
Reference computations that VERIFY multiple-choice and short-answer keys (Phase 25).

A question's verification block names a `kind` and `params`; the computed string must equal the marked option (and no
other option). Everything here is deterministic Python (or the read-only SQL sandbox); no AI is ever consulted.
"""

from __future__ import annotations

from typing import Any, Callable

from app.services.dbms_sql import design_algos as D
from app.services.dbms_sql import txn_algos as T


class UnknownReference(ValueError):
    pass


def _fds(p: dict[str, Any]) -> list[D.FD]:
    return D.parse_fds(p["fds"])


def _r(p: dict[str, Any]) -> frozenset[str]:
    return D.attrs(p["attrs"])


def _yn(v: bool) -> str:
    return "Yes" if v else "No"


def _hash_slot(p: dict[str, Any]) -> str:
    size, probe = int(p["size"]), p.get("probe", "linear")
    table: list[Any] = [None] * size
    chains: dict[int, list[int]] = {}
    for key in p["keys"]:
        h = key % size
        if probe == "chain":
            chains.setdefault(h, []).append(key)
            continue
        for i in range(size):
            slot = (h + (i if probe == "linear" else i * i)) % size
            if table[slot] is None:
                table[slot] = key
                break
    target = p["key"]
    if probe == "chain":
        return f"bucket {target % size}"
    return str(table.index(target))


def _sched(p: dict[str, Any]) -> list[T.Op]:
    return T.parse(p["schedule"])


def _order(p: dict[str, Any]) -> str:
    o = T.serial_order(_sched(p))
    return "Not serializable" if o is None else " → ".join(f"T{t}" for t in o)


def _victims(p: dict[str, Any]) -> str:
    v = T.cascade_victims(_sched(p), int(p["aborted"]))
    return ", ".join(f"T{t}" for t in v) if v else "None"


def _deadlock(p: dict[str, Any]) -> str:
    cyc = T.lock_deadlock(_sched(p))
    return "No deadlock" if cyc is None else "Deadlock: " + ", ".join(f"T{t}" for t in cyc)


def _mvd(p: dict[str, Any]) -> str:
    return "Holds" if D.mvd_holds(list(p["columns"]), [tuple(r) for r in p["rows"]], D.attrs(p["x"]), D.attrs(p["y"])) else "Does not hold"


def _nf4(p: dict[str, Any]) -> str:
    bad = D.fourth_nf_violations(_r(p), _fds(p) if p.get("fds") else [], D.parse_fds(p.get("mvds", "").replace("->>", "->")))
    return "In 4NF" if not bad else "Not in 4NF"


KINDS: dict[str, Callable[[dict[str, Any]], str]] = {
    "closure": lambda p: D.fmt_set(D.closure(D.attrs(p["x"]), _fds(p))),
    "candidate_keys": lambda p: D.fmt_keys(D.candidate_keys(_r(p), _fds(p))),
    "prime_attributes": lambda p: D.fmt_set(D.prime_attributes(_r(p), _fds(p))),
    "highest_nf": lambda p: D.highest_normal_form(_r(p), _fds(p)),
    "is_superkey": lambda p: _yn(D.is_superkey(D.attrs(p["x"]), _r(p), _fds(p))),
    "is_bcnf": lambda p: _yn(D.is_bcnf(_r(p), _fds(p))),
    "is_3nf": lambda p: _yn(D.is_3nf(_r(p), _fds(p))),
    "is_2nf": lambda p: _yn(D.is_2nf(_r(p), _fds(p))),
    "lossless": lambda p: "Lossless" if D.is_lossless(_r(p), [D.attrs(x) for x in p["decomp"]], _fds(p)) else "Lossy",
    "dep_preserving": lambda p: "Preserved" if D.preserves_dependencies(_r(p), [D.attrs(x) for x in p["decomp"]], _fds(p)) else "Not preserved",
    "mvd_holds": _mvd,
    "in_4nf": _nf4,
    "conflict_serializable": lambda p: _yn(T.is_conflict_serializable(_sched(p))),
    "serial_order": _order,
    "view_serializable": lambda p: _yn(T.is_view_serializable(_sched(p))),
    "recoverability": lambda p: T.recoverability_class(_sched(p)),
    "cascade_victims": _victims,
    "two_phase": lambda p: _yn(T.is_two_phase(_sched(p))),
    "deadlock": _deadlock,
    "isolation_allows": lambda p: "Possible" if T.isolation_allows(p["level"], p["anomaly"]) else "Not possible",
    "serial_count": lambda p: str(T.serial_schedule_count(int(p["n"]))),
    "interleavings": lambda p: str(T.interleaving_count([int(x) for x in p["lengths"]])),
    "hash_slot": _hash_slot,
    "arithmetic": lambda p: str(int(p["value"])),
}


def run_reference(kind: str, params: dict[str, Any]) -> str:
    fn = KINDS.get(kind)
    if fn is None:
        raise UnknownReference(f"unknown reference kind '{kind}'")
    try:
        return str(fn(params))
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        raise UnknownReference(f"reference '{kind}' failed: {exc}") from exc
