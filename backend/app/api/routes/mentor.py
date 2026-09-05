"""
Placeholder AI Mentor routes. Real chat endpoints arrive with the AI Mentor
feature (Step 3+), which will call the Gemini-backed AI service.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/mentor", tags=["mentor"])
