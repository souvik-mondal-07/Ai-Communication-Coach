"""
Conversation engine for voice sessions (Step 13).

The engine is deliberately *text in, text out*. It knows nothing about audio,
HTTP, or MongoDB session bookkeeping — `ConversationService` handles those.
That keeps the turn logic reusable if a streaming STT/TTS layer is added
later: only the layer around the engine would change.

A `ModeDriver` runs one kind of conversation:

    FreeformDriver       general / cybersecurity / practice
                         -> existing AIService (Gemini) + voice prompts

    InterviewDriver      interview
                         -> existing Step 9 InterviewService (questions,
                            evaluation, follow-ups, final evaluation)

    PressureDriver       pressure
                         -> existing Step 10 PressureService (pressure engine,
                            interruptions, topic switches, timing)

    CommunicationDriver  communication
                         -> existing Step 7 CommunicationService roleplay and
                            EvaluationService (which also uses Step 8 analysis)

The structured modes wrap a real Step 9/10/7 session (its id is stored on the
voice session), so their evaluations, history and progress aggregation are the
existing ones — nothing is scored or stored twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pymongo.database import Database

from app.core.config import settings
from app.services.ai.ai_service import AIService, AIServiceError, ConversationTurn, ai_service
from app.services.communication.communication_service import (
    CommunicationService,
    ScenarioNotFoundError,
    SessionCompletedError,
    communication_service,
)
from app.services.communication.evaluation_service import (
    EvaluationError,
    EvaluationService,
    evaluation_service,
)
from app.services.interview import interview_service as interview_module
from app.services.interview.evaluation_service import InterviewEvaluationError
from app.services.interview.interview_service import InterviewService
from app.services.interview.question_service import QuestionGenerationError
from app.services.interview.structured_ai import StructuredOutputError
from app.services.pressure import pressure_service as pressure_module
from app.services.pressure.pressure_service import PressureService
from app.services.voice.text_to_speech import clean_text_for_speech
from app.services.voice_conversation.prompts import (
    END_TOKEN,
    FREEFORM_MODES,
    build_opening_instruction,
    build_voice_system_prompt,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Spoken replies are kept well under the TTS input limit (2,000 characters).
MAX_SPOKEN_CHARS = 1200
DEFAULT_QUESTION_COUNT = 5
DEFAULT_PRESSURE_LEVEL = 2

_AI_ERRORS = (AIServiceError, QuestionGenerationError, InterviewEvaluationError, StructuredOutputError)

_INTERVIEW_TYPE_LABELS = {
    "hr": "HR",
    "technical": "technical",
    "cybersecurity": "cybersecurity",
    "scenario_based": "scenario-based",
    "mixed": "mixed",
}

# Neutral acknowledgements. Interviewers do not grade you mid-interview, so
# these deliberately say nothing about how the answer went.
_ACKNOWLEDGEMENTS = ("Thank you.", "Okay, thanks.", "Understood.", "Got it.", "Alright.")


# --- Errors --------------------------------------------------------------------


class ConversationEngineError(Exception):
    """Base class for engine-level errors."""


class ConversationAIError(ConversationEngineError):
    """The AI layer failed or returned nothing usable (maps to a clean 503)."""


class ConversationStateError(ConversationEngineError):
    """The underlying session can no longer accept this action (maps to 409)."""


class ConversationConfigError(ConversationEngineError):
    """The requested configuration refers to something that doesn't exist."""


# --- Result types ----------------------------------------------------------------


@dataclass(frozen=True)
class DriverStart:
    text: str
    linked: dict | None = None
    info: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TurnResult:
    text: str
    complete: bool = False
    info: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FinishResult:
    evaluation: dict | None = None
    # True when there was nothing to evaluate (the learner never answered).
    nothing_to_evaluate: bool = False


# --- Text helpers ------------------------------------------------------------------


def to_spoken_text(text: str) -> str:
    """
    Make model output safe to display *and* speak: drop the end token, strip
    markdown/code, collapse whitespace and cap the length at a sentence edge.
    """
    cleaned = clean_text_for_speech((text or "").replace(END_TOKEN, " "))
    if len(cleaned) <= MAX_SPOKEN_CHARS:
        return cleaned
    window = cleaned[:MAX_SPOKEN_CHARS]
    sentence_end = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
    if sentence_end >= MAX_SPOKEN_CHARS // 2:
        return window[: sentence_end + 1].strip()
    return window.rsplit(" ", 1)[0].strip() + "…"


def build_history(messages: list[dict], max_turns: int) -> list[ConversationTurn]:
    """
    The last `max_turns` exchanges as model history (older turns stay in
    MongoDB only). Gemini expects a conversation to start with the user, so
    when the window opens on the AI's own greeting a short placeholder user
    turn is placed in front of it.
    """
    window = messages[-(max(1, max_turns) * 2):]
    turns = [ConversationTurn(role=m["role"], content=m["text"]) for m in window if m.get("text")]
    if turns and turns[0].role == "assistant":
        turns.insert(0, ConversationTurn(role="user", content="(The conversation has just begun.)"))
    return turns


def _acknowledgement(turn_number: int) -> str:
    return _ACKNOWLEDGEMENTS[turn_number % len(_ACKNOWLEDGEMENTS)]


def _join(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


# --- Drivers -------------------------------------------------------------------------


class ModeDriver(Protocol):
    async def start(self, db: Database, *, session: dict, user_id: str, profile_context: dict | None) -> DriverStart: ...

    async def respond(
        self,
        db: Database,
        *,
        session: dict,
        user_id: str,
        transcript: str,
        audio_meta: dict | None,
        response_seconds: float | None,
    ) -> TurnResult: ...

    async def finish(self, db: Database, *, session: dict, user_id: str) -> FinishResult: ...


class FreeformDriver:
    """general / cybersecurity / practice — Gemini via the existing AIService."""

    def __init__(self, ai: AIService) -> None:
        self._ai = ai

    def _system_prompt(self, session: dict, profile_context: dict | None) -> str:
        return build_voice_system_prompt(
            mode=session["mode"],
            difficulty=session["difficulty"],
            topic=session.get("topic"),
            profile_context=profile_context,
        )

    async def _generate(self, **kwargs) -> str:
        try:
            result = await self._ai.generate_response(**kwargs)
        except AIServiceError as exc:
            raise ConversationAIError("The AI mentor is unavailable.") from exc
        return result.text or ""

    async def start(self, db, *, session, user_id, profile_context) -> DriverStart:
        raw = await self._generate(
            user_message=build_opening_instruction(session["mode"], session.get("topic")),
            system_prompt=self._system_prompt(session, profile_context),
        )
        text = to_spoken_text(raw)
        if not text:
            raise ConversationAIError("The AI mentor returned an empty reply.")
        return DriverStart(text=text)

    async def respond(self, db, *, session, user_id, transcript, audio_meta, response_seconds) -> TurnResult:
        raw = await self._generate(
            user_message=transcript,
            history=build_history(session.get("messages", []), settings.voice_conversation_max_turns),
            system_prompt=self._system_prompt(session, session.get("profile_context")),
        )
        text = to_spoken_text(raw)
        if not text:
            raise ConversationAIError("The AI mentor returned an empty reply.")
        return TurnResult(text=text, complete=END_TOKEN in raw)

    async def finish(self, db, *, session, user_id) -> FinishResult:
        # Nothing structured to evaluate: the summary reports only measured speaking metrics.
        return FinishResult(evaluation=None, nothing_to_evaluate=session.get("user_turn_count", 0) == 0)


class InterviewDriver:
    """interview — wraps a Step 9 interview session."""

    def __init__(self, interviews: InterviewService) -> None:
        self._interviews = interviews

    async def start(self, db, *, session, user_id, profile_context) -> DriverStart:
        config = session["config"]
        try:
            result = await self._interviews.start_session(
                db,
                user_id=user_id,
                interview_type=config["interview_type"],
                difficulty=session["difficulty"],
                question_count=config["question_count"],
                mode="voice",
                reveal_feedback=False,
            )
        except _AI_ERRORS as exc:
            raise ConversationAIError("The interviewer is unavailable.") from exc

        label = _INTERVIEW_TYPE_LABELS.get(config["interview_type"], config["interview_type"])
        intro = (
            f"Welcome to your {label} interview. I'll ask you {config['question_count']} questions "
            "and I may follow up on some of your answers. Take your time and answer out loud. "
            "Here is the first question."
        )
        return DriverStart(
            text=to_spoken_text(_join(intro, result["question"])),
            linked={"kind": "interview", "session_id": result["session_id"], "label": f"{label.title()} interview"},
        )

    async def respond(self, db, *, session, user_id, transcript, audio_meta, response_seconds) -> TurnResult:
        try:
            result = await self._interviews.submit_answer(
                db,
                user_id=user_id,
                session_id=session["linked"]["session_id"],
                answer=transcript,
                input_type="voice",
                audio_metadata=audio_meta,
            )
        except _AI_ERRORS as exc:
            raise ConversationAIError("The interviewer is unavailable.") from exc
        except (interview_module.SessionNotActiveError, interview_module.AnswerConflictError) as exc:
            raise ConversationStateError("The interview can no longer accept answers.") from exc

        turn_number = session.get("user_turn_count", 0) + 1
        if result["interview_complete"]:
            summary = (result.get("final_evaluation") or {}).get("summary")
            closing = "That's the end of the interview. Thank you for your time."
            return TurnResult(
                text=to_spoken_text(_join(closing, summary if isinstance(summary, str) else None)),
                complete=True,
            )

        lead = "Let me follow up on that." if result["is_follow_up"] else _acknowledgement(turn_number)
        return TurnResult(text=to_spoken_text(_join(lead, result["next_question"])), info={"is_follow_up": result["is_follow_up"]})

    async def finish(self, db, *, session, user_id) -> FinishResult:
        linked = session.get("linked")
        if not linked:
            return FinishResult(nothing_to_evaluate=True)
        try:
            result = await self._interviews.complete_session(db, user_id=user_id, session_id=linked["session_id"])
        except _AI_ERRORS as exc:
            raise ConversationAIError("The interview could not be evaluated.") from exc
        return FinishResult(
            evaluation=result.get("final_evaluation"),
            nothing_to_evaluate=result.get("status") == "abandoned",
        )


class PressureDriver:
    """pressure — wraps a Step 10 pressure session; the Step 10 engine decides everything."""

    def __init__(self, pressure: PressureService) -> None:
        self._pressure = pressure

    async def start(self, db, *, session, user_id, profile_context) -> DriverStart:
        config = session["config"]
        try:
            result = await self._pressure.start_session(
                db,
                user_id=user_id,
                pressure_level=config["pressure_level"],
                mode="interview",
                interview_type=config["interview_type"],
                difficulty=session["difficulty"],
                question_count=config["question_count"],
                input_mode="voice",
            )
        except _AI_ERRORS as exc:
            raise ConversationAIError("The interviewer is unavailable.") from exc

        intro = (
            f"Pressure training, level {config['pressure_level']}. Answer as clearly and calmly as you "
            "can. Here is your first question."
        )
        return DriverStart(
            text=to_spoken_text(_join(intro, result["question"])),
            linked={
                "kind": "pressure",
                "session_id": result["session_id"],
                "label": f"Pressure level {config['pressure_level']}",
            },
            info={"time_limit_seconds": result.get("time_limit_seconds")},
        )

    async def respond(self, db, *, session, user_id, transcript, audio_meta, response_seconds) -> TurnResult:
        try:
            result = await self._pressure.submit_response(
                db,
                user_id=user_id,
                session_id=session["linked"]["session_id"],
                answer=transcript,
                input_type="voice",
                audio_metadata=audio_meta,
                response_duration_seconds=response_seconds,
            )
        except _AI_ERRORS as exc:
            raise ConversationAIError("The interviewer is unavailable.") from exc
        except (pressure_module.SessionNotActiveError, pressure_module.AnswerConflictError) as exc:
            raise ConversationStateError("The session can no longer accept answers.") from exc

        if result["session_complete"]:
            summary = (result.get("final_evaluation") or {}).get("summary")
            closing = "That's the end of the session. Well done for staying with it."
            return TurnResult(
                text=to_spoken_text(_join(closing, summary if isinstance(summary, str) else None)),
                complete=True,
            )

        # Pressure prompts (interruptions, rapid follow-ups) are meant to be abrupt: no softening lead-in.
        condition = result.get("next_condition") or {}
        return TurnResult(
            text=to_spoken_text(result["next_prompt"]),
            info={
                "prompt_kind": result.get("next_prompt_kind"),
                "time_limit_seconds": condition.get("time_limit_seconds"),
            },
        )

    async def finish(self, db, *, session, user_id) -> FinishResult:
        linked = session.get("linked")
        if not linked:
            return FinishResult(nothing_to_evaluate=True)
        try:
            result = await self._pressure.complete_session(db, user_id=user_id, session_id=linked["session_id"])
        except _AI_ERRORS as exc:
            raise ConversationAIError("The session could not be evaluated.") from exc
        return FinishResult(
            evaluation=result.get("final_evaluation"),
            nothing_to_evaluate=result.get("status") == "abandoned",
        )


class CommunicationDriver:
    """communication — wraps a Step 7 roleplay session; evaluation reuses Steps 7 + 8."""

    def __init__(self, communication: CommunicationService, evaluation: EvaluationService) -> None:
        self._communication = communication
        self._evaluation = evaluation

    def _pick_scenario(self, db: Database, session: dict) -> dict:
        config = session["config"]
        if config.get("scenario_slug"):
            scenario = self._communication.get_scenario_by_slug(db, config["scenario_slug"])
            if scenario is None:
                raise ConversationConfigError("Scenario not found.")
            return scenario
        scenarios = self._communication.list_scenarios(db)
        if not scenarios:
            raise ConversationStateError("No communication scenarios are available.")
        matching = [s for s in scenarios if s["difficulty"] == session["difficulty"]]
        return (matching or scenarios)[0]

    async def start(self, db, *, session, user_id, profile_context) -> DriverStart:
        scenario = self._pick_scenario(db, session)
        result = self._communication.start_session(
            db, user_id=user_id, scenario_id=scenario["scenario_id"], difficulty=session["difficulty"]
        )
        # The scenario's own opening line, spoken in character.
        opening = to_spoken_text(result["scenario"]["opening_message"])
        return DriverStart(
            text=opening,
            linked={"kind": "communication", "session_id": result["session_id"], "label": scenario["title"]},
            info={"scenario_title": scenario["title"], "objective": scenario["objective"]},
        )

    async def respond(self, db, *, session, user_id, transcript, audio_meta, response_seconds) -> TurnResult:
        try:
            result = await self._communication.send_message(
                db,
                user_id=user_id,
                session_id=session["linked"]["session_id"],
                message=transcript,
                input_type="voice",
                audio_metadata=audio_meta,
            )
        except AIServiceError as exc:
            raise ConversationAIError("The conversation partner is unavailable.") from exc
        except SessionCompletedError as exc:
            raise ConversationStateError("The conversation was already completed.") from exc
        text = to_spoken_text(result["reply"])
        if not text:
            raise ConversationAIError("The conversation partner returned an empty reply.")
        return TurnResult(text=text)

    async def finish(self, db, *, session, user_id) -> FinishResult:
        linked = session.get("linked")
        if not linked or session.get("user_turn_count", 0) == 0:
            return FinishResult(nothing_to_evaluate=True)
        comm_session = self._communication.get_owned_session_for_completion(
            db=db, session_id=linked["session_id"], user_id=user_id
        )
        if comm_session["status"] == "completed" and comm_session.get("evaluation"):
            return FinishResult(evaluation=comm_session["evaluation"])
        try:
            evaluation = await self._evaluation.evaluate_session(db, session=comm_session)
        except EvaluationError as exc:
            raise ConversationAIError("The conversation could not be evaluated.") from exc
        return FinishResult(evaluation=evaluation)


# --- Engine ------------------------------------------------------------------------------


class ConversationEngine:
    """Chooses the driver for a mode and normalises per-mode configuration."""

    def __init__(
        self,
        *,
        ai_service_: AIService = ai_service,
        interview_service_: InterviewService | None = None,
        pressure_service_: PressureService | None = None,
        communication_service_: CommunicationService = communication_service,
        evaluation_service_: EvaluationService = evaluation_service,
    ) -> None:
        self._communication = communication_service_
        self._drivers: dict[str, ModeDriver] = {}
        freeform = FreeformDriver(ai_service_)
        for mode in FREEFORM_MODES:
            self._drivers[mode] = freeform
        self._drivers["interview"] = InterviewDriver(interview_service_ or interview_module.interview_service)
        self._drivers["pressure"] = PressureDriver(pressure_service_ or pressure_module.pressure_service)
        self._drivers["communication"] = CommunicationDriver(communication_service_, evaluation_service_)

    def driver_for(self, mode: str) -> ModeDriver:
        return self._drivers[mode]

    @staticmethod
    def build_config(
        mode: str,
        *,
        interview_type: str | None = None,
        question_count: int | None = None,
        pressure_level: int | None = None,
        scenario_slug: str | None = None,
    ) -> dict:
        """The stored, fully-defaulted configuration for a mode."""
        if mode == "interview":
            return {
                "interview_type": interview_type or "cybersecurity",
                "question_count": question_count or DEFAULT_QUESTION_COUNT,
            }
        if mode == "pressure":
            return {
                "interview_type": interview_type or "mixed",
                "question_count": question_count or DEFAULT_QUESTION_COUNT,
                "pressure_level": pressure_level or DEFAULT_PRESSURE_LEVEL,
            }
        if mode == "communication":
            return {"scenario_slug": scenario_slug}
        return {}

    def validate_config(self, db: Database, mode: str, config: dict) -> None:
        """Reject configuration that points at something that doesn't exist."""
        if mode == "communication" and config.get("scenario_slug"):
            try:
                found = self._communication.get_scenario_by_slug(db, config["scenario_slug"])
            except ScenarioNotFoundError:
                found = None
            if found is None:
                raise ConversationConfigError("Scenario not found.")

    @staticmethod
    def uses_profile_context(mode: str) -> bool:
        """Only free-form modes take Step 11 context; the structured engines have their own logic."""
        return mode in FREEFORM_MODES

