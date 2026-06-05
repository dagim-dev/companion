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
ELEVENLABS_API_KEY=...          # optional, for TTS
ELEVENLABS_VOICE_ID=...         # optional
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
- Chat: `POST http://localhost:8000/chat`
- Stream: `POST http://localhost:8000/chat/stream` (SSE)
- Voice: `POST /transcribe`, `POST /tts`

See [API.md](API.md).

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (API must be running on port 8000).

## Architecture

- `main.py` — terminal entry
- `api.py` — FastAPI HTTP layer
- `message_processor.py` — full turn pipeline (prepare → LLM → finalize)
- `session_state.py` — per-session engines and conversation
- `llm.py` — OpenAI streaming + personality prompt
