"""
Profile & account management schemas (Step 14).

Every value that can be stored is an explicit enum or a bounded string/list,
so the API rejects anything unexpected before it reaches MongoDB. The update
schemas use ``extra="forbid"``: a request that tries to set a protected field
(``password_hash``, ``is_admin``, ``_id``, ``email`` ...) is rejected outright
rather than silently ignored.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.auth import PASSWORD_MAX_LENGTH


# --------------------------------------------------------------------------- enums
class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CybersecurityInterest(StrEnum):
    WEB_SECURITY = "web_security"
    PENETRATION_TESTING = "penetration_testing"
    RED_TEAMING = "red_teaming"
    SOC = "soc"
    SIEM = "siem"
    DIGITAL_FORENSICS = "digital_forensics"
    INCIDENT_RESPONSE = "incident_response"
    THREAT_INTELLIGENCE = "threat_intelligence"
    NETWORK_SECURITY = "network_security"
    CLOUD_SECURITY = "cloud_security"
    MALWARE_ANALYSIS = "malware_analysis"
    ACTIVE_DIRECTORY = "active_directory"
    CTF = "ctf"
    CRYPTOGRAPHY = "cryptography"
    SECURITY_RESEARCH = "security_research"


class LearningGoal(StrEnum):
    IMPROVE_PENETRATION_TESTING = "improve_penetration_testing"
    LEARN_WEB_SECURITY = "learn_web_security"
    PREPARE_FOR_INTERVIEWS = "prepare_for_interviews"
    IMPROVE_NETWORKING = "improve_networking"
    LEARN_SOC_SIEM = "learn_soc_siem"
    PRACTICE_CTFS = "practice_ctfs"
    IMPROVE_LINUX = "improve_linux"
    IMPROVE_ACTIVE_DIRECTORY = "improve_active_directory"
    IMPROVE_COMMUNICATION = "improve_communication"


class ResponseStyle(StrEnum):
    SIMPLE = "simple"
    BALANCED = "balanced"
    TECHNICAL = "technical"


class LearningDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ADAPTIVE = "adaptive"  # stored only; the adaptive engine arrives in Step 16


class LearningStyle(StrEnum):
    EXPLANATION = "explanation"
    PRACTICAL = "practical"
    QUESTION_BASED = "question_based"
    HANDS_ON = "hands_on"
    MIXED = "mixed"


class InterviewFocus(StrEnum):
    HR = "hr"
    BEHAVIORAL = "behavioral"
    CYBERSECURITY_TECHNICAL = "cybersecurity_technical"
    SOC = "soc"
    BLUE_TEAM = "blue_team"
    RED_TEAM = "red_team"
    PENETRATION_TESTING = "penetration_testing"
    NETWORKING = "networking"
    LINUX = "linux"
    WEB_SECURITY = "web_security"
    SCENARIO_BASED = "scenario_based"
    RESUME_BASED = "resume_based"


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# ----------------------------------------------------------------- shared helpers
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Bio = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Education = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]
CareerGoal = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
CustomGoal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

MAX_CUSTOM_GOALS = 5


def _dedupe(values: list) -> list:
    """Drop duplicates while keeping the order the user chose."""
    return list(dict.fromkeys(values))


class _DedupeMixin(BaseModel):
    @field_validator(
        "cybersecurity_interests",
        "learning_goals",
        "custom_learning_goals",
        "interview_focus",
        check_fields=False,
        mode="after",
    )
    @classmethod
    def _dedupe_lists(cls, value):
        return _dedupe(value) if value is not None else value


# --------------------------------------------------------------- stored sub-docs
class ProfileData(_DedupeMixin):
    """The `profile` sub-document (the display name lives in the top-level `name`)."""

    bio: Bio = ""
    education: Education = ""
    career_goal: CareerGoal = ""
    # None = "not chosen yet" so profile completion is meaningful for new users.
    experience_level: ExperienceLevel | None = None
    cybersecurity_interests: list[CybersecurityInterest] = Field(default_factory=list, max_length=len(CybersecurityInterest))
    learning_goals: list[LearningGoal] = Field(default_factory=list, max_length=len(LearningGoal))
    custom_learning_goals: list[CustomGoal] = Field(default_factory=list, max_length=MAX_CUSTOM_GOALS)


class UserPreferences(_DedupeMixin):
    """The `preferences` sub-document, with the defaults used for existing users."""

    response_style: ResponseStyle = ResponseStyle.BALANCED
    difficulty: LearningDifficulty = LearningDifficulty.ADAPTIVE
    learning_style: LearningStyle = LearningStyle.MIXED
    interview_focus: list[InterviewFocus] = Field(default_factory=list, max_length=len(InterviewFocus))
    theme: Theme = Theme.SYSTEM


# ------------------------------------------------------------------ update bodies
class UserProfileUpdate(_DedupeMixin):
    """PATCH /users/me — only these fields can ever be changed through it."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName | None = None
    bio: Bio | None = None
    education: Education | None = None
    career_goal: CareerGoal | None = None
    experience_level: ExperienceLevel | None = None
    cybersecurity_interests: list[CybersecurityInterest] | None = Field(default=None, max_length=len(CybersecurityInterest))
    learning_goals: list[LearningGoal] | None = Field(default=None, max_length=len(LearningGoal))
    custom_learning_goals: list[CustomGoal] | None = Field(default=None, max_length=MAX_CUSTOM_GOALS)


class UserPreferencesUpdate(_DedupeMixin):
    """PATCH /users/me/preferences."""

    model_config = ConfigDict(extra="forbid")

    response_style: ResponseStyle | None = None
    difficulty: LearningDifficulty | None = None
    learning_style: LearningStyle | None = None
    interview_focus: list[InterviewFocus] | None = Field(default=None, max_length=len(InterviewFocus))
    theme: Theme | None = None


class ChangePasswordRequest(BaseModel):
    """
    Deliberately lenient here: length/match rules are enforced in the route so
    the user gets a specific message ("Password must be at least 8 characters.")
    instead of the generic validation error. Only an upper bound is applied at
    the schema level so oversized input never reaches the Argon2 hasher.
    """

    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    confirm_new_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


# --------------------------------------------------------------------- responses
class CompletionItem(BaseModel):
    key: str
    label: str
    done: bool


class ProfileCompletion(BaseModel):
    percentage: int
    items: list[CompletionItem]


class UserProfileResponse(BaseModel):
    """Safe, external-facing profile. Never includes the password hash or token data."""

    id: str
    email: str
    full_name: str
    profile: ProfileData
    preferences: UserPreferences
    completion: ProfileCompletion
    created_at: datetime | None = None
    updated_at: datetime | None = None
