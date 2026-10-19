"""Reviewed question content, organised by syllabus group. `all_seed_questions()` is the single entry point."""

from __future__ import annotations

from functools import lru_cache

from . import data, quant_a, quant_b, quant_c, quant_d, quant_e, reasoning

_BUILDERS = (
    quant_a.vedic, quant_a.number_system, quant_a.average,
    quant_b.percentage, quant_b.profit_loss,
    quant_c.ratio, quant_c.alligation, quant_c.permutation_combination, quant_c.probability, quant_c.interest,
    quant_d.time_work, quant_d.pipes, quant_d.speed_distance, quant_d.trains, quant_d.boats, quant_d.height_distance,
    quant_e.mensuration, quant_e.calendar, quant_e.clocks,
    reasoning.logical, reasoning.analytical, reasoning.syllogism, reasoning.ranking, reasoning.seating,
    data.data_interpretation, data.data_sufficiency,
)


@lru_cache(maxsize=1)
def _built() -> tuple[tuple[dict, ...], ...]:
    return tuple(tuple(b()) for b in _BUILDERS)


def all_seed_questions() -> list[dict]:
    """Fresh copies of every seed question (callers may mutate them)."""
    import copy

    return [copy.deepcopy(q) for group in _built() for q in group]
