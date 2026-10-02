"""
Profile & preferences logic (Step 14).

Pure functions only — no database access. Persistence stays in
`auth_service` (the single owner of the `users` collection); this module turns
a stored user document into a safe API response and turns a validated update
body into the exact `$set` fields that are allowed to change.

Storage layout (extends the existing user document, nothing else replaced):

    name                    <- the existing top-level field; exposed as `full_name`
    profile.*               <- bio, education, career_goal, experience_level,
                               cybersecurity_interests, learning_goals,
                               custom_learning_goals
    preferences.*           <- response_style, difficulty, learning_style,
                               interview_focus, theme
"""

from __future__ import annotations

from pydantic import ValidationError

from app.models.user import UserDocument
from app.schemas.user import (
    CompletionItem,
    ProfileCompletion,
    ProfileData,
    UserPreferences,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)

# Fields a user may set through PATCH /users/me, mapped to where they are stored.
_PROFILE_FIELDS = frozenset(ProfileData.model_fields)
_PREFERENCE_FIELDS = frozenset(UserPreferences.model_fields)

# (key, label) — equal weight, all of them are things the AI mentor can use.
_COMPLETION_FIELDS: tuple[tuple[str, str], ...] = (
    ("full_name", "Full name"),
    ("bio", "Bio"),
    ("education", "Education"),
    ("career_goal", "Career goal"),
    ("experience_level", "Experience level"),
    ("cybersecurity_interests", "Cybersecurity interests"),
    ("learning_goals", "Learning goals"),
)


def _load_profile(user: UserDocument) -> ProfileData:
    try:
        return ProfileData.model_validate(user.get("profile") or {})
    except ValidationError:
        # A hand-edited / corrupt sub-document must never break the page.
        return ProfileData()


def _load_preferences(user: UserDocument) -> UserPreferences:
    try:
        return UserPreferences.model_validate(user.get("preferences") or {})
    except ValidationError:
        return UserPreferences()


def compute_completion(full_name: str, profile: ProfileData) -> ProfileCompletion:
    done = {
        "full_name": bool(full_name.strip()),
        "bio": bool(profile.bio),
        "education": bool(profile.education),
        "career_goal": bool(profile.career_goal),
        "experience_level": profile.experience_level is not None,
        "cybersecurity_interests": bool(profile.cybersecurity_interests),
        # A custom goal counts too: the user did say what they want to learn.
        "learning_goals": bool(profile.learning_goals or profile.custom_learning_goals),
    }
    items = [CompletionItem(key=k, label=label, done=done[k]) for k, label in _COMPLETION_FIELDS]
    percentage = round(100 * sum(done.values()) / len(items))
    return ProfileCompletion(percentage=percentage, items=items)


def to_profile_response(user: UserDocument) -> UserProfileResponse:
    """Build the response from an existing user document, applying defaults for missing fields."""
    profile = _load_profile(user)
    return UserProfileResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["name"],
        profile=profile,
        preferences=_load_preferences(user),
        completion=compute_completion(user["name"], profile),
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at"),
    )


def build_profile_update(payload: UserProfileUpdate) -> dict:
    """
    Turn a validated PATCH body into `$set` fields.

    Only explicitly sent, non-null fields are included, and only names on the
    allow-list can ever appear — so there is no path to mass assignment.
    """
    sent = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    fields: dict = {}
    for key, value in sent.items():
        if key == "full_name":
            fields["name"] = value
        elif key in _PROFILE_FIELDS:
            fields[f"profile.{key}"] = value
    return fields


def build_preferences_update(payload: UserPreferencesUpdate) -> dict:
    sent = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    return {f"preferences.{k}": v for k, v in sent.items() if k in _PREFERENCE_FIELDS}
