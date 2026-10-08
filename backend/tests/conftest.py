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
from app.db import mongodb
from app.main import app
from app.services.auth import auth_service
from app.services.communication.communication_service import communication_service
from app.services.cybersecurity.learning_service import learning_service
from app.services.progress.progress_service import progress_service


@pytest.fixture(autouse=True)
def _no_real_mongodb(monkeypatch):
    """
    Never touch a real MongoDB during tests.

    The app lifespan calls `mongodb.connect()`, which otherwise blocks for the
    3s server-selection timeout on every test (and would run startup seeding
    against a developer's real database if one happened to be running).
    """
    monkeypatch.setattr(mongodb, "connect", lambda: None)


@pytest.fixture()
def fake_db():
    """A fresh in-memory database per test, with the real indexes applied."""
    client = mongomock.MongoClient()
    db = client["test_ai_cybersec_mentor"]
    auth_service.ensure_indexes(db)
    learning_service.ensure_indexes(db)
    learning_service.ensure_seeded(db)
    communication_service.ensure_indexes(db)
    communication_service.ensure_seeded(db)
    progress_service.ensure_indexes(db)
    from app.services.daily_practice.daily_practice_service import daily_practice_service
    from app.services.daily_practice.streak import streak_service
    from app.services.notifications.notification_service import notification_service

    notification_service.ensure_indexes(db)
    daily_practice_service.ensure_indexes(db)
    streak_service.ensure_indexes(db)
    return db


@pytest.fixture()
def client(fake_db):
    """A TestClient wired to the fake database instead of a real MongoDB."""
    app.dependency_overrides[get_db] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
