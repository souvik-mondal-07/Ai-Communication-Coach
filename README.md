# Personal AI Mentor for Cybersecurity, Communication & Career Development

## Description

A personal AI mentor that will help with learning cybersecurity, practicing
labs and CTFs, improving real-life and professional communication, and
practicing HR/technical interviews — including voice-based practice,
performance analysis, and personalized progress tracking.

This repository currently contains **Steps 1–9**: the project foundation,
authentication, the Gemini AI engine, the Mentor chat, Cybersecurity Learning &
Practice, the CTF mentor, the Communication Coach, voice & speaking analysis,
and the Cybersecurity Interview Simulator. See **Project status** at the end
for what is still to come.

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

## Step 9 — Cybersecurity Interview Simulator

A realistic mock **cybersecurity job interview**. The AI acts as an
*interviewer*, not a teacher: it asks one question at a time, doesn't praise or
grade you mid-interview, asks follow-ups when they'd add value, and evaluates
your **technical knowledge** and **communication** separately when you finish.

```text
Setup -> question -> your answer -> (evaluated privately) -> follow-up or next question
   -> ... -> interview ends -> technical + communication evaluation -> final feedback
```

Everything goes through the existing stack: React -> FastAPI -> Interview
Service (Question Service + Evaluation Service) -> the existing AI service ->
Gemini. There is no separate Gemini client and the browser never talks to Gemini.

### Setting up an interview

| Option | Values |
| --- | --- |
| **Interview type** | HR, Technical, Cybersecurity, Scenario-Based, Mixed |
| **Difficulty** | Beginner, Intermediate, Advanced |
| **Questions** | 5, 10, 15, 20 |
| **Mode** | Text or Voice |
| **Show feedback after each answer** | off by default |

- **HR** — behavioural and personal questions ("Tell me about yourself", why
  cybersecurity, strengths and weaknesses, a project you worked on, ...).
- **Technical** — core security knowledge: fundamentals, network security,
  Linux, web security, cryptography.
- **Cybersecurity** — the full specialty spread: everything in *Technical* plus
  SOC / blue team, digital forensics and penetration testing.
- **Scenario-Based** — practical situations (suspicious login, ransomware,
  phishing, compromised endpoint, suspicious PowerShell, data exfiltration, web
  server compromise, and more).
- **Mixed** — roughly 25% HR, 25% scenarios and 50% technical, opening with the
  HR introduction like a real interview.

Behind the scenes each question belongs to one of ten **topic areas** (HR,
fundamentals, network security, Linux, web security, SOC / blue team, digital
forensics, penetration testing, cryptography, scenario-based). The topics and
specific subjects for every question are planned when the interview starts, so
an interview spreads across topics instead of circling one. Difficulty changes
question depth and how strictly answers are judged: *Beginner* is forgiving with
simple follow-ups; *Advanced* uses harder, ambiguous situations, chained
follow-ups and stricter judging. The interviewer also adapts within your
chosen level based on how you're doing.

### Questions and follow-ups

- Questions are generated by the existing AI service from the interview type,
  difficulty, question number, topic, and the previous questions and answers.
- **No repeats.** A question that repeats — or merely rewords — an earlier one
  is rejected and regenerated. (It compares content words, so templated
  questions about *different* subjects are still allowed.)
- **Follow-ups** are generated from your actual answer. The evaluator says
  whether a probe is worthwhile, but fixed rules decide whether one is
  *allowed*, so they never happen after every answer: at most 1 per question
  (2 in Advanced), an interview-wide budget of about 30% / 40% / 50% of the
  question count (Beginner / Intermediate / Advanced), none when the answer was
  too weak to build on, and no probing two questions in a row (except in
  Advanced). A follow-up belongs to the same question number; only the main
  questions count toward the interview length.
- The interviewer never says "Great answer!". Detailed feedback is saved for
  the evaluation. Turn on *Show feedback after each answer* for a practice-style
  run; otherwise evaluations are hidden from every API response until the
  interview ends.

### Evaluation

Each answer gets **two separate evaluations** (two independent AI calls with
separate prompts), so one can't leak into the other:

- **Technical** (0-100): accuracy, completeness, relevance, depth, and — for
  scenario questions — practical reasoning. It ignores how well the answer was
  written or spoken. For HR questions the same dimensions score the substance
  of the answer, and the UI labels it *Answer Content*.
- **Communication** (0-100): clarity, grammar, vocabulary, structure,
  conciseness, professionalism, relevance. It ignores technical correctness.

A fluent wrong answer therefore scores low on technical and high on
communication, and a correct-but-clumsy answer the reverse. The headline scores
are **computed by the backend from the rubric sub-scores**, never taken from the
model, and the model's JSON is validated with Pydantic (one corrective retry,
then a controlled error).

Each answer also gets concise feedback and a short **improved answer**, shown
in the question review after the interview.

**Final evaluation** (`overall_score`, `technical_score`, `communication_score`,
`strengths`, `weaknesses`, `technical_weaknesses`, `communication_weaknesses`,
`recommended_topics`, `recommendations`, `summary`): the scores are computed
deterministically; the overall score weights technical vs. communication by
interview type (HR 40/60, Mixed 55/45, others 65/35). The written summary and
lists come from the AI; if that fails, the interview still completes with
deterministic notes and `ai_narrative_available: false`.

**Weak topics** come *only from this interview* (topics averaging below 60).
*Recommended practice* links to matching Cybersecurity Learning topics where
one exists. This is interview-level only — there is no long-term weakness
tracking yet.

### Voice mode

Voice mode **reuses Step 8** — there is no new voice pipeline. You record,
review/edit/discard the transcript, then send it as your answer (the same
`/voice/transcribe` endpoint and components as the Communication Coach). Spoken
answers reuse the Step 8 speaking analysis: filler words, pace and pauses are
stored per answer and blended into the communication scores, and the final
results show the same speaking metrics. The interviewer's questions can be read
aloud through the existing text-to-speech (if configured; otherwise "Audio
unavailable — text response is still available."). You can switch between
speaking and typing at any time. Raw audio is never stored. See Step 8 for the
microphone, Whisper and privacy details.

### Interview API

```text
POST /api/v1/interview/sessions                     Start an interview -> first question
GET  /api/v1/interview/sessions                     Your interview history (?page=&limit=)
GET  /api/v1/interview/sessions/{id}                One interview (own sessions only)
POST /api/v1/interview/sessions/{id}/answer         Submit an answer -> next question / follow-up
POST /api/v1/interview/sessions/{id}/complete       End the interview -> final evaluation
```

All require authentication; the user always comes from the JWT (requests that
include a `user_id` are rejected). Answers are 1-10,000 characters. Voice
answers add `input_type: "voice"`, `audio_metadata` and `transcript_edited`.
The interview ends automatically after the last question; `/complete` ends it
early (evaluating what you answered) and is safe to call twice. Ending before
answering anything marks the interview `abandoned` with nothing to evaluate.

If the AI fails while handling an answer, you get a clean `503` and **nothing
is saved**, so you can resubmit the same answer. Concurrent double-submits are
guarded with a version check (`409`).

### Database

One collection, `interview_sessions`, with questions, answers, follow-ups and
evaluations embedded in the session document (there is no separate answers
collection):

```text
interview_sessions {
  user_id, interview_type, difficulty, mode, question_count,
  current_question_number, status: in_progress | completed | abandoned,
  reveal_feedback, topic_plan, version, started_at, updated_at,
  completed_at, abandoned_at, final_evaluation,
  questions: [{ question_number, question, topic, focus, answer, answer_input_type,
      voice_analysis, technical_evaluation, communication_evaluation, improved_answer,
      follow_up_questions: [{ question, answer, ...same evaluation fields }] }]
}
```

Indexes (created at startup): `user_id`, `status`, `started_at`,
`interview_type`, `difficulty`, plus `(user_id, started_at desc)` for history.

### Known limits

- Evaluation quality depends on Gemini; the rubric and clamped, computed
  scores keep results consistent, but they are AI judgements, not certification.
- Candidate answers are untrusted text: they are delimited in prompts and
  instructions inside them are ignored, but prompt-injection resistance is
  best-effort. The headline scores are computed from sub-scores, which limits the
  impact.
- Not built yet: pressure/stress interviews, nervousness detection, long-term
  progress or weakness tracking, resume-based interviews.

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

POST /api/v1/interview/sessions                   Start a mock cybersecurity interview
GET  /api/v1/interview/sessions                   Interview history (own sessions)
GET  /api/v1/interview/sessions/{id}              One interview
POST /api/v1/interview/sessions/{id}/answer       Submit an answer (text or voice)
POST /api/v1/interview/sessions/{id}/complete     End the interview + final evaluation

POST /api/v1/pressure/sessions                    Start a pressure/nervousness training session
GET  /api/v1/pressure/sessions                    Pressure session history (own sessions)
GET  /api/v1/pressure/sessions/{id}               One pressure session
POST /api/v1/pressure/sessions/{id}/answer        Submit an answer under pressure conditions
POST /api/v1/pressure/sessions/{id}/complete      End the session + final evaluation

GET  /api/v1/progress/overview                          Overview: counts, performance, strengths/weaknesses, top recommendations
GET  /api/v1/progress/skills                            Per-category cybersecurity skill + CTF activity breakdown
GET  /api/v1/progress/trends?period=7d|30d|90d          Historical score series per dimension (technical/communication/interview/pressure/overall)
GET  /api/v1/progress/weaknesses                        Detected weaknesses (evidence-backed)
GET  /api/v1/progress/recommendations?active_only=bool  Active (or all) recommendations
POST /api/v1/progress/recommendations/{id}/complete     Mark a recommendation complete (ownership-checked)
POST /api/v1/progress/recalculate                       Rebuild derived progress data + personal AI profile
GET  /api/v1/progress/activity                          Recent activity across every module
GET  /api/v1/progress/profile                           The authenticated user's personal AI profile
```

All endpoints above except the two health/status checks require
authentication. All future endpoints are added under the versioned
`/api/v1` prefix. Interactive docs are available at
`http://localhost:8000/docs` while the backend is running.

## Step 11 — Progress & Personal AI Profile

Long-term progress tracking built entirely on top of existing session data
from Steps 5-10 -- nothing here invents a metric that isn't actually stored.

**Architecture**

```text
Existing Sessions (practice/ctf/communication/interview/pressure)
        v
aggregation_service   -- deterministic reads of raw session data
        v
weakness_service       -- deterministic weakness/strength detection
        v
recommendation_service -- deterministic, evidence-based recommendations
        v
profile_service        -- deterministic profile + optional AI narrative
        v
progress_service        -- facade used by the /progress routes
```

**Thresholds (documented, not arbitrary)** -- see
`app/services/progress/aggregation_service.py`:
- A category/topic/dimension is **weak** when its average score is below 60
  AND it has at least 3 attempts.
- It's **strong** at an average of 80+ with at least 3 attempts.
- Fewer than 3 attempts is always **developing** -- a single bad (or good)
  session never classifies anything.
- Severity within the weak range: <40 = high, 40-49 = medium, 50-59 = low.

**What's real vs. derived.** `practice_sessions`, `communication_sessions`,
`interview_sessions`, and `pressure_sessions` all have real numeric scores
and are the primary signal for their respective profile sections.
`ctf_sessions` have **no numeric score** (see `app/models/ctf.py`), so CTF
only ever contributes completion-rate/hint-usage signals -- never a
fabricated score.

**MongoDB collections** (all derived/cached from the session collections
above -- never a primary source of truth):
- `learning_progress` -- one document per (user, cybersecurity skill/category)
- `user_weaknesses` -- detected weaknesses with supporting evidence
- `recommendations` -- evidence-based, explains-why recommendations, with completion tracking
- `personal_profiles` -- one document per user: technical/communication/interview/pressure
  profile sections, learning preferences, recent/recommended focus, and an
  optional AI-generated narrative summary

Indexes: `learning_progress` (`user_id`+`skill`, unique), `user_weaknesses`
(`user_id`+`area`+`skill`+`source`), `recommendations` (`user_id`+`completed`,
`user_id`+`created_at`), `personal_profiles` (`user_id`, unique).

**Recalculation.** `GET /progress/overview`, `/skills`, `/weaknesses`, and
`/recommendations` all refresh the cached deterministic collections on every
read (cheap Mongo aggregation, no AI call), so the dashboard is never stale
just because nobody hit recalculate. `POST /progress/recalculate` is the only
endpoint that also calls the AI service, to produce the personal profile's
optional natural-language summary -- it is given only the already-computed
deterministic profile (never raw session history) and is explicitly
instructed not to invent numbers or make psychological/diagnostic claims. If
the AI call fails or returns invalid output, `ai_summary` is simply `null` --
the deterministic profile is always complete and usable on its own.

**Personal Mentor Context.** The mentor chat (`POST /api/v1/mentor/chat`)
now optionally personalizes its system prompt with a small, compact context
object built from the user's profile (technical level, strong/weak areas,
recent focus, recommended focus -- never raw session history). This is
best-effort: if the profile can't be loaded for any reason, the mentor
behaves exactly as it did before Step 11.

**Security.** Every progress endpoint uses the existing authenticated-user
dependency; the user always comes from the JWT (`current_user.id`), never
from a request parameter. There is no `user_id` a client can pass to read or
modify someone else's progress, weaknesses, recommendations, or profile.

**Empty/insufficient-data states.** A new user sees "Start practicing to
build your personal progress profile" rather than a 0%/"Weak" dashboard.
Trend series report `insufficient_data` (never a fabricated
improving/declining label) until there are at least two distinct weekly data
points.

**Known limitation.** Progress is not automatically recalculated the instant
a session completes elsewhere (practice/CTF/communication/interview/pressure
routes were not modified, per the Step 11 instruction to avoid touching
working Step 5-10 functionality unless required). Instead, the read
endpoints (`overview`/`skills`/`weaknesses`/`recommendations`) always
refresh the deterministic data live, so this only affects the AI-generated
profile summary, which updates when `POST /progress/recalculate` is called
(and the frontend's Progress page exposes a "Recalculate" button for this).

**Testing:** `cd backend && pytest tests/test_progress.py -v` (uses the same
`mongomock` + dependency-override pattern as the rest of the suite; the AI
service is always a scripted fake, never a real Gemini call).

## Project status

**Completed:** Step 1 — Project Foundation & Architecture, Step 2 —
Authentication, Step 3 — Gemini AI Engine, Step 4 — AI Cybersecurity Mentor
chat, Step 5 — Cybersecurity Learning & Practice System, Step 6 — CTF &
Practical Lab Mentor, Step 7 — Real-Life Communication Coach, Step 8 — Voice
& Speaking Analysis, Step 9 — Cybersecurity Interview Simulator, Step 10 —
Pressure & Nervousness Training, Step 11 — Progress & Personal AI Profile.

**Not yet implemented:** production deployment/Docker/CI-CD, an admin
dashboard, and conversation persistence for the general Mentor chat (the
Mentor's chat history still lives in frontend state only). These arrive in
Step 12 or later.
