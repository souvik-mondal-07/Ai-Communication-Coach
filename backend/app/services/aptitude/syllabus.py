"""
The complete General Aptitude syllabus (Phase 23): 26 topics (A-Z), 88 subtopics.

Every bullet of the supplied syllabus is an entry in `items`, and each item lists the subtopic
ids that cover it, so any syllabus line can be traced to topics and then to real questions
(see `coverage_matrix` in `coverage.py`). This file is static reference data: nothing here
claims a topic is "done" -- completion is always computed from questions that exist.
"""

from __future__ import annotations

from dataclasses import dataclass

QUANT = "Quantitative Aptitude"
REASONING = "Logical Reasoning"
DATA = "Data Interpretation & Sufficiency"


@dataclass(frozen=True)
class Subtopic:
    id: str
    title: str


@dataclass(frozen=True)
class SyllabusItem:
    text: str
    subtopic_ids: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    id: str
    code: str  # A-Z, matching the supplied syllabus
    title: str
    section: str
    summary: str
    subtopics: tuple[Subtopic, ...]
    items: tuple[SyllabusItem, ...]


def _t(code, tid, title, section, summary, subs, items) -> Topic:
    return Topic(
        id=tid, code=code, title=title, section=section, summary=summary,
        subtopics=tuple(Subtopic(i, n) for i, n in subs),
        items=tuple(SyllabusItem(text, tuple(ids)) for text, ids in items),
    )


TOPICS: tuple[Topic, ...] = (
    _t("A", "vedic-maths", "Vedic Maths", QUANT, "Mental-arithmetic techniques for speed.",
       [("fast-calculation", "Fast calculation techniques"), ("calculation-shortcuts", "Calculation shortcuts")],
       [("Fast calculation techniques.", ["fast-calculation"]),
        ("Calculation shortcuts appropriate for aptitude tests.", ["calculation-shortcuts"])]),
    _t("B", "number-system", "Number System", QUANT, "Properties of numbers, divisibility, factors and remainders.",
       [("classification-of-numbers", "Classification of numbers"), ("divisibility-rules", "Divisibility rules"),
        ("factorials", "Factorials"), ("unit-digit", "Unit digit calculation"),
        ("number-of-factors", "Number of factors"), ("remainders", "Remainder theorems"), ("hcf-lcm", "HCF and LCM")],
       [("Classification of numbers.", ["classification-of-numbers"]), ("Divisibility rules.", ["divisibility-rules"]),
        ("Factorials.", ["factorials"]), ("Unit digit calculation.", ["unit-digit"]),
        ("Number of factors.", ["number-of-factors"]), ("Remainder theorems.", ["remainders"]),
        ("HCF and LCM.", ["hcf-lcm"])]),
    _t("C", "average", "Average", QUANT, "Mean calculations, inclusion/exclusion and weighted averages.",
       [("average-calculations", "Average calculations"), ("inclusion-exclusion", "Inclusion and exclusion"),
        ("weighted-average", "Weighted average")],
       [("Average calculations.", ["average-calculations"]), ("Inclusion and exclusion.", ["inclusion-exclusion"]),
        ("Weighted average.", ["weighted-average"])]),
    _t("D", "percentage", "Percentage", QUANT, "Percent calculations, successive change and applied problems.",
       [("percentage-calculations", "Percentage comparison and calculations"),
        ("percentage-fraction", "Percentage-to-fraction conversion"), ("successive-change", "Successive percentage change"),
        ("marks-problems", "Problems on marks"), ("election-problems", "Problems on elections"),
        ("population-problems", "Problems on population"), ("percentage-error", "Percentage error")],
       [("Percentage comparison and calculations.", ["percentage-calculations"]),
        ("Percentage-to-fraction conversion.", ["percentage-fraction"]),
        ("Successive percentage change.", ["successive-change"]),
        ("Problems based on marks, elections, population and percentage error.",
         ["marks-problems", "election-problems", "population-problems", "percentage-error"])]),
    _t("E", "profit-loss-discount", "Profit, Loss and Discount", QUANT, "Cost, selling and marked prices; discounts; faulty weights.",
       [("cp-sp-mp", "Cost price, selling price and marked price"), ("profit-loss-percent", "Profit and loss percentages"),
        ("discounts", "Discounts"), ("faulty-weights", "Faulty weights"),
        ("number-of-articles", "Number of articles"), ("common-selling-price", "Common selling price problems")],
       [("Cost price, selling price and marked price.", ["cp-sp-mp"]), ("Profit and loss percentages.", ["profit-loss-percent"]),
        ("Discounts.", ["discounts"]), ("Faulty weights.", ["faulty-weights"]),
        ("Number of articles.", ["number-of-articles"]), ("Common selling price problems.", ["common-selling-price"])]),
    _t("F", "logical-reasoning", "Logical Reasoning", REASONING, "Series, alphabet tests and coding-decoding.",
       [("number-series", "Number series"), ("alphabet-series", "Alphabet series"),
        ("alphanumeric-series", "Alphanumeric series"), ("alphabet-tests", "Alphabet tests"),
        ("coding-decoding", "Coding and decoding"), ("language-coding", "Language coding")],
       [("Number series.", ["number-series"]), ("Alphabet series.", ["alphabet-series"]),
        ("Alphanumeric series.", ["alphanumeric-series"]), ("Alphabet tests.", ["alphabet-tests"]),
        ("Coding and decoding.", ["coding-decoding"]), ("Language coding.", ["language-coding"])]),
    _t("G", "ratio-proportion", "Ratio and Proportion", QUANT, "Ratios, proportion, ages and partnership.",
       [("ratio-concepts", "Ratio and proportion concepts"), ("age-problems", "Age-based problems"),
        ("partnership", "Partnership problems")],
       [("Ratio and proportion concepts.", ["ratio-concepts"]), ("Age-based problems.", ["age-problems"]),
        ("Partnership problems.", ["partnership"])]),
    _t("H", "alligation-mixtures", "Alligation and Mixtures", QUANT, "Mixing quantities and replacement problems.",
       [("alligation-concepts", "Alligation and mixture concepts"), ("replacement", "Replacement-based questions")],
       [("Alligation and mixture concepts.", ["alligation-concepts"]), ("Replacement-based questions.", ["replacement"])]),
    _t("I", "permutation-combination", "Permutation and Combination", QUANT, "Counting, selection, arrangement and distribution.",
       [("counting-principles", "Principles of counting"), ("selection-arrangement", "Selection and arrangement"),
        ("numbers-and-words", "Numbers and words"), ("rank-distribution", "Rank and distribution problems"),
        ("geometric-applications", "Geometric applications"), ("circular-arrangements", "Circular arrangements")],
       [("Principles of counting.", ["counting-principles"]), ("Selection and arrangement.", ["selection-arrangement"]),
        ("Numbers and words.", ["numbers-and-words"]), ("Rank and distribution problems.", ["rank-distribution"]),
        ("Geometric applications.", ["geometric-applications"]), ("Circular arrangements.", ["circular-arrangements"])]),
    _t("J", "probability", "Probability", QUANT, "Events, coins, dice, cards and conditional probability.",
       [("probability-concepts", "Probability concepts and classification of events"), ("coins", "Coins"),
        ("dice", "Dice"), ("cards", "Cards"), ("conditional-probability", "Conditional probability")],
       [("Probability concepts and classification of events.", ["probability-concepts"]),
        ("Coins, dice and cards.", ["coins", "dice", "cards"]),
        ("Conditional probability.", ["conditional-probability"])]),
    _t("K", "simple-compound-interest", "Simple and Compound Interest", QUANT, "Interest, comparison, depreciation and growth.",
       [("si-ci-comparison", "Comparison of simple and compound interest"), ("interest-calculations", "Interest calculations"),
        ("depreciation-growth", "Depreciation and growth using compounding")],
       [("Comparison of simple and compound interest.", ["si-ci-comparison"]),
        ("Interest calculations.", ["interest-calculations"]),
        ("Depreciation and growth using compounding.", ["depreciation-growth"])]),
    _t("L", "analytical-reasoning", "Analytical Reasoning", REASONING, "Blood relations and direction sense.",
       [("blood-relations", "Blood relations"), ("direction-sense", "Direction sense")],
       [("Blood relations.", ["blood-relations"]), ("Direction sense.", ["direction-sense"])]),
    _t("M", "time-and-work", "Time and Work", QUANT, "Work rates, efficiency and wages.",
       [("work-calculations", "Time and work calculations"), ("work-together", "Work done together"),
        ("efficiency", "Efficiency"), ("men-women-children", "Men, women and children problems"),
        ("wages", "Wages based on work")],
       [("Time and work calculations.", ["work-calculations"]), ("Work done together.", ["work-together"]),
        ("Efficiency.", ["efficiency"]), ("Men, women and children based problems.", ["men-women-children"]),
        ("Wages based on work.", ["wages"])]),
    _t("N", "pipes-cisterns", "Pipes and Cisterns", QUANT, "Inlets, outlets and tank-filling problems.",
       [("inlets-outlets", "Inlets and outlets"), ("parts-filled", "Parts of a tank filled"),
        ("pipe-time-problems", "Time-based problems")],
       [("Inlets and outlets.", ["inlets-outlets"]), ("Parts of a tank filled.", ["parts-filled"]),
        ("Time-based problems.", ["pipe-time-problems"])]),
    _t("O", "syllogism", "Syllogism", REASONING, "Venn diagrams, statements and conclusions.",
       [("venn-diagrams", "Logical Venn diagrams"), ("group-relationships", "Relationships between given groups"),
        ("possibility-questions", "Possibility-based questions")],
       [("Logical Venn diagrams.", ["venn-diagrams"]), ("Relationships between given groups.", ["group-relationships"]),
        ("Possibility-based questions.", ["possibility-questions"])]),
    _t("P", "number-ranking", "Number Ranking Test", REASONING, "Number tests and ranking/ordering.",
       [("number-tests", "Number tests"), ("ranking-ordering", "Ranking and ordering problems")],
       [("Number tests.", ["number-tests"]), ("Ranking and ordering problems.", ["ranking-ordering"])]),
    _t("Q", "mensuration", "Mensuration", QUANT, "Surface area and volume of common solids.",
       [("cube-cuboid", "Cubes and cuboids"), ("sphere-hemisphere", "Spheres and hemispheres"),
        ("cone-cylinder", "Cones and cylinders")],
       [("Surface area and volume of cubes and cuboids.", ["cube-cuboid"]),
        ("Surface area and volume of spheres and hemispheres.", ["sphere-hemisphere"]),
        ("Surface area and volume of cones and cylinders.", ["cone-cylinder"])]),
    _t("R", "calendar", "Calendar", QUANT, "Odd days, leap years and the day of the week.",
       [("calendar-concepts", "Calendar concepts"), ("dates-and-days", "Dates and days"),
        ("exact-day", "Finding the exact day of the week")],
       [("Calendar concepts.", ["calendar-concepts"]), ("Dates and days.", ["dates-and-days"]),
        ("Finding the exact day of the week.", ["exact-day"])]),
    _t("S", "clocks", "Clocks", QUANT, "Hand angles, overlaps and faulty clocks.",
       [("clock-concepts", "Clock concepts and formulas"), ("clock-problems", "Clock-based aptitude problems")],
       [("Clock concepts and formulas.", ["clock-concepts"]), ("Clock-based aptitude problems.", ["clock-problems"])]),
    _t("T", "time-speed-distance", "Time, Speed and Distance", QUANT, "Speed, unit conversion and average speed.",
       [("tsd-basics", "Time, speed and distance"), ("unit-conversion", "Unit conversion and proportionality"),
        ("average-speed", "Average speed")],
       [("Time, speed and distance.", ["tsd-basics"]), ("Unit conversion and proportionality.", ["unit-conversion"]),
        ("Average speed.", ["average-speed"])]),
    _t("U", "problems-on-trains", "Problems on Trains", QUANT, "Relative speed with trains, poles, platforms.",
       [("relative-speed", "Relative speed concepts"), ("train-applications", "Applications of relative speed")],
       [("Relative speed concepts and applications.", ["relative-speed", "train-applications"])]),
    _t("V", "boats-streams", "Boats and Streams", QUANT, "Upstream and downstream motion.",
       [("upstream-downstream", "Upstream and downstream problems")],
       [("Upstream and downstream problems.", ["upstream-downstream"])]),
    _t("W", "height-distance", "Height and Distance", QUANT, "Angles of elevation and depression.",
       [("height-distance-calc", "Height and distance calculations")],
       [("Height and distance calculations.", ["height-distance-calc"])]),
    _t("X", "seating-arrangement", "Seating Arrangement", REASONING, "Linear and circular arrangements.",
       [("linear-seating", "Linear seating arrangements"), ("circular-seating", "Circular seating arrangements")],
       [("Linear seating arrangements.", ["linear-seating"]), ("Circular seating arrangements.", ["circular-seating"])]),
    _t("Y", "data-interpretation", "Data Interpretation", DATA, "Tables, bar graphs, pie charts and line graphs.",
       [("di-fundamentals", "Fundamentals and types of data interpretation"), ("di-tables", "Tables"),
        ("di-bar-graphs", "Bar graphs"), ("di-pie-charts", "Pie charts"), ("di-line-graphs", "Line graphs")],
       [("Fundamentals and types of data interpretation.", ["di-fundamentals"]), ("Tables.", ["di-tables"]),
        ("Bar graphs.", ["di-bar-graphs"]), ("Pie charts.", ["di-pie-charts"]), ("Line graphs.", ["di-line-graphs"])]),
    _t("Z", "data-sufficiency", "Data Sufficiency", DATA, "Deciding whether the given information is enough.",
       [("sufficiency-checks", "Sufficiency of information")],
       [("Determining whether given information is sufficient to answer a question.", ["sufficiency-checks"])]),
)

TOPIC_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}
SUBTOPIC_TO_TOPIC: dict[str, str] = {s.id: t.id for t in TOPICS for s in t.subtopics}
SUBTOPIC_TITLES: dict[str, str] = {s.id: s.title for t in TOPICS for s in t.subtopics}

# A subtopic is reported "implemented" only with at least this many active, verified questions.
MIN_QUESTIONS_PER_SUBTOPIC = 4


def topic_title(topic_id: str) -> str:
    topic = TOPIC_BY_ID.get(topic_id)
    return topic.title if topic else topic_id
