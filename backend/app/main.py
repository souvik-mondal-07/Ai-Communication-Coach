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
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    mongodb.connect()
    if mongodb.is_connected():
        try:
            auth_service.ensure_indexes(mongodb.get_database())
        except Exception:  # noqa: BLE001 - startup should never crash on this
            logger.warning("Could not ensure database indexes", exc_info=True)
    yield
    mongodb.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
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
