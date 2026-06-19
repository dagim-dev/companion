# JARVIS Companion

A locally run, JARVIS-style AI companion with long-term memory, a cognition pipeline, adaptive personality, and optional voice. Built for developers and power users who want a personal assistant they control — not a hosted SaaS.

**Stack:** Python 3.11 (FastAPI + flat domain modules) · SQLite · Next.js 15 frontend · OpenAI · ElevenLabs (optional)

## What it does

- Conversational AI with Jarvis-style personality, customized via onboarding sliders, learned preferences, and per-turn runtime adaptation
- Long-term memory: personal facts, emotional history, reflections, episodic summaries, learned preferences
- Cognition pipeline: intent/emotion classification, rules-first cognition with optional mini-LLM reasoning, behavior and rhythm control
- Async memory extraction: background worker learns insights from messages after each turn
- Optional voice: Whisper STT + ElevenLabs TTS
- Multi-user web app: JWT auth, registration, onboarding wizard, settings panel
- CLI mode: terminal chat for local development

## Prerequisites

- **Python 3.11**
- **Node.js 18+** and npm (for the web UI)
- **OpenAI API key** (required for chat, cognition, memory extraction, and STT)
- **ElevenLabs API key** (optional; required only if `VOICE_ENABLED=true`)

## Install

```bash
git clone https://github.com/dagim-dev/companion.git
cd companion

python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # edit with your API keys
```

## Configure environment

Copy `.env.example` to `.env` and set at minimum:

```env
OPENAI_API_KEY=sk-your-key-here
JWT_SECRET=change-me-in-production
```

See [.env.example](.env.example) for all variables. For the frontend, see [frontend/.env.local.example](frontend/.env.local.example).

## Run locally

You need two terminals: API server and frontend.

**Terminal 1 — API** (initializes SQLite, starts memory extraction worker):

```bash
source .venv/bin/activate
uvicorn api:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Register or sign in, complete the onboarding wizard, then chat.

Health check: http://localhost:8000/health

## CLI mode

Terminal chat without the web UI (uses `CLI_USER_ID=local-dev`, auto-completes onboarding):

```bash
source .venv/bin/activate
python main.py
```

Type `exit` to quit.

## API usage example

With the API running on port 8000:

```bash
# Register a new account
curl -s -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

# Save the access_token from the response, then complete onboarding
export TOKEN="<access_token from register response>"

curl -s -X POST http://localhost:8000/v1/onboarding/complete \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"communication":"direct","energy":"calm","challenge_level":"medium","detail_level":"normal","address_as":"Sir","display_name":"You"}'

# Chat
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"What do you remember about me?"}'
```

Chat returns **409** with `needs_onboarding` until onboarding is complete. See [API.md](API.md) for all endpoints (streaming, voice, preferences, profile).

## Database migrations

**Fresh install:** No migration scripts needed. `init_db()` runs on API startup and creates the full schema.

**Upgrading an existing `memory.db`** from an earlier version, run once:

```bash
python migrations/001_add_user_id.py
python migrations/002_companion_preferences.py
python migrations/003_conversations.py
python migrations/004_followups.py
python migrations/005_memory_extraction_jobs.py
```

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -q
```

## Project layout

```
companion/
├── main.py                 # CLI entry point
├── api.py                  # uvicorn shim → api.main:app
├── api/                    # FastAPI routers (auth, chat, voice, …)
├── message_processor.py    # Turn pipeline orchestration
├── cognition_engine.py     # Rules-first cognition + optional LLM
├── memory.py               # SQLite persistence
├── frontend/               # Next.js web UI
├── migrations/             # One-shot DB upgrade scripts
├── tests/                  # pytest suite
└── docs/                   # Architecture and ADRs
```

## Companion personality

Personality is composed at runtime from three layers (see `personality_composer.py`):

1. **Onboarding sliders** — communication style, energy, challenge, detail level, examples, accountability, and emotional support (set in the onboarding wizard or settings panel)
2. **Learned preferences** — style modifiers inferred asynchronously from conversation by the memory extraction worker
3. **Runtime modifiers** — short-lived adjustments per turn (e.g. stress → grounding) from the cognition pipeline

The API still accepts `role_id` for backward compatibility, but only `general_jarvis` is used; the six fixed YAML role templates were removed in favor of this composable model.

## Further reading

- [API.md](API.md) — HTTP endpoint reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design and component map
- [docs/decisions/](docs/decisions/) — architecture decision records
- [CHANGELOG.md](CHANGELOG.md) — release history
