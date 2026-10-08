"""
Tests for Step 19 -- notifications, reminders, deduplication, limits and ownership.

Notifications are only ever created server-side, so most tests create them through the
service (or by running reminder evaluation) and then exercise the real HTTP API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.db.collections import Collections
from app.schemas.notification import NotificationPriority as P
from app.schemas.notification import NotificationType as T
from app.services.daily_practice.daily_practice_service import daily_practice_service
from app.services.notifications.notification_service import InvalidNotificationError, notification_service as ns
from app.services.notifications.reminder_config import MAX_DAILY_NOTIFICATIONS
from app.services.notifications.reminder_service import reminder_service
from app.services.personalization.personalization_service import clear_cache
from tests.test_communication import _register_and_login
from tests.test_daily_practice import requires_tzdata, _done_practice, _naive, _prefs, _user, _weak_practice
from tests.test_history import _communication

URL = "/api/v1/notifications"
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)  # Wednesday, 12:00 UTC


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _ttl_uses_real_clock(fake_db):
    """
    mongomock honours TTL indexes against the *real* clock, but these tests pin ``now`` to a fixed
    date, so notifications would be purged instantly. Real MongoDB's TTL monitor only deletes
    already-expired documents, which is covered by test_expired_notifications_are_hidden...;
    the index definition itself is asserted in test_notification_indexes_exist.
    """
    fake_db[Collections.NOTIFICATIONS].drop_index("expires_at_1")


def _auth(client, email="n@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _make(fake_db, user, key="k1", *, type=T.SYSTEM, title="Hello", expires=None, now=None):
    return ns.create_if_absent(fake_db, user_id=str(user["_id"]), type=type, priority=P.LOW, title=title,
                               message="msg", action_target="/dashboard", dedupe_key=key, expires_at=expires, now=now or NOW)


# ================================================================== API: auth + CRUD
def test_all_notification_endpoints_require_auth(client):
    nid = str(ObjectId())
    for method, path in (("get", URL), ("get", f"{URL}/unread-count"), ("post", f"{URL}/sync"),
                         ("post", f"{URL}/read-all"), ("post", f"{URL}/{nid}/read"), ("delete", f"{URL}/{nid}")):
        assert getattr(client, method)(path).status_code == 401, path


def test_no_endpoint_creates_notifications_from_client_input(client):
    headers = _auth(client)
    body = {"type": "system", "title": "x", "message": "y", "user_id": str(ObjectId())}
    assert client.post(URL, json=body, headers=headers).status_code == 405
    assert client.put(URL, json=body, headers=headers).status_code == 405


def test_list_unread_count_mark_read_and_read_all(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db, "n@example.com")
    ids = [_make(fake_db, user, f"k{i}", title=f"T{i}", now=NOW + timedelta(minutes=i))["id"] for i in range(3)]
    far = datetime.now(timezone.utc) + timedelta(days=1)  # nothing expires during the test
    for i in range(3):
        fake_db[Collections.NOTIFICATIONS].update_one({"_id": ObjectId(ids[i])}, {"$set": {"expires_at": None}})

    data = client.get(URL, headers=headers).json()["data"]
    assert data["total"] == 3 and data["unread_count"] == 3
    assert [n["title"] for n in data["items"]] == ["T2", "T1", "T0"]  # newest first
    assert client.get(f"{URL}/unread-count", headers=headers).json()["data"]["unread_count"] == 3

    r = client.post(f"{URL}/{ids[0]}/read", headers=headers).json()["data"]
    assert r["notification"]["is_read"] is True and r["notification"]["read_at"] and r["unread_count"] == 2
    again = client.post(f"{URL}/{ids[0]}/read", headers=headers).json()["data"]  # idempotent
    assert again["unread_count"] == 2 and again["notification"]["read_at"] == r["notification"]["read_at"]

    assert [n["id"] for n in client.get(f"{URL}?read=unread", headers=headers).json()["data"]["items"]] == [ids[2], ids[1]]
    assert [n["id"] for n in client.get(f"{URL}?read=read", headers=headers).json()["data"]["items"]] == [ids[0]]

    done = client.post(f"{URL}/read-all", headers=headers).json()["data"]
    assert done["updated"] == 2 and done["unread_count"] == 0


def test_delete_removes_only_that_notification(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db, "n@example.com")
    a, b = _make(fake_db, user, "a")["id"], _make(fake_db, user, "b")["id"]
    assert client.delete(f"{URL}/{a}", headers=headers).status_code == 200
    ids = [n["id"] for n in client.get(f"{URL}", headers=headers).json()["data"]["items"]]
    assert ids == [b]
    assert client.delete(f"{URL}/{a}", headers=headers).status_code == 404


def test_pagination(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db, "n@example.com")
    for i in range(5):
        _make(fake_db, user, f"k{i}", title=f"T{i}", now=NOW + timedelta(minutes=i))
    p1 = client.get(f"{URL}?limit=2&page=1", headers=headers).json()["data"]
    p3 = client.get(f"{URL}?limit=2&page=3", headers=headers).json()["data"]
    assert len(p1["items"]) == 2 and p1["has_next"] and p1["total"] == 5
    assert len(p3["items"]) == 1 and not p3["has_next"]
    assert client.get(f"{URL}?limit=2&page=9", headers=headers).status_code == 422
    assert client.get(f"{URL}?page=0", headers=headers).status_code == 422
    assert client.get(f"{URL}?limit=1000", headers=headers).status_code == 422


def test_type_and_date_filters_are_validated(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db, "n@example.com")
    _make(fake_db, user, "a", type=T.STREAK)
    _make(fake_db, user, "b", type=T.SYSTEM)
    assert [n["type"] for n in client.get(f"{URL}?type=streak", headers=headers).json()["data"]["items"]] == ["streak"]
    assert client.get(f"{URL}?type=made_up", headers=headers).status_code == 422
    assert client.get(f"{URL}?read=maybe", headers=headers).status_code == 422
    assert client.get(f"{URL}?start_date=not-a-date", headers=headers).status_code == 422
    bad = client.get(f"{URL}?start_date=2026-10-09T00:00:00Z&end_date=2026-10-01T00:00:00Z", headers=headers)
    assert bad.status_code == 422 and bad.json()["error_code"] == "INVALID_DATE_RANGE"
    ok = client.get(f"{URL}?start_date=2026-10-01T00:00:00Z&end_date=2026-10-08T00:00:00Z", headers=headers)
    assert ok.json()["data"]["total"] == 2


def test_malformed_ids_are_404_not_500(client):
    headers = _auth(client)
    assert client.post(f"{URL}/not-an-id/read", headers=headers).status_code == 404
    assert client.delete(f"{URL}/123", headers=headers).status_code == 404


def test_service_rejects_unknown_type_and_external_action(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    with pytest.raises(InvalidNotificationError):
        ns.create_if_absent(fake_db, user_id=str(user["_id"]), type="hacked", priority=P.LOW, title="t", message="m",
                            action_target=None, dedupe_key="x", expires_at=None)
    with pytest.raises(InvalidNotificationError):
        ns.create_if_absent(fake_db, user_id=str(user["_id"]), type=T.SYSTEM, priority=P.LOW, title="t", message="m",
                            action_target="https://evil.example", dedupe_key="y", expires_at=None)


# ================================================================== ownership
def test_users_cannot_read_modify_or_delete_each_others_notifications(client, fake_db):
    a, b = _auth(client, "a@example.com"), _auth(client, "b@example.com")
    ua = _user(fake_db, "a@example.com")
    nid = _make(fake_db, ua, "private", title="A only")["id"]
    assert client.get(URL, headers=b).json()["data"]["items"] == []
    assert client.get(f"{URL}/unread-count", headers=b).json()["data"]["unread_count"] == 0
    assert client.post(f"{URL}/{nid}/read", headers=b).status_code == 404
    assert client.delete(f"{URL}/{nid}", headers=b).status_code == 404
    assert client.post(f"{URL}/read-all", headers=b).json()["data"]["updated"] == 0
    # ...and A's notification is untouched.
    item = client.get(URL, headers=a).json()["data"]["items"][0]
    assert item["id"] == nid and item["is_read"] is False


# ================================================================== expiry + deduplication
def test_expired_notifications_are_hidden_and_not_counted(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db, "n@example.com")
    _make(fake_db, user, "old", expires=datetime.now(timezone.utc) - timedelta(minutes=1))
    _make(fake_db, user, "live", expires=datetime.now(timezone.utc) + timedelta(days=1))
    data = client.get(URL, headers=headers).json()["data"]
    assert data["total"] == 1 and data["unread_count"] == 1


def test_same_dedupe_key_creates_once(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    assert _make(fake_db, user, "same") is not None
    assert _make(fake_db, user, "same") is None
    assert fake_db[Collections.NOTIFICATIONS].count_documents({}) == 1


def test_notification_indexes_exist():
    import mongomock
    db = mongomock.MongoClient()["idx"]
    ns.ensure_indexes(db)
    info = db[Collections.NOTIFICATIONS].index_information()
    assert info["user_id_1_dedupe_key_1"]["unique"] is True
    assert "user_id_1_created_at_-1" in info and "user_id_1_is_read_1" in info
    assert info["expires_at_1"]["expireAfterSeconds"] == 0


# ================================================================== reminders
def _eval(fake_db, email="n@example.com", now=NOW):
    return reminder_service.evaluate(fake_db, user=_user(fake_db, email), now=now)


def _titles(fake_db):
    return [n["title"] for n in fake_db[Collections.NOTIFICATIONS].find({}).sort("created_at", 1)]


def test_daily_reminder_is_created_once_however_often_it_runs(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    created = [len(_eval(fake_db)["created"]) for _ in range(10)]
    assert created[0] == 1 and sum(created) == 1
    doc = fake_db[Collections.NOTIFICATIONS].find_one({})
    assert doc["type"] == "daily_practice" and doc["dedupe_key"] == "daily_practice:2026-10-07"
    assert doc["action"] == {"type": "route", "target": "/daily-practice"}
    assert doc["expires_at"] > doc["created_at"]


@requires_tzdata
def test_reminder_waits_for_the_preferred_time_in_the_users_timezone(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="18:00", preferred_timezone="Asia/Kolkata")
    # 12:00 UTC is 17:30 in Kolkata -> not yet; 12:31 UTC is 18:01 -> due.
    assert _eval(fake_db, now=NOW)["created"] == []
    assert len(_eval(fake_db, now=NOW + timedelta(minutes=31))["created"]) == 1


def test_reminders_disabled_creates_nothing_then_enabling_works(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", reminders_enabled=False)
    assert _eval(fake_db)["created"] == [] and fake_db[Collections.NOTIFICATIONS].count_documents({}) == 0
    _prefs(fake_db, "n@example.com", reminders_enabled=True)
    assert len(_eval(fake_db)["created"]) == 1


def test_daily_practice_disabled_means_no_daily_reminder(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", daily_practice_enabled=False)
    assert _eval(fake_db)["created"] == []


def test_rest_day_creates_no_reminder(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", practice_days=["mon", "tue"])
    assert _eval(fake_db)["created"] == []


def test_no_reminder_after_practicing_today(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    _done_practice(fake_db, user["_id"], NOW - timedelta(hours=1))
    assert _eval(fake_db)["created"] == []


def test_streak_appears_in_the_daily_reminder_message(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    for d in (1, 2, 3):
        _done_practice(fake_db, user["_id"], NOW - timedelta(days=d))
    made = _eval(fake_db)["created"]
    assert "3-day streak" in made[0]["message"]


def test_weakness_reminder_uses_real_evidence_and_respects_its_toggle(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _weak_practice(fake_db, user["_id"], "Web Security", [40, 45, 42, 50], NOW)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", cybersecurity_reminders_enabled=False)
    assert "weakness" not in {n["type"] for n in _eval(fake_db)["created"]}
    _prefs(fake_db, "n@example.com", cybersecurity_reminders_enabled=True)
    made = {n["type"]: n for n in _eval(fake_db)["created"]}
    assert made["weakness"]["priority"] in ("high", "medium")
    assert "Web Security" in made["weakness"]["title"] and "average" in made["weakness"]["message"]
    assert _eval(fake_db)["created"] == []  # not repeated this week


def test_interview_and_communication_reminders_follow_real_gaps_and_toggles(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", daily_practice_enabled=False)
    fake_db[Collections.USERS].update_one({"_id": user["_id"]}, {"$set": {"profile.learning_goals": ["prepare_for_interviews", "improve_communication"]}})
    types = lambda r: {n["type"] for n in r["created"]}  # noqa: E731
    _prefs(fake_db, "n@example.com", interview_reminders_enabled=False, communication_reminders_enabled=False)
    assert _eval(fake_db)["created"] == []
    _prefs(fake_db, "n@example.com", interview_reminders_enabled=True)
    assert types(_eval(fake_db)) == {"interview"}
    _prefs(fake_db, "n@example.com", communication_reminders_enabled=True)
    assert types(_eval(fake_db)) == {"communication"}


def test_recent_communication_practice_suppresses_the_communication_reminder(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00", daily_practice_enabled=False,
           interview_reminders_enabled=False)
    fake_db[Collections.USERS].update_one({"_id": user["_id"]}, {"$set": {"profile.learning_goals": ["improve_communication"]}})
    doc = _communication(user["_id"], started=_naive(NOW - timedelta(days=1, minutes=5)))
    doc["completed_at"] = _naive(NOW - timedelta(days=1))
    fake_db[Collections.COMMUNICATION_SESSIONS].insert_one(doc)
    assert _eval(fake_db)["created"] == []


def test_lapse_reminder_after_a_real_gap(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    _done_practice(fake_db, user["_id"], NOW - timedelta(days=5))
    types = {n["type"] for n in _eval(fake_db)["created"]}
    assert {"daily_practice", "practice_reminder"} <= types


def test_streak_milestone_notification(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    for d in (0, 1, 2):
        _done_practice(fake_db, user["_id"], NOW - timedelta(days=d, hours=1))
    made = _eval(fake_db)["created"]
    assert [n["type"] for n in made] == ["streak"] and "3 days" in made[0]["message"]
    assert _eval(fake_db)["created"] == []


def test_daily_notification_limit_and_priority_order(client, fake_db):
    _auth(client)
    user = _user(fake_db, "n@example.com")
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    fake_db[Collections.USERS].update_one({"_id": user["_id"]}, {"$set": {"profile.learning_goals": ["prepare_for_interviews", "improve_communication"]}})
    _weak_practice(fake_db, user["_id"], "Web Security", [40, 45, 42, 50], NOW)
    _done_practice(fake_db, user["_id"], NOW - timedelta(days=6))  # lapse too
    made = _eval(fake_db)["created"]
    assert len(made) == MAX_DAILY_NOTIFICATIONS
    ranks = [{"high": 0, "medium": 1, "low": 2}[n["priority"]] for n in made]
    assert ranks == sorted(ranks) and ranks[0] == 0
    assert _eval(fake_db)["created"] == []  # cap is reached for today
    # The next local day has a fresh budget.
    assert _eval(fake_db, now=NOW + timedelta(days=1))["created"]


def test_sync_endpoint_is_idempotent_and_bell_counts_follow(client, fake_db):
    headers = _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="00:00")
    first = client.post(f"{URL}/sync", headers=headers).json()["data"]
    assert len(first["created"]) == 1 and first["unread_count"] == 1
    for _ in range(3):
        again = client.post(f"{URL}/sync", headers=headers).json()["data"]
        assert again["created"] == [] and again["unread_count"] == 1
    nid = client.get(URL, headers=headers).json()["data"]["items"][0]["id"]
    assert client.post(f"{URL}/{nid}/read", headers=headers).json()["data"]["unread_count"] == 0
    assert client.get(f"{URL}/unread-count", headers=headers).json()["data"]["unread_count"] == 0


def test_reminder_does_not_generate_ai_calls_or_leak_user_content(client, fake_db):
    _auth(client)
    _prefs(fake_db, "n@example.com", preferred_practice_time="09:00")
    made = _eval(fake_db)["created"]
    assert set(made[0]) == {"id", "type", "priority", "title", "message", "action", "is_read", "created_at", "read_at", "expires_at"}
    assert "dedupe_key" not in made[0] and "user_id" not in made[0]
