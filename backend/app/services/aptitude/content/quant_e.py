"""Topics Q, R, S: Mensuration, Calendar, Clocks."""

from __future__ import annotations

import math
from datetime import date

from .build import E, M, X, fnum, mk
from .quant_d import mixed

PI = "π = 22/7"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _others(day, n=3):
    i = DAYS.index(day)
    return [DAYS[(i + k) % 7] for k in (1, 2, 3, 5, 6)][:n]


def mensuration():
    out = []
    cm2 = lambda v: f"{fnum(v)} cm²"
    cm3 = lambda v: f"{fnum(v)} cm³"
    sub = "cube-cuboid"
    out.append(mk(sub, "What is the total surface area of a cube of side 6 cm?", 216, [144, 36, 196], "TSA = 6a² = 6 × 36 = 216.", d="easy", t=20, fmt=cm2, formula="Cube: TSA = 6a², V = a³", ver=X("6*6**2", 216)))
    out.append(mk(sub, "The volume of a cube is 512 cm³. What is its total surface area?", 384, [256, 512, 336], "Side = ∛512 = 8, so TSA = 6 × 64 = 384.", d="medium", t=35, fmt=cm2, ver=X("6*(512**(1/3))**2", 384)))
    out.append(mk(sub, "What is the length of the longest rod that fits inside a cuboid room 12 m × 9 m × 8 m?", 17, [15, 19, 29], "Diagonal = √(144 + 81 + 64) = √289 = 17 m.", d="medium", t=40, fmt=lambda v: f"{v} m", formula="Space diagonal = √(l² + b² + h²)", ver=X("sqrt(12**2+9**2+8**2)", 17)))
    out.append(mk(sub, "What is the total surface area of a cuboid measuring 10 cm × 6 cm × 4 cm?", 248, [240, 124, 280], "TSA = 2(lb + bh + hl) = 2(60 + 24 + 40) = 248.", d="easy", t=30, fmt=cm2, formula="Cuboid: TSA = 2(lb + bh + hl), V = lbh", ver=X("2*(10*6+6*4+4*10)", 248)))
    out.append(mk(sub, "If the side of a cube increases by 10%, by what percentage does its volume increase?", 33.1, [30, 31, 21], "1.1³ = 1.331, a 33.1% increase.", d="medium", t=30, fmt=lambda v: f"{fnum(v)}%", ver=X("(1.1**3-1)*100", 33.1)))
    sub = "sphere-hemisphere"
    out.append(mk(sub, f"Find the volume of a sphere of radius 21 cm ({PI}).", 38808, [37044, 38000, 41500], "V = 4/3 × 22/7 × 21³ = 38,808.", d="medium", t=45, fmt=cm3, formula="Sphere: V = 4/3 πr³, S = 4πr²", ver=X("4/3*22/7*21**3", 38808)))
    out.append(mk(sub, f"Find the surface area of a sphere of radius 14 cm ({PI}).", 2464, [2200, 1232, 2640], "S = 4 × 22/7 × 196 = 2,464.", d="easy", t=30, fmt=cm2, ver=X("4*22/7*14**2", 2464)))
    out.append(mk(sub, f"Find the total surface area of a solid hemisphere of radius 7 cm ({PI}).", 462, [308, 616, 154], "TSA = 3πr² = 3 × 22/7 × 49 = 462.", d="medium", t=35, fmt=cm2, formula="Hemisphere: CSA = 2πr², TSA = 3πr², V = 2/3 πr³", ver=X("3*22/7*7**2", 462)))
    out.append(mk(sub, f"Find the curved surface area of a hemisphere of radius 14 cm ({PI}).", 1232, [616, 2464, 1848], "CSA = 2πr² = 2 × 22/7 × 196 = 1,232.", d="medium", t=35, fmt=cm2, ver=X("2*22/7*14**2", 1232)))
    out.append(mk(sub, "A solid sphere of radius 6 cm is melted and recast into small spheres of radius 2 cm. How many small spheres are formed?", 27, [9, 18, 36], "Number = (6/2)³ = 27.", d="hard", t=45, formula="Equal volume: n = (R/r)³", ver=X("(6/2)**3", 27)))
    sub = "cone-cylinder"
    out.append(mk(sub, f"Find the volume of a cylinder of radius 7 cm and height 10 cm ({PI}).", 1540, [1100, 1760, 770], "V = πr²h = 22/7 × 49 × 10 = 1,540.", d="easy", t=30, fmt=cm3, formula="Cylinder: V = πr²h, CSA = 2πrh", ver=X("22/7*49*10", 1540)))
    out.append(mk(sub, f"A cone has radius 7 cm and height 24 cm. Find its curved surface area ({PI}).", 550, [528, 616, 462], "Slant height = √(49 + 576) = 25; CSA = πrl = 22/7 × 7 × 25 = 550.", d="medium", t=45, fmt=cm2, formula="Cone: l = √(r² + h²), CSA = πrl, V = 1/3 πr²h", ver=X("22/7*7*sqrt(7**2+24**2)", 550)))
    out.append(mk(sub, f"Find the volume of a cone of radius 7 cm and height 24 cm ({PI}).", 1232, [3696, 1100, 1540], "V = 1/3 × 22/7 × 49 × 24 = 1,232.", d="medium", t=45, fmt=cm3, ver=X("1/3*22/7*49*24", 1232)))
    out.append(mk(sub, f"Find the curved surface area of a cylinder of radius 3.5 cm and height 10 cm ({PI}).", 220, [110, 385, 440], "CSA = 2πrh = 2 × 22/7 × 3.5 × 10 = 220.", d="easy", t=30, fmt=cm2, ver=X("2*22/7*3.5*10", 220)))
    out.append(mk(sub, "A cylinder's radius is doubled and its height is halved. By what factor does its volume change?", 2, [1, 4, 0.5], "V ∝ r²h, so the factor is 2² × 1/2 = 2.", d="hard", t=35, fmt=lambda v: f"×{fnum(v)}", ver=X("2**2*0.5", 2)))
    return out


def calendar():
    out = []
    sub = "calendar-concepts"
    out.append(mk(sub, "Which of the following is a leap year?", 2000, [1900, 2100, 1800], "A century year is a leap year only if divisible by 400: only 2000 qualifies.", d="easy", t=25, formula="Leap: divisible by 4; century years by 400",
                  ver=E("single_match", 2000, candidates=[1900, 2000, 2100, 1800], predicate={"name": "leap"})))
    out.append(mk(sub, "How many odd days are there in 100 years?", 5, [1, 3, 0], "100 years have 24 leap years: 36,524 days = 5217 weeks + 5 days.", d="medium", t=40, formula="100 yrs → 5, 200 yrs → 3, 300 yrs → 1, 400 yrs → 0", ver=E("odd_days", 5, years=100)))
    out.append(mk(sub, "How many odd days are there in 200 years?", 3, [1, 5, 0], "2 × 5 = 10, and 10 mod 7 = 3 odd days.", d="medium", t=35, ver=E("odd_days", 3, years=200)))
    out.append(mk(sub, "How many odd days does a leap year contain?", 2, [1, 0, 3], "366 = 52 weeks + 2 days.", d="easy", t=20, ver=X("366%7", 2)))
    sub = "dates-and-days"
    def day_of(y, m, d):
        return DAYS[date(y, m, d).weekday()]
    ans = day_of(1947, 8, 15)
    out.append(mk(sub, "On which day of the week did 15 August 1947 fall?", ans, _others(ans), "Counting odd days from 1 January 1 gives 5 odd days → Friday.", d="hard", t=90, texts=True,
                  formula="Odd days: 0 Sun, 1 Mon … 6 Sat", ver=E("calendar_day", ans, year=1947, month=8, day=15)))
    ans = day_of(1950, 1, 26)
    out.append(mk(sub, "On which day of the week did 26 January 1950 fall?", ans, _others(ans), "Using odd days for 1949 complete years plus 25 days of 1950 gives Thursday.", d="hard", t=90, texts=True, ver=E("calendar_day", ans, year=1950, month=1, day=26)))
    ans = day_of(2025, 3, 5)
    out.append(mk(sub, "If 5 March 2024 was a Tuesday, what day is 5 March 2025?", ans, _others(ans), "The span from 5 March 2024 to 5 March 2025 is 365 days (29 Feb 2024 is earlier), i.e. 1 odd day: Tuesday + 1 = Wednesday.", d="medium", t=45, texts=True, ver=E("calendar_day", ans, year=2025, month=3, day=5)))
    out.append(mk(sub, "Today is Thursday. What day of the week will it be 61 days from now?", "Tuesday", _others("Tuesday"), "61 = 8 × 7 + 5, so move 5 days ahead: Thursday → Tuesday.", d="medium", t=35, texts=True, ver=E("day_after", "Tuesday", start_day="Thursday", days=61)))
    sub = "exact-day"
    for (y, m, dd, what) in ((2000, 1, 1, "1 January 2000"), (1869, 10, 2, "2 October 1869"), (1999, 12, 31, "31 December 1999"), (1889, 11, 14, "14 November 1889")):
        ans = day_of(y, m, dd)
        out.append(mk(sub, f"On which day of the week did {what} fall?", ans, _others(ans), "Total odd days of the completed years, plus the odd days of the months and days elapsed, give the weekday.", d="hard", t=90, texts=True,
                      formula="Day = (odd days of years + months + date) mod 7", ver=E("calendar_day", ans, year=y, month=m, day=dd)))
    return out


def clocks():
    out = []
    deg = lambda v: f"{fnum(v)}°"
    sub = "clock-concepts"
    out.append(mk(sub, "What is the angle between the hour and minute hands at 3:00?", 90, [60, 75, 120], "At 3:00 the hour hand is 3 × 30° = 90° from 12 and the minute hand is at 12.", d="easy", t=20, fmt=deg, formula="Angle = |30H − 5.5M|", ver=E("clock_angle", 90, h=3, m=0)))
    out.append(mk(sub, "What is the angle between the hands of a clock at 4:30?", 45, [30, 60, 75], "|30 × 4 − 5.5 × 30| = |120 − 165| = 45°.", d="medium", t=35, fmt=deg, ver=E("clock_angle", 45, h=4, m=30)))
    out.append(mk(sub, "What is the angle between the hands of a clock at 7:20?", 100, [90, 110, 130], "|30 × 7 − 5.5 × 20| = |210 − 110| = 100°.", d="medium", t=35, fmt=deg, ver=E("clock_angle", 100, h=7, m=20)))
    out.append(mk(sub, "How many times do the hands of a clock coincide in 12 hours?", 11, [10, 12, 22], "They overlap every 12/11 hours, which gives 11 overlaps in 12 hours (the 11th overlap is at 12:00 itself).", d="medium", t=30, formula="Coincide: 11 times; right angle: 22 times; opposite: 11 times (per 12 h)", ver=E("clock_event_count", 11, angles=[0])))
    out.append(mk(sub, "How many times are the hands of a clock at right angles to each other in 12 hours?", 22, [11, 24, 20], "Twice for each overlap interval: 2 × 11 = 22.", d="medium", t=30, ver=E("clock_event_count", 22, angles=[90, 270])))
    sub = "clock-problems"
    out.append(mk(sub, "At what time between 4 and 5 o'clock will the hands of a clock coincide?", "21 9/11 minutes past 4", ["20 minutes past 4", "22 minutes past 4", "21 3/11 minutes past 4"],
                  "Overlap at H o'clock occurs 60H/11 minutes past: 240/11 = 21 9/11 minutes.", d="hard", t=60, texts=True, formula="Coincide at (60H/11) minutes past H", ver=E("clock_overlap", 240 / 11, h=4)))
    out.append(mk(sub, "A clock is set right at 8 a.m. and gains 3 minutes every hour. What time will it show when the true time is 8 p.m. the same day?", "8:36 PM", ["8:30 PM", "8:33 PM", "8:39 PM"], "12 true hours × 3 min = 36 minutes gained.", d="medium", t=40, texts=True, typ="scenario", ver=E("clock_gain", "8:36 PM", start_hour=8, true_hours=12, gain_per_hour=3)))
    out.append(mk(sub, "A clock seen in a mirror shows 3:40. What is the actual time?", "8:20", ["8:40", "9:20", "7:20"], "Actual time = 11:60 − 3:40 = 8:20.", d="medium", t=35, texts=True, formula="Mirror time = 11:60 − shown time", ver=E("mirror_time", "8:20", h=3, m=40)))
    out.append(mk(sub, "What is the angle between the hands of a clock at 9:15?", 172.5, [180, 165, 187.5], "|30 × 9 − 5.5 × 15| = |270 − 82.5| = 187.5, and 360 − 187.5 = 172.5°.", d="hard", t=50, fmt=deg, ver=E("clock_angle", 172.5, h=9, m=15)))
    return out
