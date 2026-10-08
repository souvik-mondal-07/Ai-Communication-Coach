"""
Notification routes (Step 19).

    GET    /api/v1/notifications               paginated list (read/type/date filters)
    GET    /api/v1/notifications/unread-count
    POST   /api/v1/notifications/sync          run due-reminder detection for *me* (idempotent)
    POST   /api/v1/notifications/read-all
    POST   /api/v1/notifications/{id}/read
    DELETE /api/v1/notifications/{id}

The user is always the JWT user; there is no user_id parameter and no endpoint that
creates a notification from client input.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_notification_service, get_reminder_service
from app.models.user import UserDocument
from app.schemas.notification import NotificationType, ReadFilter
from app.services.notifications.notification_service import (
    MAX_LIMIT,
    InvalidDateRangeError,
    NotificationNotFoundError,
    NotificationService,
    PageOutOfRangeError,
)
from app.services.notifications.reminder_service import ReminderService
from app.utils.helpers import success_response

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _error(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


def _not_found() -> HTTPException:
    return _error(status.HTTP_404_NOT_FOUND, "Notification not found.", "NOTIFICATION_NOT_FOUND")


@router.get("")
def list_notifications(
    read: ReadFilter = Query(default="all"),
    type: NotificationType | None = Query(default=None),
    start_date: datetime | None = Query(default=None, description="Inclusive, ISO 8601."),
    end_date: datetime | None = Query(default=None, description="Inclusive, ISO 8601."),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    try:
        data = service.list(db, user_id=str(current_user["_id"]), read=read, type=type,
                            start_date=start_date, end_date=end_date, page=page, limit=limit)
    except InvalidDateRangeError:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "The start date must be before the end date.", "INVALID_DATE_RANGE")
    except PageOutOfRangeError:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "That page is out of range.", "PAGE_OUT_OF_RANGE")
    return success_response(message="Notifications retrieved", data=_jsonable(data))


@router.get("/unread-count")
def unread_count(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    count = service.unread_count(db, user_id=str(current_user["_id"]))
    return success_response(message="Unread count retrieved", data={"unread_count": count})


@router.post("/sync")
def sync_reminders(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    reminders: ReminderService = Depends(get_reminder_service),
) -> dict:
    result = reminders.evaluate(db, user=current_user)
    return success_response(message="Reminders checked", data=_jsonable(result))


@router.post("/read-all")
def read_all(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    updated = service.mark_all_read(db, user_id=str(current_user["_id"]))
    return success_response(message="All notifications marked as read", data={"updated": updated, "unread_count": 0})


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    try:
        item = service.mark_read(db, user_id=str(current_user["_id"]), notification_id=notification_id)
    except NotificationNotFoundError:
        raise _not_found()
    return success_response(
        message="Notification marked as read",
        data={"notification": _jsonable(item), "unread_count": service.unread_count(db, user_id=str(current_user["_id"]))},
    )


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    try:
        service.delete(db, user_id=str(current_user["_id"]), notification_id=notification_id)
    except NotificationNotFoundError:
        raise _not_found()
    return success_response(message="Notification deleted", data={"unread_count": service.unread_count(db, user_id=str(current_user["_id"]))})


def _jsonable(value):
    """Datetimes -> ISO strings (Pydantic-free so the service stays a plain dict API)."""
    from fastapi.encoders import jsonable_encoder

    return jsonable_encoder(value)
