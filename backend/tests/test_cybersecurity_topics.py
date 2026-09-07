"""
Cybersecurity topic endpoint tests.
"""

from __future__ import annotations

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="cyber-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "Cyber User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


class TestListTopics:
    def test_requires_authentication(self, client):
        response = client.get("/api/v1/cybersecurity/topics")
        assert response.status_code == 401

    def test_lists_starter_topics(self, client):
        token = _register_and_login(client)
        response = client.get(
            "/api/v1/cybersecurity/topics", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        topics = response.json()["data"]["topics"]
        assert len(topics) >= 30
        # Listing is a summary — no full learning content included.
        assert "content" not in topics[0]
        assert "slug" in topics[0]
        assert "category" in topics[0]

    def test_filter_by_category(self, client):
        token = _register_and_login(client, email="filter-category@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics?category=Networking",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        topics = response.json()["data"]["topics"]
        assert len(topics) > 0
        assert all(t["category"] == "Networking" for t in topics)

    def test_filter_by_difficulty(self, client):
        token = _register_and_login(client, email="filter-difficulty@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics?difficulty=beginner",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        topics = response.json()["data"]["topics"]
        assert len(topics) > 0
        assert all(t["difficulty"] == "beginner" for t in topics)

    def test_filter_by_category_and_difficulty(self, client):
        token = _register_and_login(client, email="filter-both@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics?category=Networking&difficulty=beginner",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        topics = response.json()["data"]["topics"]
        assert all(t["category"] == "Networking" and t["difficulty"] == "beginner" for t in topics)

    def test_filter_with_no_matches_returns_empty_list(self, client):
        token = _register_and_login(client, email="filter-none@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics?category=NotARealCategory",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["topics"] == []


class TestTopicDetail:
    def test_requires_authentication(self, client):
        response = client.get("/api/v1/cybersecurity/topics/tcp-three-way-handshake")
        assert response.status_code == 401

    def test_returns_full_topic_content(self, client):
        token = _register_and_login(client, email="detail@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics/tcp-three-way-handshake",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        topic = response.json()["data"]["topic"]
        assert topic["slug"] == "tcp-three-way-handshake"
        assert topic["title"]
        assert "content" in topic
        assert "learning_objectives" in topic
        assert "key_points" in topic

    def test_unknown_topic_returns_404(self, client):
        token = _register_and_login(client, email="unknown-topic@example.com")
        response = client.get(
            "/api/v1/cybersecurity/topics/does-not-exist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "TOPIC_NOT_FOUND"
