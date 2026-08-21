# V4 Scope (living document)

This file tracks the intended scope for **Version 4**. Items may be added, removed, or reprioritized as work progresses.

## Status key

- **done** — shipped on `feature/v4-nova`
- **in progress** — actively being worked on
- **planned** — intended for V4, not started
- **deferred** — moved out of V4 (note why)

## V4 scope

| Area | Status | Notes |
|------|--------|-------|
| NOVA rebrand | done | Rename Jarvis → NOVA; neutral addressing; `NovaState` / `general_nova`; frontend `nova-*` theme |
| Memory migration | done | V4 ships as an intentional clean-slate release for legacy `personal_memories`: startup quarantines old rows under `legacy_personal_memories_v3*`, docs call out the reset, and the runtime only relies on current conversations/reflections/insights/learned preferences. |
| Turn correctness | done | Added a single-process per-user turn guard for sync and streaming chat, duplicate-turn `409` responses, structured SSE `error` events, frontend rendering, and focused overlap/failure/cancellation tests. |
| Release polish | done | Production docs, health/error handling, request-size limits, voice-off default, chat-history restore, non-interactive ESLint, backend tests, frontend build, and production-like browser smoke test (`scripts/smoke_release_e2e.py`) verified. |
| Interaction style calibration | deferred | Useful future personalization, but adds inference, persistence, and follow-up paths that are not needed for a clean V4 release. |
| Situation-specific curiosity | deferred | Useful future enhancement; existing curiosity behavior is sufficient for V4 while core memory and streaming behavior are completed. |


## Release target

Merge `feature/v4-nova` → `main` when the items above are complete and verified. Scope changes should be reflected in this file and `CHANGELOG.md`.

## Deferred ideas (2026-08-21)

These ideas remain worthwhile, but are intentionally out of V4 so the release can close around correctness and deployment polish:

- **Interaction style calibration** — Complements async `learned_preferences` extraction with explicit, in-the-moment calibration when heuristics detect uncertainty or mismatch. Revisit after the core memory contract is stable.
- **Situation-specific curiosity** — Replace fixed curiosity wording with policy-gated LLM wording only when needed. Revisit after V4 is deployed and existing follow-up behavior has been observed.

The broader concurrency roadmap remains documented in [`Future change.md`](../Future%20change.md); it is not V4 scope.
