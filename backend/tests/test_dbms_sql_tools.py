"""Phase 25 -- maintainer tooling and architectural guard rails."""

from __future__ import annotations

import re
from pathlib import Path

from app.services.dbms_sql import cli
from tools import verify_dbms_bank

APP = Path(__file__).resolve().parents[1] / "app"


def test_verifier_passes_on_the_shipped_bank(capsys):
    assert verify_dbms_bank.verify() == 0
    out = capsys.readouterr().out
    assert "rejected=0" in out and "OK:" in out and "PROBLEM" not in out


def test_security_probe_has_teeth(monkeypatch):
    monkeypatch.setattr(verify_dbms_bank.sandbox, "run_query", lambda sql, *a, **k: type("R", (), {"ok": True, "rows": [[16]], "error": None})())
    assert len(verify_dbms_bank._security_probe()) >= len(verify_dbms_bank.DANGEROUS)


def test_coverage_markdown_lists_every_topic_and_is_honest():
    md = cli.coverage_markdown()
    assert md.count("| implemented |") == 70 and "Remaining gaps" in md and "NO executable check" in md
    assert "SQLite" in md and "rejected" in md


def test_cli_main_codes(capsys):
    assert cli.main(["x", "coverage"]) == 0
    assert cli.main(["x", "bogus"]) == 2


def test_application_code_never_imports_the_tools_package():
    offenders = [str(p) for p in APP.rglob("*.py") if re.search(r"^\s*(from|import)\s+tools\b", p.read_text(encoding="utf-8"), re.M)]
    assert offenders == []


def test_sandbox_only_uses_the_standard_library_sqlite_and_no_process_or_dynamic_code():
    src = (APP / "services" / "dbms_sql" / "sandbox.py").read_text()
    for banned in ("subprocess", "os.system", "importlib", "pickle", "socket", "requests"):
        assert banned not in src, banned
    assert not re.search(r"(?<![\w.])(eval|exec|compile|open|__import__)\s*\(", src)
    assert "set_authorizer" in src and "set_progress_handler" in src and "query_only" in src


def test_user_sql_is_never_run_against_mongodb_or_by_the_session_layer_directly():
    for name in ("sessions.py", "bank.py", "analytics.py"):
        src = (APP / "services" / "dbms_sql" / name).read_text()
        assert "sqlite3" not in src, f"{name} must go through sandbox.run_query"
    routes = (APP / "api" / "routes" / "dbms_sql.py").read_text()
    assert "sqlite3" not in routes and "sandbox.run_query" in routes


def test_no_ai_provider_is_used_for_grading_or_answer_keys():
    for p in (APP / "services" / "dbms_sql").rglob("*.py"):
        text = p.read_text().lower()
        assert "gemini" not in text and "genai" not in text and "ai_service" not in text, p
