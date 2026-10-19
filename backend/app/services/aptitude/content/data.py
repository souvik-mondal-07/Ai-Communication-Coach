"""Topics Y, Z: Data Interpretation and Data Sufficiency."""

from __future__ import annotations

from .build import E, M, X, fnum, mk, pct, rupee

DS_OPTIONS = [
    "Statement I alone is sufficient",
    "Statement II alone is sufficient",
    "Both statements together are sufficient, but neither alone is",
    "Neither alone nor both together is sufficient",
]


def _di(sub, stem, ans, wrong, expl, data, ver, d="medium", t=60, fmt=fnum, texts=False, formula=None):
    return mk(sub, stem, ans, wrong, expl, d=d, t=t, fmt=fmt, texts=texts, typ="data_interpretation", data=data, ver=ver, formula=formula)


def data_interpretation():
    out = []
    sub = "di-fundamentals"
    out.append(mk(sub, "Which chart type is best for showing how a whole is divided into parts?", "Pie chart", ["Line graph", "Scatter plot", "Histogram of time"],
                  "A pie chart shows each part's share of a total.", d="easy", t=25, texts=True, ver=M("Standard definition: pie charts represent proportions of a whole.")))
    out.append(mk(sub, "Which chart type is best for showing how a quantity changes over time?", "Line graph", ["Pie chart", "Table of ranks", "Venn diagram"],
                  "A line graph connects values across time, revealing trends.", d="easy", t=25, texts=True, ver=M("Standard definition: line graphs show trends over ordered intervals such as time.")))
    out.append(mk(sub, "In a pie chart, a slice represents 25% of the total. What is its central angle?", 90, [25, 45, 180], "25% of 360° = 90°.", d="easy", t=20, fmt=lambda v: f"{v}°", formula="Angle = (percentage / 100) × 360°", ver=X("0.25*360", 90)))
    bar = {"kind": "bar", "title": "Units sold by a store (hundreds)", "x_label": "Product", "y_label": "Units (hundreds)", "categories": ["Pens", "Books"], "series": [{"name": "Units", "values": [20, 50]}]}
    out.append(_di(sub, "The bar chart shows units sold. By what percentage are Books sales higher than Pens sales?", 150, [60, 100, 250], "(50 − 20)/20 × 100 = 150%.", bar, X("(50-20)/20*100", 150), d="easy", t=30, fmt=pct,
                   formula="% more = (difference / base) × 100"))
    sub = "di-tables"
    cols = ["Product", "Q1", "Q2", "Q3"]
    rows = [["Laptops", 120, 150, 180], ["Tablets", 80, 90, 70], ["Phones", 200, 220, 260], ["Printers", 40, 35, 45]]
    table = {"kind": "table", "title": "Quarterly sales (₹ lakh)", "columns": cols, "rows": rows}
    out.append(_di(sub, "Using the table, what are the total sales of Phones across the three quarters (₹ lakh)?", 680, [660, 700, 640], "200 + 220 + 260 = 680.", table, X("200+220+260", 680), d="easy", t=30))
    q_cols = [[r[i] for r in rows] for i in (1, 2, 3)]
    out.append(_di(sub, "In which quarter were the combined sales of all products the highest?", "Q3", ["Q1", "Q2", "They are equal"], "Totals: Q1 = 440, Q2 = 495, Q3 = 555.", table,
                   E("di_argmax_sum", "Q3", labels=["Q1", "Q2", "Q3"], columns=q_cols), texts=True, t=60))
    out.append(_di(sub, "By what percentage did Laptop sales grow from Q1 to Q3?", 50, [30, 40, 60], "(180 − 120)/120 × 100 = 50%.", table, X("(180-120)/120*100", 50), fmt=pct, t=40))
    out.append(_di(sub, "What is the average quarterly sales of Printers (₹ lakh)?", 40, [35, 42, 45], "(40 + 35 + 45)/3 = 40.", table, X("(40+35+45)/3", 40), d="easy", t=35))
    sub = "di-bar-graphs"
    enrolled, placed = [120, 150, 135, 180, 210], [72, 105, 81, 126, 168]
    years = ["2019", "2020", "2021", "2022", "2023"]
    bar2 = {"kind": "bar", "title": "Students enrolled and placed (in hundreds)", "x_label": "Year", "y_label": "Students (hundreds)", "categories": years,
            "series": [{"name": "Enrolled", "values": enrolled}, {"name": "Placed", "values": placed}]}
    out.append(_di(sub, "In which year was the placement percentage (Placed ÷ Enrolled) the highest?", "2023", ["2019", "2020", "2022"], "Percentages: 60, 70, 60, 70, 80 — highest in 2023.", bar2,
                   E("di_argmax_ratio", "2023", labels=years, num=placed, den=enrolled), texts=True, t=75))
    out.append(_di(sub, "What is the total number of students enrolled over the five years (in hundreds)?", 795, [785, 800, 810], "120 + 150 + 135 + 180 + 210 = 795.", bar2, X("120+150+135+180+210", 795), d="easy", t=35))
    out.append(_di(sub, "What was the placement percentage in 2020?", 70, [65, 75, 60], "105 ÷ 150 × 100 = 70%.", bar2, X("105/150*100", 70), d="easy", t=30, fmt=pct))
    out.append(_di(sub, "By what percentage did enrolment grow from 2019 to 2023?", 75, [60, 70, 90], "(210 − 120)/120 × 100 = 75%.", bar2, X("(210-120)/120*100", 75), fmt=pct, t=40))
    sub = "di-pie-charts"
    pie = {"kind": "pie", "title": "Monthly budget of ₹60,000", "unit": "%", "slices": [{"label": "Rent", "value": 25}, {"label": "Food", "value": 30}, {"label": "Transport", "value": 10},
                                                                                   {"label": "Savings", "value": 20}, {"label": "Others", "value": 15}]}
    out.append(_di(sub, "Based on the pie chart, how much is spent on Food (₹)?", 18000, [15000, 16500, 20000], "30% of 60,000 = 18,000.", pie, X("60000*30/100", 18000), d="easy", t=30, fmt=rupee))
    out.append(_di(sub, "What is the central angle of the Savings sector?", 72, [60, 70, 90], "20% of 360° = 72°.", pie, X("20/100*360", 72), d="easy", t=30, fmt=lambda v: f"{v}°"))
    out.append(_di(sub, "How much is spent on Rent and Transport together (₹)?", 21000, [18000, 20000, 24000], "(25% + 10%) of 60,000 = 21,000.", pie, X("60000*(25+10)/100", 21000), t=40, fmt=rupee))
    out.append(_di(sub, "If spending on 'Others' rises by 20%, what is the new amount (₹)?", 10800, [9000, 10500, 12000], "15% of 60,000 = 9,000; × 1.2 = 10,800.", pie, X("60000*15/100*1.2", 10800), t=50, fmt=rupee))
    sub = "di-line-graphs"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    prod = [400, 460, 520, 480, 600, 660]
    line = {"kind": "line", "title": "Monthly production (units)", "x_label": "Month", "y_label": "Units", "categories": months, "series": [{"name": "Production", "values": prod}]}
    out.append(_di(sub, "In which month was the percentage growth over the previous month the highest?", "May", ["February", "March", "June"], "Growth: Feb 15%, Mar 13.04%, Apr −7.69%, May 25%, Jun 10%.", line,
                   E("di_argmax_growth", "May", labels=months, values=prod), texts=True, t=75))
    out.append(_di(sub, "What is the average monthly production over the six months?", 520, [500, 510, 540], "3,120 ÷ 6 = 520.", line, X("(400+460+520+480+600+660)/6", 520), d="easy", t=40))
    out.append(_di(sub, "By what percentage did production in June exceed production in January?", 65, [55, 60, 70], "(660 − 400)/400 × 100 = 65%.", line, X("(660-400)/400*100", 65), fmt=pct, t=40))
    out.append(_di(sub, "What is the difference between the highest and lowest monthly production?", 260, [240, 200, 280], "660 − 400 = 260.", line, X("660-400", 260), d="easy", t=25))
    return out


def data_sufficiency():
    out = []
    sub = "sufficiency-checks"
    from ..verifiers import run_verifier

    def ds(question, s1, s2, params, d, note):
        ans = run_verifier("data_sufficiency", params)
        stem = f"{question} Statement I: {s1} Statement II: {s2} Decide whether the statements are sufficient to answer the question."
        return mk(sub, stem, ans, [o for o in DS_OPTIONS if o != ans], f"{note} (Checked over every allowed value.)", d=d, t=75, texts=True, typ="multi_step",
                  formula="Sufficient = the statement(s) lead to exactly one value / one definite yes-or-no", ver=E("data_sufficiency", ans, **params))

    lin = lambda coeffs, rhs: {"kind": "linear", "coeffs": coeffs, "op": "==", "rhs": rhs}
    xy = {"vars": ["x", "y"], "domain": [1, 20]}
    out.append(ds("What is the value of x, where x and y are positive integers not exceeding 20?", "x + y = 10.", "x − y = 2.",
                  {**xy, "statements": [lin({"x": 1, "y": 1}, 10), lin({"x": 1, "y": -1}, 2)], "target": {"type": "value", "var": "x"}}, "medium",
                  "Each alone leaves several possibilities for x; together they give x = 6."))
    out.append(ds("What is the value of x, where x and y are positive integers not exceeding 20?", "2x = 12.", "x + y = 10.",
                  {**xy, "statements": [lin({"x": 2}, 12), lin({"x": 1, "y": 1}, 10)], "target": {"type": "value", "var": "x"}}, "easy", "Statement I alone gives x = 6."))
    out.append(ds("What is the value of x, where x and y are positive integers not exceeding 20?", "x + y = 10.", "3x = 18.",
                  {**xy, "statements": [lin({"x": 1, "y": 1}, 10), lin({"x": 3}, 18)], "target": {"type": "value", "var": "x"}}, "easy", "Statement II alone gives x = 6."))
    out.append(ds("Is the positive integer n (n ≤ 60) even?", "n is a multiple of 4.", "n is a multiple of 3.",
                  {"vars": ["n"], "domain": [1, 60], "statements": [{"kind": "multiple_of", "var": "n", "k": 4}, {"kind": "multiple_of", "var": "n", "k": 3}], "target": {"type": "yesno", "predicate": "even", "var": "n"}},
                  "medium", "Every multiple of 4 is even, while multiples of 3 may be odd or even."))
    out.append(ds("What is the value of x, where x and y are positive integers not exceeding 12?", "x × y = 12.", "y = 3.",
                  {"vars": ["x", "y"], "domain": [1, 12], "statements": [{"kind": "product", "a": "x", "b": "y", "rhs": 12}, lin({"y": 1}, 3)], "target": {"type": "value", "var": "x"}}, "medium",
                  "I alone allows 1, 2, 3, 4, 6 or 12; II alone says nothing about x; together x = 4."))
    out.append(ds("Is x greater than y, where x and y are positive integers not exceeding 20?", "x − y = 3.", "x + y = 9.",
                  {**xy, "statements": [lin({"x": 1, "y": -1}, 3), lin({"x": 1, "y": 1}, 9)], "target": {"type": "yesno", "predicate": "gt", "a": "x", "b": "y"}}, "medium",
                  "x − y = 3 forces x > y; x + y = 9 alone allows either order."))
    out.append(ds("What is the value of x, where x and y are positive integers not exceeding 20?", "x + y = 10.", "2x + 2y = 20.",
                  {**xy, "statements": [lin({"x": 1, "y": 1}, 10), lin({"x": 2, "y": 2}, 20)], "target": {"type": "value", "var": "x"}}, "hard", "Both statements say the same thing, so x is still not determined."))
    out.append(ds("What is the value of y, where x and y are positive integers not exceeding 20?", "x + y = 12.", "y = 2x.",
                  {**xy, "statements": [lin({"x": 1, "y": 1}, 12), lin({"y": 1, "x": -2}, 0)], "target": {"type": "value", "var": "y"}}, "hard", "Together x + 2x = 12 gives x = 4 and y = 8."))
    return out
