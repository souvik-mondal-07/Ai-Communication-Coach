"""
Daily practice orchestration (Step 19).

One ``daily_practice`` document per (user, local date) -- enforced by a unique index --
holds *today's plan*. It is generated once (deterministically, see ``planner``) and
then only read, so a browser refresh never changes it. It is rebuilt only when:

* the user explicitly asks for a new one (``regenerate``) and nothing has been started;
* the user changes the practice settings (duration/difficulty) and nothing has been started;
* a linked session no longer exists (the task simply becomes pending again).

The plan does not run a practice engine. Each task is started through the existing
module (Step 17 practice, communication, interview) and then *linked* to the plan
(``link_session``). Task and plan completion, minutes practiced and the summary are
all read from the real finished sessions; nothing here records a score of its own.
Progress, analytics and personalization are likewise derived from those sessions, so
they are up to date as soon as the session completes.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.collections import Collections
from app.models.user import UserDocument
from app.schemas.notification import NotificationPriority, NotificationType
from app.services.auth.profile_service import to_profile_response
from app.services.daily_practice import planner, timeutil
from app.services.daily_practice.streak import StreakService, qualifies, streak_service
from app.services.history.history_service import HistoryService, history_service
from app.services.notifications.notification_service import NotificationService, notification_service
from app.services.personalization.personalization_service import (
    PersonalizationService,
    invalidate_user,
    personalization_service,
)

_KIND_COLLECTION = {
    planner.CYBERSECURITY: Collections.PRACTICE_SESSIONS,
    planner.COMMUNICATION: Collections.COMMUNICATION_SESSIONS,
    planner.INTERVIEW: Collections.INTERVIEW_SESSIONS,
}
_KIND_ACTIVITY = {
    planner.CYBERSECURITY: "cybersecurity_practice",
    planner.COMMUNICATION: "communication",
    planner.INTERVIEW: "interview",
}
MILESTONES = (3, 7, 14, 30, 60, 100, 200, 365)


class PlanNotFoundError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class SessionNotEligibleError(Exception):
    """The session is not the user's, is the wrong kind, or was not started today."""


class PlanLockedError(Exception):
    """The plan has progress (or is finished) so it cannot be replaced."""


class NothingCompletedError(Exception):
    """Finishing early needs at least one completed task."""


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise SessionNotEligibleError(value) from exc


class DailyPracticeService:
    def __init__(
        self,
        *,
        history: HistoryService = history_service,
        streaks: StreakService = streak_service,
        personalization: PersonalizationService = personalization_service,
        notifications: NotificationService = notification_service,
    ) -> None:
        self._history = history
        self._streaks = streaks
        self._personalization = personalization
        self._notifications = notifications

    def ensure_indexes(self, db: Database) -> None:
        db[Collections.DAILY_PRACTICE].create_index([("user_id", 1), ("date", 1)], unique=True)

    # ------------------------------------------------------------------ settings
    @staticmethod
    def _settings(user: UserDocument):
        return to_profile_response(user)

    @staticmethod
    def _weekdays(prefs) -> frozenset[int]:
        return frozenset(timeutil.WEEKDAYS.index(d) for d in prefs.practice_days) or frozenset(range(7))

    # ------------------------------------------------------------------ public API
    def get_streak(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        prefs = self._settings(user).preferences
        return self._streaks.get_streak(
            db, user_id=str(user["_id"]), tz_name=prefs.preferred_timezone,
            practice_weekdays=self._weekdays(prefs), now=now,
        )

    def get_today(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        settings = self._settings(user)
        prefs = settings.preferences
        tz = timeutil.resolve_tz(prefs.preferred_timezone)
        today = timeutil.local_date(now, tz)
        user_id = str(user["_id"])
        streak = self._streaks.get_streak(
            db, user_id=user_id, tz_name=prefs.preferred_timezone,
            practice_weekdays=self._weekdays(prefs), now=now,
        )
        rest_day = timeutil.weekday_name(today) not in prefs.practice_days
        base = {"enabled": prefs.daily_practice_enabled, "rest_day": rest_day, "date": today.isoformat(),
                "timezone": timeutil.tz_key(tz), "plan": None, "goal": None, "streak": streak}
        if not prefs.daily_practice_enabled:
            return base

        doc = db[Collections.DAILY_PRACTICE].find_one({"user_id": user["_id"], "date": today.isoformat()})
        if doc is None and rest_day:
            return base
        if doc is None:
            doc = self._create(db, user=user, today=today, tz=tz, now=now, prefs=prefs, settings=settings)
        elif self._is_untouched(doc) and doc.get("settings_fingerprint") != self._fingerprint(prefs):
            doc = self._rebuild(db, user=user, doc=doc, today=today, now=now, prefs=prefs, settings=settings)

        plan, goal = self._reconcile(db, doc=doc, user_id=user_id, tz=tz, today=today, now=now,
                                     streak_days=streak["current_streak"], user=user)
        base.update(plan=plan, goal=goal)
        return base

    def start(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        """Mark today's plan as started (idempotent). Starting is not completing."""
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        state = self.get_today(db, user=user, now=now)
        if state["plan"] is None:
            raise PlanNotFoundError("There is no daily practice for today.")
        db[Collections.DAILY_PRACTICE].update_one(
            {"user_id": user["_id"], "date": state["date"], "status": "pending"},
            {"$set": {"status": "in_progress", "started_at": now.replace(tzinfo=None), "updated_at": now.replace(tzinfo=None)}},
        )
        return self.get_today(db, user=user, now=now)

    def link_session(self, db: Database, *, user: UserDocument, task_id: str, session_id: str,
                     now: datetime | None = None) -> dict:
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        state = self.get_today(db, user=user, now=now)
        plan = state["plan"]
        if plan is None:
            raise PlanNotFoundError("There is no daily practice for today.")
        task = next((t for t in plan["tasks"] if t["task_id"] == task_id), None)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task["session_id"] == session_id:
            return state  # idempotent
        if task["status"] == "completed":
            raise SessionNotEligibleError("This task is already completed.")

        tz = timeutil.resolve_tz(state["timezone"])
        start, end = timeutil.day_bounds_utc(date.fromisoformat(state["date"]), tz)
        session = db[_KIND_COLLECTION[task["kind"]]].find_one(
            {"_id": _oid(session_id), "user_id": user["_id"]}, {"started_at": 1, "status": 1}
        )
        if session is None:
            raise SessionNotEligibleError("Session not found.")
        started = session.get("started_at") or session.get("created_at")
        if started is None or not (start <= timeutil.as_utc(started) < end):
            raise SessionNotEligibleError("Only a session started today can count toward today's practice.")

        # Replacing an unfinished link is allowed (e.g. the user started a fresh session).
        stored = db[Collections.DAILY_PRACTICE].find_one({"user_id": user["_id"], "date": state["date"]})
        tasks = [{**t, "session_id": session_id} if t["task_id"] == task_id else t for t in stored["tasks"]]
        update = {"tasks": tasks, "updated_at": now.replace(tzinfo=None)}
        if stored["status"] == "pending":
            update.update(status="in_progress", started_at=now.replace(tzinfo=None))
        db[Collections.DAILY_PRACTICE].update_one({"_id": stored["_id"], "user_id": user["_id"]}, {"$set": update})
        return self.get_today(db, user=user, now=now)

    def regenerate(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        state = self.get_today(db, user=user, now=now)
        if state["plan"] is None:
            raise PlanNotFoundError("There is no daily practice for today.")
        doc = db[Collections.DAILY_PRACTICE].find_one({"user_id": user["_id"], "date": state["date"]})
        if doc["status"] != "pending" or not self._is_untouched(doc):
            raise PlanLockedError("Today's practice has already been started, so it can't be replaced.")
        settings = self._settings(user)
        tz = timeutil.resolve_tz(state["timezone"])
        # Same inputs would give the same plan, so a new one only differs if something changed.
        self._personalization_invalidate(user)
        self._rebuild(db, user=user, doc=doc, today=date.fromisoformat(state["date"]), now=now,
                      prefs=settings.preferences, settings=settings, rotate=int(doc.get("regenerated", 0)) + 1)
        return self.get_today(db, user=user, now=now)

    def complete(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        """Finish for today with whatever is done (needs >= 1 completed task). Idempotent."""
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        state = self.get_today(db, user=user, now=now)
        plan = state["plan"]
        if plan is None:
            raise PlanNotFoundError("There is no daily practice for today.")
        if plan["status"] == "completed":
            return state
        if not any(t["status"] == "completed" for t in plan["tasks"]):
            raise NothingCompletedError("Complete at least one task before finishing today's practice.")
        doc = db[Collections.DAILY_PRACTICE].find_one({"user_id": user["_id"], "date": state["date"]})
        self._finalize(db, doc=doc, user=user, plan=plan, goal=state["goal"], now=now, partial=True,
                       streak_days=state["streak"]["current_streak"])
        return self.get_today(db, user=user, now=now)

    # ------------------------------------------------------------------ generation
    @staticmethod
    def _fingerprint(prefs) -> str:
        return planner.settings_fingerprint(goal_minutes=prefs.daily_practice_minutes, difficulty_pref=prefs.difficulty)

    @staticmethod
    def _is_untouched(doc: dict) -> bool:
        return not any(t.get("session_id") for t in doc.get("tasks", []))

    def _personalization_invalidate(self, user: UserDocument) -> None:
        invalidate_user(str(user["_id"]))

    def _build(self, db: Database, *, user: UserDocument, settings, prefs, today: date, rotate: int = 0) -> dict:
        pers = self._personalization.compute(db, user=user)
        pers = {**pers, "learning_goals": [g.value if hasattr(g, "value") else g for g in settings.profile.learning_goals]}
        scenarios = [
            {"scenario_id": str(s["_id"]), "slug": s["slug"], "title": s["title"], "difficulty": s["difficulty"],
             "objective": s["objective"], "skills_targeted": s.get("skills_targeted", [])}
            for s in db[Collections.COMMUNICATION_SCENARIOS].find(
                {}, {"slug": 1, "title": 1, "difficulty": 1, "objective": 1, "skills_targeted": 1})
        ]
        recent = {
            str(s["scenario_id"]) for s in db[Collections.COMMUNICATION_SESSIONS]
            .find({"user_id": user["_id"]}, {"scenario_id": 1}).sort("started_at", DESCENDING).limit(10)
        }
        return planner.build_plan(
            pers=pers, goal_minutes=prefs.daily_practice_minutes, difficulty_pref=prefs.difficulty,
            scenarios=scenarios, recent_scenario_ids=recent, today=today + timedelta(days=rotate),
        )

    def _create(self, db: Database, *, user, today: date, tz, now: datetime, prefs, settings) -> dict:
        built = self._build(db, user=user, settings=settings, prefs=prefs, today=today)
        naive = now.replace(tzinfo=None)
        doc = {
            "user_id": user["_id"], "date": today.isoformat(), "timezone": timeutil.tz_key(tz), "status": "pending",
            "goal_minutes": prefs.daily_practice_minutes, "difficulty": built["difficulty"],
            "focus": built["focus"], "rationale": built["rationale"],
            "tasks": [{**t, "session_id": None} for t in built["tasks"]],
            "settings_fingerprint": self._fingerprint(prefs), "regenerated": 0,
            "generated_at": naive, "updated_at": naive, "started_at": None, "completed_at": None,
            "completion": None, "summary": None,
        }
        try:
            doc["_id"] = db[Collections.DAILY_PRACTICE].insert_one(doc).inserted_id
        except DuplicateKeyError:  # a concurrent request created it first: use that one
            doc = db[Collections.DAILY_PRACTICE].find_one({"user_id": user["_id"], "date": today.isoformat()})
        return doc

    def _rebuild(self, db: Database, *, user, doc: dict, today: date, now: datetime, prefs, settings, rotate: int = 0) -> dict:
        built = self._build(db, user=user, settings=settings, prefs=prefs, today=today, rotate=rotate)
        update = {
            "goal_minutes": prefs.daily_practice_minutes, "difficulty": built["difficulty"], "focus": built["focus"],
            "rationale": built["rationale"], "tasks": [{**t, "session_id": None} for t in built["tasks"]],
            "settings_fingerprint": self._fingerprint(prefs), "updated_at": now.replace(tzinfo=None),
            "regenerated": int(doc.get("regenerated", 0)) + (1 if rotate else 0),
        }
        db[Collections.DAILY_PRACTICE].update_one({"_id": doc["_id"], "user_id": user["_id"]}, {"$set": update})
        return {**doc, **update}

    # ------------------------------------------------------------------ reconcile / read
    def _reconcile(self, db: Database, *, doc: dict, user_id: str, tz, today: date, now: datetime,
                   streak_days: int, user: UserDocument) -> tuple[dict, dict]:
        start, end = timeutil.day_bounds_utc(today, tz)
        done_today = self._history.list_completed(db, user_id=user_id, since=start, until=min(end, now + timedelta(seconds=1)))
        by_id = {a.id: a for a in done_today if qualifies(a)}
        minutes_done = sum(round((a.duration_seconds or 0) / 60) for a in by_id.values())

        tasks, dirty = [], False
        for t in doc["tasks"]:
            sid = t.get("session_id")
            status, score, minutes = "pending", None, None
            if sid:
                activity = by_id.get(sid)
                if activity is not None:
                    status, score = "completed", activity.score
                    minutes = round((activity.duration_seconds or 0) / 60)
                else:
                    exists = db[_KIND_COLLECTION[t["kind"]]].find_one({"_id": ObjectId(sid), "user_id": ObjectId(user_id)}, {"status": 1})
                    if exists is None:          # the session was removed: the task is open again
                        t = {**t, "session_id": None}
                        dirty = True
                    elif exists.get("status") == "in_progress" or exists.get("status") in ("created", "active"):
                        status = "in_progress"
                    else:                        # finished without a scored result (e.g. nothing answered)
                        status = "in_progress"
            tasks.append({**t, "status": status, "score": score, "minutes": minutes})
        if dirty:
            db[Collections.DAILY_PRACTICE].update_one(
                {"_id": doc["_id"], "user_id": ObjectId(user_id)},
                {"$set": {"tasks": [{k: v for k, v in x.items() if k not in ("status", "score", "minutes")} for x in tasks]}},
            )

        completed_n = sum(1 for t in tasks if t["status"] == "completed")
        plan = self._plan_out(doc, tasks)
        goal = {"goal_minutes": doc["goal_minutes"], "minutes_done": minutes_done,
                "tasks_total": len(tasks), "tasks_done": completed_n}
        if doc["status"] != "completed":
            if completed_n == len(tasks) and tasks:
                self._finalize(db, doc=doc, user=user, plan=plan, goal=goal, now=now, partial=False, streak_days=streak_days)
                refreshed = db[Collections.DAILY_PRACTICE].find_one({"_id": doc["_id"]})
                plan = self._plan_out(refreshed, tasks)
            elif any(t["status"] != "pending" for t in tasks) and doc["status"] == "pending":
                db[Collections.DAILY_PRACTICE].update_one(
                    {"_id": doc["_id"], "status": "pending"},
                    {"$set": {"status": "in_progress", "started_at": now.replace(tzinfo=None)}})
                plan["status"] = "in_progress"
        return plan, goal

    @staticmethod
    def _plan_out(doc: dict, tasks: list[dict]) -> dict:
        def aware(v):
            return timeutil.as_utc(v) if v else None
        return {
            "date": doc["date"], "status": doc["status"], "goal_minutes": doc["goal_minutes"],
            "difficulty": doc["difficulty"], "focus": doc["focus"], "rationale": doc["rationale"],
            "tasks": [{k: t.get(k) for k in ("task_id", "kind", "title", "description", "why", "est_minutes",
                                             "route", "config", "status", "session_id", "score", "minutes")} for t in tasks],
            "started_at": aware(doc.get("started_at")), "completed_at": aware(doc.get("completed_at")),
            "completion": doc.get("completion"), "summary": doc.get("summary"),
        }

    # ------------------------------------------------------------------ completion
    def _finalize(self, db: Database, *, doc: dict, user: UserDocument, plan: dict, goal: dict, now: datetime,
                  partial: bool, streak_days: int) -> None:
        user_id = str(user["_id"])
        invalidate_user(user_id)  # mentor/recommendation context must see the finished session
        done = [t for t in plan["tasks"] if t["status"] == "completed"]
        tech = [t["score"] for t in done if t["kind"] in (planner.CYBERSECURITY, planner.INTERVIEW) and t["score"] is not None]
        comm = [t["score"] for t in done if t["kind"] == planner.COMMUNICATION and t["score"] is not None]
        try:
            recs = self._personalization.get_recommendations(db, user=user).get("recommendations") or []
        except Exception:  # a recommendation hiccup must never block completion
            recs = []
        nxt = recs[0]["title"] if recs else None
        topics = []
        for t in done:
            topic = t["config"].get("category") or t["config"].get("interview_type") or t["title"]
            topics.append(str(topic).replace("_", " "))
        summary = {
            "technical_score": round(sum(tech) / len(tech)) if tech else None,
            "communication_score": round(sum(comm) / len(comm)) if comm else None,
            "topics": list(dict.fromkeys(topics)),
            "minutes_practiced": goal["minutes_done"],
            "streak": streak_days,
            "results": [{"task_id": t["task_id"], "title": t["title"], "score": t["score"], "minutes": t["minutes"]} for t in done],
            "recommended_next": nxt,
        }
        completed_at = now.replace(tzinfo=None)
        res = db[Collections.DAILY_PRACTICE].update_one(
            {"_id": doc["_id"], "user_id": user["_id"], "status": {"$ne": "completed"}},
            {"$set": {"status": "completed", "completed_at": completed_at, "completion": "partial" if partial else "full",
                      "summary": summary, "updated_at": completed_at}},
        )
        if res.modified_count and user.get("preferences", {}).get("reminders_enabled", True):
            title = "Today's practice complete" if not partial else "Practice session saved"
            msg = f"{goal['minutes_done']} min practiced · {streak_days}-day streak." + (f" Next: {nxt}" if nxt else "")
            self._notifications.create_if_absent(
                db, user_id=user_id, type=NotificationType.PROGRESS, priority=NotificationPriority.LOW,
                title=title, message=msg, action_target="/progress", dedupe_key=f"progress:daily:{doc['date']}",
                expires_at=now + timedelta(days=30), now=now,
            )


daily_practice_service = DailyPracticeService()
