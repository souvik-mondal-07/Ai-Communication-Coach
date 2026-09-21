"""
Validated structured output from the existing `AIService`.

Gemini's JSON is never trusted: it is parsed and validated against a Pydantic
model. One invalid reply triggers a single corrective retry (safe recovery);
after that a `StructuredOutputError` is raised so callers can respond with a
controlled error instead of crashing. Provider failures (`AIServiceError`)
propagate unchanged.
"""

from __future__ import annotations

from typing import Annotated, TypeVar

from pydantic import BaseModel, BeforeValidator, ValidationError

from app.services.ai.ai_service import AIService
from app.utils.helpers import parse_json_object
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRY_NOTE = (
    "\n\n(Your previous reply was not valid JSON in the required shape. "
    "Reply with ONLY the JSON object, nothing else.)"
)


class StructuredOutputError(Exception):
    """The AI never returned output that validates against the expected model."""


def _coerce_score(value: object) -> int:
    """Round/clamp a near-miss score (82.4, "85", 101) into 0-100; reject junk."""
    if isinstance(value, bool):
        raise ValueError("score must be a number")
    if isinstance(value, str):
        value = float(value.strip())  # ValueError on junk
    if not isinstance(value, (int, float)) or value != value:  # NaN check
        raise ValueError("score must be a number")
    return int(max(0, min(100, round(value))))


Score = Annotated[int, BeforeValidator(_coerce_score)]


async def generate_validated(
    ai: AIService,
    *,
    user_prompt: str,
    system_prompt: str,
    model: type[T],
    retries: int = 1,
) -> T:
    prompt = user_prompt
    for attempt in range(retries + 1):
        result = await ai.generate_response(user_message=prompt, system_prompt=system_prompt)
        try:
            return model.model_validate(parse_json_object(result.text))
        except (ValueError, ValidationError) as exc:
            # Log the error type only — never the model output (may echo user text).
            logger.warning(
                "Invalid structured AI output for %s (attempt %d): %s",
                model.__name__,
                attempt + 1,
                type(exc).__name__,
            )
            prompt = user_prompt + _RETRY_NOTE
    raise StructuredOutputError(f"AI did not return valid {model.__name__}")
