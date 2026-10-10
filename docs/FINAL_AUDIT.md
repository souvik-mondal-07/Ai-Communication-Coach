# Final audit — Step 20

Scope: audit of the existing code, fixes for confirmed defects, documentation, regression tests.
No features, frameworks or providers were added. Nothing was committed (the archive has no `.git`).

## Project status

| Area | Status | Basis |
|---|---|---|
| Architecture | PASS | React reaches only the backend (`services/`); the built bundle has no Gemini/JWT/Mongo references |
| Authentication | PASS | Argon2; token-version revocation; full invalid-token matrix tested |
| Authorization | PASS | Ownership enforced in every service; two-user isolation test across 35 GET endpoints + cross-user write probes. mongomock only |
| Database | NEEDS ATTENTION | Outage handling, recovery and indexes verified against mongomock and a real server boot *without* MongoDB. **Never run against a real MongoDB** |
| AI and voice | NOT VERIFIED (live) | Logic and failure paths pass with mocked Gemini/STT/TTS (incl. transcript kept when Gemini fails). No live Gemini, STT, TTS or microphone was available |
| Cybersecurity features | PASS (mocked AI) | One concurrency defect found and fixed (CTF hints) |
| Communication and interviews | PASS (mocked AI) | Existing suites pass; double-submit/idempotency tests exist |
| Analytics | PASS (tests) | Derived from stored sessions at read time; insufficient-data states tested |
| Daily practice and notifications | PASS (tests) | Deterministic planner (no Gemini); dedupe keys + TTL index |
| Frontend | NEEDS ATTENTION | Type check, 148 tests, build pass. Responsive layout and visual accessibility **not checked** (no browser) |
| Documentation | PASS | README and `.env.example` verified against `Settings` in both directions |
| Production readiness | NOT VERIFIED | See "Remaining limitations" |

## Findings and changes

**JWT same-second invalidation (confirmed, reproduced).** My first revocation design compared the token's whole-second `iat` with a
fractional `password_changed_at`; a token issued earlier in the same second as the change was still accepted (HTTP 200
reproduced before the fix). Replaced by a per-user `token_version`: embedded in every token (`tv`), incremented atomically
together with the new hash, compared exactly. For accounts that never changed their password, tokens without `tv` count as
version 0, so their existing sessions keep working until the password changes. Two existing tests were updated to this contract (see below).

**Upgrading from the earlier Step 20 build (`password_changed_at`, no `token_version`).** Reading a missing `token_version` as 0
would have made tokens that build had revoked valid again (reproduced: HTTP 200). `auth_service.effective_token_version` now treats a
record with a non-null `password_changed_at` and no `token_version` as version 1, used by both token validation and login, and
`migrate_legacy_token_versions` persists it (idempotent, conditional; runs in the startup setup steps and before the `$inc` in
`update_password`). Consequence: those accounts' pre-upgrade tokens — including ones the old build issued *after* the change, which
cannot be told apart from revoked ones without trusting `iat` — are rejected, so each such user signs in once more. Accounts that
never changed their password are unaffected. Databases created from the original step19 code have no `password_changed_at` and need no migration.

Other fixes: `av>=16.1,<19` (av 19 breaks faster-whisper 1.2.1 transcription); production refuses a missing/weak JWT secret or
wildcard CORS; HMAC-only JWT algorithms; login timing equalised for unknown emails; request-body size limit (413, also for
chunked bodies); `page` capped; AI history character budget; MongoDB client kept and auto-recovering, DB outage = 503, setup
retried in the background; `/ai/chat` and API docs not exposed in production; CTF hint recording made atomic (concurrent
requests recorded a hint twice and double-counted `hints_used`); frontend clears all per-user stores on logout/401/user switch
and stores the fresh token after a password change; one unlabeled input (CTF flag) got an `aria-label`.

**Existing tests changed (not weakened).**
`test_profile::test_user_stays_logged_in_after_changing_password` reused the *old* token after a change and expected 200. It had
only passed because of the same-second flaw. It now asserts the fresh token works **and** the old one is rejected.
`test_security::test_token_payload_holds_only_subject_and_times` is still an exact allow-list; it now also allows the integer `tv`.

**Removed setup scripts — decision: obsolete.** `scripts/seed_data.py` and `scripts/setup_db.py` were Step 1 stubs whose only
behaviour was printing "placeholder — no logic implemented yet" (originals remain in the step19 archive). Nothing referenced
them (code, tests, README). Their intended jobs — create indexes, seed starter data — run on every backend start,
idempotently (`ensure_indexes`, `$setOnInsert` upserts, retried if MongoDB is down at boot). No replacement is needed. Git history
could not be consulted (no `.git`), so this rests on the file contents and the reference search.

## Verification (commands executed)

| Check | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest` in 3 chunks (32 test files) | **1,257 passed, 0 failed, 0 skipped** (237 + 402 + 618) |
| Frontend tests | `npx vitest run` | **148 passed** (16 files) |
| Type check | `npx tsc -b` | exit 0 |
| Lint | `npx oxlint` | 0 errors, 11 stylistic warnings (pre-existing `set-state-in-effect`) |
| Production build | `npm run build` | success; 0 secret/config references in `dist` |
| Real server boot, no MongoDB | `uvicorn app.main:app` | health reports DB down; data route 503; 2 MB body 413; protected route 401 |
| Production boot, weak secret | `APP_ENV=production JWT_SECRET_KEY=short` | refuses to start |
| Mutation checks | disabled each fix, re-ran its tests | revocation, timing, body-limit tests all fail without the fix |

Security matrix covered in `tests/test_security.py` + `tests/test_final_audit.py`: unauthenticated access; expired, malformed,
unsigned (`alg=none`), tampered and wrong-secret JWTs; same-second invalidation; cross-user sessions, notifications, history,
voice sessions, audio tokens, daily-practice linking; unauthorized profile/password change; invalid ObjectIds; oversized and
chunked bodies; invalid pagination; malformed JSON; audio upload limits; missing/weak production configuration.
**Not applicable:** document upload and path traversal — the project has no document/resume upload (only audio endpoints, tested).

## Remaining limitations and unperformed checks

- Not run against a real MongoDB (TTL expiry, index builds, very large `skip`).
- No live Gemini, STT, TTS or microphone test; the end-to-end journey ran only through the mocked `test_e2e_journey.py`.
- Responsive layout, contrast and keyboard navigation not checked in a browser; accessibility was a static scan only.
- Performance not measured.
- Git: no repository in the archive, so `git status/log/diff` and tracked-file checks could not be run. Changes were compared against the
  step19 archive instead. No history was examined, so a previously committed secret cannot be ruled out; a scan of the current tree found none.
- Logout cannot revoke a token (until expiry or a password change). No login rate limiting beyond Argon2 cost.
- Foreign resources return 403 vs 404 for missing ones (ID existence inferable; no data exposed).
- Spoken-reply audio is cached in process memory: run a single backend worker.
- JWT is kept in `localStorage` (mitigated: no raw-HTML rendering anywhere).
- Narrow check-then-act patterns elsewhere were not exhaustively reviewed; only the CTF hint race was found and fixed.

## Git status

No `.git` in the provided archive, so this cannot be reported. Nothing was committed or pushed; all changes are uncommitted file edits.
