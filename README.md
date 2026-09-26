# AI Cybersecurity Personal Mentor

An AI-powered cybersecurity learning and communication platform designed to help users practice cybersecurity concepts, CTF/lab scenarios, interviews, communication, voice responses, and performance under pressure.

## Project Status

### Completed Steps

1. Project Foundation & Architecture
2. Authentication
3. Gemini AI Engine
4. AI Cybersecurity Mentor / Chat
5. Cybersecurity Learning & Practice
6. CTF & Practical Lab Mentor
7. Real-Life Communication Coach
8. Voice & Speaking Analysis
9. Cybersecurity Interview Simulator
10. Pressure & Nervousness Training

---

# Step 10 — Pressure & Nervousness Training

The Pressure & Nervousness Training system provides realistic interview and communication practice under increasing levels of pressure.

The purpose of this feature is to help users become more comfortable answering questions when facing:

* Limited preparation time
* Time limits
* Unexpected questions
* Rapid follow-up questions
* Difficult questions
* Topic changes
* Interviewer interruptions
* Ambiguous scenarios
* Incomplete information
* Pressure to explain clearly
* Unfamiliar cybersecurity scenarios

The system is a communication and performance training tool.

It is **not a medical or psychological diagnostic system**.

---

## Pressure Levels

The system provides five pressure levels.

### Level 1 — Friendly

Designed for basic pressure practice.

Characteristics:

* Relaxed questions
* Generous response time
* Supportive interviewer behavior
* No interruptions
* Predictable topics

Purpose:

Build familiarity with answering questions under mild pressure.

---

### Level 2 — Standard

Provides a more realistic interview experience.

Characteristics:

* Realistic interview questions
* Moderate time limits
* Occasional follow-up questions
* Normal interviewer behavior

---

### Level 3 — Challenging

Introduces more demanding interview conditions.

Characteristics:

* Harder questions
* Shorter response time
* Unexpected follow-ups
* Topic switching
* More detailed explanations

---

### Level 4 — High Pressure

Introduces stronger but professional pressure.

Characteristics:

* Short response times
* Unexpected questions
* Rapid follow-ups
* Difficult scenarios
* Occasional interruptions
* Ambiguous situations

The interviewer remains professional.

The system does not use insults, harassment, humiliation, threats, or personal attacks.

---

### Level 5 — Interview Simulation

Provides a realistic interview-style experience.

The simulation can include:

* Introduction
* HR questions
* Technical questions
* Cybersecurity scenarios
* Follow-up questions
* Behavioral questions
* Difficult questions
* Closing questions

The existing Step 9 interview system is reused instead of creating another interview engine.

---

# Pressure Conditions

Pressure conditions can include:

## Time Pressure

Users may receive a limited amount of time to answer.

Example:

```text
You have 45 seconds to answer.
```

The frontend displays the remaining time when a time limit is active.

When the timer expires, the interface clearly indicates:

```text
Time's up
```

An entered answer is not silently discarded.

The backend also validates timing where practical rather than relying exclusively on the frontend timer.

---

## Rapid Follow-Ups

The interviewer may immediately ask follow-up questions such as:

```text
Why?
```

```text
Can you give a practical example?
```

```text
What would you do first?
```

---

## Topic Switching

The system can unexpectedly move between cybersecurity topics.

Example:

```text
Networking → Linux → Web Security
```

---

## Difficult Questions

Questions can be adjusted above the user's current difficulty level to provide additional challenge.

---

## Interruptions

The interviewer may occasionally interrupt the user's response.

Example:

```text
Sorry, let me stop you there. What is the main point?
```

Interruptions are used sparingly and remain professional.

---

## Ambiguous Questions

The user may receive scenarios where assumptions are incomplete.

The goal is to encourage the user to clarify assumptions before responding.

---

# Text Mode

Users can answer pressure-training questions using text responses.

The system records the response and evaluates available communication and technical information.

---

# Voice Mode

Voice mode reuses the existing Step 8 voice system.

The pressure-training voice flow is:

```text
MediaRecorder
    ↓
Existing STT
    ↓
Transcript
    ↓
Existing Communication / Interview Evaluation
    ↓
Existing Voice Analysis
```

The project does not create another Whisper/STT implementation or another TTS system for Step 10.

---

# Performance Indicators

The system uses observable communication indicators rather than attempting to determine a user's psychological state.

Possible indicators include:

* Filler-word count
* Pause count
* Average pause duration
* Speaking rate
* Response length
* Self-corrections
* Repeated phrases
* Incomplete sentences
* Response duration

Example:

```text
Speaking Rate
132 WPM

Filler Words
3

Response Time
41 sec
```

Metrics are only displayed when the relevant data is actually available.

The system does not invent missing audio metrics.

---

# Nervousness and Pressure Feedback

The system must not claim that it can diagnose or scientifically determine nervousness or anxiety.

Feedback is expressed as observable communication information.

Examples:

```text
Your speaking rate increased during the high-pressure section.
```

```text
You used more filler words during rapid follow-up questions.
```

```text
You had longer pauses on scenario-based questions.
```

The system does not make conclusions such as:

```text
You became anxious.
```

```text
You were nervous.
```

```text
You have anxiety.
```

---

# Self-Reported Difficulty

After completing a session, users can optionally report how the session felt.

Available options:

```text
Easy
Manageable
Challenging
Very Difficult
```

Users can also provide optional text explaining what made the session difficult.

This information is stored as:

```text
self_reported_difficulty
```

Self-reported difficulty is kept separate from observable communication indicators.

---

# Performance Evaluation

After completing a pressure-training session, the system can provide:

```text
Performance Under Pressure
```

with metrics such as:

* Overall score
* Technical score
* Communication score
* Pressure Performance
* Clarity score
* Response Control score

Example:

```text
Performance Under Pressure
76 / 100

Technical
80

Communication
74

Pressure Performance
72
```

The pressure-related score represents performance during the training scenario.

It is **not a clinical or psychological measurement**.

---

# Observed Indicators

The results page can display observations such as:

```text
Speaking rate increased during rapid questions.

More filler words appeared during difficult questions.

Responses became shorter under time limits.
```

These are communication/performance observations and do not identify psychological causes.

---

# Comparison With Normal Practice

When relevant historical practice data is available, the system can compare normal practice with pressure practice.

Example:

```text
Normal Practice
Speaking Rate: 128 WPM
Filler Words: 2

Pressure Practice
Speaking Rate: 145 WPM
Filler Words: 5
```

Possible comparison metrics include:

* Speaking rate
* Filler words
* Response length
* Pause patterns
* Technical score
* Communication score

The comparison represents an observed difference between practice sessions.

If there is not enough historical information, the system does not pretend that a baseline exists.

Instead it can report:

```text
No baseline available yet.
```

---

# Session History

Pressure-training sessions are stored separately from the existing interview sessions.

The history view can show:

```text
Date
Pressure Level
Mode
Score
Difficulty
```

Selecting a session displays its results.

The Step 10 history system does not create the global progress dashboard.

---

# Database

Pressure training uses a dedicated collection:

```text
pressure_sessions
```

A pressure session contains information such as:

```text
user_id
pressure_level
mode
source
difficulty
status
started_at
completed_at
total_questions
current_question
responses
metrics
evaluation
self_reported_difficulty
```

Appropriate indexes are maintained for:

```text
pressure_sessions.user_id
pressure_sessions.started_at
pressure_sessions.status
pressure_sessions.pressure_level
```

The existing `interview_sessions` collection is not modified in a way that breaks Step 9.

---

# API

Pressure-training APIs are available under:

```text
/api/v1/pressure
```

## Configuration

```http
GET /api/v1/pressure/config
```

Returns available pressure levels and supported modes.

## Start Session

```http
POST /api/v1/pressure/sessions
```

Starts a new pressure-training session.

## Get Session

```http
GET /api/v1/pressure/sessions/{session_id}
```

Returns the current user's pressure-training session.

Session ownership is enforced.

## Submit Response

```http
POST /api/v1/pressure/sessions/{session_id}/response
```

Stores and evaluates a response and generates the next interaction.

## Complete Session

```http
POST /api/v1/pressure/sessions/{session_id}/complete
```

Completes the session and generates the final evaluation.

## Session History

```http
GET /api/v1/pressure/sessions
```

Returns pressure-training sessions belonging to the authenticated user.

---

# Architecture

The Step 10 architecture reuses the existing systems:

```text
React
  ↓
FastAPI
  ↓
Pressure Service
  ├── Pressure Engine
  ├── Interview Service
  ├── Communication Service
  ├── Voice Service
  └── Existing AI Service
          ↓
        Gemini
```

The project does not create duplicate implementations of:

* Gemini
* Whisper/STT
* TTS
* Authentication
* Interview logic
* Communication analysis

---

# Security

Pressure training follows the application's existing authentication architecture.

Security requirements include:

* JWT authentication
* Session ownership validation
* Input validation
* Safe error handling
* No client-provided user identity
* No API keys in the frontend
* No secrets in frontend code
* No internal AI prompts exposed to users
* No production stack traces returned to clients

---

# Privacy and Limitations

Pressure Training processes communication and performance information required for the training experience.

The feature should only store metrics that actually exist.

The system does not claim to determine:

* Anxiety
* Clinical nervousness
* Mental-health conditions
* Psychological state
* Personality
* Scientific confidence levels

The system provides communication and performance observations.

For example:

```text
Your response contained several long pauses.
```

is an observable communication statement.

It should not be converted into:

```text
You have interview anxiety.
```

The feature is intended for practice and self-improvement, not medical or psychological assessment.

---

# Testing

Step 10 includes backend tests for:

### Configuration

* Valid pressure levels
* Invalid pressure levels
* Configuration responses

### Sessions

* Authenticated session creation
* Unauthenticated requests
* Invalid configuration
* Session ownership

### Responses

* Valid responses
* Empty responses
* Timing handling
* Pressure rules

### Completion

* Session completion
* Final evaluation
* Self-report storage

### Comparison

* Baseline available
* Baseline unavailable
* Comparison calculation

### Voice

Existing voice services are mocked during automated tests.

Actual Whisper/STT processing is not required for normal automated tests.

### AI

Gemini is mocked during automated tests.

Automated tests do not call the real Gemini service.

---

# Frontend Verification

The Pressure Training feature should verify:

1. Login works
2. Pressure Training page loads
3. Pressure levels display
4. Session setup works
5. Session starts
6. Timer works
7. Text responses work
8. Voice responses use the existing Step 8 system
9. Pressure conditions work
10. Session completion works
11. Evaluation appears
12. Self-report works
13. Comparison works when a baseline exists
14. History works
15. Existing interview system works
16. Existing communication system works
17. Existing voice system works
18. Existing cybersecurity mentor works
19. Existing CTF functionality works

---

# Step 10 Scope

Step 10 implements only Pressure & Nervousness Training.

The following are intentionally **not implemented as part of Step 10**:

* Medical or psychological diagnosis
* Anxiety diagnosis
* Mental-health scoring
* Personality assessment
* Long-term weakness engine
* Global progress dashboard
* Personal AI memory
* Resume analysis
* Job matching
* External job APIs
* Recruiter integrations
* OTP
* MFA
* Password reset
* Admin dashboard

These features belong to later development stages.

---

# Existing Features

Step 10 is designed to extend the existing application without replacing working functionality from Steps 1–9.

Existing systems remain available:

* AI Cybersecurity Mentor
* Cybersecurity Learning & Practice
* CTF & Practical Lab Mentor
* Real-Life Communication Coach
* Voice & Speaking Analysis
* Cybersecurity Interview Simulator
* Authentication
* Gemini AI Engine

---

# Development Principle

The project follows this approach for Step 10:

```text
Inspect
   ↓
Implement
   ↓
Test
   ↓
Verify Existing Features
   ↓
Update Documentation
   ↓
Stop
```

Step 10 does not start Step 11 functionality.

---

# Technology Stack

### Frontend

* React
* TypeScript
* Existing frontend state/routing architecture
* Existing voice components

### Backend

* FastAPI
* Python
* Existing authentication architecture
* Existing AI services

### Database

* MongoDB

### AI

* Existing Gemini AI integration

### Voice

* Existing Step 8 voice/STT/TTS architecture

---

# Project Structure — Step 10

```text
backend/
└── app/
    ├── api/
    │   └── routes/
    │       └── pressure.py
    ├── models/
    │   └── pressure.py
    ├── schemas/
    │   └── pressure.py
    └── services/
        └── pressure/
            ├── pressure_service.py
            ├── pressure_config.py
            ├── pressure_engine.py
            ├── evaluation_service.py
            └── prompts.py

frontend/
└── src/
    ├── pages/
    │   ├── PressureTraining.tsx
    │   └── PressureSessionPage.tsx
    └── features/
        └── pressure/
            ├── PressureSetup.tsx
            ├── PressureLevelCard.tsx
            ├── PressureSession.tsx
            ├── PressureTimer.tsx
            ├── PressureQuestion.tsx
            ├── PressureResponse.tsx
            ├── PressureIndicator.tsx
            ├── PressureResult.tsx
            ├── PressureComparison.tsx
            └── SelfReport.tsx
```

---

# Step 10 Completion

Step 10 provides a dedicated environment for practicing cybersecurity interviews and communication under increasing levels of pressure.

It combines:

* Pressure scenarios
* Timed responses
* Follow-up questions
* Topic changes
* Difficult questions
* Professional interruptions
* Text responses
* Voice responses
* Communication indicators
* Performance evaluation
* Self-reported difficulty
* Historical comparison
* Session history

The system focuses on observable communication and performance information and does not diagnose anxiety, nervousness, mental-health conditions, or personality.

---

## Current Development Status

**Step 10 — Pressure & Nervousness Training: Implemented**

Next development work should follow the project's planned step sequence and should not be started as part of Step 10.
