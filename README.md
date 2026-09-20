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

## Real-Life Communication Coach

Communication practice through realistic roleplay conversations, with
AI-graded feedback at the end. Answer by typing (this section) or by
speaking — see [Step 8 — Voice & Speaking Analysis](#step-8--voice--speaking-analysis).

- **Scenario categories:** Classmates, Teachers/Professors, Seniors,
  Recruiters, Teammates, Managers/Team Leads, Everyday Social Situations,
  Professional Situations — 18 starter scenarios across all 8 categories.
- **Modes:** Daily Life, Professional, Social, Difficult Conversation,
  Roleplay. **Difficulty:** Beginner, Intermediate, Advanced — higher
  difficulty means a more realistic, less forgiving AI character (more
  unexpected questions, mild pushback, less hand-holding).
- **Roleplay chat** — the AI stays in character as the scenario's other
  person and responds naturally; it deliberately does *not* interrupt the
  conversation with grammar corrections — that happens only at evaluation
  time, at `/communication`.
- **Evaluation** — end a session to get scores (0–100) for clarity,
  grammar, vocabulary, professionalism, confidence, relevance, and
  conversation flow, plus strengths, weaknesses, improvements, a few
  "better response" rewrites with an explanation, and a summary. Confidence
  is inferred only from the language used (hedging, tone) — this is not a
  claim of measuring actual psychological confidence.
- **Session history** — completed and in-progress sessions are persisted
  per user, same ownership rules as the rest of the app.

## Step 8 — Voice & Speaking Analysis

The Communication Coach now supports **text and voice**. In *Voice* mode you
speak, review the transcript, send it, and the AI character replies (optionally
out loud). It is the same scenario, session, roleplay, history and evaluation
as text mode — voice is an input method, not a separate system.

```text
Browser microphone -> FastAPI -> faster-whisper (local STT) -> transcript
   -> you review / edit / send -> Communication Service -> existing AI service
   -> Gemini -> reply text -> (optional) text-to-speech -> audio in the browser
```

The frontend never talks to Gemini or a speech provider directly; all keys
stay in `backend/.env`.

### Using it

1. Open **Communication**, choose **Voice** (or switch inside a session with
   the Text / Voice toggle), and start a scenario.
2. Press **🎙 Start Recording**, speak, then **Stop Recording**.
3. Review the **Transcript**. **Edit** it if it misheard you, then **Send** —
   or **Discard**. Nothing is sent to the AI until you press Send.
4. Read the reply, and press **▶ Play AI Response** to hear it (or tick
   *Auto-play AI replies*).
5. End the session to get the normal evaluation plus **Speaking Performance**.

### Requirements

- A browser with microphone recording (`MediaRecorder`) — current Chrome,
  Edge, Firefox and Safari all provide it (Safari records MP4/AAC, which the
  server accepts). The recording flow was verified against a simulated
  `MediaRecorder`, so please try it once in your own browser. Recording needs a **secure context** — `https://`
  or `http://localhost`; browsers refuse the microphone on plain `http://` to
  other hosts.
- **Microphone permission.** If you block it, the app explains how to allow
  it in your browser's site settings; text mode keeps working.
- No system ffmpeg is needed — audio decoding is bundled with faster-whisper.

### Speech-to-text (faster-whisper, local)

Speech is transcribed **on your own server** with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper); audio is not sent
to Gemini or any cloud service. Configure it in `backend/.env`:

```env
WHISPER_MODEL=small          # tiny | base | small | medium | large-v3 ...
WHISPER_DEVICE=auto          # auto | cpu | cuda
WHISPER_COMPUTE_TYPE=auto    # auto | int8 | float16 | float32
WHISPER_LANGUAGE=en          # empty = auto-detect per recording
VOICE_MAX_AUDIO_BYTES=10485760
VOICE_MAX_AUDIO_SECONDS=300
```

- **CPU (default, no setup):** works out of the box. `int8` is a good CPU
  `WHISPER_COMPUTE_TYPE`; `tiny`/`base` are fastest on weak machines.
- **GPU:** set `WHISPER_DEVICE=cuda` (and e.g. `float16`) on a machine with a
  CUDA-capable GPU and the matching CUDA/cuDNN libraries. Nothing in the app
  requires a GPU or hard-codes CUDA.
- The model is loaded **once, lazily**, on first use — never per request. The
  first run downloads the model weights, so warm it up once after installing:

  ```bash
  cd backend
  python ../scripts/download_whisper_model.py
  ```

- If the model can't load, voice endpoints return a clear error and the UI
  tells the user to type instead. Text mode is never affected.

### Text-to-speech (optional)

Spoken AI replies are **optional**. With no provider configured the app runs
in text mode and shows *"Audio unavailable — text response is still
available."* Configure a provider in `backend/.env` (backend-only — never
put these in `frontend/.env`):

```env
TTS_PROVIDER=openai          # openai | google   (empty = disabled)
TTS_API_KEY=...
TTS_MODEL=                   # openai: default tts-1
TTS_VOICE=                   # openai: default alloy | google: e.g. en-US-Neural2-F
TTS_BASE_URL=                # optional OpenAI-compatible endpoint (e.g. self-hosted)
```

Providers sit behind a small interface in
`backend/app/services/voice/text_to_speech.py`; adding another means adding one
class and one registry entry. The OpenAI and Google providers are written
against those services' documented REST APIs and covered by mocked-HTTP
tests, so confirm them once with your own key. Note that with a cloud provider, the **AI reply
text** (not your audio) is sent to that provider. Generated audio is returned
to the browser once and is not stored.

### Speaking analysis

After a session that included spoken answers, the evaluation gains a
**Speaking Performance** section:

- **Scores** — clarity, grammar, vocabulary, conciseness (blended from
  deterministic measurements and Gemini's qualitative review) alongside the
  existing overall and conversation-flow scores.
- **Speaking metrics** — words spoken, speaking rate (WPM), filler words
  (contextual: "I like security" isn't a filler, "I was, like, nervous" is),
  repeated words, and pauses measured from word timestamps.
- **What you did well / what to improve.**

Each spoken message also stores its own metrics under `voice_analysis`, and
the session evaluation stores a `voice_summary`, in the existing
`communication_sessions` collection.

**These are approximate communication indicators, not a psychological,
medical or clinical assessment.** The app does not measure confidence,
nervousness or anxiety. WPM bands (about 100–160 WPM is a typical
conversational range) are general guidance, not a standard. A metric that
can't be measured reliably (e.g. pauses when no word timing exists) is shown
as *not measured* — it is never invented. Filler detection is
English-oriented and can be tuned with `FILLER_WORDS` (comma-separated).

### Privacy

Voice is sensitive. By default: audio is written to a private temporary file
only while it is transcribed, then **deleted immediately**; raw recordings are
**never stored**; only the transcript and metrics are saved. Audio and
transcripts are not logged, audio is never sent to Gemini, and only the
transcript text is sent to the AI. Set `VOICE_TEMP_DIR` to control where the
temporary file lives (default: the OS temp directory).

### Voice API

```text
GET  /api/v1/voice/capabilities   Which voice features the server supports (no secrets)
POST /api/v1/voice/transcribe     multipart/form-data, field "audio" -> transcript + timing
POST /api/v1/voice/synthesize     {"text": "..."} -> audio (audio/mpeg)
```

A transcript becomes a normal communication message via the existing
`POST /api/v1/communication/sessions/{id}/message`, with optional
`input_type: "voice"`, `audio_metadata` and `transcript_edited` fields (text
messages are unchanged).

Uploads are limited by size and duration; the format is checked from the
file's actual bytes (never the filename or declared type); and the endpoint
authenticates before reading the body. Behind a reverse proxy, also cap the
request body size there (e.g. nginx `client_max_body_size`).

### Known limits

- Whisper transcription can misrecognise words (accents, background noise,
  technical terms) — that is why the transcript is always editable. Metrics
  are computed from the transcript you send.
- Pause measurement relies on Whisper's word timestamps, which are
  approximate, so only gaps of 0.5 s or more count as pauses (2 s or more as
  "long").
- `large` models are slow on CPU. Start with `small` (or `tiny`/`base`).

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

GET  /api/v1/communication/scenarios              List/filter scenarios
GET  /api/v1/communication/scenarios/{slug}       Scenario detail
POST /api/v1/communication/sessions               Start a practice session
POST /api/v1/communication/sessions/{id}/message  Send a message, get the AI's reply
POST /api/v1/communication/sessions/{id}/complete Evaluate and complete a session
GET  /api/v1/communication/sessions/{id}          Session detail (messages + evaluation)
GET  /api/v1/communication/sessions               Paginated session history

GET  /api/v1/voice/capabilities                   Voice features available on this server
POST /api/v1/voice/transcribe                     Audio upload -> transcript (local Whisper)
POST /api/v1/voice/synthesize                     Text -> speech audio (optional TTS provider)
```

All endpoints above except the two health/status checks require
authentication. All future endpoints are added under the versioned
`/api/v1` prefix. Interactive docs are available at
`http://localhost:8000/docs` while the backend is running.

## Project status

**Completed:** Step 1 — Project Foundation & Architecture, Step 2 —
Authentication, Step 3 — Gemini AI Engine, Step 4 — AI Cybersecurity Mentor
chat, Step 5 — Cybersecurity Learning & Practice System, Step 6 — CTF &
Practical Lab Mentor, Step 7 — Real-Life Communication Coach, Step 8 — Voice
& Speaking Analysis.

**Not yet implemented:** the interview simulator, the full progress/analytics dashboard, a
recommendations engine, and conversation persistence for the general
Mentor chat (the Mentor's chat history still lives in frontend state only —
CTF, cybersecurity practice, and communication sessions, unlike Mentor
chat, are all persisted). These arrive in later steps.
