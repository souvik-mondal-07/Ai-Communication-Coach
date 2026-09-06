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
only `POST /api/v1/ai/chat` on this backend.

## API

```text
GET  /                       Project status
GET  /api/v1/health          Health check (includes MongoDB connection status)

POST /api/v1/auth/register   Register a new account
POST /api/v1/auth/login      Log in, receive a JWT access token
GET  /api/v1/auth/me         Current authenticated user (requires Bearer token)
POST /api/v1/auth/logout     Logout (client discards the token)

POST /api/v1/ai/chat         AI mentor chat — requires a Bearer token
```

All future endpoints are added under the versioned `/api/v1` prefix.
Interactive docs are available at `http://localhost:8000/docs` while the
backend is running.

## Project status

**Completed:** Step 1 — Project Foundation & Architecture, Step 2 —
Authentication, Step 3 — Gemini AI Engine, Step 4 — AI Cybersecurity Mentor
chat.

**Not yet implemented:** cybersecurity learning dashboard, CTF/lab mentor,
communication coach, voice features, interview simulator, progress
analytics, recommendations, and conversation persistence (the current chat
history lives in frontend state for the session only). These arrive in
later steps.
