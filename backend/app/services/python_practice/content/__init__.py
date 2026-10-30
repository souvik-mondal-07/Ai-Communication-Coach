"""Seed content for the Python practice bank: one module per syllabus unit."""

from __future__ import annotations

import importlib

_MODULES = ("unit_a", "unit_b", "unit_c", "unit_d", "unit_e", "unit_f", "unit_g", "unit_h", "unit_i", "challenges", "challenges_h", "challenges_d")


def all_seed_questions() -> list[dict]:
    out: list[dict] = []
    for name in _MODULES:
        try:
            module = importlib.import_module(f"app.services.python_practice.content.{name}")
        except ModuleNotFoundError as exc:  # a unit module that does not exist yet simply contributes nothing
            if exc.name != f"app.services.python_practice.content.{name}":
                raise
            continue
        out.extend(module.questions())
    return out
