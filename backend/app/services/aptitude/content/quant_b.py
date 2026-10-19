"""Topics D-E: Percentage; Profit, Loss and Discount."""

from __future__ import annotations

from .build import M, X, fnum, mk, pct, rupee


def percentage():
    out = []
    sub = "percentage-calculations"
    out.append(mk(sub, "What is 12.5% of 640?", 80, [64, 75, 96], "12.5% = 1/8, and 640 ÷ 8 = 80.", d="easy", t=20, typ="time_pressure", formula="x% of N = N × x / 100", ver=X("640*12.5/100", 80)))
    out.append(mk(sub, "If A's salary is 20% more than B's, B's salary is what percent less than A's?", 16.67, [20, 25, 16], "Let B = 100, A = 120. Difference 20 is 20/120 = 16.67% of A.", d="medium", t=40, fmt=pct,
                  formula="If A is x% more than B, B is x/(100+x) × 100 % less than A", ver=X("20/120*100", 16.67)))
    out.append(mk(sub, "If 35% of a number is 84, what is the number?", 240, [210, 260, 294], "Number = 84 × 100 ÷ 35 = 240.", d="easy", t=30, ver=X("84*100/35", 240)))
    out.append(mk(sub, "Which is greater: 18% of 450 or 25% of 340, and by how much?", "25% of 340 by 4", ["18% of 450 by 4", "25% of 340 by 14", "They are equal"],
                  "18% of 450 = 81 and 25% of 340 = 85, so the second is greater by 4.", d="medium", t=45, texts=True, ver=M("0.18*450=81 and 0.25*340=85, difference 4 (both products also re-checked via expression elsewhere).")))
    out.append(mk(sub, "A test has 80 questions and a candidate answers 70% of them correctly. How many are correct?", 56, [48, 54, 60], "70% of 80 = 0.7 × 80 = 56.", d="easy", t=20, typ="scenario", ver=X("0.7*80", 56)))
    sub = "percentage-fraction"
    out.append(mk(sub, "Express 3/16 as a percentage.", 18.75, [16.5, 17.5, 19.25], "3/16 × 100 = 18.75%.", d="easy", t=25, fmt=pct, ver=X("3/16*100", 18.75)))
    out.append(mk(sub, "Express 37.5% as a fraction in lowest terms.", "3/8", ["5/12", "3/10", "7/16"], "37.5% = 375/1000 = 3/8.", d="easy", t=25, texts=True, ver=X("37.5/100", 0.375)))
    out.append(mk(sub, "Express 83⅓% as a fraction in lowest terms.", "5/6", ["4/5", "7/8", "6/7"], "83⅓% = 250/3 % = 250/300 = 5/6.", d="medium", t=30, texts=True, formula="16⅔% = 1/6, 33⅓% = 1/3, 66⅔% = 2/3, 83⅓% = 5/6", ver=X("250/300", 5 / 6)))
    out.append(mk(sub, "2/7 of a number is what percentage of it (to two decimals)?", 28.57, [27.5, 28.75, 29.17], "2/7 × 100 = 28.57%.", d="medium", t=30, fmt=pct, ver=X("2/7*100", 28.57)))
    sub = "successive-change"
    out.append(mk(sub, "A price rises by 20% and then by 25%. What is the net percentage increase?", 50, [45, 47.5, 55], "1.20 × 1.25 = 1.50, a 50% increase.", d="easy", t=30, fmt=pct, formula="Net = a + b + ab/100", ver=X("(1.2*1.25-1)*100", 50)))
    out.append(mk(sub, "A price is increased by 10% and then decreased by 10%. The net change is:", "1% decrease", ["No change", "1% increase", "10% decrease"], "1.10 × 0.90 = 0.99, a 1% decrease.", d="medium", t=30, texts=True, ver=X("(1.1*0.9-1)*100", -1)))
    out.append(mk(sub, "A town's population falls by 20% in one year and by another 20% in the next. What is the total percentage fall?", 36, [40, 32, 4], "0.8 × 0.8 = 0.64, a 36% fall.", d="medium", t=30, fmt=pct, ver=X("(1-0.8*0.8)*100", 36)))
    out.append(mk(sub, "The length of a rectangle increases by 20% and its breadth decreases by 10%. By what percent does its area change?", "8% increase", ["10% increase", "8% decrease", "2% increase"], "1.2 × 0.9 = 1.08, an 8% increase.", d="medium", t=40, texts=True, ver=X("(1.2*0.9-1)*100", 8)))
    sub = "marks-problems"
    out.append(mk(sub, "A student scores 210 marks and fails by 30 marks. If the pass mark is 40%, what are the maximum marks?", 600, [500, 525, 700], "Pass mark = 240, which is 40% of the maximum: 240 ÷ 0.4 = 600.", d="easy", t=40, typ="scenario", ver=X("(210+30)/0.4", 600)))
    out.append(mk(sub, "A candidate who gets 45% marks fails by 15 marks, while another who gets 55% passes by 25 marks. What is the maximum marks?", 400, [350, 450, 500], "10% of the maximum = 15 + 25 = 40, so the maximum is 400.", d="medium", t=50, ver=X("(15+25)/0.10", 400)))
    out.append(mk(sub, "In the setup of the previous question (45% fails by 15, 55% passes by 25), what is the passing mark?", 195, [180, 200, 220], "45% of 400 = 180, and 180 + 15 = 195.", d="medium", t=40, ver=X("0.45*400+15", 195)))
    out.append(mk(sub, "An exam has 5 papers of 80 marks each. A student needs 36% overall to pass and has scored 70, 65, 50 and 58 in four papers. What minimum mark does the fifth paper need?", 0, [1, 2, 5],
                  "36% of 400 = 144; so far 243 ≥ 144, so no further marks are required.", d="hard", t=50, typ="multi_step", ver=X("max(0, 0.36*400-(70+65+50+58))", 0)))
    sub = "election-problems"
    out.append(mk(sub, "In a two-candidate election the winner gets 58% of the votes and wins by 1,600 votes. What is the total number of votes cast?", 10000, [8000, 9500, 12000], "Margin = 58% − 42% = 16% of the total = 1,600, so total = 10,000.", d="easy", t=40, ver=X("1600/0.16", 10000)))
    out.append(mk(sub, "In an election 20% of 10,000 registered voters did not vote, and 5% of the votes cast were invalid. The winner got 60% of the valid votes. How many votes did the winner get?", 4560, [4800, 4600, 5700],
                  "Votes cast = 8,000; valid = 7,600; winner = 0.6 × 7,600 = 4,560.", d="medium", t=60, typ="multi_step", ver=X("10000*0.8*0.95*0.6", 4560)))
    out.append(mk(sub, "A candidate got 52% of the votes and won by 480 votes. How many votes were cast?", 12000, [10000, 11500, 15000], "Margin 52% − 48% = 4% = 480, so total = 12,000.", d="easy", t=35, ver=X("480/0.04", 12000)))
    out.append(mk(sub, "In an election between two candidates, 10% of voters did not vote. The winner got 55% of the votes cast and won by 900 votes. How many voters were registered?", 10000,
                  [9000, 9900, 11000], "Margin 10% of votes cast = 900, so votes cast = 9,000; registered = 9,000 ÷ 0.9 = 10,000.", d="hard", t=70, typ="multi_step", ver=X("900/0.10/0.9", 10000)))
    sub = "population-problems"
    out.append(mk(sub, "A town's population of 50,000 grows by 10% in the first year and 20% in the second. What is it after two years?", 66000, [65000, 64000, 70000], "50,000 × 1.1 × 1.2 = 66,000.", d="easy", t=35, ver=X("50000*1.1*1.2", 66000)))
    out.append(mk(sub, "A population of 1,20,000 decreases by 5% every year. What is it after 2 years?", 108300, [108000, 109500, 110000], "120,000 × 0.95² = 108,300.", d="medium", t=40, ver=X("120000*0.95*0.95", 108300)))
    out.append(mk(sub, "A population rose from 25,000 to 31,250 in a year. What is the percentage growth?", 25, [20, 22.5, 30], "(31,250 − 25,000)/25,000 × 100 = 25%.", d="easy", t=30, fmt=pct, ver=X("(31250-25000)/25000*100", 25)))
    out.append(mk(sub, "A town has 40,000 people. The population rises 10% in year one and falls 10% in year two. What is it after year two?", 39600, [40000, 39000, 40400], "40,000 × 1.1 × 0.9 = 39,600.", d="medium", t=35, ver=X("40000*1.1*0.9", 39600)))
    sub = "percentage-error"
    out.append(mk(sub, "The side of a square is measured 2% too large. What is the percentage error in its area?", 4.04, [4, 2.04, 4.4], "1.02² = 1.0404, an error of 4.04%.", d="medium", t=35, fmt=pct, formula="Area error = 2a + a²/100", ver=X("(1.02**2-1)*100", 4.04)))
    out.append(mk(sub, "The radius of a circle is measured 5% too small. What is the percentage error in its area?", 9.75, [10, 5, 9.5], "0.95² = 0.9025, so the area is 9.75% too small.", d="medium", t=35, fmt=pct, ver=X("(1-0.95**2)*100", 9.75)))
    out.append(mk(sub, "The edge of a cube is measured 3% too large. The error in its volume, to two decimals, is:", 9.27, [9, 9.09, 9.81], "1.03³ = 1.092727, an error of 9.27%.", d="hard", t=45, fmt=pct, ver=X("(1.03**3-1)*100", 9.27)))
    out.append(mk(sub, "A person's weight is recorded with a +4% error and the recorded value is 78 kg. What is the true weight?", 75, [74.88, 76, 72], "True = 78 ÷ 1.04 = 75 kg.", d="medium", t=35, fmt=lambda v: f"{fnum(v)} kg", ver=X("78/1.04", 75)))
    return out


def profit_loss():
    out = []
    sub = "cp-sp-mp"
    out.append(mk(sub, "An article costs ₹500. It is marked 20% above cost and sold at a 10% discount. What is the profit percentage?", 8, [10, 12, 6], "MP = 600; SP = 540; profit = 40, which is 8% of 500.", d="medium", t=45, fmt=pct, typ="scenario", ver=X("(600*0.9-500)/500*100", 8)))
    out.append(mk(sub, "An article is sold for ₹1,260 at a 10% loss. What is its cost price?", 1400, [1386, 1300, 1450], "CP = 1260 ÷ 0.9 = 1400.", d="easy", t=30, fmt=rupee, formula="CP = SP × 100/(100 − loss%)", ver=X("1260/0.9", 1400)))
    out.append(mk(sub, "A shirt has marked price ₹800 and is sold at a 15% discount, giving a 25% profit. What is the cost price?", 544, [510, 560, 600], "SP = 680; CP = 680 ÷ 1.25 = 544.", d="medium", t=45, fmt=rupee, ver=X("800*0.85/1.25", 544)))
    out.append(mk(sub, "A trader sells a phone for ₹9,000 at a 25% profit. What was his cost price?", 7200, [6750, 7000, 7500], "CP = 9000 ÷ 1.25 = 7200.", d="easy", t=30, fmt=rupee, typ="scenario", ver=X("9000/1.25", 7200)))
    sub = "profit-loss-percent"
    out.append(mk(sub, "An article bought for ₹480 is sold for ₹552. What is the profit percentage?", 15, [12, 14, 16], "Profit 72 ÷ 480 × 100 = 15%.", d="easy", t=30, fmt=pct, formula="Profit% = profit/CP × 100", ver=X("(552-480)/480*100", 15)))
    out.append(mk(sub, "An article sold for ₹1,350 incurs a 10% loss. At what price must it be sold to gain 10%?", 1650, [1485, 1500, 1750], "CP = 1350 ÷ 0.9 = 1500; SP at +10% = 1650.", d="medium", t=45, fmt=rupee, ver=X("1350/0.9*1.1", 1650)))
    out.append(mk(sub, "A sells to B at 20% profit and B sells to C at 25% profit. If C pays ₹1,500, what did A pay?", 1000, [900, 1100, 1250], "A's cost = 1500 ÷ (1.25 × 1.2) = 1000.", d="medium", t=45, fmt=rupee, ver=X("1500/(1.25*1.2)", 1000)))
    out.append(mk(sub, "A retailer buys 40 notebooks for ₹800 and sells all for ₹1,000. What is his profit percentage?", 25, [20, 22, 30], "Profit 200 ÷ 800 = 25%.", d="easy", t=30, fmt=pct, typ="scenario", ver=X("(1000-800)/800*100", 25)))
    sub = "discounts"
    out.append(mk(sub, "A marked price is ₹1,500. Two successive discounts of 20% and 10% are given. What is the selling price?", 1080, [1050, 1100, 1125], "1500 × 0.8 × 0.9 = 1080.", d="easy", t=35, fmt=rupee, ver=X("1500*0.8*0.9", 1080)))
    out.append(mk(sub, "A shopkeeper marks goods 25% above cost and allows a 12% discount. What is his profit percentage?", 10, [13, 8, 12], "1.25 × 0.88 = 1.10, a 10% profit.", d="medium", t=40, fmt=pct, ver=X("(1.25*0.88-1)*100", 10)))
    out.append(mk(sub, "By what percent must a shopkeeper discount goods marked 40% above cost to still make a 12% profit?", 20, [15, 25, 28], "1.4 × (1 − d) = 1.12, so 1 − d = 0.8 and d = 20%.", d="hard", t=50, fmt=pct, ver=X("(1-1.12/1.4)*100", 20)))
    out.append(mk(sub, "An item marked ₹2,000 is sold at a 15% discount. What is the selling price?", 1700, [1600, 1750, 1800], "2000 × 0.85 = 1700.", d="easy", t=20, typ="time_pressure", fmt=rupee, ver=X("2000*0.85", 1700)))
    sub = "faulty-weights"
    out.append(mk(sub, "A dishonest shopkeeper sells at cost price but uses a 900 g weight for 1 kg. What is his gain percentage (two decimals)?", 11.11, [10, 11, 12.5], "He gives 900 g but charges for 1000 g: gain = 100/900 × 100 = 11.11%.", d="medium", t=40, fmt=pct, formula="Gain% = (error / true weight given) × 100", ver=X("100/900*100", 11.11)))
    out.append(mk(sub, "A trader uses a 960 g weight for 1 kg and sells at cost price. What is his gain percentage (two decimals)?", 4.17, [4, 4.25, 4.5], "Gain = 40/960 × 100 = 4.17%.", d="medium", t=40, fmt=pct, ver=X("40/960*100", 4.17)))
    out.append(mk(sub, "A dealer uses a 800 g weight for 1 kg and also marks his price 10% above cost. What is his total profit percentage?", 37.5, [30, 35, 40], "Goods worth 800 g are sold at 1.1 × the cost of 1000 g: 1.1 × 1000/800 = 1.375, a 37.5% profit.", d="hard", t=60, fmt=pct, ver=X("(1.1*1000/800-1)*100", 37.5)))
    out.append(mk(sub, "A trader claims to sell at cost price but uses a 950 g weight for 1 kg. What is his gain percentage (two decimals)?", 5.26, [5, 5.5, 4.76], "Gain = 50/950 × 100 = 5.26%.", d="medium", t=40, fmt=pct, ver=X("50/950*100", 5.26)))
    out.append(mk(sub, "A dishonest merchant buys using a 1,100 g weight and sells using a 900 g weight, each called '1 kg', at cost price. What is his overall gain percentage (two decimals)?", 22.22, [20, 22, 25],
                  "He receives 1,100 g of goods per 'kg' bought but delivers 900 g per 'kg' sold: 1100/900 = 1.2222, a 22.22% gain.", d="hard", t=60, fmt=pct, typ="multi_step", ver=X("(1100/900-1)*100", 22.22)))
    sub = "number-of-articles"
    out.append(mk(sub, "If the cost price of 15 articles equals the selling price of 12 articles, what is the profit percentage?", 25, [20, 15, 30], "Let SP of 1 = 15/12 CP of 1 = 1.25 CP: profit 25%.", d="medium", t=40, fmt=pct, ver=X("(15/12-1)*100", 25)))
    out.append(mk(sub, "If the selling price of 25 articles equals the cost price of 20 articles, what is the loss percentage?", 20, [25, 15, 16], "SP of 1 = 20/25 = 0.8 CP: a 20% loss.", d="medium", t=40, fmt=pct, ver=X("(1-20/25)*100", 20)))
    out.append(mk(sub, "By selling 12 pens a vendor recovers the cost of 15 pens. What is his gain percentage?", 25, [20, 15, 30], "15 pens' cost is received for 12 pens, so each pen sells at 15/12 = 1.25 × cost.", d="medium", t=40, fmt=pct, typ="scenario", ver=X("(15/12-1)*100", 25)))
    out.append(mk(sub, "A trader buys 20 articles for ₹100 and sells them at 4 for ₹24. What is his profit percentage?", 20, [10, 15, 25], "CP each = ₹5; SP each = ₹6; profit = 1/5 = 20%.", d="medium", t=45, fmt=pct, ver=X("(24/4-100/20)/(100/20)*100", 20)))
    sub = "common-selling-price"
    out.append(mk(sub, "Two articles are sold at ₹1,200 each, one at a 20% profit and the other at a 20% loss. What is the overall result?", "4% loss", ["No loss, no gain", "4% gain", "2% loss"],
                  "CPs: 1200/1.2 = 1000 and 1200/0.8 = 1500; total CP 2500 vs total SP 2400, a loss of 100 = 4%.", d="medium", t=60, texts=True, formula="Loss% = (x²/100) %", ver=X("(2400-2500)/2500*100", -4)))
    out.append(mk(sub, "Two articles are sold at ₹990 each, one at a 10% gain and the other at a 10% loss. What is the overall loss percentage?", 1, [0, 2, 10], "Loss% = 10²/100 = 1%.", d="medium", t=45, fmt=pct, ver=X("10*10/100", 1)))
    out.append(mk(sub, "Two items are sold at the same price, one at a 25% profit and the other at a 25% loss. What is the net loss percentage?", 6.25, [5, 6, 12.5], "Loss% = 25²/100 = 6.25%.", d="medium", t=35, fmt=pct, ver=X("25*25/100", 6.25)))
    out.append(mk(sub, "A man sells two cycles at ₹3,000 each, gaining 20% on one and losing 20% on the other. What is his net loss in rupees?", 250, [100, 200, 300], "CPs: 2500 and 3750 = 6250; SP = 6000; loss = 250.", d="hard", t=60, fmt=rupee, typ="scenario", ver=X("3000/1.2+3000/0.8-6000", 250)))
    return out
