# JARVIS HTTP API

Base URL (local): `http://localhost:8000`

Run server:

```bash
uvicorn api:app --reload --port 8000
```

## GET /health

Returns service and database status.

```json
{"status": "ok", "db": "ok"}
```

## POST /chat

Synchronous full turn (prepare → LLM → finalize).

**Request**

```json
{"message": "Hello"}
```

**Response**

```json
{
  "response": "Good evening, Sir.",
  "intent": "casual",
  "emotion": "neutral",
  "response_time_s": 3.42
}
```

## POST /chat/stream

Server-Sent Events (SSE). Each event is one line:

```text
data: {"type":"token","content":"Hel"}

data: {"type":"done","content":"Hello, Sir. ...","intent":"casual","emotion":"neutral"}
```

| Event type | Meaning |
|------------|---------|
| `token` | Raw LLM token chunk (stream as received) |
| `done` | Final reply after `control_response`, rhythm, initiative |

The UI should show tokens live, then replace with `done.content` when the done event arrives.

## POST /transcribe

Multipart audio upload → Whisper transcription.

**Form:** `file` (audio webm/wav/mp3)

**Response**

```json
{"text": "transcribed speech"}
```

Requires `OPENAI_API_KEY`.

## POST /tts

**Request**

```json
{"text": "Good evening, Sir."}
```

**Response:** `audio/mpeg` bytes.

Requires `ELEVENLABS_API_KEY` and optional `ELEVENLABS_VOICE_ID`.

## Session model (V1)

Single in-memory session per server process. Restarting the server clears conversation history.
