"""
Independent answer verification by enumeration.

Content generators compute an answer with a textbook formula. Each verifier here recomputes the
same answer by a *different route* -- brute-force enumeration, `itertools`, Zeller's congruence,
exhaustive Venn-region models, a puzzle solver -- from the raw parameters stored on the question.
A question is only treated as verified when both routes agree and the agreed value matches the
correct option (see `validation.verify_question`).

Nothing here uses `eval`; every verifier is a plain function registered in VERIFIERS.
"""

from __future__ import annotations

import itertools
import math
from datetime import datetime, timedelta
from fractions import Fraction

COMPASS = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
WEEKDAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]  # Zeller order
WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class VerificationError(ValueError):
    """The parameters are inconsistent or the puzzle has no unique answer."""


# --- Number system -------------------------------------------------------------------------------


def _is_prime(n: int) -> bool:
    return n >= 2 and all(n % d for d in range(2, int(math.isqrt(n)) + 1))


def _divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


def _single_match(p):
    pred = p["predicate"]
    name = pred["name"]
    hits = []
    for cand in p["candidates"]:
        if name == "prime":
            ok = _is_prime(cand)
        elif name == "composite":
            ok = cand > 3 and not _is_prime(cand)
        elif name == "perfect":
            ok = sum(d for d in _divisors(cand) if d < cand) == cand
        elif name == "divisible":
            ok = cand % pred["by"] == 0
        elif name == "leap":
            ok = (cand % 4 == 0 and cand % 100 != 0) or cand % 400 == 0
        elif name == "coprime":
            ok = math.gcd(cand[0], cand[1]) == 1
        else:
            raise VerificationError(f"unknown predicate {name}")
        if ok:
            hits.append(cand)
    if len(hits) != 1:
        raise VerificationError(f"expected exactly one match, found {len(hits)}")
    hit = hits[0]
    return f"{hit[0]} and {hit[1]}" if isinstance(hit, list) else hit


def _missing_digit(p):
    hits = [d for d in range(10) if int(p["template"].replace("?", str(d))) % p["divisor"] == 0]
    if len(hits) != 1:
        raise VerificationError(f"digit not unique: {hits}")
    return hits[0]


def _trailing_zeros(p):
    s = str(math.factorial(p["n"]))
    return len(s) - len(s.rstrip("0"))


def _prime_power_in_factorial(p):
    value, count = math.factorial(p["n"]), 0
    while value % p["p"] == 0:
        value //= p["p"]
        count += 1
    return count


def _unit_digit_product(p):
    return math.prod(p["factors"]) % 10


def _least_with_remainder(p):
    n = p["remainder"] + 1
    while n < 10**7:
        if all(n % d == p["remainder"] for d in p["divisors"]):
            return n
        n += 1
    raise VerificationError("no solution in range")


def _hcf(p):
    nums = p["numbers"]
    return max(d for d in range(1, min(nums) + 1) if all(n % d == 0 for n in nums))


def _lcm(p):
    nums = p["numbers"]
    m = max(nums)
    k = m
    while k < 10**8:
        if all(k % n == 0 for n in nums):
            return k
        k += m
    raise VerificationError("lcm too large")


def _hcf_remainders(p):
    pairs = list(zip(p["numbers"], p["remainders"]))
    best = max(d for d in range(1, max(n for n, _ in pairs) + 1) if d > max(p["remainders"]) and all(n % d == r for n, r in pairs))
    return best


# --- Calendar and clocks -----------------------------------------------------------------------


def _zeller(y, m, d):
    if m < 3:
        m += 12
        y -= 1
    k, j = y % 100, y // 100
    h = (d + (13 * (m + 1)) // 5 + k + k // 4 + j // 4 + 5 * j) % 7
    return WEEKDAYS[h]


def _calendar_day(p):
    return _zeller(p["year"], p["month"], p["day"])


def _odd_days(p):
    leap = sum(1 for y in range(1, p["years"] + 1) if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0)
    return (p["years"] * 365 + leap) % 7


def _day_after(p):
    return WEEK_ORDER[(WEEK_ORDER.index(p["start_day"]) + p["days"]) % 7]


def _clock_angle(p):
    hour = (p["h"] % 12) * 30 + p["m"] * 0.5
    minute = p["m"] * 6
    diff = abs(hour - minute) % 360
    return min(diff, 360 - diff)


def _clock_overlap(p):
    for k in range(11):
        t = Fraction(720 * k, 11)  # minutes after 12:00 when the hands coincide
        hour = int(t // 60)
        if hour == p["h"] % 12:
            return float(t - 60 * hour)
    raise VerificationError("no overlap")


def _clock_event_count(p):
    # relative angle = 5.5 * t (degrees) for t in [0, 720) minutes
    count = 0
    for target in p["angles"]:
        for k in range(0, 20):
            t = Fraction(2 * (target + 360 * k), 11)
            if 0 <= t < 720:
                count += 1
    return count


def _mirror_time(p):
    total = (720 - (p["h"] % 12) * 60 - p["m"]) % 720
    hour = (total // 60) or 12
    return f"{hour}:{total % 60:02d}"


def _clock_gain(p):
    start = datetime(2001, 1, 1, p["start_hour"], 0)
    shown = start + timedelta(hours=p["true_hours"], minutes=p["gain_per_hour"] * p["true_hours"])
    hour = shown.hour % 12 or 12
    return f"{hour}:{shown.minute:02d} {'AM' if shown.hour < 12 else 'PM'}"


# --- Probability ------------------------------------------------------------------------------


def _fraction(num, den) -> Fraction:
    return Fraction(num, den)


def _coins(p):
    outcomes = list(itertools.product("HT", repeat=p["n"]))
    ev, k = p["event"], p.get("k", 0)
    def ok(o):
        heads = o.count("H")
        return {"exactly_heads": heads == k, "at_least_heads": heads >= k, "at_least_tails": o.count("T") >= k}[ev]
    return _fraction(sum(1 for o in outcomes if ok(o)), len(outcomes))


def _dice(p):
    outcomes = list(itertools.product(range(1, 7), repeat=2))
    ev, v = p["event"], p.get("v", 0)
    def ok(a, b):
        return {
            "sum_eq": a + b == v, "sum_ge": a + b >= v, "sum_le": a + b <= v,
            "sum_prime": _is_prime(a + b), "product_even": (a * b) % 2 == 0,
            "doublet": a == b, "product_eq": a * b == v, "differ_by": abs(a - b) == v,
        }[ev]
    return _fraction(sum(1 for a, b in outcomes if ok(a, b)), len(outcomes))


def _deck():
    return [(rank, suit) for suit in "SHDC" for rank in ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]]


def _cards(p):
    deck, ev = _deck(), p["event"]
    face = {"J", "Q", "K"}
    if ev == "two_aces":
        pairs = list(itertools.combinations(deck, 2))
        return _fraction(sum(1 for a, b in pairs if a[0] == "A" and b[0] == "A"), len(pairs))
    def ok(c):
        return {
            "ranks": c[0] in p.get("ranks", []),
            "red_face": c[1] in "HD" and c[0] in face,
            "heart_or_king": c[1] == "H" or c[0] == "K",
            "spade_or_face": c[1] == "S" or c[0] in face,
            "black_non_face": c[1] in "SC" and c[0] not in face,
            "ace_of_hearts_or_kings": (c[0] == "A" and c[1] == "H") or c[0] == "K",
        }[ev]
    return _fraction(sum(1 for c in deck if ok(c)), len(deck))


def _conditional(p):
    case = p["case"]
    if case == "bag_both_red":
        balls = ["R"] * p["red"] + ["B"] * p["blue"]
        draws = list(itertools.permutations(range(len(balls)), 2))
        return _fraction(sum(1 for i, j in draws if balls[i] == "R" and balls[j] == "R"), len(draws))
    if case == "die_given_even":
        given = [x for x in range(1, 7) if x % 2 == 0]
        return _fraction(sum(1 for x in given if x > p["greater_than"]), len(given))
    if case == "two_children_boy":
        given = [c for c in itertools.product("BG", repeat=2) if "B" in c]
        return _fraction(sum(1 for c in given if c == ("B", "B")), len(given))
    if case == "second_ace_given_first":
        deck = _deck()
        pairs = [(a, b) for a, b in itertools.permutations(range(52), 2) if deck[a][0] == "A"]
        return _fraction(sum(1 for a, b in pairs if deck[b][0] == "A"), len(pairs))
    if case == "bayes_defective":
        # machines A, B produce `share` of items with `defect` rates; P(machine A | defective)
        total = sum(s * d for s, d in zip(p["shares"], p["defects"]))
        return Fraction(p["shares"][0] * p["defects"][0]).limit_denominator(10**6) / Fraction(total).limit_denominator(10**6)
    raise VerificationError(f"unknown conditional case {case}")


# --- Series and coding ------------------------------------------------------------------------


def _letter(i: int) -> str:
    return chr(ord("A") + (i - 1) % 26)


def _series_terms(rule: dict, count: int) -> list:
    t = rule["type"]
    if t == "arith":
        return [rule["a"] + rule["d"] * i for i in range(count)]
    if t == "geom":
        return [rule["a"] * rule["r"] ** i for i in range(count)]
    if t == "affine":
        out = [rule["a"]]
        while len(out) < count:
            out.append(out[-1] * rule["m"] + rule["c"])
        return out
    if t == "square_plus":
        return [(i + rule.get("from", 1)) ** 2 + rule["c"] for i in range(count)]
    if t == "pronic":
        return [(i + 1) * (i + 2) for i in range(count)]
    if t == "fib":
        out = [rule["a"], rule["b"]]
        while len(out) < count:
            out.append(out[-1] + out[-2])
        return out[:count]
    if t == "primes":
        out, n = [], 2
        while len(out) < count:
            if _is_prime(n):
                out.append(n)
            n += 1
        return out
    if t == "diff_step":
        out, d = [rule["a"]], rule["d0"]
        while len(out) < count:
            out.append(out[-1] + d)
            d += rule["step"]
        return out
    if t == "cubes_plus":
        return [(i + 1) ** 3 + rule["c"] for i in range(count)]
    raise VerificationError(f"unknown series rule {t}")


def _series_next(p):
    terms = _series_terms(p["rule"], p["shown"] + 1)
    if terms[: p["shown"]] != p["terms"]:
        raise VerificationError("displayed terms do not follow the rule")
    return terms[p["shown"]]


def _alpha_stepped(p):
    idx, out = p["start"], []
    for step in p["steps"]:
        out.append(idx)
        idx += step
    out.append(idx)
    letters = [_letter(i) for i in out]
    if letters[: p["shown"]] != p["terms"]:
        raise VerificationError("displayed letters do not follow the steps")
    return letters[p["shown"]]


def _alpha_multi(p):
    terms = ["".join(_letter(s + d * i) for s, d in zip(p["starts"], p["deltas"])) for i in range(p["shown"] + 1)]
    if terms[: p["shown"]] != p["terms"]:
        raise VerificationError("displayed terms do not follow the rule")
    return terms[p["shown"]]


def _alnum_series(p):
    def number(i):
        r = p["num"]
        return {"arith": lambda: r["a"] + r["d"] * i, "scaled_square": lambda: r["k"] * (i + 1) ** 2}[r["type"]]()
    terms = ["".join(_letter(s + d * i) for s, d in zip(p["starts"], p["deltas"])) + str(number(i)) for i in range(p["shown"] + 1)]
    if terms[: p["shown"]] != p["terms"]:
        raise VerificationError("displayed terms do not follow the rule")
    return terms[p["shown"]]


def _shift_word(word: str, shift: int) -> str:
    return "".join(_letter(ord(c) - 64 + shift) for c in word)


def _caesar(p):
    return _shift_word(p["word"], p["shift"])


def _reverse_shift(p):
    return _shift_word(p["word"][::-1], p["shift"])


def _atbash(p):
    return "".join(chr(ord("A") + 25 - (ord(c) - 65)) for c in p["word"])


def _sum_code(p):
    return sum(ord(c) - 64 for c in p["word"])


def _alpha_position(p):
    op = p["op"]
    if op == "sorted_kth":
        return sorted(p["word"])[p["k"] - 1]
    if op == "offset":
        return _letter(p["start_pos"] + p["offset"])
    if op == "reverse_alphabet_kth":
        return _letter(27 - p["k"])
    if op == "between":
        a, b = sorted((ord(p["a"]) - 64, ord(p["b"]) - 64))
        return b - a - 1
    raise VerificationError(f"unknown alpha op {op}")


def _language_code(p):
    meanings = sorted({m for _, ms in p["statements"] for m in ms})
    codes = sorted({c for cs, _ in p["statements"] for c in cs})
    if len(meanings) != len(codes):
        raise VerificationError("meaning/code counts differ")
    answers = set()
    for perm in itertools.permutations(codes):
        mapping = dict(zip(meanings, perm))
        if all({mapping[m] for m in ms} == set(cs) for cs, ms in p["statements"]):
            answers.add(mapping[p["query"]])
    if len(answers) != 1:
        raise VerificationError(f"language code not unique: {answers}")
    return answers.pop()


# --- Direction sense, number tests, ranking ------------------------------------------------------

_VEC = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
_ORDER = ["N", "E", "S", "W"]


def _compass_from_vector(dx, dy):
    if dx == 0 and dy == 0:
        return "Starting point"
    angle = math.degrees(math.atan2(dx, dy)) % 360
    return COMPASS[int(round(angle / 45)) % 8]


def _walk(p):
    heading, x, y = _ORDER.index(p["start"]), 0.0, 0.0
    for turn, dist in p["moves"]:
        if turn == "R":
            heading = (heading + 1) % 4
        elif turn == "L":
            heading = (heading - 1) % 4
        elif turn == "B":
            heading = (heading + 2) % 4
        dx, dy = _VEC[_ORDER[heading]]
        x, y = x + dx * dist, y + dy * dist
    return round(math.hypot(x, y), 6) if p["ask"] == "distance" else _compass_from_vector(round(x, 6), round(y, 6))


def _turn_heading(p):
    angle = {"N": 0, "E": 90, "S": 180, "W": 270, "NE": 45, "SE": 135, "SW": 225, "NW": 315}[p["start"]]
    for t in p["turns"]:
        angle = (angle + t) % 360
    return COMPASS[angle // 45]


def _number_test(p):
    op, seq = p["op"], p["sequence"]
    if op == "count_followed_by":
        pred = {"even": lambda n: n % 2 == 0, "odd": lambda n: n % 2 == 1}[p["next"]]
        return sum(1 for i in range(len(seq) - 1) if seq[i] == p["target"] and pred(seq[i + 1]))
    if op == "count_preceded_not_followed":
        return sum(
            1 for i in range(1, len(seq))
            if seq[i] == p["target"] and seq[i - 1] == p["before"] and not (i + 1 < len(seq) and seq[i + 1] == p["after"])
        )
    if op == "kth_digit_sorted":
        return sorted(int(c) for c in str(p["number"]))[p["k"] - 1]
    if op == "odd_even_diff":
        digits = [int(c) for c in str(p["number"])]
        return abs(sum(d for d in digits if d % 2) - sum(d for d in digits if d % 2 == 0))
    if op == "largest_minus_smallest":
        perms = {int("".join(q)) for q in itertools.permutations(str(p["number"]))}
        return max(perms) - min(perms)
    raise VerificationError(f"unknown number test {op}")


# --- Syllogism ---------------------------------------------------------------------------------


def _holds(stmt, occupied, idx):
    kind, x, y = stmt
    xi, yi = idx[x], idx[y]
    if kind == "A":  # All x are y
        return all(r[yi] for r in occupied if r[xi])
    if kind == "E":  # No x is y
        return not any(r[xi] and r[yi] for r in occupied)
    if kind == "I":  # Some x are y
        return any(r[xi] and r[yi] for r in occupied)
    if kind == "O":  # Some x are not y
        return any(r[xi] and not r[yi] for r in occupied)
    raise VerificationError(f"unknown statement type {kind}")


LABELS = {
    (True, False): "Only conclusion I follows",
    (False, True): "Only conclusion II follows",
    (True, True): "Both conclusions I and II follow",
    (False, False): "Neither conclusion I nor II follows",
}
POSSIBLE_LABELS = {
    (True, False): "Only conclusion I is possible",
    (False, True): "Only conclusion II is possible",
    (True, True): "Both conclusions I and II are possible",
    (False, False): "Neither conclusion I nor II is possible",
}


def _syllogism(p):
    sets = p["sets"]
    idx = {s: i for i, s in enumerate(sets)}
    regions = list(itertools.product([False, True], repeat=len(sets)))
    models = []
    for mask in range(1, 2 ** len(regions)):
        occupied = [r for i, r in enumerate(regions) if mask >> i & 1]
        if not all(any(r[i] for r in occupied) for i in range(len(sets))):
            continue  # every named group has at least one member
        if all(_holds(s, occupied, idx) for s in p["premises"]):
            models.append(occupied)
    if not models:
        raise VerificationError("premises are contradictory")
    if p["mode"] == "follows":
        flags = tuple(all(_holds(c, m, idx) for m in models) for c in p["conclusions"])
        return LABELS[flags]
    flags = tuple(any(_holds(c, m, idx) for m in models) for c in p["conclusions"])
    return POSSIBLE_LABELS[flags]


# --- Counting ---------------------------------------------------------------------------------


def _count_numbers(p):
    total = 0
    for combo in (itertools.product(p["digits"], repeat=p["length"]) if p["repeat"] else itertools.permutations(p["digits"], p["length"])):
        if combo[0] == "0" and not p.get("leading_zero", False):
            continue
        if p.get("even") and int(combo[-1]) % 2:
            continue
        total += 1
    return total


def _committee(p):
    people = [("M", i) for i in range(p["men"])] + [("W", i) for i in range(p["women"])]
    return sum(1 for c in itertools.combinations(people, p["size"]) if sum(1 for x in c if x[0] == "W") >= p["min_women"])


def _arrangements(p):
    word, vowels = p["word"], set("AEIOU")
    perms = set(itertools.permutations(word))
    if p.get("constraint") == "vowels_together":
        def together(w):
            pos = [i for i, c in enumerate(w) if c in vowels]
            return pos == list(range(pos[0], pos[0] + len(pos)))
        return sum(1 for w in perms if together(w))
    return len(perms)


def _word_rank(p):
    return sorted({"".join(q) for q in itertools.permutations(p["word"])}).index(p["word"]) + 1


def _distribute_identical(p):
    return sum(
        1 for combo in itertools.product(range(p["items"] + 1), repeat=p["boxes"])
        if sum(combo) == p["items"] and all(c >= p.get("min_each", 0) for c in combo)
    )


def _functions_count(p):
    return sum(1 for _ in itertools.product(range(p["boxes"]), repeat=p["items"]))


def _triangles(p):
    collinear = set(range(p["collinear"]))
    return sum(1 for t in itertools.combinations(range(p["points"]), 3) if not set(t) <= collinear)


def _diagonals(p):
    n = p["n"]
    return sum(1 for a, b in itertools.combinations(range(n), 2) if (b - a) % n not in (1, n - 1))


def _grid_rectangles(p):
    n = p["n"] + 1
    return len(list(itertools.combinations(range(n), 2))) ** 2


def _circular(p):
    n = p["n"]
    count = 0
    for rest in itertools.permutations(range(1, n)):
        arr = (0,) + rest
        pos = {person: i for i, person in enumerate(arr)}
        ok = True
        cons = p.get("constraint")
        if cons == "together":
            a, b = p["pair"]
            ok = (pos[a] - pos[b]) % n in (1, n - 1)
        elif cons == "apart":
            a, b = p["pair"]
            ok = (pos[a] - pos[b]) % n not in (1, n - 1)
        if ok:
            count += 1
    return count


def _necklace(p):
    n, seen = p["n"], set()
    for rest in itertools.permutations(range(1, n)):
        arr = (0,) + rest
        mirror = (0,) + tuple(reversed(rest))
        seen.add(min(arr, mirror))
    return len(seen)


# --- Seating -----------------------------------------------------------------------------------


def _seat_ok_linear(order, constraints):
    pos = {person: i for i, person in enumerate(order)}
    n = len(order)
    for c in constraints:
        kind = c[0]
        if kind == "pos" and pos[c[1]] != c[2]:
            return False
        if kind == "immediate_left" and pos[c[1]] != pos[c[2]] - 1:
            return False
        if kind == "left_of" and not pos[c[1]] < pos[c[2]]:
            return False
        if kind == "adjacent" and abs(pos[c[1]] - pos[c[2]]) != 1:
            return False
        if kind == "not_adjacent" and abs(pos[c[1]] - pos[c[2]]) == 1:
            return False
        if kind == "end" and pos[c[1]] not in (0, n - 1):
            return False
        if kind == "between" and not (min(pos[c[2]], pos[c[3]]) < pos[c[1]] < max(pos[c[2]], pos[c[3]])):
            return False
    return True


def _seating_linear(p):
    answers, found = set(), 0
    for order in itertools.permutations(p["people"]):
        if _seat_ok_linear(order, p["constraints"]):
            found += 1
            ask = p["ask"]
            answers.add(order[ask["pos"]] if ask["type"] == "who_at" else order.index(ask["person"]) + 1)
    if found == 0 or len(answers) != 1:
        raise VerificationError(f"linear seating not unique ({found} arrangements, answers {answers})")
    return answers.pop()


def _seat_ok_circular(order, constraints):
    # Seats are numbered clockwise, everyone faces the centre: the clockwise neighbour is on
    # the person's LEFT, so an "immediate right" is the anticlockwise neighbour (index - 1).
    n = len(order)
    pos = {person: i for i, person in enumerate(order)}
    for c in constraints:
        kind = c[0]
        if kind == "opposite" and (pos[c[1]] - pos[c[2]]) % n != n // 2:
            return False
        if kind == "immediate_right" and pos[c[1]] != (pos[c[2]] - 1) % n:
            return False
        if kind == "immediate_left" and pos[c[1]] != (pos[c[2]] + 1) % n:
            return False
        if kind == "adjacent" and (pos[c[1]] - pos[c[2]]) % n not in (1, n - 1):
            return False
        if kind == "not_adjacent" and (pos[c[1]] - pos[c[2]]) % n in (1, n - 1):
            return False
        if kind == "second_right" and pos[c[1]] != (pos[c[2]] - 2) % n:
            return False
    return True


def _seating_circular(p):
    people = p["people"]
    answers, found = set(), 0
    for rest in itertools.permutations(people[1:]):
        order = (people[0],) + rest
        if _seat_ok_circular(order, p["constraints"]):
            found += 1
            n, pos, ask = len(order), {x: i for i, x in enumerate(order)}, p["ask"]
            if ask["type"] == "opposite":
                answers.add(order[(pos[ask["person"]] + n // 2) % n])
            elif ask["type"] == "immediate_right":
                answers.add(order[(pos[ask["person"]] - 1) % n])
            elif ask["type"] == "immediate_left":
                answers.add(order[(pos[ask["person"]] + 1) % n])
    if found == 0 or len(answers) != 1:
        raise VerificationError(f"circular seating not unique ({found} arrangements, answers {answers})")
    return answers.pop()


# --- Data sufficiency -----------------------------------------------------------------------


def _ds_constraint(c, env):
    kind = c["kind"]
    if kind == "linear":
        total = sum(coef * env[v] for v, coef in c["coeffs"].items())
        return {"==": total == c["rhs"], "<=": total <= c["rhs"], ">=": total >= c["rhs"]}[c["op"]]
    if kind == "multiple_of":
        return env[c["var"]] % c["k"] == 0
    if kind == "product":
        return env[c["a"]] * env[c["b"]] == c["rhs"]
    raise VerificationError(f"unknown constraint {kind}")


def _ds_target_values(target, env):
    if target["type"] == "value":
        return env[target["var"]]
    pred = target["predicate"]
    if pred == "even":
        return env[target["var"]] % 2 == 0
    if pred == "gt":
        return env[target["a"]] > env[target["b"]]
    raise VerificationError(f"unknown predicate {pred}")


def _data_sufficiency(p):
    names = p["vars"]
    lo, hi = p["domain"]
    sets: dict[str, set] = {"I": set(), "II": set(), "both": set()}
    for values in itertools.product(range(lo, hi + 1), repeat=len(names)):
        env = dict(zip(names, values))
        s1 = _ds_constraint(p["statements"][0], env)
        s2 = _ds_constraint(p["statements"][1], env)
        out = _ds_target_values(p["target"], env)
        if s1:
            sets["I"].add(out)
        if s2:
            sets["II"].add(out)
        if s1 and s2:
            sets["both"].add(out)
    if not sets["both"]:
        raise VerificationError("statements are contradictory in the domain")
    suff = {k: len(v) == 1 for k, v in sets.items()}
    if suff["I"] and suff["II"]:
        raise VerificationError("each statement alone is sufficient; not one of the four supported answers")
    if suff["I"]:
        return "Statement I alone is sufficient"
    if suff["II"]:
        return "Statement II alone is sufficient"
    if suff["both"]:
        return "Both statements together are sufficient, but neither alone is"
    return "Neither alone nor both together is sufficient"


# --- Data interpretation lookups --------------------------------------------------------------


def _unique_argmax(labels, scores):
    best = max(scores)
    winners = [lab for lab, sc in zip(labels, scores) if abs(sc - best) < 1e-9]
    if len(winners) != 1:
        raise VerificationError(f"maximum is not unique: {winners}")
    return winners[0]


def _di_argmax_ratio(p):
    return _unique_argmax(p["labels"], [n / d for n, d in zip(p["num"], p["den"])])


def _di_argmax_growth(p):
    v = p["values"]
    return _unique_argmax(p["labels"][1:], [(v[i] - v[i - 1]) / v[i - 1] for i in range(1, len(v))])


def _di_argmax_sum(p):
    return _unique_argmax(p["labels"], [sum(col) for col in p["columns"]])


VERIFIERS = {
    "di_argmax_ratio": _di_argmax_ratio, "di_argmax_growth": _di_argmax_growth, "di_argmax_sum": _di_argmax_sum,
    "single_match": _single_match, "missing_digit": _missing_digit, "trailing_zeros": _trailing_zeros,
    "prime_power_in_factorial": _prime_power_in_factorial,
    "unit_digit": lambda p: pow(p["base"], p["exp"], 10), "unit_digit_product": _unit_digit_product,
    "factor_count": lambda p: len(_divisors(p["n"])), "factor_sum": lambda p: sum(_divisors(p["n"])),
    "odd_factor_count": lambda p: sum(1 for d in _divisors(p["n"]) if d % 2),
    "factor_pair_count": lambda p: sum(1 for d in _divisors(p["n"]) if d * d <= p["n"]),
    "powmod": lambda p: pow(p["base"], p["exp"], p["mod"]), "mod_value": lambda p: p["n"] % p["mod"],
    "count_primes_range": lambda p: sum(1 for n in range(p["lo"], p["hi"] + 1) if _is_prime(n)),
    "least_with_remainder": _least_with_remainder, "hcf": _hcf, "lcm": _lcm, "hcf_remainders": _hcf_remainders,
    "calendar_day": _calendar_day, "odd_days": _odd_days, "day_after": _day_after,
    "clock_angle": _clock_angle, "clock_overlap": _clock_overlap, "clock_event_count": _clock_event_count,
    "mirror_time": _mirror_time, "clock_gain": _clock_gain,
    "coins": _coins, "dice": _dice, "cards": _cards, "conditional": _conditional,
    "series_next": _series_next, "alpha_stepped": _alpha_stepped, "alpha_multi": _alpha_multi,
    "alnum_series": _alnum_series, "caesar": _caesar, "reverse_shift": _reverse_shift, "atbash": _atbash,
    "sum_code": _sum_code, "alpha_position": _alpha_position, "language_code": _language_code,
    "walk": _walk, "turn_heading": _turn_heading, "number_test": _number_test, "syllogism": _syllogism,
    "count_numbers": _count_numbers, "committee": _committee, "arrangements": _arrangements,
    "word_rank": _word_rank, "distribute_identical": _distribute_identical, "functions_count": _functions_count,
    "triangles": _triangles, "diagonals": _diagonals, "grid_rectangles": _grid_rectangles,
    "circular": _circular, "necklace": _necklace,
    "seating_linear": _seating_linear, "seating_circular": _seating_circular,
    "data_sufficiency": _data_sufficiency,
}


def run_verifier(kind: str, params: dict):
    """Recompute the expected answer; Fractions become floats so they compare with parsed options."""
    if kind not in VERIFIERS:
        raise VerificationError(f"unknown verifier kind '{kind}'")
    value = VERIFIERS[kind](params)
    return float(value) if isinstance(value, Fraction) else value
