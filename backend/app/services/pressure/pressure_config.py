"""
Pressure-level configuration.

Five fixed levels, each mapping to a `PressureConfigDocument` (see
`app.models.pressure`). Configuration is entirely server-side: the client
only ever selects a `pressure_level` integer, never the underlying
frequencies -- this keeps randomization details out of the UI, as required.
"""

from __future__ import annotations

from dataclasses import dataclass

PRESSURE_LEVELS = (1, 2, 3, 4, 5)

_LEVEL_LABELS = {
    1: "Friendly",
    2: "Standard",
    3: "Challenging",
    4: "High Pressure",
    5: "Interview Simulation",
}

_LEVEL_DESCRIPTIONS = {
    1: "Relaxed questions, generous time, a supportive tone, and no interruptions. Good for building basic confidence.",
    2: "Realistic questions with moderate time limits and the occasional follow-up.",
    3: "Harder questions, shorter response time, unexpected follow-ups and topic switches.",
    4: "Short time limits, unexpected questions, rapid follow-ups, and occasional interviewer interruptions.",
    5: "A realistic full interview simulation: introduction, HR, technical, scenario and behavioral questions.",
}

# What changes at each level, shown on the setup screen -- plain descriptions,
# not the internal probabilities that drive them.
_LEVEL_CHARACTERISTICS: dict[int, tuple[str, ...]] = {
    1: ("Generous time to answer", "Supportive, predictable questions", "No interruptions"),
    2: ("Moderate time limits", "Occasional follow-up questions", "Normal interviewer behavior"),
    3: ("Shorter response time", "Unexpected follow-ups", "Occasional topic switching"),
    4: ("Short time limits", "Rapid follow-ups", "Occasional interruptions", "Ambiguous scenarios"),
    5: ("Full interview simulation", "HR, technical and scenario questions", "Realistic pacing throughout"),
}


@dataclass(frozen=True)
class PressureConfig:
    pressure_level: int
    time_limit_seconds: int | None
    allow_hints: bool
    follow_up_frequency: float
    topic_switch_frequency: float
    difficulty_modifier: int
    interruption_frequency: float
    unexpected_question_frequency: float

    def as_document(self) -> dict:
        return {
            "time_limit_seconds": self.time_limit_seconds,
            "allow_hints": self.allow_hints,
            "follow_up_frequency": self.follow_up_frequency,
            "topic_switch_frequency": self.topic_switch_frequency,
            "difficulty_modifier": self.difficulty_modifier,
            "interruption_frequency": self.interruption_frequency,
            "unexpected_question_frequency": self.unexpected_question_frequency,
        }


_CONFIGS: dict[int, PressureConfig] = {
    1: PressureConfig(
        pressure_level=1,
        time_limit_seconds=None,
        allow_hints=True,
        follow_up_frequency=0.10,
        topic_switch_frequency=0.0,
        difficulty_modifier=0,
        interruption_frequency=0.0,
        unexpected_question_frequency=0.0,
    ),
    2: PressureConfig(
        pressure_level=2,
        time_limit_seconds=90,
        allow_hints=True,
        follow_up_frequency=0.30,
        topic_switch_frequency=0.05,
        difficulty_modifier=0,
        interruption_frequency=0.0,
        unexpected_question_frequency=0.10,
    ),
    3: PressureConfig(
        pressure_level=3,
        time_limit_seconds=60,
        allow_hints=False,
        follow_up_frequency=0.50,
        topic_switch_frequency=0.20,
        difficulty_modifier=1,
        interruption_frequency=0.05,
        unexpected_question_frequency=0.20,
    ),
    4: PressureConfig(
        pressure_level=4,
        time_limit_seconds=40,
        allow_hints=False,
        follow_up_frequency=0.60,
        topic_switch_frequency=0.30,
        difficulty_modifier=1,
        interruption_frequency=0.15,
        unexpected_question_frequency=0.35,
    ),
    5: PressureConfig(
        pressure_level=5,
        time_limit_seconds=60,
        allow_hints=False,
        follow_up_frequency=0.50,
        topic_switch_frequency=0.15,
        difficulty_modifier=1,
        interruption_frequency=0.10,
        unexpected_question_frequency=0.25,
    ),
}


def get_pressure_config(level: int) -> PressureConfig:
    try:
        return _CONFIGS[level]
    except KeyError as exc:
        raise ValueError(f"Unknown pressure level: {level}") from exc


def public_levels() -> list[dict]:
    """The setup screen's view: label, description and characteristics -- no frequencies."""
    return [
        {
            "pressure_level": level,
            "label": _LEVEL_LABELS[level],
            "description": _LEVEL_DESCRIPTIONS[level],
            "characteristics": list(_LEVEL_CHARACTERISTICS[level]),
            "time_limit_seconds": _CONFIGS[level].time_limit_seconds,
            "allow_hints": _CONFIGS[level].allow_hints,
        }
        for level in PRESSURE_LEVELS
    ]
