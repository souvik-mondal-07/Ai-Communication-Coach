"""
Shared test fixtures.

MongoDB isn't available in this environment (see the Step 1 report), so
these tests substitute `mongomock` — an in-memory, API-compatible stand-in
for PyMongo — via FastAPI's dependency override mechanism. This exercises
all of the app's real auth logic (hashing, JWT, route behavior, unique-email
enforcement) without needing a live database server. It does not replace
verifying against a real MongoDB instance in an environment that has one.
"""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_db
from app.main import app
from app.services.auth import auth_service


@pytest.fixture()
def fake_db():
    """A fresh in-memory database per test, with the real indexes applied."""
    client = mongomock.MongoClient()
    db = client["test_ai_cybersec_mentor"]
    auth_service.ensure_indexes(db)
    return db


@pytest.fixture()
def client(fake_db):
    """A TestClient wired to the fake database instead of a real MongoDB."""
    app.dependency_overrides[get_db] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
