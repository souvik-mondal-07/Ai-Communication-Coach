"""Topics G-K: Ratio, Alligation, Permutation & Combination, Probability, Interest."""

from __future__ import annotations

from fractions import Fraction

from .build import E, M, X, fnum, frac, mk, pct, rupee


def ratio():
    out = []
    sub = "ratio-concepts"
    out.append(mk(sub, "₹1,200 is divided among three people in the ratio 3 : 5 : 4. What is the largest share?", 500, [400, 450, 600], "Total parts 12; each part ₹100; largest = 5 × 100.", d="easy", t=30, fmt=rupee, ver=X("1200*5/12", 500)))
    out.append(mk(sub, "Two numbers are in the ratio 3 : 4. If 6 is added to each, the ratio becomes 4 : 5. What is the larger number?", 24, [18, 20, 30], "(3x+6)/(4x+6) = 4/5 gives x = 6, so the numbers are 18 and 24.", d="medium", t=60, ver=X("4*6", 24)))
    out.append(mk(sub, "If A : B = 2 : 3 and B : C = 4 : 5, what is A : C?", "8 : 15", ["2 : 5", "6 : 5", "4 : 15"], "Make B equal: A:B = 8:12, B:C = 12:15, so A:C = 8:15.", d="medium", t=45, texts=True, ver=M("A:B=2:3=8:12 and B:C=4:5=12:15, hence A:C=8:15.")))
    out.append(mk(sub, "Find the mean proportional between 4 and 16.", 8, [6, 10, 12], "Mean proportional = √(4 × 16) = 8.", d="easy", t=20, formula="Mean proportional of a, b = √(ab)", ver=X("sqrt(4*16)", 8)))
    out.append(mk(sub, "Find the fourth proportional to 3, 6 and 9.", 18, [12, 15, 27], "3 : 6 = 9 : x gives x = 6 × 9 ÷ 3 = 18.", d="easy", t=25, ver=X("6*9/3", 18)))
    out.append(mk(sub, "Find the third proportional to 4 and 6.", 9, [8, 12, 10], "4 : 6 = 6 : x gives x = 36 ÷ 4 = 9.", d="easy", t=25, ver=X("6*6/4", 9)))
    sub = "age-problems"
    out.append(mk(sub, "The ages of a father and son are in the ratio 7 : 2. After 10 years the ratio becomes 9 : 4. What is the father's present age?", 35, [28, 42, 49], "(7x+10)/(2x+10) = 9/4 gives x = 5, so father = 35.", d="medium", t=60, ver=X("7*5", 35)))
    out.append(mk(sub, "A father is three times as old as his son. After 15 years he will be twice as old. What is the son's present age?", 15, [10, 12, 18], "3x + 15 = 2(x + 15) gives x = 15.", d="medium", t=45, ver=X("2*15-15", 15)))
    out.append(mk(sub, "The sum of the ages of A and B is 50 years. Five years ago their ages were in the ratio 3 : 2. What is A's present age?", 29, [27, 30, 33], "Sum 5 years ago = 40, so A was 24 and B 16; A is now 29.", d="hard", t=60, ver=X("40*3/5+5", 29)))
    out.append(mk(sub, "Ritu is 4 times as old as her daughter. In 6 years she will be 3 times as old. What is the daughter's present age?", 12, [6, 8, 10], "4x + 6 = 3(x + 6) gives x = 12.", d="medium", t=45, ver=X("3*6-6", 12)))
    sub = "partnership"
    out.append(mk(sub, "A and B invest ₹20,000 and ₹30,000 for the same period. Of a profit of ₹15,000, what is B's share?", 9000, [6000, 7500, 10000], "Ratio 2 : 3, so B gets 3/5 × 15,000.", d="easy", t=30, fmt=rupee, ver=X("15000*3/5", 9000)))
    out.append(mk(sub, "A invests ₹50,000 for 12 months; B joins after 4 months with ₹60,000. Of a ₹9,000 profit, how much does A get?", 5000, [4000, 4500, 6000], "A : B = 50000 × 12 : 60000 × 8 = 5 : 4, so A gets 5/9 of 9,000.", d="medium", t=50, fmt=rupee, typ="scenario", ver=X("9000*(50000*12)/(50000*12+60000*8)", 5000)))
    out.append(mk(sub, "A, B and C invest in the ratio 4 : 5 : 6 for equal time. Of ₹3,000 profit, what does C get?", 1200, [1000, 1500, 1800], "C's share = 6/15 × 3,000.", d="easy", t=30, fmt=rupee, ver=X("3000*6/15", 1200)))
    out.append(mk(sub, "A invests ₹8,000 for 12 months and B invests ₹12,000 for 8 months. How is a ₹6,000 profit divided (A's share)?", 3000, [2400, 3600, 4000], "A : B = 96,000 : 96,000 = 1 : 1.", d="medium", t=40, fmt=rupee, ver=X("6000*8000*12/(8000*12+12000*8)", 3000)))
    return out


def alligation():
    out = []
    sub = "alligation-concepts"
    out.append(mk(sub, "In what ratio should rice at ₹40/kg be mixed with rice at ₹50/kg to get a mixture worth ₹44/kg?", "3 : 2", ["2 : 3", "4 : 1", "1 : 1"], "Cheaper : dearer = (50 − 44) : (44 − 40) = 6 : 4 = 3 : 2.", d="medium", t=40, texts=True, formula="Cheaper : Dearer = (d − m) : (m − c)",
                  ver=M("(50-44):(44-40)=6:4=3:2; mean price check: (3*40+2*50)/5 = 44.")))
    out.append(mk(sub, "In what ratio must a 20% acid solution be mixed with a 50% acid solution to get a 35% solution?", "1 : 1", ["2 : 1", "1 : 2", "3 : 2"], "(50 − 35) : (35 − 20) = 15 : 15.", d="medium", t=40, texts=True, ver=M("(50-35):(35-20)=15:15=1:1; mean check (20+50)/2=35.")))
    out.append(mk(sub, "In what ratio should water be mixed with milk costing ₹12/litre to get a mixture worth ₹8/litre?", "1 : 2", ["2 : 1", "1 : 3", "3 : 2"], "Water (₹0) : milk (₹12) = (12 − 8) : (8 − 0) = 4 : 8 = 1 : 2.", d="medium", t=45, texts=True,
                  ver=M("(12-8):(8-0)=4:8=1:2; mean check (1*0+2*12)/3 = 8.")))
    out.append(mk(sub, "A grocer mixes 6 kg of tea at ₹300/kg with 4 kg of tea at ₹350/kg. What is the mixture's price per kg?", 320, [325, 330, 315], "(6 × 300 + 4 × 350) ÷ 10 = 3200 ÷ 10 = 320.", d="easy", t=35, fmt=rupee, typ="scenario", ver=X("(6*300+4*350)/10", 320)))
    sub = "replacement"
    out.append(mk(sub, "A vessel holds 40 litres of milk. 4 litres are removed and replaced with water, and this is repeated once more. How much milk remains?", 32.4, [32, 33.6, 36], "40 × (1 − 4/40)² = 40 × 0.81 = 32.4.", d="medium", t=45, fmt=lambda v: f"{fnum(v)} litres", formula="Remaining = V(1 − x/V)ⁿ", ver=X("40*(1-4/40)**2", 32.4)))
    out.append(mk(sub, "A jar holds 60 litres of pure alcohol. 12 litres are drawn off and replaced by water, and this is done once more. How much pure alcohol remains?", 38.4, [36, 40, 48], "60 × (1 − 12/60)² = 60 × 0.64 = 38.4.", d="medium", t=45, fmt=lambda v: f"{fnum(v)} litres", ver=X("60*(1-12/60)**2", 38.4)))
    out.append(mk(sub, "A 60-litre mixture has milk and water in the ratio 5 : 1. If 12 litres of the mixture are replaced by water, what is the new milk : water ratio?", "2 : 1", ["5 : 2", "3 : 1", "4 : 3"],
                  "Milk 50, water 10. Removing 12 L takes out 10 L milk and 2 L water: milk 40, water 8 + 12 = 20, ratio 2 : 1.", d="hard", t=70, texts=True, typ="multi_step",
                  ver=M("Milk 50, water 10; remove 12 L (10 milk, 2 water) leaves 40 milk, 8 water; add 12 water gives 40:20 = 2:1.")))
    out.append(mk(sub, "A can of 80 litres is full of milk. 8 litres are replaced by water, three times in all. What is the milk left?", 58.32, [56, 60, 64], "80 × 0.9³ = 58.32.", d="hard", t=50, fmt=lambda v: f"{fnum(v)} litres", ver=X("80*(1-8/80)**3", 58.32)))
    return out


def permutation_combination():
    out = []
    sub = "counting-principles"
    out.append(mk(sub, "A shop has 5 shirt colours and 4 trouser colours. How many different outfits can be made?", 20, [9, 16, 25], "Multiplication principle: 5 × 4 = 20.", d="easy", t=20, typ="time_pressure", ver=X("5*4", 20)))
    out.append(mk(sub, "How many 3-digit numbers have no repeated digits?", 648, [720, 729, 900], "Hundreds: 9 choices (not 0); tens: 9; units: 8 → 648.", d="medium", t=45, formula="9 × 9 × 8", ver=E("count_numbers", 648, digits="0123456789", length=3, repeat=False)))
    out.append(mk(sub, "How many 4-digit PINs can be formed from digits 0-9 if repetition is allowed?", 10000, [5040, 9000, 9999], "10 choices for each of 4 positions: 10⁴.", d="easy", t=25, typ="scenario", ver=E("count_numbers", 10000, digits="0123456789", length=4, repeat=True, leading_zero=True)))
    out.append(mk(sub, "A traveller goes from A to B by any of 3 routes and returns by a different route. In how many ways can the round trip be made?", 6, [9, 3, 8], "3 ways out × 2 different ways back = 6.", d="easy", t=30, ver=X("3*2", 6)))
    sub = "selection-arrangement"
    out.append(mk(sub, "In how many ways can a team of 3 be chosen from 8 people?", 56, [24, 336, 48], "⁸C₃ = 8·7·6/6 = 56.", d="easy", t=30, formula="ⁿCᵣ = n!/(r!(n−r)!)", ver=X("comb(8,3)", 56)))
    out.append(mk(sub, "A committee of 4 is chosen from 6 men and 4 women with at least 2 women. How many committees are possible?", 115, [90, 120, 210], "2W2M: 6·15 = 90; 3W1M: 4·6 = 24; 4W: 1. Total 115.", d="hard", t=75, typ="multi_step", ver=E("committee", 115, men=6, women=4, size=4, min_women=2)))
    out.append(mk(sub, "In how many ways can 5 people stand in a row?", 120, [24, 60, 25], "5! = 120.", d="easy", t=20, typ="time_pressure", ver=X("factorial(5)", 120)))
    out.append(mk(sub, "In how many ways can 2 boys be chosen from 5 and 3 girls from 4?", 40, [20, 30, 60], "⁵C₂ × ⁴C₃ = 10 × 4 = 40.", d="medium", t=40, ver=X("comb(5,2)*comb(4,3)", 40)))
    sub = "numbers-and-words"
    out.append(mk(sub, "How many distinct arrangements are there of the letters of the word LEVEL?", 30, [60, 120, 24], "5!/(2!·2!) = 30 (L and E each repeat twice).", d="medium", t=40, formula="n!/(p!q!…)", ver=E("arrangements", 30, word="LEVEL")))
    out.append(mk(sub, "In how many ways can the letters of the word APPLE be arranged?", 60, [120, 30, 24], "5!/2! = 60.", d="easy", t=30, ver=E("arrangements", 60, word="APPLE")))
    out.append(mk(sub, "How many even 4-digit numbers can be formed from the digits 1, 2, 3, 4, 5 without repetition?", 48, [24, 60, 72], "Units digit 2 or 4 (2 ways), then 4·3·2 = 24 for the rest: 48.", d="medium", t=50, ver=E("count_numbers", 48, digits="12345", length=4, repeat=False, even=True)))
    out.append(mk(sub, "In how many ways can the letters of the word CODE be arranged so that the vowels are together?", 12, [24, 6, 18], "Treat OE as one block: 3! × 2! = 12.", d="medium", t=45, ver=E("arrangements", 12, word="CODE", constraint="vowels_together")))
    out.append(mk(sub, "How many arrangements are possible for the letters of MISSISSIPPI?", 34650, [39916800, 69300, 17325], "11!/(4!·4!·2!) = 34650.", d="hard", t=60, ver=X("factorial(11)/(factorial(4)*factorial(4)*factorial(2))", 34650)))
    sub = "rank-distribution"
    out.append(mk(sub, "If all arrangements of the letters of BEAT are listed in dictionary order, what is the rank of BEAT?", 9, [7, 8, 10], "Words starting with A: 6; then BAET, BATE; BEAT is the 9th.", d="hard", t=70, ver=E("word_rank", 9, word="BEAT")))
    out.append(mk(sub, "In how many ways can 10 identical sweets be distributed among 3 children so that each gets at least one?", 36, [45, 28, 66], "Give 1 to each, then distribute 7 freely: ⁹C₂ = 36.", d="hard", t=70, ver=E("distribute_identical", 36, items=10, boxes=3, min_each=1)))
    out.append(mk(sub, "In how many ways can 5 different books be given to 3 students if each book can go to any student?", 243, [125, 60, 15], "Each of 5 books has 3 choices: 3⁵ = 243.", d="medium", t=35, ver=E("functions_count", 243, items=5, boxes=3)))
    out.append(mk(sub, "In how many ways can 6 identical balls be put into 3 distinct boxes if boxes may be empty?", 28, [18, 36, 20], "⁸C₂ = 28.", d="hard", t=60, ver=E("distribute_identical", 28, items=6, boxes=3, min_each=0)))
    sub = "geometric-applications"
    out.append(mk(sub, "How many diagonals does a hexagon have?", 9, [6, 12, 15], "n(n − 3)/2 = 6 × 3/2 = 9.", d="easy", t=25, formula="Diagonals = n(n−3)/2", ver=E("diagonals", 9, n=6)))
    out.append(mk(sub, "How many triangles can be formed using 8 points, no three collinear?", 56, [28, 24, 336], "⁸C₃ = 56.", d="easy", t=30, ver=E("triangles", 56, points=8, collinear=0)))
    out.append(mk(sub, "How many triangles can be formed from 10 points of which 4 are collinear?", 116, [120, 112, 124], "¹⁰C₃ − ⁴C₃ = 120 − 4 = 116.", d="medium", t=50, ver=E("triangles", 116, points=10, collinear=4)))
    out.append(mk(sub, "How many rectangles (of all sizes) are there on an 8 × 8 chessboard?", 1296, [204, 1024, 729], "Choose 2 of 9 horizontal and 2 of 9 vertical lines: 36 × 36 = 1296.", d="hard", t=60, formula="C(n+1,2)²", ver=E("grid_rectangles", 1296, n=8)))
    sub = "circular-arrangements"
    out.append(mk(sub, "In how many ways can 5 people sit around a circular table?", 24, [120, 12, 60], "(5 − 1)! = 24.", d="easy", t=25, formula="Circular arrangements of n = (n−1)!", ver=X("factorial(4)", 24)))
    out.append(mk(sub, "In how many ways can 6 people sit around a circular table if two particular people must sit together?", 48, [120, 24, 72], "Treat the pair as one: (5 − 1)! × 2! = 48.", d="medium", t=45, ver=E("circular", 48, n=6, constraint="together", pair=[0, 1])))
    out.append(mk(sub, "In how many ways can 8 people sit around a circular table so that two particular people are not adjacent?", 3600, [5040, 1440, 4320], "Total 7! = 5040; together 2 × 6! = 1440; difference 3600.", d="hard", t=70, ver=E("circular", 3600, n=8, constraint="apart", pair=[0, 1])))
    out.append(mk(sub, "How many different necklaces can be made from 6 distinct beads?", 60, [120, 720, 30], "(6 − 1)!/2 = 60 (a necklace can be flipped).", d="hard", t=45, ver=E("necklace", 60, n=6)))
    return out


def probability():
    out = []
    sub = "probability-concepts"
    out.append(mk(sub, "If P(A) = 0.3 and P(B) = 0.4 and A, B are mutually exclusive, what is P(A or B)?", 0.7, [0.12, 0.1, 0.58], "For mutually exclusive events P(A∪B) = P(A) + P(B) = 0.7.", d="easy", t=25, formula="P(A∪B) = P(A) + P(B) − P(A∩B)", ver=X("0.3+0.4", 0.7)))
    out.append(mk(sub, "If A and B are independent with P(A) = 0.5 and P(B) = 0.4, what is P(A and B)?", 0.2, [0.9, 0.1, 0.45], "P(A∩B) = 0.5 × 0.4 = 0.2.", d="easy", t=25, ver=X("0.5*0.4", 0.2)))
    out.append(mk(sub, "If P(A) = 0.5, P(B) = 0.6 and P(A and B) = 0.3, what is P(A or B)?", 0.8, [1.1, 0.7, 0.9], "0.5 + 0.6 − 0.3 = 0.8.", d="medium", t=30, ver=X("0.5+0.6-0.3", 0.8)))
    out.append(mk(sub, "A fair die is rolled once. What is the probability of NOT getting a 6?", "5/6", ["1/6", "1/2", "4/6 + 1/6"], "P(not 6) = 1 − 1/6 = 5/6.", d="easy", t=20, texts=True, typ="time_pressure", ver=X("1-1/6", 5 / 6)))
    out.append(mk(sub, "On tossing a coin once, 'getting a head' and 'getting a tail' are:", "Mutually exclusive and exhaustive", ["Independent and exhaustive", "Mutually exclusive but not exhaustive", "Neither mutually exclusive nor exhaustive"],
                  "They cannot both occur, and together they cover every outcome.", d="easy", t=30, texts=True, ver=M("A single toss has outcomes {H,T}; the two events are disjoint and their union is the whole sample space.")))
    sub = "coins"
    for n, ev, k, ans, expl, d in ((3, "exactly_heads", 2, Fraction(3, 8), "3 of the 8 outcomes (HHT, HTH, THH) have exactly two heads.", "easy"),
                                   (3, "at_least_heads", 1, Fraction(7, 8), "1 − P(no heads) = 1 − 1/8 = 7/8.", "easy"),
                                   (4, "exactly_heads", 4, Fraction(1, 16), "Only one of the 16 outcomes is HHHH.", "easy"),
                                   (2, "at_least_tails", 1, Fraction(3, 4), "1 − P(HH) = 3/4.", "easy")):
        label = {"exactly_heads": f"exactly {k} heads", "at_least_heads": f"at least {k} head", "at_least_tails": f"at least {k} tail"}[ev]
        out.append(mk(sub, f"{n} fair coins are tossed together. What is the probability of getting {label}?", frac(ans.numerator, ans.denominator),
                      [x for x in ("1/2", "1/4", "3/4", "5/8", "1/8", "7/16") if x != frac(ans.numerator, ans.denominator)], expl, d=d, t=35, texts=True,
                      formula="P = favourable / total (2ⁿ outcomes)", ver=E("coins", ans, n=n, event=ev, k=k)))
    sub = "dice"
    for ev, v, ans, label, expl in (("sum_eq", 8, Fraction(5, 36), "a sum of 8", "(2,6),(3,5),(4,4),(5,3),(6,2): 5 of 36."),
                                    ("sum_prime", 0, Fraction(5, 12), "a prime sum", "Sums 2,3,5,7,11 occur 1+2+4+6+2 = 15 ways of 36 = 5/12."),
                                    ("product_even", 0, Fraction(3, 4), "an even product", "Product is odd only when both are odd (9 of 36), so even = 27/36 = 3/4."),
                                    ("doublet", 0, Fraction(1, 6), "a doublet (same number on both)", "6 doublets out of 36 = 1/6."),
                                    ("sum_ge", 10, Fraction(1, 6), "a sum of at least 10", "Sums 10, 11, 12 occur 3 + 2 + 1 = 6 ways: 6/36 = 1/6.")):
        a = frac(ans.numerator, ans.denominator)
        out.append(mk(sub, f"Two fair dice are rolled. What is the probability of getting {label}?", a, [x for x in ("1/6", "5/36", "1/12", "7/36", "5/12", "1/2", "2/3") if x != a],
                      expl, d="medium", t=40, texts=True, ver=E("dice", ans, event=ev, v=v)))
    sub = "cards"
    for ev, extra, ans, label, expl in (("ranks", {"ranks": ["K", "Q"]}, Fraction(2, 13), "a king or a queen", "8 of 52 cards = 2/13."),
                                        ("red_face", {}, Fraction(3, 26), "a red face card", "Red face cards: 3 × 2 = 6, so 6/52 = 3/26."),
                                        ("heart_or_king", {}, Fraction(4, 13), "a heart or a king", "13 + 4 − 1 = 16 cards, so 16/52 = 4/13."),
                                        ("spade_or_face", {}, Fraction(11, 26), "a spade or a face card", "13 + 12 − 3 = 22 cards, so 22/52 = 11/26.")):
        a = frac(ans.numerator, ans.denominator)
        out.append(mk(sub, f"One card is drawn at random from a standard 52-card deck. What is the probability that it is {label}?", a, [x for x in ("1/13", "1/4", "3/13", "1/2", "2/13", "4/13", "5/26") if x != a],
                      expl, d="medium", t=40, texts=True, ver=E("cards", ans, event=ev, **extra)))
    out.append(mk(sub, "Two cards are drawn together from a standard deck. What is the probability that both are aces?", "1/221", ["1/169", "1/13", "4/663"], "⁴C₂ / ⁵²C₂ = 6/1326 = 1/221.", d="hard", t=50, texts=True, ver=E("cards", Fraction(1, 221), event="two_aces")))
    sub = "conditional-probability"
    out.append(mk(sub, "A bag has 5 red and 3 blue balls. Two balls are drawn one after another without replacement. What is the probability both are red?", "5/14", ["25/64", "5/16", "3/14"], "5/8 × 4/7 = 20/56 = 5/14.", d="medium", t=45, texts=True, typ="scenario", ver=E("conditional", Fraction(5, 14), case="bag_both_red", red=5, blue=3)))
    out.append(mk(sub, "If P(A and B) = 0.2 and P(A) = 0.5, what is P(B | A)?", 0.4, [0.1, 0.7, 0.25], "P(B|A) = P(A∩B)/P(A) = 0.2/0.5 = 0.4.", d="easy", t=25, formula="P(B|A) = P(A∩B) / P(A)", ver=X("0.2/0.5", 0.4)))
    out.append(mk(sub, "A fair die is rolled and it is known that the result is even. What is the probability that it is greater than 3?", "2/3", ["1/2", "1/3", "3/4"], "Even outcomes: 2, 4, 6; those above 3: 4, 6. So 2/3.", d="medium", t=35, texts=True, ver=E("conditional", Fraction(2, 3), case="die_given_even", greater_than=3)))
    out.append(mk(sub, "Two cards are drawn without replacement from a standard deck. Given the first is an ace, what is the probability that the second is also an ace?", "1/17", ["1/13", "1/221", "4/51"], "3 aces remain among 51 cards: 3/51 = 1/17.", d="medium", t=40, texts=True, ver=E("conditional", Fraction(1, 17), case="second_ace_given_first")))
    out.append(mk(sub, "A family has two children. Assume each child is equally likely to be a boy or a girl, independently. Given that at least one is a boy, what is the probability that both are boys?", "1/3", ["1/2", "1/4", "2/3"], "Equally likely cases with at least one boy: BB, BG, GB. Only BB qualifies: 1/3.", d="hard", t=50, texts=True, ver=E("conditional", Fraction(1, 3), case="two_children_boy")))
    return out


def interest():
    out = []
    sub = "si-ci-comparison"
    out.append(mk(sub, "What is the difference between compound and simple interest on ₹5,000 at 10% per annum for 2 years?", 50, [100, 25, 55], "CI = 5000(1.21 − 1) = 1050; SI = 1000; difference 50.", d="medium", t=45, fmt=rupee, formula="CI − SI (2 yrs) = P(r/100)²", ver=X("5000*(0.1)**2", 50)))
    out.append(mk(sub, "The simple interest on a sum for 2 years at 10% is ₹600. What is the compound interest on the same sum for the same period and rate?", 630, [600, 660, 620], "P = 600 × 100 ÷ (2 × 10) = 3000; CI = 3000 × 0.21 = 630.", d="medium", t=50, fmt=rupee, ver=X("3000*(1.1**2-1)", 630)))
    out.append(mk(sub, "The difference between CI and SI on a sum for 2 years at 8% per annum is ₹32. What is the sum?", 5000, [4000, 4500, 6000], "P (r/100)² = 32 gives P = 32 × 10000 ÷ 64 = 5000.", d="hard", t=50, fmt=rupee, ver=X("32*100*100/(8*8)", 5000)))
    out.append(mk(sub, "For the same principal and rate over 3 years, which is larger and by how much on ₹10,000 at 10%?", "CI by ₹310", ["SI by ₹290", "CI by ₹300", "CI by ₹331"], "SI = 3000; CI = 10000 × (1.331 − 1) = 3310; difference 310.", d="hard", t=60, texts=True, ver=X("10000*(1.1**3-1)-10000*0.1*3", 310)))
    out.append(mk(sub, "On ₹8,000 at 5% per annum for 2 years, how much more does compound interest yield than simple interest?", 20, [10, 40, 25], "CI − SI = 8000 × 0.05² = 20.", d="medium", t=40, fmt=rupee, ver=X("8000*0.05**2", 20)))
    sub = "interest-calculations"
    out.append(mk(sub, "What is the simple interest on ₹8,000 at 7.5% per annum for 4 years?", 2400, [2000, 2250, 2800], "SI = 8000 × 7.5 × 4 / 100 = 2400.", d="easy", t=30, fmt=rupee, formula="SI = PRT/100", ver=X("8000*7.5*4/100", 2400)))
    out.append(mk(sub, "At simple interest, a sum becomes 3 times itself in 10 years. What is the rate per annum?", 20, [15, 25, 30], "Interest = 2P in 10 years: R = 2 × 100 / 10 = 20%.", d="medium", t=35, fmt=pct, ver=X("2*100/10", 20)))
    out.append(mk(sub, "What is the compound interest on ₹10,000 at 10% per annum, compounded annually, for 2 years?", 2100, [2000, 2200, 2310], "10000 × 1.21 − 10000 = 2100.", d="easy", t=35, fmt=rupee, formula="A = P(1 + r/100)ⁿ", ver=X("10000*(1.1**2-1)", 2100)))
    out.append(mk(sub, "What is the amount on ₹8,000 at 5% per annum compounded half-yearly for 1 year?", 8405, [8400, 8404, 8500], "Rate 2.5% per half-year for 2 periods: 8000 × 1.025² = 8405.", d="hard", t=50, fmt=rupee, ver=X("8000*1.025**2", 8405)))
    sub = "depreciation-growth"
    out.append(mk(sub, "A machine worth ₹50,000 depreciates 10% per year. What is its value after 2 years?", 40500, [40000, 41000, 45000], "50,000 × 0.9² = 40,500.", d="easy", t=35, fmt=rupee, formula="Value = P(1 − r/100)ⁿ", ver=X("50000*0.9**2", 40500)))
    out.append(mk(sub, "A town of 2,00,000 people grows 5% per year. What is the population after 2 years?", 220500, [220000, 210000, 222000], "200,000 × 1.05² = 220,500.", d="easy", t=35, ver=X("200000*1.05**2", 220500)))
    out.append(mk(sub, "A car bought for ₹5,00,000 loses 20% of its value in the first year and 10% in the second. What is its value after 2 years?", 360000, [350000, 375000, 400000], "500,000 × 0.8 × 0.9 = 360,000.", d="medium", t=40, fmt=rupee, typ="scenario", ver=X("500000*0.8*0.9", 360000)))
    out.append(mk(sub, "₹10,000 is invested at 20% per annum compounded annually. What is the amount after 3 years?", 17280, [16000, 17000, 17500], "10,000 × 1.2³ = 17,280.", d="medium", t=35, fmt=rupee, ver=X("10000*1.2**3", 17280)))
    return out
