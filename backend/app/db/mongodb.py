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
    Create the MongoDB client. Called once on app startup.

    This does not raise on failure — MongoDB may simply not be running yet, and the
    rest of the app (e.g. the health endpoint) should still start and clearly report
    the problem. The client is kept even when the first ping fails: PyMongo reconnects
    by itself once the server is reachable, so a database that comes up (or recovers)
    after the API has started is picked up without restarting the process. Requests made
    while it is down fail with a clean 503 (see `core.error_handlers`).
    """
    global _client, _connection_error

    try:
        client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=3000,
        )
    except PyMongoError as exc:  # e.g. a malformed MONGODB_URI
        _client = None
        _connection_error = type(exc).__name__
        logger.error("MongoDB client could not be created: %s", type(exc).__name__)
        return

    _client = client
    try:
        # Force a round trip so connection issues surface immediately.
        client.admin.command("ping")
        _connection_error = None
        logger.info("Connected to MongoDB at database '%s'", settings.mongodb_database)
    except PyMongoError as exc:
        _connection_error = str(exc)
        logger.warning("Could not connect to MongoDB yet (will keep retrying): %s", exc)


def disconnect() -> None:
    """Close the MongoDB client on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


def is_connected() -> bool:
    """True only if the server answers right now (a live ping, not just 'a client exists')."""
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def get_connection_error() -> str | None:
    return _connection_error


def get_database() -> Database:
    """
    Return the configured MongoDB database.

    Raises a RuntimeError if no client could be created at all — callers
    (e.g. FastAPI dependencies) should catch this and turn it into a clean
    503-style API error rather than letting it bubble up as a stack trace.
    """
    if _client is None:
        raise RuntimeError("MongoDB is not connected")
    return _client[settings.mongodb_database]
