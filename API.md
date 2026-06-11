# JARVIS HTTP API

Base URL (local): `http://localhost:8000`

Run server:

```bash
uvicorn api:app --reload --port 8000
```

## Authentication

Protected routes require `Authorization: Bearer <access_token>`.

Register or login to obtain a token:

- `POST /v1/auth/register` — body: `{"email": "...", "password": "..."}` (min 8 chars)
- `POST /v1/auth/login` — same body shape

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": "<uuid>"
}
```

Environment:

- `JWT_SECRET` — required when `ENV=production`
- `JWT_EXPIRE_MINUTES` — default `10080` (7 days)
- `CORS_ORIGINS` — comma-separated origins (default `http://localhost:3000`)
- `DATABASE_PATH` — SQLite file (default `memory.db`)

For local web dev without the login UI, set `NEXT_PUBLIC_DEV_TOKEN` in the frontend to a valid JWT.

Upgrade an existing single-user database:

```bash
python migrations/001_add_user_id.py
python migrations/002_companion_preferences.py
```

## GET /v1/auth/me

Returns `{ "user_id", "email", "onboarding_completed" }`. Use to route new users to onboarding.

## Companion preferences & onboarding

- `GET /v1/onboarding/roles` — role catalog (auth required)
- `POST /v1/onboarding/complete` — body: `{ "role_id", "communication", "energy", "address_as", "display_name?", "custom_notes?" }`
- `GET /v1/profile` — `{ "address_as", "name" }` (how Jarvis greets you)
- `PATCH /v1/profile` — body: `{ "address_as" }` (max 32 chars)
- `GET /v1/preferences` — current preferences
- `PUT /v1/preferences` — update role / communication / energy / notes
- `POST /v1/preferences/reset-learned` — clear runtime adaptation and `interaction_style` memories

Chat endpoints return **409** with `needs_onboarding` until onboarding is complete.

## GET /health

Returns service and database status (no auth).

```json
{"status": "ok", "db": "ok"}
```

## POST /v1/chat

Synchronous full turn (prepare → LLM → finalize). **Requires Bearer token.**

**Request**

```json
{"message": "Hello", "thread_id": null}
```

`thread_id` is reserved for future persisted threads (optional, no-op today).

**Response**

```json
{
  "response": "Good evening, Sir.",
  "intent": "casual",
  "emotion": "neutral",
  "response_time_s": 3.42
}
```

## POST /v1/chat/stream

Server-Sent Events (SSE). **Requires Bearer token.** Each event is one line:

```text
data: {"type":"token","content":"Hel"}

data: {"type":"done","content":"Hello, Sir. ...","intent":"casual","emotion":"neutral"}
```

| Event type | Meaning |
|------------|---------|
| `token` | Raw LLM token chunk (stream as received) |
| `done` | Final reply after `control_response` and rhythm |

The UI should show tokens live, then replace with `done.content` when the done event arrives.

## POST /v1/transcribe

Multipart audio upload → Whisper transcription. **Requires Bearer token.**

**Form:** `file` (audio webm/wav/mp3)

**Response**

```json
{"text": "transcribed speech"}
```

Requires `OPENAI_API_KEY`.

## POST /v1/tts

**Requires Bearer token.**

**Request**

```json
{"text": "Good evening, Sir."}
```

**Response:** `audio/mpeg` bytes.

Requires `ELEVENLABS_API_KEY` and optional `ELEVENLABS_VOICE_ID`.

## Session model (V2)

- **Database:** Per-user isolation via `user_id` on all memory tables.
- **In-memory:** One `JarvisState` (conversation + engines) per authenticated user in `state_store`. Restarting the server clears in-memory conversation history but keeps SQLite memories.
