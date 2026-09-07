"""
Learning service.

Owns all reads/writes to the `cybersecurity_topics` collection: listing,
filtering, detail lookup, and idempotently seeding the starter dataset.
Pure catalog/database operations — no AI calls here (question generation
and evaluation live in `practice_service`, which is the only place Gemini
is used for the cybersecurity feature).
"""

from __future__ import annotations

from pymongo import ASCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.models.cybersecurity import TopicDocument
from app.services.cybersecurity.seed_data import STARTER_TOPICS

TOPIC_SUMMARY_PROJECTION = {
    "_id": 0,
    "slug": 1,
    "title": 1,
    "category": 1,
    "difficulty": 1,
    "description": 1,
    "practice_enabled": 1,
}

TOPIC_DETAIL_PROJECTION = {"_id": 0}


class LearningService:
    """Cybersecurity topic catalog: listing, detail lookup, and seeding."""

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent — safe to call on every startup."""
        collection = db[Collections.CYBERSECURITY_TOPICS]
        collection.create_index("slug", unique=True)
        collection.create_index("category")
        collection.create_index("difficulty")

    def ensure_seeded(self, db: Database) -> None:
        """
        Upsert the starter topic dataset by slug. Safe to call every startup:
        existing topics are left as-is (matched and replaced by their own
        slug), and nothing is duplicated.
        """
        collection = db[Collections.CYBERSECURITY_TOPICS]
        for topic in STARTER_TOPICS:
            collection.update_one({"slug": topic["slug"]}, {"$setOnInsert": topic}, upsert=True)

    def list_topics(
        self, db: Database, *, category: str | None = None, difficulty: str | None = None
    ) -> list[dict]:
        """Return lightweight topic summaries, optionally filtered."""
        query: dict = {}
        if category:
            query["category"] = category
        if difficulty:
            query["difficulty"] = difficulty

        cursor = (
            db[Collections.CYBERSECURITY_TOPICS]
            .find(query, TOPIC_SUMMARY_PROJECTION)
            .sort([("category", ASCENDING), ("title", ASCENDING)])
        )
        return list(cursor)

    def get_topic_by_slug(self, db: Database, slug: str) -> TopicDocument | None:
        """Return the full topic document (learning content included), or None."""
        return db[Collections.CYBERSECURITY_TOPICS].find_one(
            {"slug": slug}, TOPIC_DETAIL_PROJECTION
        )


# Module-level singleton, matching the project's existing pattern.
learning_service = LearningService()
