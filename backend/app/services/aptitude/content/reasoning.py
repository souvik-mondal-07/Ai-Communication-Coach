"""Topics F, L, O, P, X: Logical Reasoning, Analytical Reasoning, Syllogism, Number Ranking, Seating."""

from __future__ import annotations

from .build import E, M, X, fnum, mk
from ..verifiers import LABELS, POSSIBLE_LABELS, _letter, _series_terms

OPTS_FOLLOW = list(LABELS.values())
OPTS_POSSIBLE = list(POSSIBLE_LABELS.values())


def _wrong_numbers(ans, extra=()):
    base = [ans + 2, ans - 2, ans + 5, ans - 3, ans + 10, ans * 2]
    return [w for w in list(extra) + base if w != ans]


def logical():
    out = []
    sub = "number-series"
    specs = [
        ({"type": "pronic"}, 5, "easy", "Each term is n(n + 1): 1×2, 2×3, 3×4, 4×5, 5×6, so the next is 6 × 7."),
        ({"type": "geom", "a": 3, "r": 2}, 5, "easy", "Each term is double the previous one."),
        ({"type": "affine", "a": 5, "m": 2, "c": 1}, 5, "medium", "Each term = previous × 2 + 1."),
        ({"type": "primes"}, 6, "easy", "These are consecutive prime numbers."),
        ({"type": "fib", "a": 1, "b": 1}, 6, "medium", "Each term is the sum of the previous two (Fibonacci)."),
        ({"type": "diff_step", "a": 100, "d0": -9, "step": 1}, 5, "medium", "Differences are −9, −8, −7, −6, so the next difference is −5."),
        ({"type": "square_plus", "c": 1}, 5, "medium", "Terms are n² + 1: 2, 5, 10, 17, 26, so the next is 6² + 1."),
        ({"type": "cubes_plus", "c": 1}, 5, "hard", "Terms are n³ + 1: 2, 9, 28, 65, 126, so the next is 6³ + 1."),
    ]
    for rule, shown, d, expl in specs:
        terms = _series_terms(rule, shown + 1)
        ans = terms[shown]
        shown_terms = terms[:shown]
        out.append(mk(sub, "Find the next term of the series: " + ", ".join(map(str, shown_terms)) + ", ?", ans, _wrong_numbers(ans, [ans + 1, ans - 1]), expl, d=d, t=40,
                      formula="Look at differences, ratios, squares/cubes, or two-step rules",
                      ver=E("series_next", ans, rule=rule, shown=shown, terms=shown_terms)))
    sub = "alphabet-series"
    for start, steps, shown, d, expl in ((1, [2, 3, 4, 5, 6], 5, "medium", "The gaps between letters grow 2, 3, 4, 5, so the next gap is 6."),
                                         (2, [3] * 5, 5, "easy", "Each letter is 3 places after the previous one."),
                                         (26, [-2, -3, -4, -5, -6], 5, "hard", "Moving backwards by 2, 3, 4, 5, so the next move is 6 back.")):
        idx, letters = start, []
        for s in steps:
            letters.append(_letter(idx))
            idx += s
        letters.append(_letter(idx))
        ans = letters[shown]
        wrong = [_letter(ord(ans) - 64 + k) for k in (1, -1, 2, -2, 3)]
        out.append(mk(sub, "Find the next letter: " + ", ".join(letters[:shown]) + ", ?", ans, wrong, expl, d=d, t=40, texts=True,
                      formula="Convert letters to positions (A=1 … Z=26) and find the pattern", ver=E("alpha_stepped", ans, start=start, steps=steps, shown=shown, terms=letters[:shown])))
    for starts, deltas, shown, d, expl in (([1, 26], [1, -1], 4, "medium", "First letters move forward (A, B, C, D) while second letters move backward (Z, Y, X, W)."),
                                           ([1, 3, 5], [1, 1, 1], 3, "easy", "Every letter in the group moves forward by one each time.")):
        terms = ["".join(_letter(s + dl * i) for s, dl in zip(starts, deltas)) for i in range(shown + 1)]
        ans = terms[shown]
        wrong = ["".join(_letter(s + dl * shown + k) for s, dl in zip(starts, deltas)) for k in (1, -1, 2)]
        out.append(mk(sub, "Find the next group: " + ", ".join(terms[:shown]) + ", ?", ans, wrong, expl, d=d, t=40, texts=True,
                      ver=E("alpha_multi", ans, starts=starts, deltas=deltas, shown=shown, terms=terms[:shown])))
    sub = "alphanumeric-series"
    for starts, deltas, num, shown, d, expl in (([1], [2], {"type": "arith", "a": 1, "d": 2}, 4, "easy", "Letters jump by 2 (A, C, E, G, I) and numbers by 2 (1, 3, 5, 7, 9)."),
                                                ([2], [2], {"type": "scaled_square", "k": 2}, 4, "hard", "Letters step by 2 (B, D, F, H, J); numbers are 2n²: 2, 8, 18, 32, 50."),
                                                ([26], [-2], {"type": "arith", "a": 26, "d": -2}, 4, "medium", "Letters step back by 2 (Z, X, V, T, R); numbers drop by 2 (26, 24, 22, 20, 18)."),
                                                ([1, 2], [1, 1], {"type": "scaled_square", "k": 1}, 4, "hard", "Letter pairs advance by one (AB, BC, CD, DE, EF); numbers are squares 1, 4, 9, 16, 25.")):
        def num_at(i):
            return num["a"] + num["d"] * i if num["type"] == "arith" else num["k"] * (i + 1) ** 2
        terms = ["".join(_letter(s + dl * i) for s, dl in zip(starts, deltas)) + str(num_at(i)) for i in range(shown + 1)]
        ans = terms[shown]
        letters = "".join(_letter(s + dl * shown) for s, dl in zip(starts, deltas))
        n = num_at(shown)
        wrong = [letters + str(n + 2), "".join(_letter(s + dl * shown + 1) for s, dl in zip(starts, deltas)) + str(n), letters + str(n - 1), letters + str(n + 5)]
        out.append(mk(sub, "Find the next term: " + ", ".join(terms[:shown]) + ", ?", ans, wrong, expl, d=d, t=50, texts=True,
                      ver=E("alnum_series", ans, starts=starts, deltas=deltas, num=num, shown=shown, terms=terms[:shown])))
    sub = "alphabet-tests"
    out.append(mk(sub, "If the letters of the word PLAYER are arranged in alphabetical order, which letter is third from the left?", "L", ["A", "E", "P"], "Alphabetical order: A, E, L, P, R, Y; the third is L.", d="easy", t=30, texts=True,
                  ver=E("alpha_position", "L", op="sorted_kth", word="PLAYER", k=3)))
    out.append(mk(sub, "Which letter is 5 places to the right of the 10th letter from the left in the English alphabet?", "O", ["N", "P", "T"], "10th letter is J; 5 places right gives the 15th letter, O.", d="easy", t=30, texts=True, ver=E("alpha_position", "O", op="offset", start_pos=10, offset=5)))
    out.append(mk(sub, "If the English alphabet is written in reverse order (Z to A), which letter is the 7th from the left?", "T", ["S", "U", "R"], "Position from the reversed left equals 27 − 7 = 20th letter of the normal order, T.", d="medium", t=35, texts=True, ver=E("alpha_position", "T", op="reverse_alphabet_kth", k=7)))
    out.append(mk(sub, "How many letters of the English alphabet lie between G and R (excluding both)?", 10, [9, 11, 12], "G is 7th and R is 18th: 18 − 7 − 1 = 10.", d="easy", t=25, ver=E("alpha_position", 10, op="between", a="G", b="R")))
    out.append(mk(sub, "If the letters of the word COMPUTER are arranged in alphabetical order, which letter is fourth from the left?", "O", ["M", "P", "E"], "Alphabetical order: C, E, M, O, P, R, T, U; the fourth is O.", d="medium", t=35, texts=True, ver=E("alpha_position", "O", op="sorted_kth", word="COMPUTER", k=4)))
    sub = "coding-decoding"
    out.append(mk(sub, "In a certain code, each letter is moved 2 places forward, so CODE is written as EQFG. How is MIND written in that code?", "OKPF", ["OKNF", "PKQE", "NJOE"], "M→O, I→K, N→P, D→F.", d="easy", t=40, texts=True, ver=E("caesar", "OKPF", word="MIND", shift=2)))
    out.append(mk(sub, "In a code, the word is reversed and then each letter is moved one place forward. How is TEAM written?", "NBFU", ["MAET", "UFBN", "NBEU"], "Reversed: MAET; each letter +1: N, B, F, U.", d="medium", t=50, texts=True, ver=E("reverse_shift", "NBFU", word="TEAM", shift=1)))
    out.append(mk(sub, "In a code where A = Z, B = Y, C = X and so on, how is CAT written?", "XZG", ["XYG", "XZH", "WZG"], "Each letter is replaced by its mirror in the alphabet: C→X, A→Z, T→G.", d="medium", t=45, texts=True, formula="Mirror letter = 27 − position", ver=E("atbash", "XZG", word="CAT")))
    out.append(mk(sub, "If A = 1, B = 2, C = 3 … Z = 26, what is the sum-code of the word FACE?", 15, [14, 16, 18], "F(6) + A(1) + C(3) + E(5) = 15.", d="easy", t=30, ver=E("sum_code", 15, word="FACE")))
    out.append(mk(sub, "In a code, each letter is replaced by the letter 3 places before it, so HELLO is written as EBIIL. How is WORLD written?", "TLOIA", ["TLOHA", "ZRUOG", "TLPIA"], "W→T, O→L, R→O, L→I, D→A.", d="medium", t=50, texts=True, ver=E("caesar", "TLOIA", word="WORLD", shift=-3)))
    sub = "language-coding"
    p1 = [[["pa", "ro", "ki"], ["red", "fast", "car"]], [["ro", "mu"], ["fast", "sky"]], [["ki", "ze"], ["car", "blue"]]]
    p2 = [[["ka", "lu", "mo"], ["sweet", "red", "fruit"]], [["lu", "ne"], ["red", "apple"]], [["mo", "ne", "pi"], ["fruit", "apple", "juice"]]]
    p3 = [[["ru", "sa", "ta"], ["good", "tall", "boys"]], [["sa", "vo"], ["tall", "girls"]], [["ta", "ze"], ["boys", "dance"]]]
    def stmts(p):
        return " ".join(f"'{' '.join(c)}' means '{' '.join(m)}'" + ("." if i == len(p) - 1 else ";") for i, (c, m) in enumerate(p))
    for puzzle, query, ans, wrong, expl in ((p1, "sky", "mu", ["ro", "ze", "pa"], "'ro' is common to the first two and 'fast' too, so ro = fast; ki = car from statements 1 and 3; then pa = red, mu = sky and ze = blue."),
                                            (p1, "blue", "ze", ["ki", "mu", "pa"], "Statements 1 and 3 share 'car' and 'ki', so ki = car and ze = blue."),
                                            (p2, "juice", "pi", ["ka", "mo", "ne"], "lu = red (statements 1, 2); mo = fruit (1, 3); then ne = apple, ka = sweet and pi = juice."),
                                            (p3, "girls", "vo", ["sa", "ta", "ze"], "sa = tall (1, 2); ta = boys (1, 3); ru = good; so vo = girls and ze = dance.")):
        out.append(mk(sub, f"In a certain language, {stmts(puzzle)} What is the code for '{query}'?", ans, wrong, expl, d="medium", t=75, texts=True, typ="multi_step",
                      ver=E("language_code", ans, statements=puzzle, query=query)))
    return out


def analytical():
    out = []
    sub = "blood-relations"
    rel = [
        ("Pointing to a man, Riya said, \"He is the son of my mother's only brother.\" How is the man related to Riya?", "Cousin", ["Brother", "Uncle", "Nephew"],
         "Riya's mother's brother is Riya's maternal uncle; his son is Riya's cousin.", "easy"),
        ("A is B's sister. C is B's mother. D is C's father. E is D's mother. How is A related to D?", "Granddaughter", ["Daughter", "Grandmother", "Sister"],
         "C is D's child; B and A are C's children, so A is D's grandchild, and A is female.", "medium"),
        ("Pointing to a photograph, Arun says, \"She is the daughter of my father's father's only son.\" How is she related to Arun?", "Sister", ["Cousin", "Aunt", "Mother"],
         "My father's father's only son is Arun's father, so she is Arun's father's daughter: his sister.", "medium"),
        ("P is the mother of Q. Q is the sister of R. R is the father of S. How is P related to S?", "Grandmother", ["Mother", "Aunt", "Great-grandmother"],
         "R is Q's sibling, so R is P's child; S is R's child, so P is S's grandmother.", "medium"),
        ("Introducing a woman, Vikram said, \"Her mother is the only daughter of my mother.\" How is the woman related to Vikram?", "Niece", ["Sister", "Daughter", "Cousin"],
         "Vikram's mother's only daughter is Vikram's sister, so the woman is the daughter of Vikram's sister: his niece.", "hard"),
        ("A is the brother of B, B is the sister of C, and C is the father of D. How is D related to A?", "Child of A's brother (nephew or niece)", ["A's son or daughter", "A's cousin", "A's brother"],
         "A, B and C are siblings (A and C are male). D is C's child, hence A's brother's child.", "hard"),
    ]
    for stem, ans, wrong, expl, d in rel:
        out.append(mk(sub, stem, ans, wrong, expl, d=d, t=50, texts=True, typ="multi_step" if d == "hard" else "direct",
                      ver=M("Traced by hand through each link of the family chain, with gender inferred only where the wording states it: " + expl)))
    sub = "direction-sense"
    out.append(mk(sub, "A man walks 5 km north, turns left and walks 3 km, then turns left again and walks 5 km. How far is he from the starting point?", "3 km", ["5 km", "8 km", "13 km"],
                  "North 5, west 3, south 5: the north-south movement cancels, leaving 3 km west.", d="easy", t=40, texts=True, typ="scenario",
                  ver=E("walk", 3.0, start="N", moves=[[None, 5], ["L", 3], ["L", 5]], ask="distance")))
    out.append(mk(sub, "In the same walk (5 km north, left for 3 km, left for 5 km), in which direction is he from the starting point?", "West", ["East", "South", "North"], "The net displacement is 3 km to the west.", d="easy", t=35, texts=True,
                  ver=E("walk", "West", start="N", moves=[[None, 5], ["L", 3], ["L", 5]], ask="direction")))
    out.append(mk(sub, "A person walks 8 m east, turns right and walks 6 m. How far is he from the starting point?", "10 m", ["14 m", "12 m", "2 m"], "The legs are perpendicular: √(8² + 6²) = 10 m.", d="easy", t=35, texts=True,
                  ver=E("walk", 10.0, start="E", moves=[[None, 8], ["R", 6]], ask="distance")))
    out.append(mk(sub, "Rahul faces north. He turns 135° clockwise and then 90° anticlockwise. Which direction is he facing now?", "North-East", ["East", "South-East", "North-West"], "135° − 90° = 45° clockwise from north, which is North-East.", d="medium", t=40, texts=True,
                  ver=E("turn_heading", "North-East", start="N", turns=[135, -90])))
    out.append(mk(sub, "A man walks 12 m south, turns right and walks 5 m. How far is he from the starting point?", "13 m", ["17 m", "7 m", "15 m"], "Right turn from south faces west; distance = √(12² + 5²) = 13 m.", d="easy", t=40, texts=True,
                  ver=E("walk", 13.0, start="S", moves=[[None, 12], ["R", 5]], ask="distance")))
    out.append(mk(sub, "A cyclist rides 7 km east and then 7 km north. In which direction is he from his starting point?", "North-East", ["East", "North", "South-East"], "Equal east and north displacements put him exactly North-East.", d="medium", t=35, texts=True,
                  ver=E("walk", "North-East", start="E", moves=[[None, 7], ["L", 7]], ask="direction")))
    out.append(mk(sub, "In the morning, just after sunrise, Meera stands with her shadow falling to her left. Which direction is she facing?", "North", ["South", "East", "West"],
                  "The sun is in the east, so the morning shadow falls to the west. If the west is on her left, she faces north.", d="medium", t=40, texts=True,
                  ver=M("Sunrise is in the east, so the shadow points west. Facing north, the left hand points west, so the shadow lies to her left.")))
    return out


def _stmt(kind, x, y):
    return {"A": f"All {x} are {y}", "E": f"No {x} is {y}", "I": f"Some {x} are {y}", "O": f"Some {x} are not {y}"}[kind]


def syllogism():
    out = []
    note = " (Assume every group named has at least one member.)"
    def build(sub, premises, conclusions, mode, d):
        sets = ["A", "B", "C"]
        label = E("syllogism", None, sets=sets, premises=premises, conclusions=conclusions, mode=mode)
        from ..verifiers import run_verifier
        ans = run_verifier("syllogism", label["params"])
        label["expected"] = ans
        prem = " ".join(f"{i + 1}. {_stmt(*p)}." for i, p in enumerate(premises))
        if mode == "follows":
            concl = " ".join(f"{'I' * (i + 1) if i < 2 else 'III'}. {_stmt(*c)}." for i, c in enumerate(conclusions))
            question = "Which of the following is correct?"
            options = OPTS_FOLLOW
        else:
            concl = " ".join(f"{'I' * (i + 1)}. It is possible that {_stmt(*c)[0].lower() + _stmt(*c)[1:]}." for i, c in enumerate(conclusions))
            question = "Which of the following is correct?"
            options = OPTS_POSSIBLE
        stem = f"Statements: {prem} Conclusions: {concl}{note} {question}"
        wrong = [o for o in options if o != ans]
        expl = f"Checking every possible Venn arrangement of A, B and C consistent with the statements, the correct choice is '{ans}'."
        return mk(sub, stem, ans, wrong, expl, d=d, t=75, texts=True, typ="multi_step", formula="Draw every valid Venn arrangement; a conclusion 'follows' only if it holds in all of them", ver=label)
    sub = "group-relationships"
    for premises, conclusions, d in (
        ([["A", "A", "B"], ["I", "B", "C"]], [["I", "A", "C"], ["I", "C", "B"]], "medium"),
        ([["E", "A", "B"], ["A", "B", "C"]], [["E", "A", "C"], ["O", "C", "A"]], "hard"),
        ([["A", "A", "B"], ["A", "B", "C"]], [["A", "A", "C"], ["I", "C", "A"]], "medium"),
        ([["I", "A", "B"], ["E", "B", "C"]], [["O", "A", "C"], ["E", "A", "C"]], "hard"),
        ([["A", "A", "B"], ["E", "B", "C"]], [["E", "A", "C"], ["E", "C", "A"]], "medium"),
    ):
        out.append(build(sub, premises, conclusions, "follows", d))
    sub = "possibility-questions"
    for premises, conclusions, d in (
        ([["A", "A", "B"], ["I", "B", "C"]], [["I", "A", "C"], ["E", "A", "C"]], "medium"),
        ([["E", "A", "B"], ["I", "B", "C"]], [["I", "A", "C"], ["A", "A", "B"]], "hard"),
        ([["A", "A", "B"], ["A", "B", "C"]], [["O", "C", "A"], ["E", "A", "C"]], "hard"),
        ([["I", "A", "B"], ["I", "B", "C"]], [["A", "A", "C"], ["E", "A", "C"]], "hard"),
    ):
        out.append(build(sub, premises, conclusions, "possible", d))
    sub = "venn-diagrams"
    out.append(mk(sub, "Which Venn description best represents Mango, Fruit and Vegetable?", "The Mango circle lies inside the Fruit circle; the Vegetable circle is separate from both",
                  ["Three separate circles that do not touch", "All three circles lie inside one another", "The Mango circle lies inside the Vegetable circle; Fruit is separate"],
                  "Every mango is a fruit, while vegetables are neither fruits nor mangoes.", d="easy", t=40, texts=True, ver=M("Mango ⊂ Fruit; Vegetable disjoint from Fruit (and so from Mango).")))
    out.append(mk(sub, "Which Venn description best represents Doctors, Teachers and Humans?", "Doctors and Teachers are overlapping circles that both lie inside the Humans circle",
                  ["Doctors and Teachers are separate circles that both lie inside Humans", "Humans lies inside the Doctors circle", "Three separate circles"],
                  "Doctors and teachers are all human; a person may be both, so those circles overlap.", d="medium", t=40, texts=True, ver=M("Both groups are subsets of Humans, and the two groups can share members, so they overlap.")))
    out.append(mk(sub, "In a group of 50 people, 30 like tea, 25 like coffee and 10 like neither. How many like both?", 15, [10, 20, 25], "Those liking at least one drink = 40; both = 30 + 25 − 40 = 15.", d="medium", t=45, formula="n(A∪B) = n(A) + n(B) − n(A∩B)", ver=X("30+25-(50-10)", 15)))
    out.append(mk(sub, "In the same group (50 people, 30 tea, 25 coffee, 10 neither), how many like only tea?", 15, [10, 20, 30], "Both = 15, so only tea = 30 − 15 = 15.", d="medium", t=45, ver=X("30-(30+25-(50-10))", 15)))
    return out


def ranking():
    out = []
    sub = "number-tests"
    seq = [2, 5, 4, 5, 7, 5, 8, 3, 5, 6]
    out.append(mk(sub, "How many 5s in the sequence 2 5 4 5 7 5 8 3 5 6 are immediately followed by an even number?", 3, [2, 4, 1], "The 5s are followed by 4, 7, 8 and 6: three of them are even.", d="easy", t=40, ver=E("number_test", 3, op="count_followed_by", sequence=seq, target=5, next="even")))
    seq2 = [3, 7, 8, 4, 3, 7, 5, 6, 3, 7, 9]
    out.append(mk(sub, "How many 7s in the sequence 3 7 8 4 3 7 5 6 3 7 9 are immediately preceded by 3 but not immediately followed by 8?", 2, [1, 3, 0], "The 7s are preceded by 3 each time; the first is followed by 8 and is excluded, leaving two.", d="medium", t=50, ver=E("number_test", 2, op="count_preceded_not_followed", sequence=seq2, target=7, before=3, after=8)))
    out.append(mk(sub, "If the digits of 7352 are arranged in ascending order, which digit is third from the left?", 5, [3, 7, 2], "Ascending order: 2, 3, 5, 7; the third is 5.", d="easy", t=25, ver=E("number_test", 5, op="kth_digit_sorted", sequence=[], number=7352, k=3)))
    out.append(mk(sub, "What is the difference between the sum of odd digits and the sum of even digits in 83472916?", 0, [2, 4, 6], "Odd: 3 + 7 + 9 + 1 = 20; even: 8 + 4 + 2 + 6 = 20; difference 0.", d="medium", t=40, ver=E("number_test", 0, op="odd_even_diff", sequence=[], number=83472916)))
    out.append(mk(sub, "Using all digits of 528 once each, what is the difference between the largest and the smallest 3-digit number that can be formed?", 594, [492, 396, 693], "Largest 852, smallest 258; 852 − 258 = 594.", d="medium", t=45, ver=E("number_test", 594, op="largest_minus_smallest", sequence=[], number=528)))
    sub = "ranking-ordering"
    out.append(mk(sub, "In a class of 40, Ravi ranks 12th from the top. What is his rank from the bottom?", "29th", ["28th", "30th", "27th"], "Rank from bottom = 40 − 12 + 1 = 29.", d="easy", t=25, texts=True, formula="Total = rank from top + rank from bottom − 1", ver=X("40-12+1", 29)))
    out.append(mk(sub, "Neha ranks 7th from the top and 28th from the bottom in a class. How many students are in the class?", 34, [35, 33, 36], "Total = 7 + 28 − 1 = 34.", d="easy", t=25, ver=X("7+28-1", 34)))
    out.append(mk(sub, "In a row of 40 people, Kiran is 15th from the left and Meera is 18th from the right. How many people are between them?", 7, [6, 8, 9], "Meera is 40 − 18 + 1 = 23rd from the left; people between = 23 − 15 − 1 = 7.", d="medium", t=45, ver=X("(40-18+1)-15-1", 7)))
    out.append(mk(sub, "Rohan is 5th from the top and Soham is 8th from the bottom. If they exchange places, Rohan becomes 10th from the top. How many students are there?", 17, [15, 16, 18], "Soham's place is 10th from the top and 8th from the bottom: total = 10 + 8 − 1 = 17.", d="hard", t=60, ver=X("10+8-1", 17)))
    out.append(mk(sub, "Meena ranks 9th from the top and 32nd from the bottom in an exam. How many students took the exam?", 40, [41, 39, 42], "Total = 9 + 32 − 1 = 40.", d="easy", t=25, ver=X("9+32-1", 40)))
    return out


def _lin_text(constraints, names):
    parts = []
    for c in constraints:
        k = c[0]
        if k == "pos":
            parts.append(f"{c[1]} sits {['at the extreme left end', 'second from the left', 'in the middle', 'second from the right', 'at the extreme right end'][c[2]] if len(names) == 5 else 'third from the left'}.")
        elif k == "immediate_left":
            parts.append(f"{c[1]} sits immediately to the left of {c[2]}.")
        elif k == "left_of":
            parts.append(f"{c[1]} sits somewhere to the left of {c[2]}.")
        elif k == "adjacent":
            parts.append(f"{c[1]} sits next to {c[2]}.")
        elif k == "not_adjacent":
            parts.append(f"{c[1]} does not sit next to {c[2]}.")
        elif k == "end":
            parts.append(f"{c[1]} sits at one of the ends.")
        elif k == "between":
            parts.append(f"{c[1]} sits between {c[2]} and {c[3]}.")
    return " ".join(parts)


def seating():
    out = []
    from ..verifiers import run_verifier
    sub = "linear-seating"
    puzzles = [
        (["P", "Q", "R", "S", "T"], [["pos", "P", 0], ["immediate_left", "P", "R"], ["pos", "T", 4], ["between", "S", "R", "T"], ["adjacent", "Q", "T"]],
         {"type": "who_at", "pos": 2}, "Who sits in the middle?", "medium"),
        (["A", "B", "C", "D", "E", "F"], [["pos", "F", 2], ["immediate_left", "D", "F"], ["left_of", "E", "D"], ["end", "A"], ["adjacent", "C", "A"]],
         {"type": "who_at", "pos": 4}, "Who sits second from the right end?", "hard"),
        (["A", "B", "C", "D", "E", "F"], [["pos", "F", 2], ["immediate_left", "D", "F"], ["left_of", "E", "D"], ["end", "A"], ["adjacent", "C", "A"]],
         {"type": "position_of", "person": "B"}, "What is B's position from the left end?", "hard"),
        (["M", "N", "O", "P", "Q"], [["pos", "N", 2], ["immediate_left", "M", "N"], ["not_adjacent", "O", "N"], ["left_of", "Q", "M"]],
         {"type": "who_at", "pos": 4}, "Who sits at the extreme right end?", "medium"),
    ]
    for people, cons, ask, q, d in puzzles:
        params = {"people": people, "constraints": cons, "ask": ask}
        ans = run_verifier("seating_linear", params)
        text = _lin_text(cons, people)
        wrong = [p for p in people if p != ans] if isinstance(ans, str) else [x for x in range(1, len(people) + 1) if x != ans]
        stem = f"{', '.join(people)} sit in a row facing north. {text} {q}"
        out.append(mk(sub, stem, ans, wrong, "Place the fixed positions first, then use the remaining clues to settle the others; exactly one arrangement satisfies every clue.", d=d, t=90, typ="multi_step", texts=isinstance(ans, str),
                      ver=E("seating_linear", ans, **params)))
    sub = "circular-seating"
    circ = [
        (["A", "B", "C", "D", "E", "F"], [["opposite", "A", "D"], ["immediate_left", "B", "A"], ["immediate_left", "C", "B"], ["opposite", "E", "B"]],
         {"type": "opposite", "person": "C"}, "Who sits opposite C?", "hard"),
        (["A", "B", "C", "D", "E", "F"], [["opposite", "A", "D"], ["immediate_left", "B", "A"], ["immediate_left", "C", "B"], ["opposite", "E", "B"]],
         {"type": "immediate_right", "person": "D"}, "Who sits immediately to the right of D?", "hard"),
        (["A", "B", "C", "D", "E", "F"], [["opposite", "B", "E"], ["immediate_right", "A", "B"], ["immediate_right", "F", "A"], ["opposite", "C", "F"]],
         {"type": "immediate_left", "person": "C"}, "Who sits immediately to the left of C?", "hard"),
        (["A", "B", "C", "D", "E", "F"], [["second_right", "A", "C"], ["opposite", "A", "D"], ["immediate_left", "E", "D"], ["opposite", "B", "E"]],
         {"type": "immediate_right", "person": "A"}, "Who sits immediately to the right of A?", "hard"),
    ]
    tmpl = {"opposite": "{0} sits opposite {1}.", "immediate_left": "{0} sits immediately to the left of {1}.", "immediate_right": "{0} sits immediately to the right of {1}.",
            "adjacent": "{0} sits next to {1}.", "second_right": "{0} sits second to the right of {1}.", "not_adjacent": "{0} does not sit next to {1}."}
    for people, cons, ask, q, d in circ:
        params = {"people": people, "constraints": cons, "ask": ask}
        ans = run_verifier("seating_circular", params)
        text = " ".join(tmpl[c[0]].format(c[1], c[2]) for c in cons)
        stem = f"{', '.join(people)} sit around a circular table, all facing the centre. {text} {q}"
        out.append(mk(sub, stem, ans, [p for p in people if p != ans], "Fix one person, place their opposite, then use left/right clues (for people facing the centre, 'left' is the clockwise side). Only one arrangement fits every clue.",
                      d=d, t=100, typ="multi_step", texts=True, ver=E("seating_circular", ans, **params)))
    return out
