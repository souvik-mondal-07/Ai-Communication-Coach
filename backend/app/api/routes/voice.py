"""
Placeholder voice routes (speech-to-text / text-to-speech / WebSocket voice
sessions), implemented alongside the voice conversation feature.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/voice", tags=["voice"])
