# Personal AI Mentor for Cybersecurity, Communication & Career Development

## Description

A personal AI mentor that will help with learning cybersecurity, practicing
labs and CTFs, improving real-life and professional communication, and
practicing HR/technical interviews — including voice-based practice,
performance analysis, and personalized progress tracking.

This repository currently contains **Step 1 — Project Foundation &
Architecture**: a clean, modular scaffold with working routing, a live
health-checked backend, and a MongoDB connection foundation. None of the
mentor/interview/communication/voice features are implemented yet — those
land in later steps.

## Architecture

```text
React Frontend
      ↓
REST API (versioned: /api/v1)
      ↓
FastAPI Backend
      ↓
Services layer
      ↓
MongoDB / AI Providers / Voice Services
```

The frontend never talks to MongoDB, Gemini, Ollama, or Whisper directly —
every request goes through the FastAPI backend, which is the only place
that holds credentials and API keys. Backend routes stay thin; business
logic is intended to live in the `services/` layer so features can be
added without restructuring the app.

## Current technology stack

**Frontend:** React 19, TypeScript 5, Vite 7, Tailwind CSS 4, shadcn/ui,
React Router 7, Zustand, Axios, Recharts.

**Backend:** Python 3.12, FastAPI, Pydantic 2, Uvicorn, PyMongo 4.

**Database:** MongoDB 8.

## Prerequisites

- Node.js (v20+ recommended)
- Python 3.12
- MongoDB running locally (or reachable via `MONGODB_URI`)
- Git

## Project layout

```text
ai-cybersec-mentor/
├── frontend/    # React + Vite app
├── backend/     # FastAPI app
├── data/        # Static learning/interview/communication content (seeded later)
├── uploads/     # User-uploaded files (resumes, documents, audio)
├── scripts/     # One-off setup/seed scripts (placeholders for now)
```

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

To build for production:

```bash
npm run build
```

## Running the backend

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment:

- macOS/Linux: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

Then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

## MongoDB

MongoDB must be running locally before starting the backend (or point
`MONGODB_URI` in `backend/.env` at a reachable instance). If MongoDB isn't
running, the backend still starts — `GET /api/v1/health` will simply report
`"database_connected": false` instead of crashing.

Default local start commands (varies by install method):

```bash
# macOS (Homebrew)
brew services start mongodb-community

# Linux (systemd)
sudo systemctl start mongod

# Windows (as a service, if installed that way)
net start MongoDB
```

## Environment configuration

Copy the example env files and fill in real values as needed — never commit
`.env` itself:

```bash
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

`GEMINI_API_KEY` and `JWT_SECRET_KEY` are reserved for later steps and can
stay blank for now.

## Gemini setup

The AI mentor engine is backed by Google Gemini. To enable it:

1. Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. Open `backend/.env` (copy it from `backend/.env.example` first if you
   haven't already).
3. Set the following:

   ```env
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-3.1-flash-lite
   GEMINI_TIMEOUT_SECONDS=60
   ```

   Never commit a real key — `backend/.env` is already git-ignored, and
   `backend/.env.example` must always stay blank.
4. Start the backend (`uvicorn app.main:app --reload`).
5. Authenticate: register/login via `/api/v1/auth/register` and
   `/api/v1/auth/login` to get an access token (see the API section below).
6. Test the AI engine:

   ```bash
   curl -X POST http://localhost:8000/api/v1/ai/chat \
     -H "Authorization: Bearer <your_access_token>" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is SQL injection?", "conversation_history": []}'
   ```

If `GEMINI_API_KEY` is left blank, the endpoint still responds — it returns
a clean `503 AI_SERVICE_UNAVAILABLE` error instead of crashing.

The API key is backend-only. It is never sent to the frontend, never
appears in `frontend/.env`, and the frontend never calls Gemini directly —
only `POST /api/v1/ai/chat` and the mentor/cybersecurity endpoints on this
backend do.

## Cybersecurity Learning

A structured learning-and-practice system, separate from the free-form
Mentor chat.

- **Browse topics** at `/cybersecurity` — a starter set of ~36 topics across
  16 categories (Fundamentals, Networking, Linux, Windows, Web Security,
  SOC, SIEM, Incident Response, Digital Forensics, Penetration Testing,
  Cryptography, Threat Intelligence, Cloud Security, Active Directory,
  Malware Basics, Security Tools), searchable and filterable by category
  and difficulty (beginner / intermediate / advanced).
- **Learning mode** — open a topic to read its overview, learning
  objectives, explanation, examples, and key points.
- **Practice mode** — click "Start Practice" (or "Practice" from a topic
  card) to generate a short quiz for that topic. Gemini generates each
  question (multiple-choice or short-answer) through the same `AIService`
  used by the Mentor — never a second AI client — and the backend validates
  every generated question before it's shown to you; the correct answer is
  never sent to the frontend before you submit.
- **Answer evaluation** — multiple-choice is scored directly; short answers
  are graded by Gemini for accuracy, completeness, and technical
  understanding, with feedback, missing points, and an ideal answer shown
  after you submit.
- **Practice history** — completed (and in-progress) sessions are
  persisted in MongoDB and visible under practice history, paginated. A
  session only shows up for the user who created it — the backend checks
  ownership on every request.
- **Basic progress** — a simple per-category average score and attempt
  count, with a topic marked "weak" below 60, "developing" 60–79, and
  "strong" 80+. This is not the full progress dashboard (that's a later
  step) — just enough to see where you're weak right now.

## CTF & Practical Lab Mentor

An AI *guidance* system for CTFs and practical labs (Hack The Box,
TryHackMe, a local VM, or any other environment you're already
authorized to work in) — separate from both the free-form Mentor chat and
the structured Cybersecurity Learning quizzes.

**It does not automatically attack, scan, or access anything.** There's no
HTB/TryHackMe integration, no automatic exploitation, and no automatic flag
submission — you do the practical work yourself, the AI reasons about what
*you* tell it and never claims to have run a command or observed an output
it wasn't given.

- **Supported categories:** Web Security, Cryptography, Digital Forensics,
  Steganography, OSINT, Reverse Engineering, Binary/Exploitation Concepts,
  Linux, Networking, Miscellaneous.
- **Supported platforms (informational only):** Hack The Box, TryHackMe,
  CTF, Custom Lab, Other.
- **Challenge sessions** — describe a challenge (platform, category,
  difficulty, title, description, and what you've tried so far) at `/ctf`
  to start a session. Every session belongs to one user; the backend
  checks ownership on every request, so you can never open someone else's
  session.
- **Mentor chat** — ask follow-up questions with the full challenge context
  already in scope. Conversation history is persisted per session (unlike
  the general Mentor chat) and bounded before being sent to Gemini on each
  request.
- **Progressive hints** — request `hint_1`, `hint_2`, `hint_3`, or go
  straight to the `solution` if you want it directly. Hints 1–3 unlock in
  order; each level is generated once and then persisted, so re-requesting
  the same level always returns the same hint rather than generating a new
  one.
- **Solution mode** — the full vulnerability/technique, reasoning,
  methodology, an illustrative example (using `<LAB_TARGET>` instead of a
  real address), and how to detect/prevent it defensively.
- **Session history** — reopen an `in_progress` session to pick up where
  you left off, or mark it `completed` (optionally recording a flag for
  your own tracking — it's never verified against HTB/TryHackMe).

## API

```text
GET  /                       Project status
GET  /api/v1/health          Health check (includes MongoDB connection status)

POST /api/v1/auth/register   Register a new account
POST /api/v1/auth/login      Log in, receive a JWT access token
GET  /api/v1/auth/me         Current authenticated user (requires Bearer token)
POST /api/v1/auth/logout     Logout (client discards the token)

POST /api/v1/ai/chat         AI mentor chat — requires a Bearer token
POST /api/v1/mentor/chat     Mode/level-aware cybersecurity mentor chat

GET  /api/v1/cybersecurity/topics                    List/filter topics
GET  /api/v1/cybersecurity/topics/{slug}             Topic detail
POST /api/v1/cybersecurity/practice/start            Start a practice session
POST /api/v1/cybersecurity/practice/{id}/answer      Submit an answer
POST /api/v1/cybersecurity/practice/{id}/complete    Complete a session
GET  /api/v1/cybersecurity/practice/history          Paginated practice history
GET  /api/v1/cybersecurity/progress                  Basic per-category progress

POST /api/v1/ctf/sessions                    Create a CTF/lab challenge session
GET  /api/v1/ctf/sessions                    Paginated session history
GET  /api/v1/ctf/sessions/{id}               Session detail (messages + hints)
POST /api/v1/ctf/sessions/{id}/chat          Mentor chat with challenge context
GET  /api/v1/ctf/sessions/{id}/hint          Request a hint (?level=hint_1|hint_2|hint_3|solution)
POST /api/v1/ctf/sessions/{id}/complete      Mark a session complete
```

All endpoints above except the two health/status checks require
authentication. All future endpoints are added under the versioned
`/api/v1` prefix. Interactive docs are available at
`http://localhost:8000/docs` while the backend is running.

## Project status

**Completed:** Step 1 — Project Foundation & Architecture, Step 2 —
Authentication, Step 3 — Gemini AI Engine, Step 4 — AI Cybersecurity Mentor
chat, Step 5 — Cybersecurity Learning & Practice System, Step 6 — CTF &
Practical Lab Mentor.

**Not yet implemented:** communication coach, voice features, interview
simulator, the full progress/analytics dashboard, a recommendations
engine, and conversation persistence for the general Mentor chat (the
Mentor's chat history still lives in frontend state only — CTF and
practice sessions, unlike Mentor chat, are persisted). These arrive in
later steps.
