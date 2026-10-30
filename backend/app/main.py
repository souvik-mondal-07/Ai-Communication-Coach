"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.request_limits import BodySizeLimitMiddleware
from app.db import mongodb
from app.services.auth import auth_service
from app.services.cybersecurity import learning_service as learning_service_module
from app.services.cybersecurity import practice_service as practice_service_module
from app.services.cybersecurity import ctf_service as ctf_service_module
from app.services.communication import communication_service as communication_service_module
from app.services.interview import interview_service as interview_service_module
from app.services.pressure import pressure_service as pressure_service_module
from app.services.progress import progress_service as progress_service_module
from app.services.voice_conversation import conversation_service as voice_conversation_module
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _ensure_database_ready(db) -> bool:
    """
    Create indexes and seed reference data. Idempotent — safe to run repeatedly.

    Every step is isolated, so one failing step never blocks the others. Returns True
    only if all of them succeeded (False means "try again later").
    """
    from app.services.daily_practice.daily_practice_service import daily_practice_service
    from app.services.daily_practice.streak import streak_service
    from app.services.news.news_service import news_service
    from app.services.notifications.notification_service import notification_service

    def learning() -> None:
        learning_service_module.learning_service.ensure_indexes(db)
        learning_service_module.learning_service.ensure_seeded(db)

    def aptitude() -> None:
        from app.services.aptitude import bank as aptitude_bank

        aptitude_bank.ensure_indexes(db)
        aptitude_bank.ensure_seeded(db)

    def dsa() -> None:
        from app.services.dsa import bank as dsa_bank

        dsa_bank.ensure_indexes(db)
        dsa_bank.ensure_seeded(db)

    def dbms_sql() -> None:
        from app.services.dbms_sql import bank as dbms_sql_bank

        dbms_sql_bank.ensure_indexes(db)
        dbms_sql_bank.ensure_seeded(db)

    def python_practice() -> None:
        from app.services.python_practice import bank as python_bank

        python_bank.ensure_indexes(db)
        python_bank.ensure_seeded(db)

    def communication() -> None:
        communication_service_module.communication_service.ensure_indexes(db)
        communication_service_module.communication_service.ensure_seeded(db)

    def daily_and_notifications() -> None:
        notification_service.ensure_indexes(db)
        daily_practice_service.ensure_indexes(db)
        streak_service.ensure_indexes(db)

    steps = (
        ("auth indexes", lambda: auth_service.ensure_indexes(db)),
        ("legacy token versions", lambda: auth_service.migrate_legacy_token_versions(db)),
        ("cybersecurity topic data", learning),
        ("practice session indexes", lambda: practice_service_module.practice_service.ensure_indexes(db)),
        ("CTF session indexes", lambda: ctf_service_module.ctf_service.ensure_indexes(db)),
        ("communication coach data", communication),
        ("interview session indexes", lambda: interview_service_module.interview_service.ensure_indexes(db)),
        ("pressure session indexes", lambda: pressure_service_module.pressure_service.ensure_indexes(db)),
        ("progress indexes", lambda: progress_service_module.progress_service.ensure_indexes(db)),
        ("voice conversation indexes", lambda: voice_conversation_module.voice_conversation_service.ensure_indexes(db)),
        ("notification / daily practice indexes", daily_and_notifications),
        ("news cache indexes", lambda: news_service.ensure_indexes(db)),
        ("aptitude question bank", aptitude),
        ("DSA question bank", dsa),
        ("DBMS & SQL question bank", dbms_sql),
        ("Python practice question bank", python_practice),
    )
    all_ok = True
    for label, step in steps:
        try:
            step()
        except Exception:  # noqa: BLE001 - startup should never crash on this
            all_ok = False
            logger.warning("Could not ensure %s", label, exc_info=True)
    return all_ok


DB_SETUP_RETRY_SECONDS = 15


async def _retry_database_setup() -> None:
    """Keep trying until the database is reachable and fully set up, then stop."""
    while True:
        await asyncio.sleep(DB_SETUP_RETRY_SECONDS)
        try:
            if not mongodb.is_connected():
                continue
            if await asyncio.to_thread(_ensure_database_ready, mongodb.get_database()):
                logger.info("Database setup completed after retry")
                return
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - never let the retry loop die
            logger.warning("Database setup retry failed", exc_info=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    mongodb.connect()
    retry_task: asyncio.Task | None = None
    ready = False
    if mongodb.is_connected():
        ready = _ensure_database_ready(mongodb.get_database())
    if not ready:
        # MongoDB was down (or a setup step failed) at boot. Without this the unique
        # email index and the others would never be created until a manual restart.
        logger.warning("Database not ready at startup; will retry every %ss", DB_SETUP_RETRY_SECONDS)
        retry_task = asyncio.create_task(_retry_database_setup())
    warm_task: asyncio.Task | None = None
    if settings.news_enabled and mongodb.is_connected():
        # Warm the news cache once without delaying startup (never blocks, never raises).
        from app.services.news.news_service import news_service

        warm_task = asyncio.create_task(asyncio.to_thread(news_service.refresh_if_due, mongodb.get_database()))
    try:
        yield
    finally:
        if warm_task is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(asyncio.shield(warm_task), timeout=0.1)
        if retry_task is not None:
            retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await retry_task
        mongodb.disconnect()
        logger.info("Shutdown complete")


# `debug` is deliberately NOT passed through: Starlette's debug mode takes
# precedence over the custom 500 handler and would return a full Python
# traceback (paths, code, exception text) to the client. `settings.debug`
# only controls log verbosity; tracebacks stay in the server log.
# The interactive docs and the schema describe every endpoint, so they are development-only.
_docs_urls = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if settings.is_production
    else {}
)

app = FastAPI(
    title=settings.app_name,
    debug=False,
    lifespan=lifespan,
    **_docs_urls,
)

# Added before CORS so CORS stays outermost and 413 responses still carry CORS headers.
# Audio routes (/voice, /voice-conversation) enforce their own, larger upload limit.
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.max_request_body_bytes,
    exempt_prefixes=(f"{settings.api_v1_prefix}/voice",),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict:
    """Simple project status response at the API root."""
    return success_response(
        message="Service is running.",
        data={
            "service": settings.app_name,
            "environment": settings.app_env,
            "api_prefix": settings.api_v1_prefix,
        },
    )
