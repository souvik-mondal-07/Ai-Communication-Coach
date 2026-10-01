"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    mongodb.connect()
    if mongodb.is_connected():
        db = mongodb.get_database()
        try:
            auth_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001 - startup should never crash on this
            logger.warning("Could not ensure auth indexes", exc_info=True)
        try:
            learning_service_module.learning_service.ensure_indexes(db)
            learning_service_module.learning_service.ensure_seeded(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure cybersecurity topic data", exc_info=True)
        try:
            practice_service_module.practice_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure practice session indexes", exc_info=True)
        try:
            ctf_service_module.ctf_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure CTF session indexes", exc_info=True)
        try:
            communication_service_module.communication_service.ensure_indexes(db)
            communication_service_module.communication_service.ensure_seeded(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure communication coach data", exc_info=True)
        try:
            interview_service_module.interview_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure interview session indexes", exc_info=True)
        try:
            pressure_service_module.pressure_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure pressure session indexes", exc_info=True)
        try:
            progress_service_module.progress_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure progress indexes", exc_info=True)
        try:
            voice_conversation_module.voice_conversation_service.ensure_indexes(db)
        except Exception:  # noqa: BLE001
            logger.warning("Could not ensure voice conversation indexes", exc_info=True)
    yield
    mongodb.disconnect()
    logger.info("Shutdown complete")


# `debug` is deliberately NOT passed through: Starlette's debug mode takes
# precedence over the custom 500 handler and would return a full Python
# traceback (paths, code, exception text) to the client. `settings.debug`
# only controls log verbosity; tracebacks stay in the server log.
app = FastAPI(
    title=settings.app_name,
    debug=False,
    lifespan=lifespan,
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
