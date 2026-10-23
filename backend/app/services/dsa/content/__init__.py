"""Seed content for the DSA question bank. Each module exposes `all_questions()` returning plain dicts."""

from __future__ import annotations

from . import coding, complexity, graphs, heaps_hashing, linear, sorting, trees


def all_seed_questions() -> list[dict]:
    out: list[dict] = []
    for module in (complexity, sorting, linear, trees, heaps_hashing, graphs, coding):
        out.extend(module.all_questions())
    return out
