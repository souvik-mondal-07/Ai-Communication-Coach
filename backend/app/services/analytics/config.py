"""
Every analytics threshold in one place (spec: "keep thresholds configurable").

Nothing here is stored or learned; change a number and the analytics change.
All "minimum" values exist so one lucky/unlucky session never produces a label.
"""

from __future__ import annotations

# --- Data sufficiency ----------------------------------------------------------
EARLY_DATA_SESSIONS = 5          # fewer total completed sessions => "early" data
MIN_SESSIONS_FOR_SCORE = 3       # sessions needed before a mean score is shown as reliable
MIN_COMPARE_SAMPLES = 2          # sessions needed in EACH window to compare windows
MIN_TREND_POINTS = 3             # time buckets needed before a trend label
MIN_DOMAIN_QUESTIONS = 5         # scored questions needed before a domain gets a percentage
MIN_MODE_SESSIONS = 1            # a mode row is shown from the first session (flagged "early" below 3)

# --- Result bounds (security / performance) -----------------------------------
MAX_SESSIONS_PER_SOURCE = 300    # newest N sessions per collection per request
MAX_RANGE_DAYS = 3650            # custom date ranges may not span more than this
MAX_LIST_ITEMS = 8

# --- Change labelling (score points; higher_is_better handled by the caller) ---
SIGNIFICANT_DELTA = 10.0
IMPROVING_DELTA = 4.0
# |delta| < IMPROVING_DELTA => "Stable"; <= -IMPROVING_DELTA => "Slight decline";
# <= -SIGNIFICANT_DELTA => "Needs attention".

# --- Strength / weakness bands ---------------------------------------------------
STRONG_SCORE = 75
WEAK_SCORE = 60

# --- Recurring communication weaknesses ----------------------------------------
# A weakness needs at least `min_samples` measurements AND the problem must occur
# in at least `min_rate` of them.
WEAKNESS_RULES = {
    "filler_words": {"min_samples": 5, "min_rate": 0.5, "filler_per_100_words": 3.0},
    "long_pauses": {"min_samples": 5, "min_rate": 0.4},
    "repeated_words": {"min_samples": 5, "min_rate": 0.5, "min_repeats": 2},
    "weak_structure": {"min_samples": 5, "min_rate": 0.5, "score_below": 60},
    "answers_too_short": {"min_samples": 5, "min_rate": 0.4},
    "answers_too_long": {"min_samples": 5, "min_rate": 0.4},
    "shallow_technical_explanation": {"min_samples": 5, "min_rate": 0.5, "score_below": 60},
    "low_confidence": {"min_samples": 3, "min_rate": 0.5, "score_below": 60},
}

# --- Answer length bands in words, per question kind ---------------------------
# (short_below, long_above, very_long_above)
LENGTH_BANDS = {
    "behavioral": (40, 180, 280),
    "technical": (30, 150, 230),
    "scenario": (50, 220, 330),
}
DEFAULT_LENGTH_BAND = LENGTH_BANDS["technical"]

# --- Speaking ----------------------------------------------------------------------
MIN_VOICE_SAMPLES = 3            # spoken answers needed before speaking trends/aggregates
MIN_WORDS_FOR_RATE = 15          # tiny answers give meaningless per-minute rates
MIN_DURATION_FOR_RATE = 5.0      # seconds
# Normal-vs-pressure differences smaller than this are not reported as a change.
PRESSURE_NOTABLE_DELTA = 8.0

# --- Interview readiness ---------------------------------------------------------
# Documented formula (weights sum to 1.0). A component is used only when it has
# enough data; the weights of the components that ARE used are re-normalised, and
# the share of the original weight that was available is reported as `coverage`.
READINESS_WEIGHTS = {
    "technical": 0.35,
    "communication": 0.25,
    "confidence": 0.15,
    "consistency": 0.10,
    "follow_up": 0.10,
    "pressure": 0.05,
}
READINESS_REQUIRED = ("technical", "communication")   # no score without these two
READINESS_MIN_SESSIONS = {
    "technical": 3, "communication": 3, "confidence": 3,
    "consistency": 4, "follow_up": 5, "pressure": 2,   # follow_up counts answers
}
# Consistency = 100 - CONSISTENCY_PENALTY * stdev(overall interview scores), floored at 0.
CONSISTENCY_PENALTY = 2.5
READINESS_BANDS = ((80, "Strong"), (65, "Developing well"), (50, "Building"), (0, "Early stage"))
