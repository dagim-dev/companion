# Nova Benchmark Suite

Purpose: give you a measurable baseline before the stabilization branch, so you can
tell whether a "fix" actually helped and whether anything regresses on resume months
from now. Every metric below is tied to something real found in the audit — nothing
here is a generic checklist.

**Baseline status: none currently exists.** `docs/ARCHITECTURE.md` references a
`benchmarks.md` with an informal "~1.3–1.8s per turn" figure, but that file is not in
the repo (see `todo.md` item 6 / Open Questions). Treat that number as
**historical/unverified** until you confirm its source — do not use it as a hard
target.

---

## 1. End-to-end turn latency

- **What to measure:** Wall-clock time for one full `process_message()` call
  (`prepare_turn` → LLM call → `finalize_response`).
- **Why it matters:** This is the number the user actually feels. It's also already
  instrumented — no new code needed to start collecting it.
- **Where to measure:** `message_processor.process_message()` already computes and
  returns `response_time_s` (`time.time() - start_time`). CLI mode (`main.py`) already
  prints it per turn.
- **How to measure:** Run `python main.py` locally and send ~20 varied messages
  (short/long, first message of session vs. mid-conversation, with/without
  reflection-topic keywords). Log the printed `[RESPONSE TIME]` values.
- **Input/workload:** A fixed script of 20 representative prompts (mix of casual
  chat, an anxiety/stress-keyword message to trigger reflection recall, and a message
  matching an existing reflection topic to trigger the recall + embedding path)
  gives you an apples-to-apples comparison run over run.
- **Baseline value:** Not currently available — run the above once before starting
  the stabilization branch and record the median and p95 here.
- **Target/comparison:** No fix in `todo.md` should make this number worse. Item 3
  (synchronous embedding calls) and item 1 (SQLite connection storm) are the two most
  likely to visibly move this number if addressed.
- **Units:** seconds (already what `response_time_s` reports).
- **Expected benefit of tracking:** Lets you confirm whether the P2 performance items
  are worth doing at all — if turn latency is already fine, you can deprioritize them
  with evidence instead of guessing.
- **What a regression looks like:** Median or p95 turn latency increases after a
  change with no corresponding new feature that would explain it (e.g. more DB calls
  added without measuring).

## 2. Time spent in the pre-LLM pipeline vs. the LLM call itself

- **What to measure:** Split `response_time_s` into two components: time inside
  `prepare_turn()` (everything before the OpenAI call) vs. time inside `llm.chat()` /
  `chat_stream()` (the actual OpenAI round trip).
- **Why it matters:** This is the direct way to confirm or rule out the "per-turn
  SQLite connection storm" and "synchronous embedding call in the critical path"
  bottlenecks flagged in `todo.md`. Right now there's no way to tell how much of a
  1.5s turn is Nova's own overhead vs. OpenAI's response time.
- **Where to measure:** Wrap `prepare_turn(...)` and the `chat(...)` call in
  `message_processor.process_message()` with separate `time.time()` markers (temporary
  instrumentation, or a lightweight `time.perf_counter()`-based decorator if you want
  it to persist).
- **How to measure:** Same 20-prompt script as benchmark 1, log both sub-timings per
  turn.
- **Input/workload:** Same as benchmark 1.
- **Baseline value:** Not currently available — first stabilization-branch run
  establishes it.
- **Target/comparison:** If `prepare_turn()` consistently accounts for more than ~20%
  of total turn time, that's a concrete signal the P2 bottleneck items are worth
  fixing before Nova scales past single-user local use. If it's consistently under
  that, deprioritize them.
- **Units:** seconds, and also as a percentage of total turn time.
- **Expected benefit:** Turns a hypothesis ("the connection storm is probably slow")
  into a measured fact, per the audit's own evidence standard.
- **What a regression looks like:** `prepare_turn()`'s share of total time creeping up
  as more `memory_*` modules are added over time.

## 3. Embedding call latency (isolated)

- **What to measure:** Latency of `embedding_engine.create_embedding()` alone, called
  from both `reflection_engine.update_reflection()` (write path) and
  `memory_retriever.retrieve_relevant_reflections()` (read path).
- **Why it matters:** Both call sites make this OpenAI network call synchronously,
  inline, in the chat critical path (see `todo.md` Performance/Bottlenecks #3). This
  isolates whether that call — not the SQLite overhead — is the dominant cost.
- **Where to measure:** `embedding_engine.py`, around the `client.embeddings.create(...)`
  call.
- **How to measure:** Time 20 calls with realistic message lengths (4–40 words, since
  `retrieve_relevant_reflections` already skips embedding for messages under 4 words).
- **Input/workload:** Same message set as benchmark 1, filtered to the ones that
  actually trigger embedding (reflection-topic keyword messages + messages ≥4 words
  during an active reflection).
- **Baseline value:** Not currently available.
- **Target/comparison:** Compare against benchmark 2's `prepare_turn()` time — if
  embedding calls account for the majority of `prepare_turn()`'s overhead, the
  highest-leverage fix is making this call async/non-blocking (e.g. run it in the
  background and use it on the *next* turn rather than blocking the current one),
  not the SQLite connection cleanup.
- **Units:** seconds (network round trip).
- **Expected benefit:** Directly informs whether item 3 in Performance/Bottlenecks is
  worth fixing before the pause or can be deferred.
- **What a regression looks like:** Sudden jump suggests an OpenAI-side issue (rate
  limiting, model deprecation) rather than a Nova code problem — useful to be able to
  tell apart when you resume months from now and something feels slow.

## 4. `reflections.content` length growth (data-quality regression guard)

- **What to measure:** Max and average `LENGTH(content)` across the `reflections`
  table for a given user, over the lifetime of a topic.
- **Why it matters:** Directly measures whether `todo.md` item 1 (unbounded string
  concatenation) is fixed and stays fixed. This is a correctness/data-quality metric,
  not a speed one, but it belongs in the benchmark suite because an unbounded
  `content` field silently increases every future turn's prompt size and cost — it's
  a slow-motion performance regression if left unfixed.
- **Where to measure:** `SELECT topic, LENGTH(content), reflection_count FROM
  reflections WHERE user_id = ? ORDER BY LENGTH(content) DESC` against `memory.db`.
- **How to measure:** Run the query before and after applying item 1's fix; also add
  it as an assertion in the regression test recommended in `todo.md` (update the same
  topic 20+ times, assert length stays under the chosen cap).
- **Input/workload:** Real `memory.db` if you have one from local use, or a synthetic
  test that calls `update_reflection()` repeatedly.
- **Baseline value:** Unknown until you inspect your current `memory.db` — this alone
  is worth running once immediately, since it tells you how bad the problem already is
  in practice.
- **Target/comparison:** After the fix, max `LENGTH(content)` should never exceed the
  chosen cap (e.g. 1500 chars), regardless of `reflection_count`.
- **Units:** characters.
- **Expected benefit:** Confirms the P0 fix actually holds under real repeated use,
  not just in the unit test.
- **What a regression looks like:** Any row where `LENGTH(content)` exceeds the cap
  after the fix ships — should never happen; if it does, the cap logic has a bug.

## 5. Memory extraction job backlog and latency

- **What to measure:** Time between a job's `created_at` (enqueued in
  `finalize_response()` via `enqueue_extraction_job`) and its `completed_at`
  (`memory_extraction_jobs` table), plus the count of jobs sitting in
  `pending`/`pending_retry` status at any given time.
- **Why it matters:** This is the async pipeline's health signal — the worker polls
  every 5 seconds (`memory_extraction_worker._POLL_SECONDS`) and processes one job at
  a time; if job creation ever outpaces single-threaded processing, insights and
  learned preferences fall permanently behind live conversation.
- **Where to measure:** `memory_extraction_jobs` table directly, or via the existing
  dev dashboard (`api/routers/dev_memory.py`, `/v1/dev/memory-extraction/*`,
  surfaced in `frontend/src/app/dev/memory-extraction/page.tsx`) — this instrumentation
  already exists, just use it.
- **How to measure:** During the 20-message benchmark script, watch the dev dashboard
  or query `SELECT status, COUNT(*), AVG(julianday(completed_at) -
  julianday(created_at)) * 86400 FROM memory_extraction_jobs GROUP BY status`.
- **Input/workload:** Same 20-message script, sent at natural chat pace (not a burst),
  since that's the realistic usage pattern for a single-user local companion.
- **Baseline value:** Not currently available — this is a good one to capture before
  and after item 5's fix (test coverage for the actual production job-claiming path),
  even though the fix itself is about test coverage, not runtime behavior — a stable
  baseline here gives you confidence the refactor in item 5 didn't change real
  behavior.
- **Target/comparison:** At single-user local scale, jobs should complete within
  one poll interval plus extraction LLM call time (a few seconds). No target needed
  beyond "no growing backlog."
- **Units:** seconds (completion latency), count (backlog size).
- **Expected benefit:** Confirms the async pipeline you already built stays healthy;
  catches silent backlog growth if `extract_insights_from_message` ever starts
  failing quietly.
- **What a regression looks like:** Backlog count trending upward across a session
  instead of staying near zero, or completion latency growing past ~30–60s under
  normal (non-burst) single-user load.

## 6. Startup time and health check

- **What to measure:** Time from `uvicorn api:app` process start to `/health`
  returning 200.
- **Why it matters:** The most basic "does it still work" signal after months of not
  touching the project — cheap to check, catches import errors, DB init failures, or
  a bad `JWT_SECRET`/`.env` immediately.
- **Where to measure:** `api/main.py` startup event (or its lifespan-handler
  replacement, per item 7); `api/routers/health.py`.
- **How to measure:** `time curl -sf http://localhost:8000/health` right after
  starting the server; also confirm the log line `"NOVA API ready..."` appears.
- **Input/workload:** N/A — cold start only.
- **Baseline value:** Not currently available — capture once, it should be a couple
  seconds at most (FastAPI + SQLite init, no heavyweight ML models to load).
- **Target/comparison:** Should stay near-instant; any large increase signals a
  startup-path regression (e.g. a slow migration check added later).
- **Units:** seconds.
- **Expected benefit:** A single fast manual check to run first after resuming the
  project, before debugging anything else.
- **What a regression looks like:** `/health` taking noticeably longer, or returning
  non-2xx (it's designed to, per `CHANGELOG.md`, when SQLite is unreachable — that's
  the intended failure signal, not a bug).

## 7. Test suite runtime and pass rate

- **What to measure:** `python -m pytest tests/ -q` pass count and wall-clock time.
- **Why it matters:** Cheapest possible regression signal; already fully working.
- **Where to measure:** CI or local terminal.
- **How to measure:** `python -m pytest tests/ -q`.
- **Input/workload:** N/A.
- **Baseline value (verified during this audit):** **115 passed, ~1.9s**, run against
  Python 3.12 with placeholder env vars (`OPENAI_API_KEY=sk-test`,
  `JWT_SECRET=test-secret`, `ENV=development`). No failures.
- **Target/comparison:** Should stay at 115+ passed (growing as items 1, 2, 3, 5 add
  tests) with runtime staying in the low single-digit seconds — this suite doesn't hit
  real OpenAI, so it should never get meaningfully slower unless something is wrong.
- **Units:** count (passed/failed), seconds.
- **Expected benefit:** The one number to check after literally any change.
- **What a regression looks like:** Any failure, or runtime jumping by an order of
  magnitude (would suggest a test accidentally started hitting the network).

---

## Metrics intentionally excluded

To keep this suite honest and avoid inventing targets with no basis:

- **Cost per conversation / API spend** — not tracked anywhere in the current code
  (no token-usage logging), and out of scope to add speculatively. If you want this,
  it would need new instrumentation around the `client.chat.completions.create(...)`
  call in `llm.py` first.
- **Concurrent-user scaling behavior** — Nova is explicitly a single-user local app
  today (per README, `.env.example`, and the SQLite-file architecture). Benchmarking
  multi-user throughput would test a scenario the project isn't currently designed
  for; revisit only if/when Nova is deployed for more than one person.
- **Output/response quality metrics** — no existing eval harness or labeled quality
  data in the repo to build on. Adding one is a legitimate future project but is a
  new capability, not a baseline to measure against existing behavior, so it's out of
  scope for this stabilization pass.
