"""
Reusable MongoDB connection module.

Establishes a single PyMongo client for the app's lifetime. Connection
problems are reported clearly through `is_connected()` / `ping()` instead of
crashing the app with a raw traceback — routes that need the database can
check the connection and return a clean error response if it's unavailable.
"""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: MongoClient | None = None
_connection_error: str | None = None


def connect() -> None:
    """
    Attempt to create the MongoDB client. Called once on app startup.

    This does not raise on failure — MongoDB may simply not be running yet
    locally, and the rest of the app (e.g. the health endpoint) should still
    be able to start and clearly report the problem.
    """
    global _client, _connection_error

    try:
        client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=3000,
        )
        # Force a round trip so connection issues surface immediately.
        client.admin.command("ping")
        _client = client
        _connection_error = None
        logger.info("Connected to MongoDB at database '%s'", settings.mongodb_database)
    except PyMongoError as exc:
        _client = None
        _connection_error = str(exc)
        logger.warning("Could not connect to MongoDB: %s", exc)


def disconnect() -> None:
    """Close the MongoDB client on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


def is_connected() -> bool:
    return _client is not None


def get_connection_error() -> str | None:
    return _connection_error


def get_database() -> Database:
    """
    Return the configured MongoDB database.

    Raises a RuntimeError if the connection was never established — callers
    (e.g. FastAPI dependencies) should catch this and turn it into a clean
    503-style API error rather than letting it bubble up as a stack trace.
    """
    if _client is None:
        raise RuntimeError("MongoDB is not connected")
    return _client[settings.mongodb_database]
