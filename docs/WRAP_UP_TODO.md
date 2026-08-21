# NOVA V4 Wrap-Up TODO

Goal: ship a clean, correct, small-scope deployment. Prioritize completed, predictable behavior over additional companion features.

**Status (2026-08-21):** All items below are complete. V4 scope tracker: [`V4_SCOPE.md`](V4_SCOPE.md).

## 1. Finish the memory migration

Decide and implement one release contract before any new feature work.

- Recommended: retain or migrate factual personal memories and add bounded, relevant retrieval.
- Alternative: make V4 an intentional clean-slate release; add a migration/version check, document the reset, and remove every residual legacy-table reference.
- Chosen for V4: intentional clean slate. Legacy `personal_memories` rows are quarantined as `legacy_personal_memories_v3*` and are not read by the V4 runtime.
- Do not ship with old personal-memory records silently retained but unreachable.

## 2. Make chat failure-safe and serialize turns per user

- Add a keyed, single-process per-user turn guard covering prepare, generation, and finalize for both synchronous and streaming chat.
- Define duplicate-turn behavior: queue it or return a clear `409` response.
- Emit structured SSE error events for streaming failures and render them in the frontend.
- Add tests for same-user overlap, pre-stream failure, mid-stream failure, and disconnect/cancellation.

## 3. Define the deployment contract and smoke-test it

- Document production backend/frontend commands and required environment variables.
- Document persistent SQLite storage, backup/restore, CORS origins, and frontend API configuration.
- Ensure production does not depend on localhost rewrites.
- Run an end-to-end production-like check: register, onboard, stream chat, refresh, and sign in again. (`scripts/smoke_release_e2e.py`)

## 4. Fix release-facing correctness and safety edges

- Return a non-2xx response when the health probe cannot reach SQLite.
- Add size limits for chat text, TTS text, and audio uploads.
- Use structured server logging instead of printing tracebacks in request handlers.
- Disable voice for the first deployment unless upload, timeout, and error behavior are verified.

## 5. Decide the chat-history experience

- Recommended: add a minimal authenticated endpoint for recent conversations and restore the transcript after refresh.
- If omitted, explicitly document the release boundary: memory persists, but the visible transcript does not.

## 6. Remove or quarantine dead code and stale claims

- Delete unused helpers and subscription-tier scaffolding, or move them to future notes.
- Remove stale legacy-memory references.
- Make README and architecture claims match the memory behavior actually shipped.

## 7. Make checks repeatable and release-gated

- Configure non-interactive ESLint; replace deprecated `next lint`.
- Require backend tests, frontend lint/type checks, frontend production build, and an authenticated API smoke test before release.

## Deferred from V4

Do not build interaction-style calibration or LLM-written situation-specific curiosity for this release. Both introduce further inference, persistence, and follow-up paths while the existing memory and streaming paths still need closure.

Keep only the narrowed concurrency item: a single-process per-user turn guard. It is correctness work, not scale optimization.
