"""
Centralized text for pressure conditions.

Question generation, follow-up generation and answer evaluation all reuse
the existing Step 9 interview prompts and AI calls unchanged (see
`pressure_service.py`) -- nothing here talks to Gemini. This module only
holds the small set of scripted, non-AI lines used for two pressure
conditions that are deliberately *not* AI-generated because they must never
drift into anything unprofessional:

* rapid follow-ups ("Why?", "Can you give a practical example?")
* interruptions ("Sorry, let me stop you there...")

Both are asked verbatim -- there is nothing to "prompt" here.
"""

from __future__ import annotations

# Short, neutral rapid follow-ups. Deliberately generic so they fit after any
# answer, in any topic, without needing the AI to invent one.
RAPID_FOLLOW_UPS: tuple[str, ...] = (
    "Why?",
    "Can you give a practical example?",
    "What would you do first?",
    "How would you verify that?",
    "What's the risk if you're wrong about that?",
    "Can you explain that more concisely?",
    "What would you do differently under time pressure?",
)

# Interruptions are used sparingly (see MAX_INTERRUPTIONS_PER_SESSION in
# pressure_engine.py) and are always followed by a request to wrap up --
# never a put-down.
INTERRUPTIONS: tuple[str, ...] = (
    "Sorry, let me stop you there. What is the main point?",
    "I'll interrupt for a second — can you finish that in one sentence?",
    "Let's move on. Quickly, what's the key takeaway from that?",
)

AMBIGUOUS_QUESTION_PREFACE = (
    "This next question is intentionally open-ended. State any assumptions "
    "you're making before you answer."
)
