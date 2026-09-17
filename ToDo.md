# Nova Stabilization TODO

Derived from a direct audit of `dagim-dev/companion` (main, cloned 2026-09-03). Every
item below cites the specific file/lines behind it. Ordered so earlier items unblock
or de-risk later ones where relevant.

Legend: **Verified** = confirmed by reading code/tests directly. **Inferred** = strong
evidence, not runtime-confirmed. **Unknown** = flagged for your confirmation.

---

## P0 — Critical

### [x] 1. Cap unbounded growth of `reflections.content`
- **Location:** `reflection_engine.py`, `update_reflection()`, lines 104–125
- **Problem:** Every time a user mentions a topic again, the existing row's `content`
  column is extended with `content = content || ' || ' || ?` — no truncation, no cap
  on fragment count or total length.
- **Evidence (verified):** Raw SQL concatenation, no `LENGTH()` guard. This same
  `content` field is later read by `memory_retriever.retrieve_relevant_reflections()`
  and injected verbatim into the LLM system prompt under `IMPORTANT CONTINUITY
  MEMORIES` (`llm.py` line 104). Anyone who mentions "school" or "stress" repeatedly
  over months will accumulate a single ever-growing run-on string that gets sent to
  OpenAI on every relevant turn.
- **Why it matters:** Silent, unbounded per-turn token cost growth; eventual risk of
  blowing the context window for long-running topics; degrades response quality (the
  model is fed a garbled concatenation instead of a clean summary).
- **Recommended fix:** On update, keep only the last N fragments (e.g. 3–5) or hard-cap
  total length (e.g. 1500 chars, trimming from the oldest end) before writing back.
  Longer term, consider summarizing into a single sentence instead of concatenating
  raw text — but a hard cap is sufficient to stop the bleeding before the pause.
- **Validation:** New test — call `update_reflection()` with the same topic 20+ times,
  assert `content` length stays under the cap.
- **Dependencies/blockers:** None.

### [x] 2. Stop persisting the OpenAI fallback string as a real assistant turn
- **Location:** `llm.py`, `chat_stream()` lines 244–264; `message_processor.py`,
  `finalize_response()` lines 202–248
- **Problem (historical):** If the OpenAI streaming call raised *any* exception,
  `chat_stream()` yielded a hardcoded fallback string ("Apologies. The connection to my
  higher cognitive functions appears temporarily unstable."). `finalize_response()`
  then unconditionally wrote that string into `conversations` via
  `create_conversation_message()` — with no flag distinguishing it from a genuine
  reply.
- **Evidence (historical):** `except Exception: print("[LLM ERROR]"); traceback.print_exc();
  yield <fallback>` in `llm.py`; the caller had no branch that checked whether
  the response was a fallback before persisting it.
- **Why it matters:** A transient OpenAI outage or rate limit permanently corrupts the
  user's real conversation history with a canned error message that's indistinguishable
  from a real reply after the fact — this is data users may rely on for continuity.
- **Recommended fix:** Return/raise a distinguishable error signal from `chat_stream()`
  instead of silently yielding fallback text, and have `finalize_response()` skip
  persistence (or persist with an explicit `role="system_error"` / metadata flag) when
  the turn failed. Also replace the bare `print`/`traceback.print_exc()` with the
  existing `logging_config` logger used elsewhere.
- **Validation:** New test — mock the OpenAI client to raise, assert no fallback text
  lands in `conversations` (or lands tagged as an error, per chosen fix).
- **Dependencies/blockers:** None. Do this before item 3 (observability cleanup) so the
  fix pattern is established once and reused.
- **Status:** Resolved in `fd1dcbc`; docs/changelog follow-up completed 2026-09-14.

---

## P1 — High Priority

### [x] 3. Standardize silent-failure handling in `embedding_engine.py` and related modules
- **Location:** `embedding_engine.py` lines 19–36 (`create_embedding`); same
  print+swallow pattern also present in `voice_service.py` and `llm.py` (see item 2)
- **Problem:** `create_embedding()` catches every exception (auth errors, rate limits,
  network failures — anything) and returns `None`, logging only via `print()` to
  stdout. Callers (`reflection_engine.update_reflection`,
  `memory_retriever.retrieve_relevant_reflections`) treat `None` as "nothing to embed"
  and continue silently.
- **Why it matters:** This is exactly the failure mode that's dangerous for a project
  about to sit untouched for months: if `OPENAI_API_KEY` expires or billing lapses,
  reflection embeddings quietly stop being written/read and semantic memory recall
  quietly goes to zero — with no error surfaced anywhere but a `print()` that nobody
  will see in production.
- **Recommended fix:** Replace `print`/`traceback.print_exc()` with the shared logger
  (`logging_config.py` pattern already used in `memory_extraction_worker.py`,
  `api/main.py`). Distinguish auth/config errors (fail loud, e.g. log at ERROR with a
  clear "check OPENAI_API_KEY" hint) from transient errors (log at WARNING, degrade
  gracefully as today).
- **Validation:** New test — mock the OpenAI client to raise `AuthenticationError`,
  assert it's logged at ERROR level (not just swallowed).
- **Dependencies/blockers:** Do after item 2 so both fixes use the same logging
  convention.
- **Status:** Resolved 2026-09-14 — `create_embedding()` logs auth failures at ERROR
  (with `OPENAI_API_KEY` hint) and transient OpenAI errors at WARNING; `voice_service.py`
  uses `logger.exception` instead of `print`/`traceback`; covered by
  `tests/test_embedding_engine.py` and `tests/test_voice_service.py`.

### [x] 4. Fix dead "emotionally important past memories" code path
- **Location:** `context_builder.py`, `select_relevant_memory()`, lines 40–45
- **Problem:** `for entry in profile.get("history", []): if entry.get("intensity", 0)
  > 0.7: ...` — `profile` here is the dict from `memory.get_profile()`, which only ever
  contains keys written by `set_profile()`.
- **Evidence (verified):** Grepped every `set_profile()` call site in the repo
  (`companion_prefs.py:372,375`, `main.py:19-20`, `api/routers/profile.py:40`) — the
  only keys ever written are `address_as`, `name`, `communication_style`. `"history"`
  is never written anywhere. This loop always iterates zero items; the
  "emotional_memory" branch of `format_memory()` in the same file is consequently also
  unreachable.
- **Why it matters:** Not a crash, but a silently broken feature — this looks like it
  contributes emotionally-weighted past context to the prompt, and it never does
  anything. Worth knowing before you build on top of it or assume it's protecting
  against forgotten distressing topics.
- **Recommended fix:** Either wire it up for real (populate `profile["history"]` from
  `get_emotional_history()` before calling `build_context`), or delete the dead branch
  and its now-unreachable code in `format_memory()`. Given `reflections` +
  `learned_preferences` already cover "remembering what matters," deletion is the
  lower-risk option — confirm with Dagi which is wanted (see Open Questions).
- **Validation:** If wired up, add a test asserting an intensity>0.7 history entry
  appears in `context["relevant_memory"]`. If deleted, existing tests should still pass
  unchanged.
- **Dependencies/blockers:** Needs your decision — see Open Questions.
- **Status:** Resolved 2026-09-14 — deleted the never-populated `profile["history"]`
  branch in `select_relevant_memory()` and its unreachable `emotional_memory` case in
  `format_memory()`; covered by `tests/test_context_builder.py`.

### [x] 5. Consolidate `memory_extraction_worker.py`'s two job-processing functions
- **Location:** `memory_extraction_worker.py` — `process_next_job()` (lines 42–64) vs.
  `process_next_available_job()` + `_claim_any_due_job()` (lines 67–117)
- **Problem:** Two nearly-identical implementations of "claim and process one
  extraction job" exist side by side.
- **Evidence (verified):** `grep` shows `process_next_job` is called **only** from
  `tests/test_memory_extraction_worker.py`. Production (`_worker_loop`, called from
  `start_worker()` in `api/main.py`) calls `process_next_available_job()` exclusively.
  The two differ meaningfully: `process_next_job` requires the caller to already know
  the `user_id`; `process_next_available_job` does its own cross-user job discovery via
  `_claim_any_due_job()`.
- **Why it matters:** The tests exercising `process_next_job` give you confidence in
  logic that production never runs. The actual production code path
  (`_claim_any_due_job`'s cross-user `SELECT ... ORDER BY created_at ASC LIMIT 1`
  query, and `process_next_available_job`'s error handling) has **no direct unit test
  coverage**. Before a long pause, this is the gap most likely to bite you on resume.
- **Recommended fix:** Either (a) delete `process_next_job` and rewrite
  `tests/test_memory_extraction_worker.py` against `process_next_available_job` /
  `_claim_any_due_job`, or (b) keep `process_next_job` only if it's still useful as a
  lower-level single-user primitive, but add new tests that exercise
  `process_next_available_job` and `_claim_any_due_job` directly (multi-user claim
  ordering, retry timing via `next_retry_at`).
- **Validation:** New/rewritten tests directly cover the function `start_worker()`
  actually calls.
- **Dependencies/blockers:** None.
- **Status:** Resolved 2026-09-14 — removed unused `process_next_job()`, extracted
  shared `_process_claimed_job()` helper, and rewrote `tests/test_memory_extraction_worker.py`
  against `process_next_available_job()` / `_claim_any_due_job()` (FIFO cross-user ordering,
  `next_retry_at` gating, and retry-count assertions).

### [x] 6. Fix stale documentation links and gaps in `docs/ARCHITECTURE.md` / `docs/V4_SCOPE.md`
- **Location:** `docs/ARCHITECTURE.md`, `docs/V4_SCOPE.md`
- **Problem (all verified — files checked directly against the repo):**
  - Both files link to `[Future change.md](../Future%20change.md)` — **this file does
    not exist anywhere in the repo** (`git ls-files` confirms it was never committed,
    or was deleted without updating the links).
  - `ARCHITECTURE.md` links to `[benchmarks.md](../benchmarks.md)` — also does not
    exist. The doc describes it as "Manual latency log (~1.3–1.8s per turn)"; that
    number is now orphaned (see `benchmark.md` Open Questions on reusing it as a
    provisional baseline).
  - `ARCHITECTURE.md` states *"No `prompts/__init__.py` — import `prompts.core`
    directly"* — this is factually wrong; `prompts/__init__.py` exists (as an empty
    0-byte file).
  - `turn_guard.py` (actively used — imported by `api/routers/chat.py` and
    `tests/test_chat_stream_threading.py`, implements the per-user single-turn
    concurrency guard) is **not mentioned anywhere** in `ARCHITECTURE.md`'s file-by-file
    walkthrough or its "Root module quick index" section, despite every other root
    module being documented there.
- **Why it matters:** This is explicitly the last documentation pass before a long
  gap — dead links and an undocumented concurrency-safety module are exactly what
  will cost you time when you come back in months.
- **Recommended fix:** Remove or fix the two dead links (confirm with Dagi whether
  `Future change.md` should be recreated from git history or the links just deleted);
  correct the `prompts/__init__.py` claim; add a `turn_guard.py` entry to both the
  file-by-file walkthrough and the module quick index.
- **Validation:** Manual read-through; optionally a simple CI/pre-commit link-checker
  script (see P3).
- **Dependencies/blockers:** None. Do after item 4 is decided, since that decision
  also touches `context_builder.py`'s documented behavior.
- **Status:** Resolved 2026-09-14 — restored `docs/V4_SCOPE.md`, removed dead
  `Future change.md` / `benchmarks.md` links, corrected `prompts/__init__.py` note,
  documented `turn_guard.py`, swept `CHANGELOG.md` and ADR 0002.

### [x] 7. Migrate FastAPI `@app.on_event` to lifespan handlers
- **Location:** `api/main.py` lines 36–57
- **Problem:** Uses the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")`
  pattern.
- **Evidence (verified):** Running the test suite emits explicit
  `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead`
  from `fastapi/applications.py`, pointing directly at `api/main.py:36` and `:55`.
- **Why it matters:** This is the single piece of infrastructure code most likely to
  break outright on a routine `pip install --upgrade fastapi` after a long pause —
  deprecated APIs get removed, not just warned about.
- **Recommended fix:** Replace both decorators with a single `@asynccontextmanager
  async def lifespan(app): ... yield ...` passed to `FastAPI(lifespan=lifespan)`, per
  FastAPI's own migration guide. Startup/shutdown logic itself doesn't need to change,
  just the wiring.
- **Validation:** Existing tests (`test_release_contract.py`, health-check tests)
  should pass unchanged; manually confirm `/health` and worker start/stop still fire
  in local run.
- **Dependencies/blockers:** None. Small, low-risk, single-file change.

---

## P2 — Medium Priority

### [x] 8. Pin dependency versions before hibernation
- **Location:** `requirements.txt`, `frontend/package.json`
- **Problem:** `requirements.txt` uses only floating lower-bound specifiers
  (`fastapi>=0.115.0`, `openai>=1.0.0`, etc.) with no upper bounds and no lockfile.
  `frontend/package.json` uses caret ranges (`^15.1.0`, `^19.0.0`) with `package-lock.json`
  present (good — npm is reproducible today).
- **Evidence (verified):** Read `requirements.txt` in full — every line is `>=`, none
  pinned; no `requirements.lock.txt`, `pyproject.toml`, or `poetry.lock` in the repo.
- **Why it matters:** A fresh `pip install -r requirements.txt` months from now can
  silently pull newer major versions of FastAPI, Pydantic (via FastAPI), or the
  `openai` SDK — any of which have historically shipped breaking changes. The frontend
  is already reproducible via `package-lock.json`; the backend isn't.
- **Recommended fix:** Generate a pinned snapshot now while everything is known-working:
  `pip freeze > requirements.lock.txt` (or adopt `pip-tools`/`uv pip compile`), and
  update the README install instructions to install from the lock file for
  reproducibility, keeping `requirements.txt` as the human-edited source of loose
  constraints.
- **Validation:** Fresh venv install from the lock file reproduces the exact
  currently-passing test run.
- **Dependencies/blockers:** Do last among P2 items, after any other dependency-touching
  fixes above are merged, so the pin captures the final state.
- **Status:** Resolved 2026-09-14 — added `requirements.lock.txt` (Python 3.11 `pip freeze`
  snapshot), README install uses the lock; `requirements.txt` remains the editable constraint
  source; architecture docs updated.

### [x] 9. Narrow the broad `except Exception` fallback in `auth_store.get_user_by_id`
- **Location:** `auth_store.py` lines 63–78
- **Problem:** Selects `onboarding_completed` and falls back to a query without it
  inside a bare `except Exception`, to support both pre- and post-migration schemas.
- **Evidence (verified):** Compare with `memory.py`'s `_ensure_learned_preferences_columns()`
  (lines 93–118), which does the equivalent check properly via `PRAGMA table_info(...)`
  before deciding what to query — a pattern already established elsewhere in this
  codebase but not used here.
- **Why it matters:** This runs on every authenticated request. A broad `except
  Exception` here would also silently swallow a genuinely broken/locked database and
  retry with a different query instead of surfacing the real error.
- **Recommended fix:** Replace the try/except-based schema detection with an explicit
  `PRAGMA table_info(users)` check (same style as `memory.py`), consistent with the
  rest of the codebase.
- **Validation:** Existing auth tests should pass unchanged; add a test that a genuine
  DB error (e.g. locked file) propagates instead of falling back silently.
- **Dependencies/blockers:** None.
- **Status:** Resolved 2026-09-14 — `get_user_by_id()` uses `PRAGMA table_info(users)` to
  choose the query; legacy four-column `users` tables still return `onboarding_completed=False`;
  covered by `tests/test_auth_store.py`.

### [x] 10. Standardize error logging (replace `print()`/`traceback.print_exc()`)
- **Location:** `llm.py` (see item 2), `embedding_engine.py` (see item 3),
  `voice_service.py`
- **Problem:** Three modules use `print()`/`traceback.print_exc()` for error reporting
  instead of the `logging_config.py`-based logger used consistently in
  `memory_extraction_worker.py`, `api/main.py`, `persistence_policy.py`.
- **Evidence (verified):** `grep -rln "print("` across non-script/non-test files
  returns exactly `voice_service.py`, `llm.py`, `embedding_engine.py` (migrations
  scripts also print, which is fine — they're one-shot CLI tools, not runtime code).
- **Why it matters:** Inconsistent observability — the modules on the hot path most
  likely to fail loudly during an OpenAI/ElevenLabs outage are the ones whose errors
  are least likely to be captured by whatever log aggregation you set up on redeploy.
- **Recommended fix:** Swap `print`/`traceback.print_exc()` for
  `logger.exception(...)` using the existing `logging_config` setup, in all three
  files. Folds naturally into items 2 and 3 above — do together.
- **Validation:** Manual — trigger a failure path in each of the three modules,
  confirm it appears in logs, not stdout only.
- **Dependencies/blockers:** Do together with items 2 and 3.
- **Status:** Resolved 2026-09-14 — runtime error paths in `llm.py` (item 2),
  `embedding_engine.py` (item 3), and `voice_service.py` (item 3) now use module
  loggers; remaining `print()` in `llm.py` is intentional CLI stream echo only.

---

## P3 — Optional Cleanup

### [x] 11. Replace deprecated `datetime.utcnow()` calls
- **Location:** `companion_prefs.py:286`, `auth_store.py:22`
- **Evidence (verified):** Both flagged by `DeprecationWarning` during the test run
  ("scheduled for removal in a future version").
- **Fix:** Replace with `datetime.now(timezone.utc)`. Purely mechanical, zero behavior
  change (both already produce UTC ISO strings).
- **Priority note:** Genuinely optional — Python won't remove this soon — but it's a
  five-minute fix while you're already in these files for items 2 and 9.
- **Status:** Resolved 2026-09-14 — `create_user()` and `save_companion_preferences()`
  use `datetime.now(timezone.utc).isoformat()`; regression assertions in
  `tests/test_auth_store.py` and `tests/test_companion_preferences_v2.py`.

### [x] 12. Clean up contradictory voice config comments
- **Location:** `config.py` lines 8–12
- **Evidence (verified):** `ELEVENLABS_VOICE_ID` default is preceded by the comment
  `# Calm British male — set in ElevenLabs dashboard or env`, but the literal value on
  the next line has its own inline comment `# Jessica — override via .env`, and that ID
  doesn't match the one in `.env.example`. Contradictory as written.
- **Fix:** Pick one accurate description of the actual default voice and update both
  comments to agree. Cosmetic only — `VOICE_ENABLED` already defaults to `false` so
  this isn't affecting current behavior.
- **Status:** Resolved 2026-09-14 — single generic comment in `config.py` (fallback ID
  unchanged); `.env.example` labeled as example voice ID.

---

## Cleanup / Deletion

**No files are recommended for deletion.** Specifically checked and ruled out:
- No orphaned YAML role templates (README/CHANGELOG say six fixed role templates were
  removed in favor of the composable personality model — verified no `.yaml`/`.yml`
  files exist anywhere in the repo).
- No tracked junk files (`git ls-files` shows no `.DS_Store`, no `.env`, no `memory.db`
  — `.gitignore` is doing its job).
- No unusually large tracked files (largest is `frontend/package-lock.json` at 212K,
  which is expected and should stay).
- The legacy `personal_memories` quarantine logic in `memory.py`
  (`_quarantine_legacy_personal_memories`, `get_legacy_personal_memory_status`) is
  live, intentional defensive code for a real historical migration path (per
  `CHANGELOG.md` "Removed" section and `README.md`'s migration notes) — **keep, do not
  delete**, even though it looks like it could be dead weight at first glance.

## Architecture / Structure

**No structural restructuring is necessary.** The flat root-module layout for backend
domain logic, with `api/` as a thin HTTP shell and `frontend/` as a self-contained
Next.js app, is consistent, matches what `docs/ARCHITECTURE.md` describes (modulo the
fixes in item 6), and every root module has a single clear responsibility. Folder
structure was not a source of any finding in this audit.

## Performance / Bottlenecks

See dedicated `benchmark.md` for what to measure. Summary of the two real bottlenecks
found:

1. **Per-turn SQLite connection storm.** `memory.get_connection()` opens/configures
   (WAL + busy_timeout PRAGMAs) and closes a fresh `sqlite3.connect()` on every single
   call, and a single chat turn makes roughly 10–15 such calls serially
   (`decay_memories`, `consolidate_memories`, `get_profile`, `get_emotional_profile`
   [2 queries], conditionally `retrieve_relevant_reflections`,
   `retrieve_style_preference_memories`, `get_recent_insights`,
   `get_active_learned_preferences`, then post-response `create_conversation_message`
   ×2, `enqueue_extraction_job`, conditionally `create_episode` /
   `save_runtime_personality`) — all before/around the actual OpenAI call.
   **Priority: P2.** Not urgent for single-user local use (SQLite + WAL handles this
   fine at Dagi's current scale), but the first thing to revisit if Nova ever serves
   concurrent users.
2. **Decay/consolidation run unconditionally every turn.** `prepare_turn()` calls
   `decay_memories()` and `consolidate_memories()` (both full `UPDATE ... WHERE
   user_id = ?` scans of `reflections`) on **every message**, regardless of whether
   anything changed, rather than on the interval-based schedule already used elsewhere
   in the codebase for runtime personality persistence (`persistence_policy.py`).
   **Priority: P3.** Currently cheap (few rows per user), but is unconditional
   per-turn overhead that doesn't need to be.
3. **Synchronous OpenAI embedding calls inside the chat critical path.**
   `update_reflection()` and `retrieve_relevant_reflections()` both call
   `embedding_engine.create_embedding()` — a live network round-trip to OpenAI —
   inline, synchronously, before the main chat completion even starts. **Priority:
   P2.** This is likely a bigger latency contributor than the SQLite overhead above;
   see `benchmark.md` for how to confirm.

## Testing

- **Current state (verified):** `python -m pytest tests/ -q` → **143 passed**, ~2s, no
  failures, run clean against Python 3.11+ with dummy env vars. Test suite is in good
  health and is a real asset going into hibernation.
- **Coverage gap (item 5):** **closed** — `tests/test_memory_extraction_worker.py` now
  exercises `process_next_available_job()` / `_claim_any_due_job()` directly.
- **Recommended new tests before pause**, in priority order:
  1. Bounded-length regression test for `update_reflection()` (item 1) — done.
  2. Fallback-response-not-silently-persisted test for `chat_stream()` /
     `finalize_response()` (item 2) — done.
  3. Embedding-auth-failure-logs-loudly test for `create_embedding()` (item 3) — done.
  4. Direct tests for `process_next_available_job()` / `_claim_any_due_job()` (item 5) — done.
- **Note (unknown, requires confirmation):** README specifies Python 3.11 as a
  prerequisite; this audit's test run used Python 3.12 without issue. No 3.11-specific
  API usage was found in a scan of the codebase, but this wasn't exhaustively verified
  — confirm whether the 3.11 pin is load-bearing or can be relaxed/widened in the
  README.

## Documentation

Covered in detail under item 6. Summary of what needs to change before pause:
- Remove or restore the two dead links (`Future change.md`, `benchmarks.md`) in
  `docs/ARCHITECTURE.md` and `docs/V4_SCOPE.md`.
- Correct the false "no `prompts/__init__.py`" claim.
- Add `turn_guard.py` to `docs/ARCHITECTURE.md`'s file walkthrough and module index.
- Everything else in `README.md`, `API.md`, `CHANGELOG.md`, and the ADRs in
  `docs/decisions/` was spot-checked against the actual code (routers, migrations,
  env vars, CLI flow) and found to be **accurate and current** — no other changes
  needed there.

## Open Questions (need your input before proceeding)

1. **`Future change.md`** — was this file intentionally deleted, renamed, or never
   committed? If it has content you want to keep (e.g. the concurrency/scaling
   roadmap referenced by `docs/V4_SCOPE.md`), let me know and I can help recover it
   from git history or recreate it as a stub; otherwise I'll just remove the dead
   links (item 6).
2. **`benchmarks.md`** — same question. It's cited as containing a manual latency log
   (~1.3–1.8s/turn). If you still have that data, it'd be a genuinely useful seed for
   the new `benchmark.md` baseline; otherwise that number should be treated as
   historical/unverified.
3. **Item 4 (`profile.get("history")` dead code)** — **resolved:** deletion chosen;
   dead branch removed from `context_builder.py` (see item 4 status).

## Final Validation Checklist

- [ ] `python -m pytest tests/ -q` passes (currently 143/143 — re-run after each fix)
- [ ] `cd frontend && npm run lint && npm run build` passes
- [ ] Manual smoke test: `scripts/smoke_release_e2e.py` against a locally built
      frontend + running API
- [ ] Fresh `git clone` + `pip install -r requirements.lock.txt` + `.env` from
      `.env.example` boots cleanly end to end
- [x] `docs/ARCHITECTURE.md` has no dead links (manual check or simple script)
- [ ] Reflection content length stays bounded after repeated mentions of the same
      topic (manual or automated per item 1's new test)
- [x] A forced OpenAI failure does not leave fallback text indistinguishable from a
      real reply in `conversations` (per item 2's new test)
