"""
Central API router.

All versioned API routes are aggregated here and mounted once in `main.py`
under `settings.api_v1_prefix` (`/api/v1`). Domain routers with no routes
yet (auth, mentor, etc.) are still included so the URL structure is fixed
in place before their endpoints are implemented.
"""

from fastapi import APIRouter

from app.api.routes import (
    auth,
    communication,
    cybersecurity,
    health,
    interview,
    mentor,
    progress,
    users,
    voice,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(mentor.router)
api_router.include_router(cybersecurity.router)
api_router.include_router(communication.router)
api_router.include_router(interview.router)
api_router.include_router(voice.router)
api_router.include_router(progress.router)
