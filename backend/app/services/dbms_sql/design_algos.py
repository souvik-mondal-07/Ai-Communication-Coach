"""
Relational-design algorithms (Phase 25): attribute closure, keys, normal forms, lossless-join and dependency preservation,
multivalued dependencies. Pure Python, single-letter attributes. They are used to VERIFY answer keys in the question bank
(never to ask an AI) and are unit-tested against textbook results.
"""

from __future__ import annotations

from itertools import combinations

FD = tuple[frozenset[str], frozenset[str]]


def attrs(text: str) -> frozenset[str]:
    return frozenset(ch for ch in text.upper() if ch.isalpha())


def parse_fds(text: str) -> list[FD]:
    """'A->B, BC->D' -> [({A},{B}), ({B,C},{D})]."""
    out: list[FD] = []
    for part in text.replace(";", ",").split(","):
        if "->" in part:
            left, right = part.split("->", 1)
            out.append((attrs(left), attrs(right)))
    return out


def closure(x: frozenset[str], fds: list[FD]) -> frozenset[str]:
    result = set(x)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            if lhs <= result and not rhs <= result:
                result |= rhs
                changed = True
    return frozenset(result)


def is_superkey(x: frozenset[str], relation: frozenset[str], fds: list[FD]) -> bool:
    return relation <= closure(x, fds)


def candidate_keys(relation: frozenset[str], fds: list[FD]) -> list[frozenset[str]]:
    letters = sorted(relation)
    keys: list[frozenset[str]] = []
    for size in range(1, len(letters) + 1):
        for combo in combinations(letters, size):
            c = frozenset(combo)
            if any(k <= c for k in keys):
                continue
            if is_superkey(c, relation, fds):
                keys.append(c)
    return keys


def prime_attributes(relation: frozenset[str], fds: list[FD]) -> frozenset[str]:
    return frozenset().union(*candidate_keys(relation, fds)) if fds or relation else frozenset()


def _nontrivial(fds: list[FD]) -> list[FD]:
    return [(l, r - l) for l, r in fds if r - l]


def is_bcnf(relation: frozenset[str], fds: list[FD]) -> bool:
    return all(is_superkey(l, relation, fds) for l, _ in _nontrivial(fds))


def is_3nf(relation: frozenset[str], fds: list[FD]) -> bool:
    prime = prime_attributes(relation, fds)
    return all(is_superkey(l, relation, fds) or r <= prime for l, r in _nontrivial(fds))


def is_2nf(relation: frozenset[str], fds: list[FD]) -> bool:
    prime = prime_attributes(relation, fds)
    for key in candidate_keys(relation, fds):
        letters = sorted(key)
        for size in range(1, len(letters)):
            for combo in combinations(letters, size):
                part = frozenset(combo)
                if (closure(part, fds) & relation) - part - prime:
                    return False
    return True


def highest_normal_form(relation: frozenset[str], fds: list[FD]) -> str:
    """Highest of 1NF/2NF/3NF/BCNF assuming atomic values (1NF). Uses implied FDs for 2NF, the given FDs for 3NF/BCNF."""
    if is_bcnf(relation, fds):
        return "BCNF"
    if is_3nf(relation, fds):
        return "3NF"
    if is_2nf(relation, fds):
        return "2NF"
    return "1NF"


def project_fds(sub: frozenset[str], fds: list[FD]) -> list[FD]:
    out: list[FD] = []
    letters = sorted(sub)
    for size in range(1, len(letters) + 1):
        for combo in combinations(letters, size):
            x = frozenset(combo)
            rhs = (closure(x, fds) & sub) - x
            if rhs:
                out.append((x, rhs))
    return out


def is_lossless(relation: frozenset[str], decomposition: list[frozenset[str]], fds: list[FD]) -> bool:
    """Tableau (chase) test for lossless-join decomposition."""
    cols = sorted(relation)
    table = [{a: (f"a_{a}" if a in part else f"b_{i}_{a}") for a in cols} for i, part in enumerate(decomposition)]
    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            for r1, r2 in combinations(table, 2):
                if all(r1[a] == r2[a] for a in lhs):
                    for a in rhs:
                        if r1[a] != r2[a]:
                            keep = r1[a] if r1[a].startswith("a_") else r2[a]
                            drop = r2[a] if keep == r1[a] else r1[a]
                            for row in table:
                                if row[a] == drop:
                                    row[a] = keep
                            changed = True
    return any(all(row[a].startswith("a_") for a in cols) for row in table)


def preserves_dependencies(relation: frozenset[str], decomposition: list[frozenset[str]], fds: list[FD]) -> bool:
    for lhs, rhs in fds:
        z = set(lhs)
        grew = True
        while grew:
            grew = False
            for part in decomposition:
                add = closure(frozenset(z) & part, fds) & part
                if not add <= z:
                    z |= add
                    grew = True
        if not rhs <= z:
            return False
    return True


def mvd_holds(columns: list[str], rows: list[tuple], x: frozenset[str], y: frozenset[str]) -> bool:
    """Does X ->> Y hold in this relation INSTANCE? (swap Y between every pair of tuples that agree on X)."""
    idx = {c.upper(): i for i, c in enumerate(columns)}
    xi = [idx[a] for a in sorted(x)]
    yi = [idx[a] for a in sorted(y - x)]
    zi = [i for i in range(len(columns)) if i not in xi and i not in yi]
    have = {tuple(r) for r in rows}
    for t1 in rows:
        for t2 in rows:
            if all(t1[i] == t2[i] for i in xi):
                t3 = list(t2)
                for i in yi:
                    t3[i] = t1[i]
                for i in zi:
                    t3[i] = t2[i]
                if tuple(t3) not in have:
                    return False
    return True


def fourth_nf_violations(relation: frozenset[str], fds: list[FD], mvds: list[FD]) -> list[FD]:
    """Nontrivial dependencies (given MVDs and FDs, since every FD is an MVD) whose left side is not a superkey."""
    bad: list[FD] = []
    for lhs, rhs in list(mvds) + list(fds):
        y = rhs - lhs
        if not y or (lhs | rhs) == relation:
            continue
        if not is_superkey(lhs, relation, fds):
            bad.append((lhs, rhs))
    return bad


def fmt_set(s: frozenset[str]) -> str:
    return "{" + ", ".join(sorted(s)) + "}"


def fmt_keys(keys: list[frozenset[str]]) -> str:
    return ", ".join(fmt_set(k) for k in sorted(keys, key=lambda k: ("".join(sorted(k)))))
