"""Topics A-C: Vedic Maths, Number System, Average."""

from __future__ import annotations

import math

from .build import E, M, X, fnum, mk


def vedic():
    out = []
    sub = "fast-calculation"
    for n in (35, 65, 85, 95):
        a = n // 10
        out.append(mk(sub, f"Using the 'square of a number ending in 5' trick (multiply the tens digit by the next digit, then append 25), find {n}².",
                      n * n, [n * n + 100, n * n - 100, n * n + 25, (n + 5) ** 2 // 2],
                      f"{a} × {a + 1} = {a * (a + 1)}, then append 25 to get {a * (a + 1)}25.",
                      d="easy", t=25, typ="time_pressure", formula="(n5)² = n(n+1) | 25",
                      ver=X(f"{n}*{n}", n * n)))
    out.append(mk(sub, "Multiply 53 × 11 using the 'sum of digits in the middle' method.", 583, [593, 573, 538, 5300 // 9],
                  "Write 5, then 5 + 3 = 8, then 3: 583.", d="easy", t=20, typ="time_pressure",
                  formula="ab × 11 = a | (a+b) | b", ver=X("53*11", 583)))
    out.append(mk(sub, "Using the base-100 method, find 97 × 94.", 9118, [9128, 9108, 9018, 9218],
                  "Deficits are 3 and 6. Cross-subtract: 97 − 6 = 91; multiply deficits: 3 × 6 = 18. Result 9118.",
                  d="medium", t=40, formula="(100−a)(100−b) = (100−a−b)·100 + ab", ver=X("97*94", 9118)))
    out.append(mk(sub, "Using (a + b)(a − b) = a² − b², find 51 × 49.", 2499, [2501, 2599, 2399, 2489],
                  "51 × 49 = (50 + 1)(50 − 1) = 2500 − 1 = 2499.", d="easy", t=25, typ="time_pressure",
                  formula="(a+b)(a−b) = a² − b²", ver=X("51*49", 2499)))
    sub = "calculation-shortcuts"
    out.append(mk(sub, "Quickly compute 47 × 99 by writing 99 as 100 − 1.", 4653, [4743, 4563, 4653 + 100, 4700],
                  "47 × 100 − 47 = 4700 − 47 = 4653.", d="easy", t=25, typ="time_pressure",
                  formula="n × 99 = 100n − n", ver=X("47*100-47", 4653)))
    out.append(mk(sub, "Multiply 36 × 25 using the fact that 25 = 100 ÷ 4.", 900, [800, 950, 925, 960],
                  "36 ÷ 4 = 9, then × 100 = 900.", d="easy", t=20, typ="time_pressure", formula="n × 25 = n × 100 ÷ 4",
                  ver=X("36*100/4", 900)))
    out.append(mk(sub, "A shop assistant needs 12.5% of ₹960 quickly. Using 12.5% = 1/8, what is it?", 120, [96, 108, 125, 150],
                  "960 ÷ 8 = 120.", d="easy", t=25, typ="scenario", formula="12.5% = 1/8", fmt=lambda v: f"₹{v}",
                  ver=X("960/8", 120)))
    out.append(mk(sub, "Using complements from a power of 10, compute 1000 − 367.", 633, [643, 623, 733, 637],
                  "Subtract each digit from 9 and the last from 10: 9−3=6, 9−6=3, 10−7=3 → 633.", d="easy", t=20,
                  typ="time_pressure", formula="Nikhilam: all from 9, last from 10", ver=X("1000-367", 633)))
    return out


def number_system():
    out = []
    sub = "classification-of-numbers"
    out.append(mk(sub, "Which of the following numbers is prime?", 97, [91, 87, 93, 91 + 2 * 3], "91 = 7 × 13, 87 = 3 × 29, 93 = 3 × 31 are composite; 97 has no divisor up to 9.",
                  d="easy", t=40, formula="Test divisibility by primes up to √n", ver=E("single_match", 97, candidates=[91, 87, 97, 93], predicate={"name": "prime"})))
    out.append(mk(sub, "How many prime numbers lie between 20 and 40?", 4, [3, 5, 6], "The primes are 23, 29, 31 and 37.", d="easy", t=40,
                  ver=E("count_primes_range", 4, lo=21, hi=39)))
    out.append(mk(sub, "Which pair of numbers is co-prime?", "15 and 28", ["14 and 21", "18 and 27", "24 and 36"],
                  "Co-prime means HCF = 1. HCF(15, 28) = 1, whereas the other pairs share 7, 9 and 12.", d="medium", t=45, texts=True,
                  formula="Co-prime ⇔ HCF = 1",
                  ver=E("single_match", "15 and 28", candidates=[[14, 21], [15, 28], [18, 27], [24, 36]], predicate={"name": "coprime"})))
    out.append(mk(sub, "Which of the following is a perfect number (equal to the sum of its proper divisors)?", 28, [24, 30, 36],
                  "Proper divisors of 28: 1, 2, 4, 7, 14 sum to 28.", d="medium", t=45, formula="Perfect number: σ(n) − n = n",
                  ver=E("single_match", 28, candidates=[24, 28, 30, 36], predicate={"name": "perfect"})))
    sub = "divisibility-rules"
    out.append(mk(sub, "Which of the following numbers is divisible by 11?", 2728, [2738, 2718, 2748],
                  "Alternating digit sum for 2728: (2 + 2) − (7 + 8) = −11, a multiple of 11.", d="easy", t=40,
                  formula="Divisible by 11 ⇔ (sum of odd-place digits − sum of even-place digits) is 0 or a multiple of 11",
                  ver=E("single_match", 2728, candidates=[2738, 2718, 2728, 2748], predicate={"name": "divisible", "by": 11})))
    out.append(mk(sub, "If the number 52x4 is divisible by 9, what is the digit x?", 7, [5, 6, 8],
                  "Digit sum 5 + 2 + x + 4 = 11 + x must be a multiple of 9, so x = 7.", d="medium", t=40,
                  formula="Divisible by 9 ⇔ digit sum divisible by 9", ver=E("missing_digit", 7, template="52?4", divisor=9)))
    out.append(mk(sub, "If 83x56 is divisible by 11, find the digit x.", 5, [3, 4, 6],
                  "From the right: (6 + x + 8) − (5 + 3) = x + 6 must be a multiple of 11, so x = 5.", d="medium", t=60,
                  formula="Alternating digit sum divisible by 11", ver=E("missing_digit", 5, template="83?56", divisor=11)))
    out.append(mk(sub, "Which of the following numbers is divisible by 8?", 7416, [7418, 7412, 7414],
                  "A number is divisible by 8 when its last three digits are: 416 ÷ 8 = 52.", d="easy", t=35,
                  formula="Divisible by 8 ⇔ last three digits divisible by 8",
                  ver=E("single_match", 7416, candidates=[7418, 7412, 7416, 7414], predicate={"name": "divisible", "by": 8})))
    sub = "factorials"
    for n, ans, wr in ((50, 12, [10, 11, 13]), (100, 24, [20, 25, 22]), (125, 31, [30, 28, 32])):
        out.append(mk(sub, f"How many zeros are at the end of {n}!?", ans, wr,
                      f"Count factors of 5: " + " + ".join(str(n // 5 ** k) for k in range(1, 5) if n // 5 ** k) + f" = {ans}.",
                      d="medium", t=40, formula="Trailing zeros = ⌊n/5⌋ + ⌊n/25⌋ + ⌊n/125⌋ + …", ver=E("trailing_zeros", ans, n=n)))
    out.append(mk(sub, "What is the highest power of 3 that divides 30! exactly?", 14, [10, 13, 15], "⌊30/3⌋ + ⌊30/9⌋ + ⌊30/27⌋ = 10 + 3 + 1 = 14.",
                  d="hard", t=60, formula="Legendre: Σ ⌊n/pᵏ⌋", ver=E("prime_power_in_factorial", 14, n=30, p=3)))
    out.append(mk(sub, "Evaluate 7! ÷ 5!.", 42, [35, 49, 56], "7!/5! = 7 × 6 = 42.", d="easy", t=20, typ="time_pressure", ver=X("factorial(7)/factorial(5)", 42)))
    sub = "unit-digit"
    for base, exp, ans, cyc in ((7, 45, 7, "7, 9, 3, 1"), (13, 102, 9, "3, 9, 7, 1"), (2, 2023, 8, "2, 4, 8, 6"), (9, 99, 9, "9, 1")):
        wr = [x for x in (1, 3, 5, 6, 7, 9, 2, 4, 8) if x != ans][:4]
        out.append(mk(sub, f"What is the unit digit of {base}^{exp}?", ans, wr,
                      f"The unit digit cycles through {cyc}; the exponent's position in the cycle gives {ans}.", d="medium", t=45,
                      formula="Use the cycle of the unit digit and the exponent modulo the cycle length", ver=E("unit_digit", ans, base=base, exp=exp)))
    out.append(mk(sub, "What is the unit digit of 17 × 23 × 49?", 9, [1, 3, 7], "7 × 3 = 21 → 1; 1 × 9 = 9.", d="easy", t=30, typ="time_pressure",
                  ver=E("unit_digit_product", 9, factors=[17, 23, 49])))
    sub = "number-of-factors"
    out.append(mk(sub, "How many factors does 360 have?", 24, [18, 20, 30], "360 = 2³ × 3² × 5; factors = (3+1)(2+1)(1+1) = 24.", d="medium", t=40,
                  formula="N = aᵖbᵠcʳ ⇒ (p+1)(q+1)(r+1) factors", ver=E("factor_count", 24, n=360)))
    out.append(mk(sub, "What is the sum of all factors of 36?", 91, [81, 85, 97], "36 = 2² × 3²; sum = (1+2+4)(1+3+9) = 7 × 13 = 91.", d="medium", t=45,
                  formula="σ(N) = (a^(p+1)−1)/(a−1) × …", ver=E("factor_sum", 91, n=36)))
    out.append(mk(sub, "How many odd factors does 180 have?", 6, [4, 8, 9], "180 = 2² × 3² × 5; odd factors come from 3² × 5: (2+1)(1+1) = 6.", d="medium", t=45,
                  ver=E("odd_factor_count", 6, n=180)))
    out.append(mk(sub, "In how many ways can 72 be written as a product of two positive factors (order ignored)?", 6, [5, 8, 12],
                  "72 = 2³ × 3² has 12 factors, which pair up into 12 ÷ 2 = 6 pairs.", d="hard", t=60, ver=E("factor_pair_count", 6, n=72)))
    sub = "remainders"
    out.append(mk(sub, "What is the remainder when 2^100 is divided by 7?", 2, [1, 3, 4], "2³ ≡ 1 (mod 7) and 100 = 3 × 33 + 1, so 2^100 ≡ 2.", d="medium", t=50,
                  formula="Find the cycle of remainders", ver=E("powmod", 2, base=2, exp=100, mod=7)))
    out.append(mk(sub, "What is the remainder when 17^200 is divided by 18?", 1, [0, 2, 17], "17 ≡ −1 (mod 18), and (−1)^200 = 1.", d="medium", t=40,
                  ver=E("powmod", 1, base=17, exp=200, mod=18)))
    out.append(mk(sub, "What is the remainder when 1234567 is divided by 9?", 1, [0, 2, 7], "The digit sum 28 leaves remainder 1 on division by 9.", d="easy", t=30,
                  formula="n mod 9 = (digit sum) mod 9", ver=E("mod_value", 1, n=1234567, mod=9)))
    out.append(mk(sub, "Find the least number which leaves remainder 5 when divided by 6, 8 and 12.", 29, [24, 26, 53], "LCM(6, 8, 12) = 24, so the number is 24 + 5 = 29.",
                  d="medium", t=45, formula="LCM + common remainder", ver=E("least_with_remainder", 29, divisors=[6, 8, 12], remainder=5)))
    sub = "hcf-lcm"
    out.append(mk(sub, "Find the HCF of 84 and 126.", 42, [21, 6, 14], "84 = 2²·3·7, 126 = 2·3²·7; HCF = 2·3·7 = 42.", d="easy", t=30, ver=E("hcf", 42, numbers=[84, 126])))
    out.append(mk(sub, "Find the LCM of 12, 18 and 30.", 180, [90, 120, 360], "12 = 2²·3, 18 = 2·3², 30 = 2·3·5; LCM = 2²·3²·5 = 180.", d="easy", t=35, ver=E("lcm", 180, numbers=[12, 18, 30])))
    out.append(mk(sub, "The HCF of two numbers is 12 and their LCM is 360. If one number is 72, the other is:", 60, [48, 90, 120],
                  "Product of the numbers = HCF × LCM, so the other = 12 × 360 ÷ 72 = 60.", d="medium", t=40, formula="a × b = HCF × LCM", ver=X("12*360/72", 60)))
    out.append(mk(sub, "Three bells ring every 12, 18 and 30 minutes. They ring together at 9:00 a.m. At what time will they next ring together?", "12:00 noon",
                  ["10:30 a.m.", "11:00 a.m.", "12:30 p.m."], "LCM(12, 18, 30) = 180 minutes = 3 hours after 9:00 a.m.", d="medium", t=50, typ="scenario",
                  texts=True, formula="Next meeting after LCM of intervals",
                  ver=M("LCM(12,18,30)=180 min=3 h, so 9:00 + 3 h = 12:00 noon; the LCM itself is machine-checked in the previous question.")))
    out.append(mk(sub, "Find the largest number that divides 62, 136 and 245 leaving remainders 2, 4 and 5 respectively.", 12, [6, 3, 24],
                  "Subtract the remainders: 60, 132, 240. Their HCF is 12 (and 12 exceeds every remainder).", d="hard", t=75, formula="HCF of (number − remainder)",
                  ver=E("hcf_remainders", 12, numbers=[62, 136, 245], remainders=[2, 4, 5])))
    return out


def average():
    out = []
    sub = "average-calculations"
    out.append(mk(sub, "What is the average of the first 20 natural numbers?", 10.5, [10, 11, 20.5], "Sum = 20 × 21 / 2 = 210; average = 210 ÷ 20 = 10.5.", d="easy", t=25,
                  formula="Average of 1..n = (n+1)/2", ver=X("(20+1)/2", 10.5)))
    out.append(mk(sub, "A student's average in 4 subjects is 72. What must the fifth subject's mark be to raise the average to 75?", 87, [84, 80, 90],
                  "Needed total = 5 × 75 = 375; current total = 4 × 72 = 288; difference = 87.", d="easy", t=40, typ="scenario", formula="Required = new total − old total",
                  ver=X("5*75-4*72", 87)))
    out.append(mk(sub, "The average of five consecutive even numbers is 36. What is the largest of them?", 40, [38, 42, 44], "The middle number is the average (36), so they are 32, 34, 36, 38, 40.",
                  d="easy", t=30, ver=X("36+2*2", 40)))
    out.append(mk(sub, "The average of 12 numbers is 15. If every number is multiplied by 3, what is the new average?", 45, [15, 30, 60], "Multiplying every item by k multiplies the average by k.",
                  d="easy", t=20, typ="time_pressure", ver=X("15*3", 45)))
    sub = "inclusion-exclusion"
    out.append(mk(sub, "The average age of 30 students is 14 years. When the teacher's age is included, the average rises to 15. What is the teacher's age?", 45, [44, 40, 46],
                  "Total with teacher = 31 × 15 = 465; without = 30 × 14 = 420; teacher = 45.", d="medium", t=45, typ="scenario", ver=X("31*15-30*14", 45)))
    out.append(mk(sub, "The average of 10 numbers is 40. The average of the first 4 is 35 and of the last 5 is 45. What is the 5th number?", 35, [30, 40, 45],
                  "Total 400; first four 140; last five 225; the 5th = 400 − 140 − 225 = 35.", d="medium", t=50, ver=X("10*40-4*35-5*45", 35)))
    out.append(mk(sub, "A batsman's average after his 12th innings is 48, which is 2 more than before it. How many runs did he score in the 12th innings?", 70, [58, 68, 72],
                  "Before: 11 × 46 = 506; after: 12 × 48 = 576; the 12th innings = 70.", d="medium", t=50, typ="scenario", ver=X("12*48-11*46", 70)))
    out.append(mk(sub, "The average weight of 8 people increases by 2.5 kg when a person weighing 65 kg is replaced by a new person. What is the new person's weight?", 85, [80, 87.5, 90],
                  "Increase in total = 8 × 2.5 = 20 kg, so the new person weighs 65 + 20 = 85 kg.", d="medium", t=40, fmt=lambda v: f"{fnum(v)} kg", ver=X("65+8*2.5", 85)))
    sub = "weighted-average"
    out.append(mk(sub, "Section A has 40 students averaging 72 marks and Section B has 60 students averaging 80. What is the combined average?", 76.8, [76, 77, 78.4],
                  "(40 × 72 + 60 × 80) ÷ 100 = (2880 + 4800) ÷ 100 = 76.8.", d="easy", t=40, typ="scenario", formula="Σ(nᵢ × xᵢ) / Σnᵢ", ver=X("(40*72+60*80)/100", 76.8)))
    out.append(mk(sub, "20 kg of rice costing ₹40/kg is mixed with 30 kg costing ₹50/kg. What is the average cost per kg of the mixture?", 46, [45, 47, 48],
                  "(20 × 40 + 30 × 50) ÷ 50 = 2300 ÷ 50 = 46.", d="easy", t=40, fmt=lambda v: f"₹{v}", ver=X("(20*40+30*50)/50", 46)))
    out.append(mk(sub, "A student scores 60, 70 and 90 in three tests weighted in the ratio 2 : 3 : 5. What is the weighted average?", 78, [73.33, 75, 80],
                  "(2 × 60 + 3 × 70 + 5 × 90) ÷ 10 = 780 ÷ 10 = 78.", d="medium", t=45, ver=X("(2*60+3*70+5*90)/10", 78)))
    out.append(mk(sub, "The average age of a group of men and women is 27. Men average 30 and women average 24. What is the ratio of men to women?", "1 : 1", ["2 : 1", "1 : 2", "3 : 2"],
                  "Men are 3 above the mean and women 3 below, so they are equal in number.", d="hard", t=50, texts=True, formula="Alligation on averages",
                  ver=M("Distance of each group from the mean is 3 (30−27 and 27−24), so by alligation the ratio is 3:3 = 1:1.")))
    return out
