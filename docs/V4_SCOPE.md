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
| Memory improvements | planned | Recall, extraction, follow-ups, persistence — details TBD |
| Session / concurrency | planned | Per-user turn serialization, scaling prep — see `Future change1.md` |
| API & UX polish | planned | Endpoints, onboarding, settings — as needed for V4 release |

## Out of scope (for now)

- Database migration for existing `memory.db` rows (`general_jarvis` → `general_nova`) — fresh DB expected
- Changes to `prompts/core.py` feminine persona framing unless explicitly reopened

## Release target

Merge `feature/v4-nova` → `main` when the items above are complete and verified. Scope changes should be reflected in this file and `CHANGELOG.md`.
