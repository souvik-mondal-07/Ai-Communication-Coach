"""
Daily practice routes (Step 19).

    GET  /api/v1/daily-practice                      today's plan, goal progress and streak
    GET  /api/v1/daily-practice/streak
    POST /api/v1/daily-practice/start                mark today's plan as started (idempotent)
    POST /api/v1/daily-practice/tasks/{task}/link    attach a session started via an existing module
    POST /api/v1/daily-practice/regenerate           new plan (only while nothing has been started)
    POST /api/v1/daily-practice/complete             finish for today (needs >= 1 completed task)

No endpoint takes a user id; the plan, sessions and streak all belong to the JWT user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_daily_practice_service, get_db, get_notification_service
from app.models.user import UserDocument
from app.schemas.daily_practice import DailyPracticeOut, LinkSessionRequest, StreakOut, TaskKind
from app.services.daily_practice.daily_practice_service import (
    DailyPracticeService,
    NothingCompletedError,
    PlanLockedError,
    PlanNotFoundError,
    SessionNotEligibleError,
    TaskNotFoundError,
)
from app.services.notifications.notification_service import NotificationService
from app.utils.helpers import success_response

router = APIRouter(prefix="/daily-practice", tags=["daily-practice"])


def _error(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


def _out(db: Database, user: UserDocument, notifications: NotificationService, state: dict, message: str) -> dict:
    state = {**state, "unread_notifications": notifications.unread_count(db, user_id=str(user["_id"]))}
    return success_response(message=message, data=jsonable_encoder(DailyPracticeOut.model_validate(state)))


@router.get("")
def get_daily_practice(
    db: Database = Depends(get_db),
    user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    return _out(db, user, notifications, service.get_today(db, user=user), "Daily practice retrieved")


@router.get("/streak")
def get_streak(
    db: Database = Depends(get_db),
    user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
) -> dict:
    return success_response(message="Streak retrieved",
                            data=jsonable_encoder(StreakOut.model_validate(service.get_streak(db, user=user))))


def _guard(call, db, user, notifications, message):
    try:
        return _out(db, user, notifications, call(), message)
    except PlanNotFoundError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, str(exc), "DAILY_PRACTICE_NOT_FOUND")
    except TaskNotFoundError:
        raise _error(status.HTTP_404_NOT_FOUND, "That task is not part of today's practice.", "TASK_NOT_FOUND")
    except SessionNotEligibleError as exc:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc) or "Session cannot be linked.", "SESSION_NOT_ELIGIBLE")
    except PlanLockedError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "DAILY_PRACTICE_LOCKED")
    except NothingCompletedError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "NOTHING_COMPLETED")


@router.post("/start")
def start(
    db: Database = Depends(get_db), user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    return _guard(lambda: service.start(db, user=user), db, user, notifications, "Daily practice started")


@router.post("/tasks/{task_id}/link")
def link_task_session(
    task_id: TaskKind, body: LinkSessionRequest,
    db: Database = Depends(get_db), user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    return _guard(lambda: service.link_session(db, user=user, task_id=task_id, session_id=body.session_id),
                  db, user, notifications, "Session linked to today's practice")


@router.post("/regenerate")
def regenerate(
    db: Database = Depends(get_db), user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    return _guard(lambda: service.regenerate(db, user=user), db, user, notifications, "Daily practice regenerated")


@router.post("/complete")
def complete(
    db: Database = Depends(get_db), user: UserDocument = Depends(get_current_user),
    service: DailyPracticeService = Depends(get_daily_practice_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    return _guard(lambda: service.complete(db, user=user), db, user, notifications, "Daily practice completed")
