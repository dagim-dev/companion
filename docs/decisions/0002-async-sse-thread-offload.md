# ADR 0002: Async SSE with asyncio.to_thread offloading

**Date:** 2026-06-11  
**Status:** Accepted  
**Commit:** `0a673df`

## Context

`/v1/chat/stream` is an async SSE endpoint, but the turn pipeline underneath is synchronous:

- `prepare_turn()` — SQLite reads/writes, memory decay, embeddings, reflection updates
- `stream_llm_tokens()` — sync OpenAI HTTP streaming
- `finalize_response()` — post-processing, DB writes, episode summarization

When these ran directly inside the async generator, they blocked the asyncio event loop for the entire request. Health checks, auth, and other concurrent streams on the same Uvicorn worker were starved.

The sync `/v1/chat` route was less affected because FastAPI runs sync handlers in a thread pool. The streaming route looked non-blocking but was not.

## Decision

**Option B:** Keep the endpoint async; offload blocking work via `asyncio.to_thread()` in `api/routers/chat.py`:

| Phase | Approach |
|-------|----------|
| `prepare_turn()` | `await asyncio.to_thread(...)` with `user_scope(user_id)` set inside the worker |
| Token streaming | One `asyncio.to_thread(next, ...)` per token |
| `finalize_response()` | `await asyncio.to_thread(...)` with `user_scope(user_id)` set inside the worker |

SSE event shape and order are unchanged: `token` events, then a single `done` event with `content`, `intent`, and `emotion`.

## Alternatives considered

| Option | Summary | Why rejected |
|--------|---------|--------------|
| **A — Sync stream endpoint** | Change `async def` to `def`; FastAPI offloads whole handler | Gives up async routing style; still caps at thread-pool size with no incremental path |
| **B — asyncio.to_thread()** | Keep async SSE; offload blocking phases explicitly | **Chosen.** Fixes starvation without rewriting memory/LLM layers |
| **C/E — Worker queue** | Celery, Redis, arq, or dedicated turn-engine service | Requires session persistence and job infra not present yet |
| **D — Full async rewrite** | AsyncOpenAI, async DB, async generators end-to-end | Touches most of the repo with high regression risk; no broad test suite at the time |

Decision criteria that favored B: preserve behavior and SSE contract, minimal scope (router-level only), fast to ship and verify, incremental (later options remain available).

## Consequences

**Positive:**

- Event loop responsive during chat streams; health and auth stay usable under load.
- `message_processor.py`, `llm.py`, and `memory.py` remain synchronous — no cascade refactor.
- Regression tests in `tests/test_chat_stream_threading.py` cover offloading and event ordering.

**Negative (known limits):**

- Default asyncio thread pool (~40 workers) caps concurrent blocking turns per process.
- Shared in-memory `NovaState` is not thread-safe; overlapping streams for the same user can race.
- SQLite concurrent writes can contend under load.
- `ContextVar` must be set inside each worker thread, not only on the event-loop task.
- Time-to-first-token still dominated by sync `prepare_turn()` work.

Scaling beyond these limits is documented in [Future change1.md](../../Future%20change1.md) (Tier 1–4 roadmap).

## References

- Commit `0a673df`
- [Future change1.md](../../Future%20change1.md) — original tradeoff analysis
- `api/routers/chat.py`, `tests/test_chat_stream_threading.py`
