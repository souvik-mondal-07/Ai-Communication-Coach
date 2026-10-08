"""
Tests for Step 19 -- daily practice, streaks and timezones.

Sessions are seeded into the (mongomock) collections in the shape the real services
write them; the plan/streak code is a read+reconcile layer over them. Time-sensitive
cases call the services with an explicit ``now`` so day/timezone boundaries are exact.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.db.collections import Collections
from app.services.daily_practice import planner, timeutil
from app.services.daily_practice.daily_practice_service import (
    NothingCompletedError,
    PlanLockedError,
    SessionNotEligibleError,
    daily_practice_service as svc,
)
from app.services.daily_practice.streak import compute_streak, qualifies, streak_service
from app.services.personalization.personalization_service import clear_cache
from tests.test_communication import _register_and_login
from tests.test_history import _communication, _practice as _history_practice

URL = "/api/v1/daily-practice"


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


def _auth(client, email="d@example.com"):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _user(fake_db, email="d@example.com"):
    return fake_db[Collections.USERS].find_one({"email": email})


def _prefs(fake_db, email="d@example.com", **prefs):
    fake_db[Collections.USERS].update_one({"email": email}, {"$set": {f"preferences.{k}": v for k, v in prefs.items()}})
    return _user(fake_db, email)


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _done_practice(fake_db, uid, completed: datetime, *, minutes=8, score=80, category="Linux"):
    doc = _history_practice(uid, category=category, started=_naive(completed - timedelta(minutes=minutes)), score=score)
    doc["completed_at"] = _naive(completed)
    return fake_db[Collections.PRACTICE_SESSIONS].insert_one(doc).inserted_id


def _weak_practice(fake_db, uid, category, scores, now):
    for i, score in enumerate(scores):
        fake_db[Collections.PRACTICE_SESSIONS].insert_one({
            "user_id": uid, "topic_slug": f"{category.lower()}-{i}", "topic_title": f"{category} {i}",
            "category": category, "difficulty": "intermediate", "status": "completed", "score": score,
            "questions_answered": 5, "correct_answers": round(5 * score / 100),
            "started_at": _naive(now - timedelta(days=20 - i)), "completed_at": _naive(now - timedelta(days=20 - i)),
        })


def _has_tzdata() -> bool:
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("Asia/Kolkata")
        return True
    except Exception:  # noqa: BLE001
        return False


# Named zones need the IANA database (`pip install tzdata`, listed in requirements.txt).
requires_tzdata = pytest.mark.skipif(not _has_tzdata(), reason="IANA timezone database not installed (pip install tzdata)")

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)  # a Wednesday


# ================================================================== streak (pure)
def test_first_practice_starts_a_streak_of_one():
    r = compute_streak({date(2026, 10, 7)}, today=date(2026, 10, 7))
    assert r["current_streak"] == 1 and r["longest_streak"] == 1 and r["total_active_days"] == 1
    assert r["practiced_today"] and not r["at_risk"]


def test_no_activity_means_no_streak():
    r = compute_streak(set(), today=date(2026, 10, 7))
    assert r["current_streak"] == 0 and r["last_practice_date"] is None


def test_consecutive_days_accumulate():
    days = {date(2026, 10, d) for d in (1, 2, 3, 4, 5, 6, 7)}
    assert compute_streak(days, today=date(2026, 10, 7))["current_streak"] == 7


def test_streak_survives_until_the_day_ends_then_is_at_risk():
    r = compute_streak({date(2026, 10, 5), date(2026, 10, 6)}, today=date(2026, 10, 7))
    assert r["current_streak"] == 2 and r["at_risk"] and not r["practiced_today"]


def test_missed_day_resets_current_but_keeps_longest():
    days = {date(2026, 10, d) for d in (1, 2, 3, 4)} | {date(2026, 10, 7)}
    r = compute_streak(days, today=date(2026, 10, 7))
    assert r["current_streak"] == 1 and r["longest_streak"] == 4


def test_two_missed_days_ends_current_streak():
    r = compute_streak({date(2026, 10, 3), date(2026, 10, 4)}, today=date(2026, 10, 7))
    assert r["current_streak"] == 0 and r["longest_streak"] == 2 and not r["at_risk"]


def test_future_dates_are_ignored():
    r = compute_streak({date(2026, 10, 7), date(2026, 10, 9), date(2026, 10, 10)}, today=date(2026, 10, 7))
    assert r["current_streak"] == 1 and r["total_active_days"] == 1 and r["last_practice_date"] == "2026-10-07"


def test_rest_days_do_not_break_a_streak():
    # Mon-Fri practice days; Fri 2, Mon 5, Tue 6 -- the weekend is skipped.
    weekdays = frozenset(range(5))
    days = {date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6)}
    assert compute_streak(days, today=date(2026, 10, 6), practice_weekdays=weekdays)["current_streak"] == 4
    assert compute_streak(days, today=date(2026, 10, 6))["current_streak"] == 2  # all-days rule


def test_missing_a_practice_day_breaks_it_even_with_rest_days():
    weekdays = frozenset(range(5))
    days = {date(2026, 10, 1), date(2026, 10, 5), date(2026, 10, 6)}  # Fri Oct 2 missed
    assert compute_streak(days, today=date(2026, 10, 6), practice_weekdays=weekdays)["current_streak"] == 2


# ================================================================== completion rule + timezone
def test_only_completed_scored_sessions_qualify(client, fake_db):
    _auth(client)
    uid = _user(fake_db)["_id"]
    fake_db[Collections.PRACTICE_SESSIONS].insert_one({**_history_practice(uid, status="in_progress"), "started_at": _naive(NOW)})
    fake_db[Collections.PRACTICE_SESSIONS].insert_one({**_history_practice(uid, score=None), "score": None})
    streak = streak_service.get_streak(fake_db, user_id=str(uid), tz_name="UTC", now=NOW)
    assert streak["current_streak"] == 0 and streak["total_active_days"] == 0


def test_several_sessions_on_one_day_count_once(client, fake_db):
    _auth(client)
    uid = _user(fake_db)["_id"]
    for h in (8, 9, 10):
        _done_practice(fake_db, uid, NOW.replace(hour=h))
    streak = streak_service.get_streak(fake_db, user_id=str(uid), tz_name="UTC", now=NOW)
    assert streak["total_active_days"] == 1 and streak["current_streak"] == 1


@requires_tzdata
def test_timezone_decides_which_day_a_session_belongs_to(client, fake_db):
    _auth(client)
    uid = _user(fake_db)["_id"]
    # 20:00 UTC on Oct 6 is 01:30 on Oct 7 in Kolkata (UTC+5:30).
    _done_practice(fake_db, uid, datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc))
    now = datetime(2026, 10, 7, 3, 0, tzinfo=timezone.utc)  # 08:30 Oct 7 in Kolkata; still Oct 7 UTC
    kolkata = streak_service.get_streak(fake_db, user_id=str(uid), tz_name="Asia/Kolkata", now=now)
    utc = streak_service.get_streak(fake_db, user_id=str(uid), tz_name="UTC", now=now)
    assert kolkata["practiced_today"] is True and kolkata["last_practice_date"] == "2026-10-07"
    assert utc["practiced_today"] is False and utc["last_practice_date"] == "2026-10-06"


@requires_tzdata
def test_changing_timezone_rebuilds_instead_of_reusing_stale_dates(client, fake_db):
    _auth(client)
    uid = str(_user(fake_db)["_id"])
    _done_practice(fake_db, ObjectId(uid), datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc))
    now = datetime(2026, 10, 7, 3, 0, tzinfo=timezone.utc)
    assert streak_service.get_streak(fake_db, user_id=uid, tz_name="UTC", now=now)["last_practice_date"] == "2026-10-06"
    assert streak_service.get_streak(fake_db, user_id=uid, tz_name="Asia/Kolkata", now=now)["last_practice_date"] == "2026-10-07"
    assert streak_service.get_streak(fake_db, user_id=uid, tz_name="UTC", now=now)["last_practice_date"] == "2026-10-06"


def test_works_without_any_timezone_database(monkeypatch, client, fake_db):
    """Windows without `tzdata`: every ZoneInfo lookup fails, yet plans and streaks still work in UTC."""
    from zoneinfo import ZoneInfoNotFoundError

    def _missing(key):
        raise ZoneInfoNotFoundError(f"No time zone found with key {key}")

    monkeypatch.setattr(timeutil, "ZoneInfo", _missing)
    assert timeutil.resolve_tz("Asia/Kolkata") is timezone.utc and timeutil.tz_name("Asia/Kolkata") == "UTC"
    headers = _auth(client)
    data = client.get(URL, headers=headers).json()["data"]
    assert data["timezone"] == "UTC" and data["plan"] is not None and data["streak"]["timezone"] == "UTC"
    # "UTC" is always an acceptable preference; a named zone cannot be validated without the database.
    assert client.patch("/api/v1/users/me/preferences", json={"preferred_timezone": "UTC"}, headers=headers).status_code == 200


def test_invalid_timezone_falls_back_to_utc():
    assert timeutil.tz_name("Not/AZone") == "UTC" and timeutil.tz_name(None) == "UTC"


@requires_tzdata
def test_dst_day_has_23_hours():
    tz = timeutil.resolve_tz("America/New_York")
    start, end = timeutil.day_bounds_utc(date(2026, 3, 8), tz)  # spring forward
    assert end - start == timedelta(hours=23)


def test_streak_grows_over_consecutive_real_days(client, fake_db):
    _auth(client)
    uid = _user(fake_db)["_id"]
    for n in range(1, 5):
        day = NOW - timedelta(days=4 - n)
        _done_practice(fake_db, uid, day)
        s = streak_service.get_streak(fake_db, user_id=str(uid), tz_name="UTC", now=day + timedelta(hours=1))
        assert s["current_streak"] == n  # 1, 2, 3, 4


def test_qualifies_rule_ctf_without_score(client, fake_db):
    from tests.test_history import _ctf
    from app.services.history.history_service import history_service
    _auth(client)
    uid = _user(fake_db)["_id"]
    fake_db[Collections.CTF_SESSIONS].insert_one({**_ctf(uid, created=_naive(NOW - timedelta(hours=2)))})
    acts = history_service.list_completed(fake_db, user_id=str(uid))
    assert acts and all(qualifies(a) for a in acts)


# ================================================================== planner (pure)
def _pers(**kw):
    base = {"data_status": "none", "recommended_difficulty": "beginner", "recommendations": [],
            "interview_focus": [], "learning_goals": []}
    return {**base, **kw}


SCENARIOS = [
    {"scenario_id": "a" * 24, "slug": "alpha", "title": "Alpha", "difficulty": "beginner", "objective": "o", "skills_targeted": ["clarity"]},
    {"scenario_id": "b" * 24, "slug": "beta", "title": "Beta", "difficulty": "beginner", "objective": "o", "skills_targeted": []},
]


def test_plan_follows_the_weakest_area_and_explains_why():
    rec = {"type": "practice", "topic": "SOC", "topic_slug": "soc-1", "difficulty": "intermediate",
           "reasons": ["Average 41/100 over 4 recorded attempts."], "basis": "performance", "priority": "high"}
    plan = planner.build_plan(pers=_pers(recommendations=[rec]), goal_minutes=15, difficulty_pref="intermediate",
                              scenarios=SCENARIOS, recent_scenario_ids=set(), today=date(2026, 10, 7))
    cyber = plan["tasks"][0]
    assert cyber["config"]["category"] == "SOC" and cyber["config"]["mode"] == "topic"
    assert "Average 41/100" in cyber["why"][0]
    assert plan["focus"]["basis"] == "performance"


def test_plan_differs_for_different_weaknesses():
    def rec(topic):
        return {"type": "practice", "topic": topic, "topic_slug": None, "difficulty": "beginner", "reasons": ["x"],
                "basis": "performance", "priority": "medium"}
    a = planner.build_plan(pers=_pers(recommendations=[rec("Linux")]), goal_minutes=10, difficulty_pref="adaptive",
                           scenarios=SCENARIOS, recent_scenario_ids=set(), today=date(2026, 10, 7))
    b = planner.build_plan(pers=_pers(recommendations=[rec("Cryptography")]), goal_minutes=10, difficulty_pref="adaptive",
                           scenarios=SCENARIOS, recent_scenario_ids=set(), today=date(2026, 10, 7))
    assert a["tasks"][0]["config"]["category"] != b["tasks"][0]["config"]["category"]


def test_adaptive_only_with_enough_data():
    few = planner.build_plan(pers=_pers(data_status="limited"), goal_minutes=10, difficulty_pref="adaptive",
                             scenarios=[], recent_scenario_ids=set(), today=date(2026, 10, 7))
    many = planner.build_plan(pers=_pers(data_status="sufficient"), goal_minutes=10, difficulty_pref="adaptive",
                              scenarios=[], recent_scenario_ids=set(), today=date(2026, 10, 7))
    fixed = planner.build_plan(pers=_pers(data_status="sufficient"), goal_minutes=10, difficulty_pref="advanced",
                               scenarios=[], recent_scenario_ids=set(), today=date(2026, 10, 7))
    assert few["tasks"][0]["config"]["difficulty"] == "beginner"
    assert many["tasks"][0]["config"]["difficulty"] == "adaptive"
    assert fixed["tasks"][0]["config"]["difficulty"] == "advanced"


@pytest.mark.parametrize("minutes,kinds", [
    (5, ["cybersecurity"]), (10, ["cybersecurity", "communication"]),
    (30, ["cybersecurity", "communication", "interview"]),
])
def test_task_mix_fits_the_time_budget(minutes, kinds):
    plan = planner.build_plan(pers=_pers(), goal_minutes=minutes, difficulty_pref="adaptive",
                              scenarios=SCENARIOS, recent_scenario_ids=set(), today=date(2026, 10, 7))
    assert [t["kind"] for t in plan["tasks"]] == kinds
    assert sum(t["est_minutes"] for t in plan["tasks"]) <= minutes + 3


def test_scenario_choice_avoids_recent_and_matches_skill():
    chosen = planner.pick_scenario(SCENARIOS, level="beginner", skill="Clarity", recent_ids=set(), today=date(2026, 10, 7))
    assert chosen["slug"] == "alpha"
    other = planner.pick_scenario(SCENARIOS, level="beginner", skill="Clarity", recent_ids={"a" * 24}, today=date(2026, 10, 7))
    assert other["slug"] == "beta"


def test_plan_is_deterministic():
    kw = dict(pers=_pers(), goal_minutes=20, difficulty_pref="adaptive", scenarios=SCENARIOS,
              recent_scenario_ids=set(), today=date(2026, 10, 7))
    assert planner.build_plan(**kw) == planner.build_plan(**kw)


# ================================================================== service: generation / persistence
def test_new_user_gets_a_plan_with_no_fabricated_progress(client, fake_db):
    headers = _auth(client)
    data = client.get(URL, headers=headers).json()["data"]
    assert data["enabled"] and data["plan"]["status"] == "pending"
    assert data["goal"]["minutes_done"] == 0 and data["goal"]["tasks_done"] == 0
    assert data["streak"]["current_streak"] == 0
    assert all(t["status"] == "pending" and t["score"] is None for t in data["plan"]["tasks"])


def test_plan_is_stable_across_refreshes_and_not_duplicated(client, fake_db):
    headers = _auth(client)
    first = client.get(URL, headers=headers).json()["data"]["plan"]
    for _ in range(5):
        again = client.get(URL, headers=headers).json()["data"]["plan"]
        assert again["tasks"] == first["tasks"] and again["focus"] == first["focus"]
    assert fake_db[Collections.DAILY_PRACTICE].count_documents({}) == 1


def test_plan_uses_real_weakness(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db)
    _weak_practice(fake_db, user["_id"], "Web Security", [40, 45, 42, 50], datetime.now(timezone.utc))
    plan = client.get(URL, headers=headers).json()["data"]["plan"]
    assert plan["tasks"][0]["config"]["category"] == "Web Security"
    assert plan["focus"]["basis"] == "performance"
    assert any("average 44/100" in line for line in plan["tasks"][0]["why"])  # real evidence, not invented


def test_disabled_daily_practice_returns_no_plan(client, fake_db):
    headers = _auth(client)
    _prefs(fake_db, daily_practice_enabled=False)
    data = client.get(URL, headers=headers).json()["data"]
    assert data["enabled"] is False and data["plan"] is None
    assert fake_db[Collections.DAILY_PRACTICE].count_documents({}) == 0


def test_rest_day_creates_no_plan(client, fake_db):
    _auth(client)
    user = _prefs(fake_db, practice_days=["mon", "tue"])  # NOW is a Wednesday
    state = svc.get_today(fake_db, user=user, now=NOW)
    assert state["rest_day"] is True and state["plan"] is None


def test_settings_change_rebuilds_an_untouched_plan_only(client, fake_db):
    headers = _auth(client)
    first = client.get(URL, headers=headers).json()["data"]["plan"]
    assert first["goal_minutes"] == 15
    client.patch("/api/v1/users/me/preferences", json={"daily_practice_minutes": 5}, headers=headers)
    second = client.get(URL, headers=headers).json()["data"]["plan"]
    assert second["goal_minutes"] == 5 and [t["kind"] for t in second["tasks"]] == ["cybersecurity"]
    assert fake_db[Collections.DAILY_PRACTICE].count_documents({}) == 1


def test_started_plan_is_not_replaced_by_settings_change_or_regenerate(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db)
    state = svc.get_today(fake_db, user=user, now=datetime.now(timezone.utc))
    sid = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(user["_id"], status="in_progress"), "started_at": _naive(datetime.now(timezone.utc))}).inserted_id
    r = client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=headers)
    assert r.status_code == 200 and r.json()["data"]["plan"]["status"] == "in_progress"
    client.patch("/api/v1/users/me/preferences", json={"daily_practice_minutes": 60}, headers=headers)
    after = client.get(URL, headers=headers).json()["data"]["plan"]
    assert after["tasks"][0]["session_id"] == str(sid) and after["goal_minutes"] == 15
    assert client.post(f"{URL}/regenerate", headers=headers).status_code == 409


def test_regenerate_untouched_plan_ok(client, fake_db):
    headers = _auth(client)
    client.get(URL, headers=headers)
    r = client.post(f"{URL}/regenerate", headers=headers)
    assert r.status_code == 200 and fake_db[Collections.DAILY_PRACTICE].count_documents({}) == 1


def test_start_is_idempotent_and_is_not_completion(client, fake_db):
    headers = _auth(client)
    a = client.post(f"{URL}/start", headers=headers).json()["data"]["plan"]
    b = client.post(f"{URL}/start", headers=headers).json()["data"]["plan"]
    assert a["status"] == b["status"] == "in_progress" and a["started_at"] == b["started_at"]
    assert client.get(f"{URL}/streak", headers=headers).json()["data"]["current_streak"] == 0


# ================================================================== linking + completion
def test_link_rejects_foreign_wrong_kind_stale_and_malformed_sessions(client, fake_db):
    headers = _auth(client)
    _auth(client, "other@example.com")
    me, other = _user(fake_db), _user(fake_db, "other@example.com")
    client.get(URL, headers=headers)
    now = datetime.now(timezone.utc)
    foreign = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(other["_id"]), "started_at": _naive(now)}).inserted_id
    stale = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(me["_id"]), "started_at": _naive(now - timedelta(days=2))}).inserted_id
    comm = fake_db[Collections.COMMUNICATION_SESSIONS].insert_one(
        {**_communication(me["_id"], started=_naive(now))}).inserted_id
    for sid in (foreign, stale, comm, ObjectId()):  # comm id is the wrong *kind* for the cybersecurity task
        r = client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=headers)
        assert r.status_code == 422 and r.json()["error_code"] == "SESSION_NOT_ELIGIBLE"
    assert client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": "nope"}, headers=headers).status_code == 422
    assert client.post(f"{URL}/tasks/bogus/link", json={"session_id": str(stale)}, headers=headers).status_code == 422


def test_completing_the_plan_updates_goal_summary_streak_and_notifies(client, fake_db):
    headers = _auth(client)
    _prefs(fake_db, daily_practice_minutes=5)  # cybersecurity-only plan
    user = _user(fake_db)
    now = datetime.now(timezone.utc)
    client.get(URL, headers=headers)
    started = now - timedelta(minutes=14)
    sid = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(user["_id"], status="in_progress"), "started_at": _naive(started)}).inserted_id
    client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=headers)

    # Still running: nothing is completed, nothing is invented.
    mid = client.get(URL, headers=headers).json()["data"]
    assert mid["plan"]["tasks"][0]["status"] == "in_progress" and mid["streak"]["current_streak"] == 0

    fake_db[Collections.PRACTICE_SESSIONS].update_one(
        {"_id": sid}, {"$set": {"status": "completed", "score": 82, "completed_at": _naive(now)}})
    data = client.get(URL, headers=headers).json()["data"]
    plan = data["plan"]
    assert plan["status"] == "completed" and plan["completion"] == "full"
    assert data["goal"]["tasks_done"] == 1 and data["goal"]["minutes_done"] == 14
    assert plan["summary"]["technical_score"] == 82 and plan["summary"]["communication_score"] is None
    assert plan["summary"]["minutes_practiced"] == 14 and plan["summary"]["streak"] == 1
    assert data["streak"]["current_streak"] == 1 and data["streak"]["practiced_today"]
    notes = client.get("/api/v1/notifications", headers=headers).json()["data"]["items"]
    assert [n["type"] for n in notes] == ["progress"]
    # Reading again must not re-finalize or duplicate the notification.
    client.get(URL, headers=headers)
    assert fake_db[Collections.NOTIFICATIONS].count_documents({}) == 1


def test_manual_complete_needs_a_completed_task_and_is_partial(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db)
    now = datetime.now(timezone.utc)
    client.get(URL, headers=headers)
    assert client.post(f"{URL}/complete", headers=headers).status_code == 409
    sid = _done_practice(fake_db, user["_id"], now)
    fake_db[Collections.PRACTICE_SESSIONS].update_one({"_id": sid}, {"$set": {"started_at": _naive(now - timedelta(minutes=8))}})
    client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=headers)
    data = client.post(f"{URL}/complete", headers=headers).json()["data"]
    assert data["plan"]["status"] == "completed" and data["plan"]["completion"] == "partial"
    assert data["plan"]["summary"]["technical_score"] == 80
    again = client.post(f"{URL}/complete", headers=headers)
    assert again.status_code == 200


def test_deleted_linked_session_reopens_the_task(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db)
    client.get(URL, headers=headers)
    sid = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(user["_id"], status="in_progress"), "started_at": _naive(datetime.now(timezone.utc))}).inserted_id
    client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=headers)
    fake_db[Collections.PRACTICE_SESSIONS].delete_one({"_id": sid})
    task = client.get(URL, headers=headers).json()["data"]["plan"]["tasks"][0]
    assert task["status"] == "pending" and task["session_id"] is None


# ================================================================== ownership / auth
def test_daily_practice_requires_authentication(client):
    for method, path in (("get", URL), ("post", f"{URL}/start"), ("post", f"{URL}/complete"),
                         ("post", f"{URL}/regenerate"), ("get", f"{URL}/streak")):
        assert getattr(client, method)(path).status_code == 401


def test_users_only_see_their_own_plan_and_streak(client, fake_db):
    a = _auth(client, "a@example.com")
    b = _auth(client, "b@example.com")
    ua = _user(fake_db, "a@example.com")
    _done_practice(fake_db, ua["_id"], datetime.now(timezone.utc))
    assert client.get(f"{URL}/streak", headers=a).json()["data"]["current_streak"] == 1
    assert client.get(f"{URL}/streak", headers=b).json()["data"]["current_streak"] == 0
    client.get(URL, headers=a); client.get(URL, headers=b)
    assert fake_db[Collections.DAILY_PRACTICE].count_documents({}) == 2
    # a user id supplied by the client is simply not an input
    assert client.get(f"{URL}?user_id={ua['_id']}", headers=b).json()["data"]["streak"]["current_streak"] == 0


# ================================================================== preferences validation
@pytest.mark.parametrize("payload", [
    {"daily_practice_minutes": 1}, {"daily_practice_minutes": 500}, {"preferred_practice_time": "25:99"},
    {"preferred_timezone": "Mars/Base"}, {"practice_days": ["funday"]}, {"practice_days": []},
])
def test_invalid_practice_preferences_are_rejected(client, payload):
    headers = _auth(client)
    assert client.patch("/api/v1/users/me/preferences", json=payload, headers=headers).status_code == 422


@requires_tzdata
def test_valid_practice_preferences_round_trip(client):
    headers = _auth(client)
    body = {"daily_practice_minutes": 20, "preferred_practice_time": "07:30", "preferred_timezone": "Asia/Kolkata",
            "practice_days": ["mon", "wed", "mon"], "reminders_enabled": False, "browser_notifications_enabled": True}
    r = client.patch("/api/v1/users/me/preferences", json=body, headers=headers)
    assert r.status_code == 200
    prefs = client.get("/api/v1/users/me/preferences", headers=headers).json()["data"]["preferences"]
    assert prefs["daily_practice_minutes"] == 20 and prefs["preferred_timezone"] == "Asia/Kolkata"
    assert prefs["practice_days"] == ["mon", "wed"] and prefs["reminders_enabled"] is False


# ================================================================== end-to-end personalization / ownership
def test_plan_adapts_when_a_new_weakness_appears(client, fake_db):
    headers = _auth(client)
    user = _user(fake_db)
    now = datetime.now(timezone.utc)
    _weak_practice(fake_db, user["_id"], "Web Security", [40, 45, 42, 50], now)
    first = client.get(URL, headers=headers).json()["data"]["plan"]
    assert first["tasks"][0]["config"]["category"] == "Web Security"
    # Another, worse area accumulates; the untouched plan can be refreshed on request.
    _weak_practice(fake_db, user["_id"], "Cryptography", [20, 25, 22, 30, 28], now + timedelta(seconds=1))
    clear_cache()
    again = client.post(f"{URL}/regenerate", headers=headers).json()["data"]["plan"]
    assert again["tasks"][0]["config"]["category"] == "Cryptography"


def test_preferences_and_plans_are_per_user(client, fake_db):
    a, b = _auth(client, "a@example.com"), _auth(client, "b@example.com")
    client.patch("/api/v1/users/me/preferences", json={"daily_practice_minutes": 60, "reminders_enabled": False}, headers=a)
    pb = client.get("/api/v1/users/me/preferences", headers=b).json()["data"]["preferences"]
    assert pb["daily_practice_minutes"] == 15 and pb["reminders_enabled"] is True
    assert client.get(URL, headers=a).json()["data"]["plan"]["goal_minutes"] == 60
    assert client.get(URL, headers=b).json()["data"]["plan"]["goal_minutes"] == 15
    # a user cannot link someone else's session id into their own plan
    ua = _user(fake_db, "a@example.com")
    sid = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {**_history_practice(ua["_id"], status="in_progress"), "started_at": _naive(datetime.now(timezone.utc))}).inserted_id
    r = client.post(f"{URL}/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=b)
    assert r.status_code == 422
