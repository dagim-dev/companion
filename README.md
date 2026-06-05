# JARVIS Companion (V1)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=sk_...       # TTS only — NOT the voice ID
ELEVENLABS_VOICE_ID=onwK4e9ZLuTAKqWW03F9   # voice ID from Voices → ⋮ → Copy voice ID (not sk_...)
VOICE_ENABLED=true              # set false to disable mic/TTS until keys are verified
JWT_SECRET=change-me-in-production
CORS_ORIGINS=http://localhost:3000
```

If you have an existing `memory.db` from single-user mode, run once:

```bash
python migrations/001_add_user_id.py
```

## Terminal

```bash
python main.py
```

## API server

```bash
uvicorn api:app --reload --port 8000
```

- Health: `GET http://localhost:8000/health`
- Auth: `POST /v1/auth/register`, `POST /v1/auth/login`
- Chat: `POST /v1/chat` (Bearer token)
- Stream: `POST /v1/chat/stream` (SSE, Bearer token)
- Voice: `POST /v1/transcribe`, `POST /v1/tts` (Bearer token)

See [API.md](API.md).

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (API must be running on port 8000). Register or sign in on first load; optional `NEXT_PUBLIC_DEV_TOKEN` for token-only local testing.

## Architecture

- `main.py` — terminal entry
- `api/` — FastAPI HTTP layer (`api.py` shim for `uvicorn api:app`)
- `auth_store.py`, `auth_jwt.py` — users table + JWT
- `state_store.py`, `memory_scope.py` — per-user session and DB scope
- `message_processor.py` — full turn pipeline (prepare → LLM → finalize)
- `session_state.py` — per-session engines and conversation
- `llm.py` — OpenAI streaming + personality prompt
