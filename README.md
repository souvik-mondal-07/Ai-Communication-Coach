# AI Cybersecurity Mentor

A personal AI mentor for learning cybersecurity, practising CTFs and labs,
improving professional communication, rehearsing interviews (typed or spoken),
training composure under pressure, and tracking how you improve over time.

> The mentor is **advisory only**. It explains, quizzes, coaches and gives
> hints. It never runs commands, scans or attacks targets, or submits CTF flags.

## Features

| Area | What it does |
| --- | --- |
| **Authentication** | Register / login with Argon2-hashed passwords and JWT access tokens. |
| **AI Mentor** | Chat in four modes (learn, explain, practice, troubleshoot) at three levels. |
| **Cybersecurity** | Topic library plus AI-generated practice sessions with scoring and history. |
| **CTF & Labs** | Guidance-only mentor with staged hints (hint 1 → 3 → solution). |
| **Communication coach** | Scenario-based role-play with evaluation and feedback. |
| **Voice** | Local speech-to-text (faster-whisper), optional text-to-speech, speaking analysis (pace, fillers, pauses). |
| **Interview simulator** | HR / technical interviews with per-answer and final evaluation. |
| **Pressure training** | Five pressure levels (interruptions, follow-ups) for building composure. |
| **Progress & profile** | Skill breakdown, trends, detected weaknesses, recommendations and an AI-written personal profile that ties every module together. |

## Architecture

```text
React (Vite, TypeScript)
   ↓  REST  /api/v1
FastAPI routes (thin)
   ↓
Services (business logic)
   ↓                    ↓
MongoDB          Gemini · faster-whisper · TTS provider (optional)
```

The browser only ever talks to the backend. API keys, the JWT secret and all
database access stay server-side. A single AI client (`app/services/ai`) is
used by every module.

## Tech stack (versions pinned in `requirements.txt` / `package.json`)

**Backend:** Python 3.12, FastAPI 0.115.6, Pydantic 2.12.5, PyMongo 4.10.1,
PyJWT 2.10.1, argon2-cffi 23.1.0, google-genai 2.22.0, faster-whisper 1.2.1,
httpx 0.28.1. Tests: pytest 8.3.4 + mongomock 4.3.0.

**Frontend:** React 19.2.8, TypeScript 6.0.3, Vite 8.2.2, Tailwind CSS 4.3.3,
React Router 7.18.3, Zustand 5.0.15, Axios 1.20.0, Recharts 3.10.1, Oxlint.

**Database:** MongoDB (any recent version reachable via `MONGODB_URI`).
**AI model:** Gemini (`gemini-3.1-flash-lite` by default).

## Setup

Prerequisites: Node.js 20+, Python 3.12, a running MongoDB, a Gemini API key.

### 1. MongoDB

```bash
brew services start mongodb-community   # macOS (Homebrew)
sudo systemctl start mongod             # Linux (systemd)
net start MongoDB                       # Windows (service)
```

If MongoDB is down the backend still starts; `GET /api/v1/health` reports
`"database_connected": false` and data routes return `503`.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env (see below)
uvicorn app.main:app --reload      # http://localhost:8000  (docs: /docs)
```

Optional: pre-download the Whisper model so the first voice request is fast:

```bash
python ../scripts/download_whisper_model.py
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                        # http://localhost:5173
```

## Environment variables

Backend (`backend/.env`; copy from `.env.example`, which holds placeholders only):

| Variable | Purpose |
| --- | --- |
| `JWT_SECRET_KEY` | **Required for stable sessions.** Long random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`. If empty, a random per-process secret is generated and logins reset on every restart. |
| `GEMINI_API_KEY` | Gemini key. Without it AI features return a safe `503`. |
| `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS` | Model name and request timeout (default 60s). |
| `MONGODB_URI`, `MONGODB_DATABASE` | Database connection. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins (no wildcard). |
| `APP_ENV`, `DEBUG` | Set `DEBUG=false` outside development (controls log verbosity). |
| `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token settings (HS256, 60 min). |
| `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `WHISPER_LANGUAGE` | Local speech-to-text. |
| `VOICE_MAX_AUDIO_BYTES`, `VOICE_MAX_AUDIO_SECONDS`, `VOICE_TEMP_DIR` | Upload limits (10 MB / 300 s by default). |
| `TTS_PROVIDER` (`openai`\|`google`), `TTS_API_KEY`, `TTS_MODEL`, `TTS_VOICE`, `TTS_BASE_URL` | Optional spoken replies. Leave `TTS_PROVIDER` empty to disable. |

Frontend (`frontend/.env`): only `VITE_API_BASE_URL`. **Never put secrets in
`VITE_*` variables** – Vite ships them to the browser.

## API overview

All routes are under `/api/v1`, return `{success, message, data}` (errors:
`{success:false, message, error_code}`), and – apart from `health`,
`auth/register` and `auth/login` – require `Authorization: Bearer <token>`.

| Group | Endpoints |
| --- | --- |
| `auth` | `POST /register`, `POST /login`, `GET /me` |
| `mentor` | `POST /chat` |
| `cybersecurity` | `GET /topics`, `GET /topics/{slug}`, `POST /practice/start`, `POST /practice/{id}/answer`, `POST /practice/{id}/complete`, `GET /practice/history` |
| `ctf` | `POST/GET /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/chat`, `GET /sessions/{id}/hint`, `POST /sessions/{id}/complete` |
| `communication` | `GET /scenarios`, `GET /scenarios/{slug}`, `POST/GET /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/message`, `POST /sessions/{id}/complete` |
| `voice` | `POST /transcribe`, `POST /synthesize` |
| `interview` | `POST/GET /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/answer`, `POST /sessions/{id}/complete` |
| `pressure` | `GET /config`, `POST/GET /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/response`, `POST /sessions/{id}/complete` |
| `progress` | `GET /overview`, `/skills`, `/trends`, `/weaknesses`, `/recommendations`, `/activity`, `/profile`; `POST /recalculate`, `POST /recommendations/{id}/complete` |

Interactive docs: `http://localhost:8000/docs`.

## Testing

```bash
# Backend (no MongoDB, Gemini, Whisper or TTS needed – all mocked)
cd backend
pytest -q

# Frontend
cd frontend
npm run build      # type-checks (tsc -b) then builds
npm run lint
```

`backend/tests/test_security.py` covers cross-cutting security: every
protected route requires auth, JWT edge cases, cross-user access, secret
leakage, input limits, upload validation, CORS and error handling.
`test_e2e_journey.py` walks one user through the API end to end.

## Security

- Passwords: Argon2 hashes; never stored in plaintext, logged or returned.
- JWT: secret from the environment, expiry enforced, `sub` is the only identity
  used – user ids are never taken from request bodies or query strings.
- Ownership: every session/progress query is scoped to the authenticated user;
  another user's resource returns `403`/`404`.
- Input limits on all AI-facing schemas (message length, history size,
  pagination bounds, TTS text length); audio upload size and type checked
  (magic bytes, not the claimed MIME type or filename).
- Audio is written to a private temp file only while transcribing and always
  deleted (`try/finally`); recordings are never stored.
- Errors are generic JSON; tracebacks and internals go only to server logs.
  Framework debug mode is disabled so a `DEBUG=true` config cannot leak them.
- CORS is an explicit origin allow-list. `.env` files are git-ignored.
- No code path executes shell commands or AI output; the CTF mentor cannot
  scan, exploit or submit flags.
- Third-party HTTP/SDK loggers are held at WARNING to keep credentials out of logs.

## Limitations

- Requires a Gemini API key and internet access for all AI features.
- Speech-to-text needs `faster-whisper` and a local model (download on first
  use; CPU works but is slower). Spoken replies need a configured TTS provider.
- Voice input needs browser microphone permission (HTTPS or `localhost`).
- Access tokens are stored in `localStorage` and there is no server-side
  logout/revocation: logout discards the token client-side and it expires
  after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.
- No rate limiting beyond request/input size limits.
- No automatic exploitation, and no HackTheBox / TryHackMe integration.
- Tests use `mongomock`; behaviour against a real MongoDB has not been
  covered by the automated suite.
- The `uploads/` folder is reserved; no resume/document upload feature exists.

Earlier per-step build notes are kept in [`docs/development-notes.md`](docs/development-notes.md).
