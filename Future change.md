# Future Changes — Companion Roadmap

> SSE threading decision recorded in [docs/decisions/0002-async-sse-thread-offload.md](docs/decisions/0002-async-sse-thread-offload.md). Scaling roadmap below remains living notes.

This document records architectural decisions and planned scaling work. It is a living roadmap, not an implementation spec.

---

## Async SSE Event-Loop Blocking (Option B)

### Problem

`/v1/chat/stream` is an async SSE endpoint, but the turn pipeline underneath it is synchronous:

- `prepare_turn()` — SQLite reads/writes, memory decay/consolidation, embeddings, reflection updates
- `stream_llm_tokens()` — sync OpenAI HTTP streaming
- `finalize_response()` — post-processing, DB writes, optional episode summarization

When these ran directly inside the async generator, they blocked the asyncio event loop for the entire request. That starved health checks, auth, and other concurrent streams on the same Uvicorn worker.

The sync `/v1/chat` route was less affected because FastAPI already runs sync `def` handlers in a thread pool. The streaming route looked non-blocking but was not.

### Solution implemented: Option B (`asyncio.to_thread()`)

Blocking work in `api/routers/chat.py` is offloaded to worker threads while the endpoint stays async:

| Phase | Approach |
|-------|----------|
| `prepare_turn()` | `await asyncio.to_thread(...)` with `user_scope(user_id)` set inside the worker |
| Token streaming | One `asyncio.to_thread(next, ...)` per token so the loop is free while waiting for model chunks |
| `finalize_response()` | `await asyncio.to_thread(...)` with `user_scope(user_id)` set inside the worker |

SSE event shape and order are unchanged: `token` events, then a single `done` event with `content`, `intent`, and `emotion`.

### Why Option B was chosen

Several fixes were considered. Option B was selected as the best balance for this codebase today.

| Option | Summary | Why not chosen (or deferred) |
|--------|---------|------------------------------|
| **A — Sync stream endpoint** | Change `async def` to `def`; FastAPI offloads the whole handler to a thread pool | Minimal diff, but gives up async routing style and still caps concurrency at thread-pool size with no path to incremental improvement |
| **B — `asyncio.to_thread()` wrapper** | Keep async SSE; offload blocking phases explicitly | **Chosen.** Fixes event-loop starvation without rewriting memory/LLM layers; preserves SSE contract and frontend compatibility |
| **C/E — Worker queue / separate process** | Celery, Redis, arq, or a dedicated turn-engine service | Correct for multi-worker production, but requires session persistence and job infra this project does not have yet |
| **D — Full async rewrite** | AsyncOpenAI, async DB, async generators end-to-end | Architecturally correct long-term, but touches most of the repo (`memory.py`, embeddings, recall) with high regression risk and no broad test suite yet |

**Decision criteria that favored B:**

1. **Preserve behavior** — No change to turn semantics, memory retrieval/storage, or frontend SSE contract.
2. **Minimal scope** — Router-level change only; `message_processor.py`, `llm.py`, and `memory.py` stay synchronous.
3. **Fast to ship and verify** — Focused tests can assert thread offloading, `user_scope` in workers, and unchanged event ordering.
4. **Incremental** — Each blocking phase can be offloaded independently; later options (C, D) remain available without throwing this work away.
5. **Honest trade-off** — Thread pools have limits, but that is an acceptable ceiling for current user count and deployment size.

**What B does not fix (known limits):**

- Time-to-first-token is still dominated by pre-LLM work in `prepare_turn()`; streaming only helps during generation.
- Default asyncio thread-pool size (~40 workers) caps concurrent blocking turns per process.
- A blocking sync OpenAI `next()` already running in a worker cannot be force-cancelled; only further token requests are avoided after disconnect.
- Shared in-memory `NovaState` per user (`state_store.py`) is not made thread-safe; overlapping streams for the same user can still race.

### Residual risks after Option B

| Area | Risk | Mitigation today |
|------|------|------------------|
| **SQLite** | Per-call connections (WAL + `busy_timeout`) avoid cross-thread connection reuse; concurrent writes can still contend or reorder | Acceptable at low concurrency; monitor lock waits |
| **`user_scope`** | `ContextVar` must be set inside each worker thread, not only on the event-loop task | Enforced in `_to_thread_with_user_scope()` and per-token helpers |
| **`NovaState`** | Same user, two concurrent streams mutate one shared object | No per-user lock yet; rare for single-tab usage |
| **OpenAI client** | Global sync `OpenAI` client shared across threads | Same pattern as sync `/v1/chat`; revisit if SDK thread-safety issues appear |

---

## Scaling Roadmap (as user count grows)

Work below is ordered roughly by when it becomes necessary. None of it is required for a single-worker local or low-traffic deploy.

### Tier 1 — Modest concurrency (tens of simultaneous streams, one worker)

**Triggers:** Other API routes feel sluggish during chat; thread-pool exhaustion under load tests.

| Work item | What | Why |
|-----------|------|-----|
| Per-user turn serialization | Mutex or async lock per `user_id` around prepare → stream → finalize | Prevents same-user overlapping streams from corrupting `NovaState`, conversation order, and `turn_count` |
| Dedicated executor for LLM work | Separate `ThreadPoolExecutor` with an explicit max size for chat turns | Isolates chat from other `to_thread` usage; makes concurrency tunable |
| Stream error SSE / HTTP errors | `try/except` around threaded phases with explicit client-facing errors | Sync `/chat` returns 500 with detail; stream path should fail predictably |
| Expanded tests | Same-user concurrent streams, slow LLM, client disconnect | Covers the main regression surfaces Option B introduces |
| Observability | Log turn phase durations, thread-pool queue depth, SQLite busy timeouts | Data to decide when Tier 2 is needed |

### Tier 2 — Sustained multi-user load (hundreds of users, still one or few workers)

**Triggers:** SQLite write contention, memory recall latency grows linearly, thread pool consistently saturated.

| Work item | What | Why |
|-----------|------|-----|
| Memory recall performance | Indexing, embedding cache, limit linear scans in `memory_recall` | `prepare_turn()` does multiple DB + embedding calls per turn |
| Connection / write discipline | Audit all DB paths for short transactions; batch where safe | Reduces lock duration under concurrent threads |
| Rate limiting per user | Cap concurrent streams and turns per minute | Protects thread pool and OpenAI quota |
| Session TTL and cleanup | Already partially in `state_store.py`; tune TTL and eviction | Limits memory growth of `_states` dict |
| Horizontal scaling prep | Externalize session state or require sticky sessions | Required before running multiple Uvicorn workers with shared `NovaState` |

### Tier 3 — Production multi-worker / multi-instance

**Triggers:** Need for >1 Uvicorn worker or multiple API instances; session state must survive restarts.

| Work item | What | Why |
|-----------|------|-----|
| **Session persistence** | Reload `NovaState` from DB/Redis each turn, or sticky routing per user | In-memory `_states` does not work across workers or restarts |
| **Worker queue for turns** | arq, Celery, or a thin turn-engine subprocess; API proxies SSE from job events | Decouples LLM latency from API process; natural place for retries and metrics |
| **Async persistence layer** | Async DB driver + `AsyncOpenAI` (Option D) | Best single-process concurrency; large refactor |
| **Dedicated vector / memory service** | Move embeddings and recall off the hot path | `prepare_turn()` embedding work dominates pre-stream latency |
| **Infrastructure** | Redis pub/sub or similar for cross-instance SSE fan-out | Multiple API nodes serving one stream subscription |

### Tier 4 — High scale

**Triggers:** Thousands of concurrent users, strict SLOs, cost controls.

- Separate read replicas or purpose-built store for conversation history and memories
- Model routing, caching, and token budgets per tier
- Episode summarization and consolidation as background jobs, not inline in `finalize_response()`
- Full observability: tracing per turn phase, OpenAI latency, DB lock metrics, per-user cost

---

## Decision log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-06 | Option B for async SSE | `api/routers/chat.py` — `asyncio.to_thread()` for prepare, per-token stream, finalize; tests in `tests/test_chat_stream_threading.py` |

---

## Related files

| File | Role |
|------|------|
| `api/routers/chat.py` | Async SSE endpoint and thread offloading |
| `message_processor.py` | Sync turn pipeline (`prepare_turn`, `finalize_response`, `stream_llm_tokens`) |
| `state_store.py` | Per-user in-memory `NovaState` |
| `memory_scope.py` | `user_scope` / `ContextVar` for DB isolation |
| `memory.py` | SQLite access (per-call connections) |
| `tests/test_chat_stream_threading.py` | Regression tests for offloading and SSE ordering |
