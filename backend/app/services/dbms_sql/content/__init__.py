"""Seed content for the DBMS & SQL bank: one module per syllabus unit."""

from __future__ import annotations

import importlib

_UNIT_MODULES = ("unit_a", "unit_b", "unit_c", "unit_d", "unit_e", "unit_f", "unit_g", "labs", "scenarios")


def all_seed_questions() -> list[dict]:
    out: list[dict] = []
    for name in _UNIT_MODULES:
        try:
            module = importlib.import_module(f"app.services.dbms_sql.content.{name}")
        except ModuleNotFoundError as exc:  # a unit module that does not exist yet simply contributes nothing
            if exc.name != f"app.services.dbms_sql.content.{name}":
                raise
            continue
        out.extend(module.questions())
    return out
