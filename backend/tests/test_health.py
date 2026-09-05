"""
Verifies the foundation actually boots: the app imports cleanly and the
health endpoint responds. Added beyond the four test files named in the
brief because Step 1's own verification requirements ask for this check.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "ai-cybersec-mentor"


def test_root() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["success"] is True
