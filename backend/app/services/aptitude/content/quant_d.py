"""Topics M, N, T, U, V, W: Time & Work, Pipes, Speed/Distance, Trains, Boats, Height & Distance."""

from __future__ import annotations

import math
from fractions import Fraction

from .build import M, X, fnum, mk, rupee


def mixed(n: int, d: int) -> str:
    g = math.gcd(n, d)
    n, d = n // g, d // g
    whole, rem = divmod(n, d)
    if rem == 0:
        return str(whole)
    return f"{whole} {rem}/{d}" if whole else f"{rem}/{d}"


def days(v):
    return f"{fnum(v)} days"


def hours(v):
    return f"{fnum(v)} hours"


def time_work():
    out = []
    sub = "work-calculations"
    out.append(mk(sub, "A can complete a piece of work in 12 days. What fraction of the work does he finish in 5 days?", "5/12", ["1/12", "7/12", "5/6"], "A does 1/12 of the work per day, so 5 days give 5/12.", d="easy", t=20, texts=True, formula="Work per day = 1/days", ver=X("5/12", 5 / 12)))
    out.append(mk(sub, "12 men can finish a job in 20 days. How many days will 15 men take?", 16, [18, 25, 15], "Man-days are constant: 12 × 20 = 240, and 240 ÷ 15 = 16.", d="easy", t=30, fmt=days, formula="M₁D₁ = M₂D₂", ver=X("12*20/15", 16)))
    out.append(mk(sub, "A does one-third of a job in 5 days. How many days would he need for the whole job?", 15, [10, 12, 20], "Whole job = 3 × 5 = 15 days.", d="easy", t=20, fmt=days, typ="time_pressure", ver=X("5*3", 15)))
    out.append(mk(sub, "A can finish a task in 10 days and works on it for 4 days. What fraction of the task is still left?", "3/5", ["2/5", "1/2", "4/5"], "Done = 4/10 = 2/5, so left = 3/5.", d="easy", t=25, texts=True, ver=X("1-4/10", 0.6)))
    sub = "work-together"
    out.append(mk(sub, "A can do a job in 20 days and B in 30 days. Working together, how many days do they need?", 12, [10, 15, 25], "1/20 + 1/30 = 5/60 = 1/12 per day.", d="easy", t=30, fmt=days, formula="Together = ab/(a+b)", ver=X("20*30/(20+30)", 12)))
    out.append(mk(sub, "A and B together finish a job in 12 days; A alone takes 20 days. How long would B alone take?", 30, [24, 32, 36], "1/12 − 1/20 = 1/30 per day.", d="medium", t=40, fmt=days, ver=X("1/(1/12-1/20)", 30)))
    out.append(mk(sub, "A, B and C can do a job alone in 10, 15 and 30 days. How many days will all three take together?", 5, [6, 7.5, 10], "1/10 + 1/15 + 1/30 = 6/30 = 1/5.", d="medium", t=40, fmt=days, ver=X("1/(1/10+1/15+1/30)", 5)))
    out.append(mk(sub, "A and B can finish a job in 6 days, B and C in 8 days, and C and A in 12 days. How long will all three take together?", mixed(16, 3) + " days", ["6 days", "4 days", "7 1/2 days"],
                  "Adding the three rates gives 2(A+B+C) = 1/6 + 1/8 + 1/12 = 3/8, so A+B+C = 3/16 per day: 16/3 days.", d="hard", t=70, texts=True, ver=X("1/((1/6+1/8+1/12)/2)", 16 / 3)))
    sub = "efficiency"
    out.append(mk(sub, "A is twice as efficient as B and together they finish a job in 18 days. How long would B alone take?", 54, [27, 36, 45], "Rates 2x and x: 3x × 18 = 1 gives x = 1/54, so B alone takes 54 days.", d="medium", t=45, fmt=days, ver=X("3*18", 54)))
    out.append(mk(sub, "A is 25% more efficient than B. If B alone takes 20 days, how long does A take?", 16, [15, 18, 25], "Time is inversely proportional to efficiency: 20 ÷ 1.25 = 16.", d="medium", t=35, fmt=days, ver=X("20/1.25", 16)))
    out.append(mk(sub, "A is three times as good a workman as B, and takes 40 days less than B alone. How many days do they take working together?", 15, [12, 18, 20], "B takes x, A takes x/3, so x − x/3 = 40 gives x = 60 and A = 20; together 1/(1/20 + 1/60) = 15.", d="hard", t=70, fmt=days, typ="multi_step", ver=X("1/(1/20+1/60)", 15)))
    out.append(mk(sub, "The efficiencies of A and B are in the ratio 3 : 2. If A alone takes 20 days, how long does B alone take?", 30, [24, 40, 45], "Time ratio is 2 : 3, so B takes 20 × 3/2 = 30 days.", d="easy", t=30, fmt=days, ver=X("20*3/2", 30)))
    sub = "men-women-children"
    out.append(mk(sub, "12 men or 18 women can finish a job in 14 days. How many days will 8 men and 16 women take together?", 9, [10, 8, 12], "1 man = 1.5 women, so 8 men = 12 women; total 28 women; 18 × 14 ÷ 28 = 9.", d="hard", t=70, fmt=days, typ="multi_step", ver=X("18*14/(8*1.5+16)", 9)))
    out.append(mk(sub, "2 men and 3 women can do a job in 10 days. How many days will 4 men and 6 women take?", 5, [4, 8, 20], "Doubling the workforce halves the time.", d="easy", t=25, fmt=days, ver=X("10/2", 5)))
    out.append(mk(sub, "10 men can finish a job in 15 days, and 5 women do as much work as 3 men. How many days will 6 men and 10 women take?", 12.5, [10, 15, 11], "10 women = 6 men, so the team equals 12 men: 10 × 15 ÷ 12 = 12.5.", d="hard", t=70, fmt=days, ver=X("10*15/(6+10*3/5)", 12.5)))
    out.append(mk(sub, "4 men can do a job in 30 days. If 1 man = 2 women = 4 children in work, how many days will 2 men, 2 women and 4 children take?", 30, [24, 20, 40], "2 women = 1 man and 4 children = 1 man, so the team equals 4 men: 30 days.", d="hard", t=60, fmt=days, ver=X("4*30/(2+2/2+4/4)", 30)))
    sub = "wages"
    out.append(mk(sub, "A can do a job in 12 days and B in 18 days. They finish it together and are paid ₹1,500. What is A's share?", 900, [750, 800, 1000], "Shares are in the ratio of work done: 1/12 : 1/18 = 3 : 2, so A gets 3/5 of 1,500.", d="medium", t=45, fmt=rupee, ver=X("1500*(1/12)/(1/12+1/18)", 900)))
    out.append(mk(sub, "A, B and C can do a job in 10, 15 and 30 days and share ₹3,000 for completing it together. How much does C get?", 500, [300, 600, 1000], "Efficiency ratio 3 : 2 : 1, so C gets 1/6 of 3,000.", d="medium", t=45, fmt=rupee, ver=X("3000*(1/30)/(1/10+1/15+1/30)", 500)))
    out.append(mk(sub, "8 men working 6 days earn ₹9,600 in total. At the same daily wage, what would 5 men working 9 days earn?", 9000, [8000, 9600, 10800], "Wage per man-day = 9600 ÷ 48 = 200; 45 man-days × 200 = 9,000.", d="medium", t=45, fmt=rupee, typ="scenario", ver=X("9600/(8*6)*5*9", 9000)))
    out.append(mk(sub, "On a job paying ₹3,000, A works 4 days and B works 6 days at equal daily wages. How much does A receive?", 1200, [1000, 1500, 1800], "A's share = 4/10 of 3,000.", d="easy", t=30, fmt=rupee, ver=X("3000*4/10", 1200)))
    return out


def pipes():
    out = []
    sub = "inlets-outlets"
    out.append(mk(sub, "Pipe A fills a tank in 12 hours and pipe B fills it in 6 hours. Both open together, how long to fill the tank?", 4, [3, 6, 9], "1/12 + 1/6 = 3/12 = 1/4 per hour.", d="easy", t=30, fmt=hours, formula="Net rate = Σ inlets − Σ outlets", ver=X("1/(1/12+1/6)", 4)))
    out.append(mk(sub, "A pipe fills a tank in 10 hours but a leak empties it in 15 hours. With the leak, how long does the pipe take to fill the tank?", 30, [25, 20, 35], "1/10 − 1/15 = 1/30 per hour.", d="medium", t=40, fmt=hours, ver=X("1/(1/10-1/15)", 30)))
    out.append(mk(sub, "An inlet fills a tank in 8 hours and an outlet empties it in 12 hours. If both are open, how long to fill the empty tank?", 24, [20, 18, 30], "1/8 − 1/12 = 1/24 per hour.", d="easy", t=35, fmt=hours, ver=X("1/(1/8-1/12)", 24)))
    out.append(mk(sub, "Pipes A and B fill a tank in 20 and 30 minutes, and pipe C empties it in 60 minutes. All three are opened together. In how many minutes is the tank full?", 15, [12, 18, 20], "1/20 + 1/30 − 1/60 = 4/60 = 1/15 per minute.", d="medium", t=50, fmt=lambda v: f"{fnum(v)} minutes", ver=X("1/(1/20+1/30-1/60)", 15)))
    sub = "parts-filled"
    out.append(mk(sub, "Pipes A and B fill a tank in 12 and 16 hours. Both are opened for 4 hours, then B is closed. How many more hours does A need to fill the rest?", 5, [4, 6, 7], "Both fill 4 × 7/48 = 7/12; remaining 5/12 at A's rate 1/12 takes 5 hours.", d="hard", t=70, fmt=hours, typ="multi_step", ver=X("(1-4*(1/12+1/16))/(1/12)", 5)))
    out.append(mk(sub, "A pipe fills 1/4 of a tank in 5 hours. How long to fill the whole tank?", 20, [15, 16, 25], "5 × 4 = 20 hours.", d="easy", t=20, fmt=hours, typ="time_pressure", ver=X("5*4", 20)))
    out.append(mk(sub, "A pipe fills a tank in 15 hours. What fraction of the tank is filled in 6 hours?", "2/5", ["1/3", "3/5", "7/15"], "6/15 = 2/5.", d="easy", t=20, texts=True, ver=X("6/15", 0.4)))
    out.append(mk(sub, "A tank is 1/3 full. A pipe that can fill the whole tank in 9 hours is opened. How long to fill the rest?", 6, [3, 4.5, 9], "Remaining 2/3 × 9 = 6 hours.", d="medium", t=30, fmt=hours, ver=X("(1-1/3)*9", 6)))
    sub = "pipe-time-problems"
    out.append(mk(sub, "Two pipes together fill a tank in 6 hours. One alone takes 10 hours. How long would the other take alone?", 15, [12, 16, 18], "1/6 − 1/10 = 1/15 per hour.", d="medium", t=40, fmt=hours, ver=X("1/(1/6-1/10)", 15)))
    out.append(mk(sub, "A tank fills in 8 hours normally, but a leak makes it take 10 hours. How long would the leak alone take to empty a full tank?", 40, [32, 36, 80], "1/8 − 1/10 = 1/40 per hour is the leak's rate.", d="hard", t=50, fmt=hours, ver=X("1/(1/8-1/10)", 40)))
    out.append(mk(sub, "Pipe A fills a tank in 20 minutes and pipe B in 30 minutes. They are opened alternately for one minute each, starting with A. How many minutes to fill the tank?", 24, [25, 30, 12], "Each 2-minute cycle fills 1/20 + 1/30 = 1/12, so 12 cycles = 24 minutes.", d="hard", t=70, fmt=lambda v: f"{fnum(v)} minutes", ver=X("2/(1/20+1/30)", 24)))
    out.append(mk(sub, "A tap fills a tank in 6 hours and a drain empties a full tank in 8 hours. With both open, how long to fill an empty tank?", 24, [14, 12, 48], "1/6 − 1/8 = 1/24 per hour.", d="medium", t=35, fmt=hours, ver=X("1/(1/6-1/8)", 24)))
    return out


def speed_distance():
    out = []
    sub = "tsd-basics"
    out.append(mk(sub, "A car covers 180 km in 3 hours. What is its speed?", 60, [45, 54, 90], "Speed = 180 ÷ 3 = 60 km/h.", d="easy", t=15, fmt=lambda v: f"{v} km/h", typ="time_pressure", formula="Speed = Distance / Time", ver=X("180/3", 60)))
    out.append(mk(sub, "How far does a vehicle travel in 45 minutes at 80 km/h?", 60, [45, 55, 64], "45 min = 0.75 h, and 80 × 0.75 = 60 km.", d="easy", t=25, fmt=lambda v: f"{v} km", ver=X("80*45/60", 60)))
    out.append(mk(sub, "Walking at 5 km/h a man reaches his office 10 minutes late; at 6 km/h he is 5 minutes early. How far is the office?", 7.5, [6, 8, 9], "d/5 − d/6 = 15/60, so d/30 = 1/4 and d = 7.5 km.", d="hard", t=70, fmt=lambda v: f"{fnum(v)} km", typ="scenario", ver=X("(15/60)/(1/5-1/6)", 7.5)))
    out.append(mk(sub, "Two cars start from towns 300 km apart and drive towards each other at 40 km/h and 60 km/h. After how many hours do they meet?", 3, [2.5, 3.5, 5], "Closing speed 100 km/h, so 300 ÷ 100 = 3 hours.", d="easy", t=30, fmt=hours, ver=X("300/(40+60)", 3)))
    sub = "unit-conversion"
    out.append(mk(sub, "Convert 72 km/h into m/s.", 20, [18, 22, 25], "Multiply by 5/18: 72 × 5/18 = 20.", d="easy", t=15, fmt=lambda v: f"{v} m/s", typ="time_pressure", formula="1 km/h = 5/18 m/s", ver=X("72*5/18", 20)))
    out.append(mk(sub, "Convert 15 m/s into km/h.", 54, [45, 60, 72], "Multiply by 18/5: 15 × 18/5 = 54.", d="easy", t=15, fmt=lambda v: f"{v} km/h", typ="time_pressure", ver=X("15*18/5", 54)))
    out.append(mk(sub, "If a driver increases speed by 25%, by what percentage does the time for the same trip decrease?", 20, [25, 15, 33.33], "Time falls to 1/1.25 = 0.8 of the original: a 20% decrease.", d="medium", t=35, fmt=lambda v: f"{fnum(v)}%", formula="Time ∝ 1/Speed", ver=X("(1-1/1.25)*100", 20)))
    out.append(mk(sub, "A cyclist covers 6 km in 18 minutes. What is his speed in km/h?", 20, [18, 24, 30], "18 min = 0.3 h, so 6 ÷ 0.3 = 20 km/h.", d="easy", t=30, fmt=lambda v: f"{v} km/h", ver=X("6/(18/60)", 20)))
    sub = "average-speed"
    out.append(mk(sub, "A man travels from A to B at 60 km/h and returns at 40 km/h. What is his average speed for the round trip?", 48, [50, 52, 45], "Average = 2·60·40/(60 + 40) = 48 km/h.", d="medium", t=35, fmt=lambda v: f"{v} km/h", formula="Equal distances: 2xy/(x+y)", ver=X("2*60*40/(60+40)", 48)))
    out.append(mk(sub, "A cyclist covers the first half of a journey at 30 km/h and the second half at 20 km/h. What is the average speed?", 24, [25, 26, 22.5], "2·30·20/(30 + 20) = 24 km/h.", d="medium", t=35, fmt=lambda v: f"{v} km/h", ver=X("2*30*20/(30+20)", 24)))
    out.append(mk(sub, "A bus travels for equal times at 30 km/h and 50 km/h. What is the average speed?", 40, [38, 42, 37.5], "For equal times the average is the arithmetic mean: (30 + 50)/2 = 40 km/h.", d="easy", t=25, fmt=lambda v: f"{v} km/h", ver=X("(30+50)/2", 40)))
    out.append(mk(sub, "A train covers 120 km at 40 km/h and another 120 km at 60 km/h. What is its average speed for the whole 240 km?", 48, [50, 52, 45], "Time = 3 + 2 = 5 hours, so 240 ÷ 5 = 48 km/h.", d="medium", t=40, fmt=lambda v: f"{v} km/h", ver=X("240/(120/40+120/60)", 48)))
    return out


def trains():
    out = []
    sub = "relative-speed"
    out.append(mk(sub, "Two trains of lengths 100 m and 150 m run in opposite directions at 60 km/h and 40 km/h. How long do they take to cross each other?", 9, [7.5, 10, 12], "Relative speed 100 km/h = 250/9 m/s; distance 250 m, so time = 9 s.", d="medium", t=60, fmt=lambda v: f"{fnum(v)} seconds", formula="Opposite: add speeds; same direction: subtract", ver=X("250/(100*5/18)", 9)))
    out.append(mk(sub, "Two trains of lengths 100 m and 80 m run in the same direction at 60 km/h and 42 km/h. How long does the faster take to overtake the slower completely?", 36, [30, 40, 18], "Relative speed 18 km/h = 5 m/s; distance 180 m; 180 ÷ 5 = 36 s.", d="medium", t=60, fmt=lambda v: f"{v} seconds", ver=X("180/(18*5/18)", 36)))
    out.append(mk(sub, "A 120 m long train crosses a pole in 6 seconds. What is its speed in km/h?", 72, [60, 66, 80], "Speed = 120 ÷ 6 = 20 m/s = 72 km/h.", d="easy", t=30, fmt=lambda v: f"{v} km/h", formula="Crossing a pole: distance = train length", ver=X("120/6*18/5", 72)))
    out.append(mk(sub, "A 150 m long train crosses a 250 m long platform in 20 seconds. What is its speed in km/h?", 72, [54, 60, 90], "Distance = 400 m in 20 s = 20 m/s = 72 km/h.", d="medium", t=45, fmt=lambda v: f"{v} km/h", formula="Crossing a platform: distance = train + platform", ver=X("(150+250)/20*18/5", 72)))
    sub = "train-applications"
    out.append(mk(sub, "A 150 m long train running at 63 km/h passes a man walking at 3 km/h in the same direction. How long does it take to pass him?", 9, [8, 10, 7.5], "Relative speed 60 km/h = 50/3 m/s; 150 ÷ (50/3) = 9 s.", d="medium", t=60, fmt=lambda v: f"{v} seconds", ver=X("150/((63-3)*5/18)", 9)))
    out.append(mk(sub, "Two trains start from stations 350 km apart and run towards each other at 60 km/h and 40 km/h. After how many hours do they meet?", 3.5, [3, 4, 5], "350 ÷ 100 = 3.5 hours.", d="easy", t=30, fmt=hours, typ="scenario", ver=X("350/(60+40)", 3.5)))
    out.append(mk(sub, "A 200 m long train passes through a 400 m long tunnel in 40 seconds. What is its speed in km/h?", 54, [48, 60, 72], "600 m in 40 s = 15 m/s = 54 km/h.", d="medium", t=45, fmt=lambda v: f"{v} km/h", ver=X("(200+400)/40*18/5", 54)))
    out.append(mk(sub, "Two trains, each 120 m long, run in opposite directions at 36 km/h each. How many seconds do they take to cross each other?", 12, [10, 15, 24], "Relative speed 72 km/h = 20 m/s; 240 ÷ 20 = 12 s.", d="medium", t=50, fmt=lambda v: f"{v} seconds", ver=X("240/((36+36)*5/18)", 12)))
    return out


def boats():
    out = []
    sub = "upstream-downstream"
    out.append(mk(sub, "A boat goes 15 km/h in still water and the stream flows at 3 km/h. How long does it take to travel 54 km downstream?", 3, [2.5, 3.6, 4.5], "Downstream speed = 18 km/h; 54 ÷ 18 = 3 hours.", d="easy", t=30, fmt=hours, formula="Downstream = u + v; upstream = u − v", ver=X("54/(15+3)", 3)))
    out.append(mk(sub, "A boat's downstream speed is 20 km/h and upstream speed 12 km/h. What is the speed of the stream?", 4, [3, 5, 8], "Stream = (20 − 12)/2 = 4 km/h.", d="easy", t=25, fmt=lambda v: f"{v} km/h", formula="Stream = (D − U)/2; boat = (D + U)/2", ver=X("(20-12)/2", 4)))
    out.append(mk(sub, "A man rows 30 km downstream in 3 hours and 18 km upstream in 3 hours. What is his speed in still water?", 8, [6, 7, 10], "Downstream 10 km/h, upstream 6 km/h; still water = (10 + 6)/2 = 8 km/h.", d="medium", t=45, fmt=lambda v: f"{v} km/h", ver=X("(30/3+18/3)/2", 8)))
    out.append(mk(sub, "A boat goes at 10 km/h in still water and the stream is 2 km/h. How long does a trip of 24 km downstream and 24 km back take?", 5, [4.8, 4, 6], "24/12 + 24/8 = 2 + 3 = 5 hours.", d="medium", t=50, fmt=hours, typ="scenario", ver=X("24/(10+2)+24/(10-2)", 5)))
    out.append(mk(sub, "A person can row at 6 km/h in still water and the river flows at 2 km/h. How long does he take to row 32 km downstream and back?", 12, [10, 8, 16], "32/8 + 32/4 = 4 + 8 = 12 hours.", d="hard", t=55, fmt=hours, ver=X("32/(6+2)+32/(6-2)", 12)))
    return out


def height_distance():
    out = []
    sub = "height-distance-calc"
    m = lambda v: f"{fnum(round(v, 2))} m"
    out.append(mk(sub, "From a point 30 m from the foot of a tower, the angle of elevation of its top is 45°. What is the height of the tower?", 30, [15, 30 * math.sqrt(3), 60], "tan 45° = 1, so height = 30 m.", d="easy", t=30, fmt=m, formula="tan θ = height / distance", ver=X("30*tan(radians(45))", 30)))
    out.append(mk(sub, "From a point 20 m from the foot of a tower, the angle of elevation of its top is 60°. What is the height (use √3 = 1.732)?", 34.64, [20, 11.55, 40], "Height = 20 × tan 60° = 20√3 ≈ 34.64 m.", d="medium", t=40, fmt=m, ver=X("20*tan(radians(60))", 34.64)))
    out.append(mk(sub, "A tower is 50 m high. At what distance from its foot is the angle of elevation of its top 30° (use √3 = 1.732)?", 86.6, [50, 28.87, 100], "Distance = 50 ÷ tan 30° = 50√3 ≈ 86.60 m.", d="medium", t=45, fmt=m, ver=X("50/tan(radians(30))", 86.6)))
    out.append(mk(sub, "A 10 m long ladder leans against a wall making 60° with the ground. How high up the wall does it reach (use √3 = 1.732)?", 8.66, [5, 10, 11.55], "Height = 10 × sin 60° = 5√3 ≈ 8.66 m.", d="medium", t=40, fmt=m, typ="scenario", ver=X("10*sin(radians(60))", 8.66)))
    out.append(mk(sub, "A tower casts a shadow 40 m long when the sun's elevation is 45°. How tall is the tower?", 40, [20, 40 * math.sqrt(2), 80], "tan 45° = 1, so the height equals the shadow length.", d="easy", t=25, fmt=m, ver=X("40*tan(radians(45))", 40)))
    out.append(mk(sub, "From the top of a 100 m high cliff, the angle of depression of a boat is 30°. How far is the boat from the foot of the cliff (use √3 = 1.732)?", 173.2, [100, 57.74, 200], "Distance = 100 ÷ tan 30° = 100√3 ≈ 173.20 m.", d="hard", t=50, fmt=m, typ="scenario", ver=X("100/tan(radians(30))", 173.2)))
    return out
