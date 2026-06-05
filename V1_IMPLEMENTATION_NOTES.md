# JARVIS V1 — Implementation Notes & Your Checklist

This document records **everything that was changed** during the V1 implementation (stabilize → API → stream → frontend → voice → optimization), and **what you still need to do on your machine**.

Date of implementation: 2026-05-30  
Plan reference: JARVIS V1 Roadmap (stabilize → API → stream → frontend → voice)

---

## Executive summary

Your project went from a **single terminal script** (`main.py` with a ~300-line loop) to a **layered system**:

1. **Terminal** — `python main.py` (thin wrapper)
2. **HTTP API** — `uvicorn api:app` (FastAPI)
3. **Web UI** — `frontend/` (Next.js + Tailwind)
4. **Voice** — Whisper STT + ElevenLabs TTS via API routes

The AI behavior modules (`memory.py`, `classifier.py`, `decision_engine.py`, etc.) were **not removed**. The **orchestration** was extracted so the same brain can run from terminal, API, and browser.

**Folder structure was kept flat** (no `backend/` move) per the plan.

---

## New files created

| File | Purpose |
|------|---------|
| `session_state.py` | Holds per-session objects: conversation history, `InternalState`, `MetaCognition`, `PersonalityState`, `ThoughtEngine`, `SelfPerception`, `CuriosityEngine`, VADER analyzer |
| `message_processor.py` | Core pipeline: `prepare_turn` → LLM → `finalize_response`, plus `process_message` for full sync turns |
| `api.py` | FastAPI app: health, chat, SSE stream, transcribe, TTS |
| `voice_service.py` | OpenAI Whisper transcription + ElevenLabs text-to-speech |
| `requirements.txt` | Python dependencies (FastAPI, uvicorn, openai, etc.) |
| `API.md` | HTTP API documentation (endpoints, SSE format) |
| `README.md` | Quick start for terminal, API, and frontend |
| `benchmarks.md` | Template to record response-time numbers (you fill in) |
| `frontend/` | Entire Next.js app (see Frontend section below) |

---

## Modified files (backend)

### `main.py` — simplified

**Before:** ~307 lines; contained the full chat loop (emotion, memory, LLM, post-processing, episodic memory).

**After:** ~34 lines:

- `init_db()`, seed profile
- `create_state()` once
- Loop: `input()` → `process_message(state, user_input)` → print `[RESPONSE TIME]` and reply

All intelligence now lives in `message_processor.py`.

---

### `llm.py` — logging, streaming refactor, compression

**Changes:**

1. **`import traceback`** — on LLM errors, prints full stack trace (not only `str(e)`).
2. **`build_system_message(...)`** — extracted the large system prompt builder.
3. **`build_chat_messages(...)`** — system message + conversation messages for OpenAI.
4. **`chat_stream(...)`** — generator yielding token chunks (`stream=True`).
   - `echo_to_terminal=True` — prints tokens in terminal (used by `main.py`).
   - `echo_to_terminal=False` — silent (used by API).
5. **`chat(...)`** — collects `chat_stream` into one string (sync path).
6. **`_compress_conversation_for_llm(...)`** — if conversation &gt; 6 messages, older turns are summarized into one compact user message; last 6 turns stay verbatim (Phase 6 prompt compression).

**Unchanged:** `SYSTEM_PERSONALITY` / JARVIS character text.

---

### `message_processor.py` — the main brain loop (new logic, moved from `main.py`)

**Functions:**

| Function | What it does |
|----------|----------------|
| `prepare_turn(state, user_input)` | Everything **before** OpenAI: decay/consolidate memories, append user message, personal memory extraction, emotion/intent, internal engines, reflections, context, decision engine, curiosity/followup prep. Returns `PreparedTurn` or `None` if intent is `uncertain`. |
| `finalize_response(state, turn, raw_response)` | Everything **after** OpenAI: `control_response`, `apply_rhythm`, meta-cognition, initiative, curiosity question, followup, append assistant message, episodic memory every 12 messages. |
| `process_message(state, user_input)` | Full turn with **end-to-end timing** in `response_time_s` (prepare + LLM + finalize). |
| `stream_llm_tokens(state, turn)` | Yields LLM tokens for SSE (no post-processing until stream ends). |

**Bug fix vs old `main.py`:** LLM kwargs now pass `self_perception` and `thought_state` in the order `llm.py` expects (old code may have swapped thought/self-perception args).

---

### `api.py` — HTTP server (new)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | `{"status":"ok","db":"ok"}` — pings SQLite |
| `/chat` | POST | JSON `{"message":"..."}` → full reply JSON |
| `/chat/stream` | POST | SSE: `token` events, then `done` with final post-processed text |
| `/transcribe` | POST | Multipart audio file → `{"text":"..."}` (Whisper) |
| `/tts` | POST | JSON `{"text":"..."}` → `audio/mpeg` bytes (ElevenLabs) |

**Other:**

- CORS enabled for `http://localhost:3000` and `127.0.0.1:3000`
- Single global session (`get_state()`) — **one conversation per server process** (V1 limitation)
- Global exception handler returns a polite JSON error on 500

---

### `config.py` — extended

**Added:**

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID` (default voice ID in code; override in `.env`)

**Existing:** `OPENAI_API_KEY` via `python-dotenv`

---

### `memory.py` — SQLite stability (Phase 6)

**Changes in `get_connection()`:**

- `timeout=30.0`
- `PRAGMA journal_mode=WAL`
- `PRAGMA busy_timeout=30000`

**`init_db()`:** also sets WAL on startup.

---

### `context_builder.py` — lighter context (Phase 6)

- `build_conversation_context`: `recent_messages` reduced from last **5** to last **4** messages.

---

### `personal_memory.py` — critical bug fix

**Problem:** `save_personal_memory` had broken SQL (nested broken triple-quoted strings). This caused a **SyntaxError** and blocked **all** imports (`api`, `main`, etc.).

**Fix:** Proper `cursor.execute(...)` with embedding creation before insert; timestamps as ISO strings.

---

### `memory_retriever.py` — no code change in this pass

Already returns at most **top 3** reflections (diversity filter). Documented here for Phase 6 awareness.

---

### `embedding_engine.py` — no change in this pass

Already used `traceback.print_exc()` on errors.

---

## Frontend (`frontend/`) — all new

Scaffolded manually (App Router, TypeScript, Tailwind). **Not** `npm install`’d in the agent environment — you must install dependencies locally.

### Config / root

| File | Purpose |
|------|---------|
| `package.json` | Next 15, React 19, Tailwind |
| `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `tailwind.config.ts` | Tooling |
| `.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `.env.local.example` | Template for API URL |

### Source

| Path | Purpose |
|------|---------|
| `src/app/page.tsx` | Main chat page |
| `src/app/layout.tsx`, `globals.css` | Dark theme layout |
| `src/hooks/useChat.ts` | Messages state, SSE streaming, typing state |
| `src/lib/api.ts` | `streamChat`, `transcribeAudio`, `synthesizeSpeech` |
| `src/components/ChatWindow.tsx` | Scrollable messages + empty state |
| `src/components/MessageBubble.tsx` | User/assistant bubbles, fade-in |
| `src/components/TypingIndicator.tsx` | “JARVIS is thinking…” |
| `src/components/ChatInput.tsx` | Textarea, Send, voice controls |
| `src/components/VoiceButton.tsx` | Hold-to-talk (MediaRecorder) + play last response |

### UI behavior

- Streaming: tokens append live; **`done` event replaces** text with final post-processed reply (rhythm, initiative, etc.).
- Voice: hold mic button → `POST /transcribe` → sends transcript as a chat message.
- Speaker button: `POST /tts` on last assistant message → browser audio playback.

---

## Architecture diagram (current)

```
Terminal:  main.py  ──► process_message() ──► message_processor.py
                              │
Web:       frontend ──► api.py (/chat/stream) ──► prepare_turn → chat_stream → finalize_response
                              │
Voice:     VoiceButton ──► /transcribe ──► text ──► same chat path
           VoiceButton ──► /tts ◄── last assistant reply
```

---

## What was NOT changed / deferred (per plan)

- No move to `backend/` / `services/` folders
- No user accounts, settings UI, cloud sync
- No ChromaDB / Pinecone / vector DB migration
- No Version 2 features (autonomous initiative, webcam, etc.)
- No automated benchmark numbers filled in (template only)
- No long multi-hour session test run on your machine

---

## What you still need to do on your machine

### 1. Python environment

```bash
cd /Users/dagi/companion
source venv/bin/activate          # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Confirm:

```bash
python -c "from api import app; print('OK')"
```

---

### 2. Environment variables

Create or update `.env` in the **project root** (same folder as `main.py`):

```env
OPENAI_API_KEY=sk-your-key-here

# Required only for voice playback (TTS):
ELEVENLABS_API_KEY=your-elevenlabs-key

# Optional — override default British voice in voice_service.py:
ELEVENLABS_VOICE_ID=your-voice-id
```

- **Chat + STT** need `OPENAI_API_KEY`.
- **TTS** needs `ELEVENLABS_API_KEY` or the play button will error.

---

### 3. Start the API server

```bash
uvicorn api:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# Expect: {"status":"ok","db":"ok"}
```

Optional sync chat test (uses OpenAI, costs tokens):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

Optional streaming test:

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

You should see `data: {"type":"token",...}` lines, then a `done` event.

---

### 4. Install and run the frontend

Requires **Node.js and npm** on your Mac (not bundled with the Python venv).

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:3000  

Keep the API running on port **8000** at the same time.

If the API is on another host/port, edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### 5. Terminal mode (optional)

Still works without the API:

```bash
python main.py
```

You should see `[RESPONSE TIME] X.XXs` each turn (full turn timing, not LLM-only).

---

### 6. Record benchmarks (recommended)

After a few real chats, fill in `benchmarks.md` with times from:

- Terminal: `[RESPONSE TIME]` lines, or
- API: `response_time_s` in `/chat` responses

Use varied prompts: greeting, stress/emotional, help request.

---

### 7. Voice smoke test

1. API running with both API keys set.  
2. Frontend open in Chrome (mic permission).  
3. **Hold** the microphone button, speak, release.  
4. Confirm message appears and JARVIS replies.  
5. Click **play** on last response for TTS.

If transcribe fails: check `OPENAI_API_KEY` and browser mic permission.  
If TTS fails: check `ELEVENLABS_API_KEY`.

---

### 8. Things that were NOT verified in the build environment

| Item | Your action |
|------|-------------|
| `npm install` / `npm run build` | Run locally; fix any Node version issues |
| Full OpenAI chat through API | Test with real key |
| ElevenLabs TTS | Test with real key |
| Extended 1–2 hour session / memory leaks | Manual soak test when ready |
| Git commit | Commit when you are satisfied |

---

## Quick troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `SyntaxError` in `personal_memory.py` | Should be fixed; pull latest / ensure save fix is present |
| `ImportError` on startup | Run from project root; activate venv; `pip install -r requirements.txt` |
| Frontend can’t connect | API not running; wrong `NEXT_PUBLIC_API_URL`; CORS (should allow :3000) |
| Stream shows text then jumps | Normal: `done` replaces raw stream with final formatted reply |
| Empty or instant LLM errors | Missing/invalid `OPENAI_API_KEY` — check terminal running uvicorn |
| Voice 503 | Missing API keys for transcribe/TTS |

---

## File inventory (project root, excluding `venv/`)

**Core Python:** `main.py`, `api.py`, `message_processor.py`, `session_state.py`, `llm.py`, `voice_service.py`, `config.py`, `memory.py`, plus all existing engines (`classifier.py`, `decision_engine.py`, …).

**Docs:** `README.md`, `API.md`, `benchmarks.md`, **this file** (`V1_IMPLEMENTATION_NOTES.md`).

**Frontend:** entire `frontend/` directory.

**Data:** `memory.db` (SQLite, unchanged location).

---

## Suggested order for first run

1. `pip install -r requirements.txt`  
2. Add `.env` with `OPENAI_API_KEY`  
3. `uvicorn api:app --reload --port 8000`  
4. `curl` health + one chat  
5. `cd frontend && npm install && npm run dev`  
6. Chat in browser  
7. Add ElevenLabs key → test voice  
8. Fill `benchmarks.md`  

---

*End of implementation notes.*
