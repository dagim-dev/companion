# ADR 0001: Multi-user SQLite with JWT and ContextVar scoping

**Date:** 2026-06-05  
**Status:** Accepted  
**Commit:** `7da92cc`

## Context

V1 was a single-user companion: monolithic `api.py`, one global session per server process, fixed personality in `llm.py`, and no authentication. The goal for V2 was to support multiple registered users with isolated memory and customizable companion roles, while keeping the existing flat Python domain layout (~40 root-level modules).

Several storage and architecture options were on the table:

- Migrate to PostgreSQL or add a vector DB (Chroma, Pinecone) for memory recall
- Restructure into a `backend/` package with a formal service layer
- Add persisted multi-thread chat with `thread_id`
- Design for horizontal scaling from the start

## Decision

Add multi-user support with minimal disruption to existing domain code:

1. **JWT auth** — `auth_jwt.py` + `auth_store.py`; register/login endpoints; Bearer token on protected routes.
2. **Per-user session** — `state_store.py` caches one `NovaState` per `user_id` (in-memory, 1-hour TTL).
3. **SQLite scoping** — Add `user_id` column to all data tables; use `memory_scope.user_scope()` ContextVar so domain helpers (`get_profile()`, etc.) need no signature changes.
4. **API restructure** — Move from monolithic `api.py` to `api/` package with `/v1/*` routers; keep `api.py` as a uvicorn shim.
5. **Personality** — YAML role templates in `prompts/roles/`, slider preferences, `prompt_builder.py` (six roles).

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| Vector DB for memory | Overkill for local/personal use; existing embedding-in-SQLite recall works at current scale |
| PostgreSQL | Adds deployment complexity; SQLite + WAL handles current concurrency |
| `backend/` restructure | High churn across imports with no functional benefit for a solo project |
| Persisted multi-thread chat | Deferred; `thread_id` accepted as no-op placeholder |
| Parameter threading (`user_id` everywhere) | Would require rewriting every DB helper and engine call site |

## Consequences

**Positive:**

- Domain modules stayed at repo root; turn pipeline unchanged in structure.
- Existing V1 SQLite data migratable via one-shot scripts (`migrations/001`, `002`).
- Clear separation: auth crypto (`auth_jwt.py`), auth persistence (`auth_store.py`), HTTP wiring (`api/deps.py`).

**Negative:**

- ContextVar must be set in every route handler and worker thread — forgetting it causes cross-user data leaks or errors.
- In-memory `NovaState` does not survive restarts or work across multiple Uvicorn workers without sticky sessions or external state.
- SQLite write contention under concurrent threads (mitigated by per-call connections, WAL mode, 30s busy timeout).

## References

- Commit `7da92cc` — V2 update
- Recovered notes: `git show 9ca0cde:V1_IMPLEMENTATION_NOTES.md`
