# JARVIS HTTP API

Reference for the Companion backend HTTP API (FastAPI `2.0.0`).

**Base URL (local):** `http://localhost:8000`

**Interactive docs:** `http://localhost:8000/docs` (OpenAPI / Swagger UI)

---

## Table of contents

1. [Quick start](#quick-start)
2. [Environment](#environment)
3. [Database migrations](#database-migrations)
4. [Authentication](#authentication)
5. [Health](#health)
6. [Onboarding](#onboarding)
7. [Preferences](#preferences)
8. [Learned preferences](#learned-preferences)
9. [Profile](#profile)
10. [Chat](#chat)
11. [Voice](#voice)
12. [Dev: memory extraction](#dev-memory-extraction)
13. [Session model](#session-model)

---

## Quick start

```bash
uvicorn api:app --reload --port 8000
```

Most routes live under `/v1/*`. Health is at `/health`.

**Auth header** (protected routes):

```http
Authorization: Bearer <access_token>
```

For local web dev without the login UI, set `NEXT_PUBLIC_DEV_TOKEN` in the frontend to a valid JWT.

---

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENV` | `development` | Set to `production` in prod; hides dev-only routes |
| `JWT_SECRET` | — | **Required** when `ENV` is not `development` |
| `JWT_EXPIRE_MINUTES` | `10080` (7 days) | Access token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed origins |
| `DATABASE_PATH` | `memory.db` | SQLite database file |
| `OPENAI_API_KEY` | — | LLM + speech-to-text (Whisper) |
| `ELEVENLABS_API_KEY` | — | Text-to-speech |
| `ELEVENLABS_VOICE_ID` | Daniel (British) | Optional TTS voice override |
| `VOICE_ENABLED` | `true` | Master switch for `/v1/transcribe` and `/v1/tts` |

---

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

| Migration | What it adds |
|-----------|--------------|
| `001` | `user_id` columns for multi-user isolation |
| `002` | `companion_preferences` table |
| `003` | `conversations` table (message persistence) |
| `004` | Episode `resolved` column, `followup_state` table |
| `005` | `memory_extraction_jobs`, expanded `learned_preferences` schema |

---

## Authentication

### Register

`POST /v1/auth/register` — no auth required

**Request**

```json
{
  "email": "you@example.com",
  "password": "password123"
}
```

Password minimum length: 8 characters.

**Response `200`**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": "<uuid>"
}
```

**Errors:** `409` if email is already registered.

---

### Login

`POST /v1/auth/login` — no auth required

Same request body as register.

**Response `200`:** same shape as register.

**Errors:** `401` for invalid email or password.

---

### Current user

`GET /v1/auth/me` — **auth required**

**Response `200`**

```json
{
  "user_id": "<uuid>",
  "email": "you@example.com",
  "onboarding_completed": true
}
```

Use `onboarding_completed` to route new users to onboarding before chat.

---

## Health

`GET /health` — no auth required

**Response `200`**

```json
{
  "status": "ok",
  "db": "ok",
  "voice": {
    "enabled": true,
    "stt_configured": true,
    "tts_configured": true,
    "available": true
  }
}
```

| Field | Meaning |
|-------|---------|
| `status` | Service is running |
| `db` | `"ok"` or `"error: …"` if SQLite is unreachable |
| `voice.enabled` | `VOICE_ENABLED` env flag |
| `voice.stt_configured` | `OPENAI_API_KEY` is set |
| `voice.tts_configured` | `ELEVENLABS_API_KEY` is set |
| `voice.available` | `enabled` and both keys configured |

No secrets are exposed in this payload.

---

## Onboarding

Chat endpoints return **409** until onboarding is complete (see [Chat errors](#errors)).

### Role catalog

`GET /v1/onboarding/roles` — no auth required

**Response `200`**

```json
[
  {
    "id": "general_jarvis",
    "title": "General JARVIS",
    "description": "Balanced, capable companion for everyday use"
  }
]
```

---

### Complete onboarding

`POST /v1/onboarding/complete` — **auth required**

**Request** — all fields except `address_as` have defaults:

```json
{
  "role_id": "general_jarvis",
  "communication": "balanced",
  "energy": "calm",
  "challenge_level": "medium",
  "emotional_support": "medium",
  "detail_level": "normal",
  "examples_preference": "when_useful",
  "accountability_style": "steady",
  "address_as": "Sir",
  "display_name": "You",
  "custom_notes": "Optional free-text notes"
}
```

| Field | Allowed values |
|-------|----------------|
| `communication` | `direct`, `balanced`, `gentle` |
| `energy` | `calm`, `upbeat` |
| `challenge_level` | `low`, `medium`, `high` |
| `emotional_support` | `low`, `medium`, `high` |
| `detail_level` | `concise`, `normal`, `detailed` |
| `examples_preference` | `few`, `when_useful`, `often` |
| `accountability_style` | `light`, `steady`, `firm` |
| `address_as` | 1–32 chars (required) |
| `display_name` | max 64 chars (optional) |
| `custom_notes` | max 300 chars (optional) |

**Response `200`:** [PreferencesResponse](#preferencesresponse) (same shape as `GET /v1/preferences`).

**Errors:** `400` for invalid field values.

---

## Preferences

### PreferencesResponse

Returned by onboarding complete, `GET /v1/preferences`, and `PUT /v1/preferences`.

```json
{
  "role_id": "general_jarvis",
  "communication": "balanced",
  "energy": "calm",
  "challenge_level": "medium",
  "emotional_support": "medium",
  "detail_level": "normal",
  "examples_preference": "when_useful",
  "accountability_style": "steady",
  "sliders": {
    "directness": 0.6,
    "warmth": 0.55,
    "humor": 0.35,
    "verbosity": 0.5,
    "accountability": 0.5,
    "emotional_support": 0.5
  },
  "baseline_directives": {
    "examples_frequency": "when_useful"
  },
  "custom_notes": "",
  "onboarding_completed": true,
  "template_version": "2"
}
```

---

### Get preferences

`GET /v1/preferences` — **auth required**

**Response `200`:** [PreferencesResponse](#preferencesresponse)

**Errors:** `404` if onboarding has not been completed.

---

### Update preferences

`PUT /v1/preferences` — **auth required**

Send only the fields you want to change. Omitted fields are left unchanged.

```json
{
  "role_id": "general_jarvis",
  "communication": "direct",
  "energy": "upbeat",
  "challenge_level": "high",
  "emotional_support": "low",
  "detail_level": "concise",
  "examples_preference": "often",
  "accountability_style": "firm",
  "sliders": { "verbosity": 0.8 },
  "custom_notes": "Updated notes"
}
```

**Response `200`:** [PreferencesResponse](#preferencesresponse)

Clears the in-memory session cache for the user so changes take effect on the next message.

**Errors:** `400` for invalid field values.

---

### Reset personality

`POST /v1/preferences/reset-learned` — **auth required**

Reset learned or runtime personality state. Body is optional.

```json
{
  "scope": "learned"
}
```

| `scope` | Effect |
|---------|--------|
| `learned` (default) | Clear learned preferences extracted from conversation |
| `runtime` | Clear runtime personality adaptation (session-level tweaks) |
| `baseline` | Reset baseline style fields to defaults (`communication`, `energy`, challenge/support/detail/examples/accountability) |
| `all_personality` | Clear learned preferences **and** reset baseline fields |

**Response `200`**

```json
{
  "status": "ok",
  "message": "Personality reset applied: learned."
}
```

Clears the in-memory session cache for the user.

---

## Learned preferences

Preferences inferred from conversation (background memory extraction). Distinct from explicit settings in [Preferences](#preferences).

### List learned preferences

`GET /v1/preferences/learned` — **auth required**

Returns up to 50 active learned preferences, ordered by pin status, confidence, and recency.

**Response `200`** — array of objects:

```json
[
  {
    "id": 1,
    "user_id": "<uuid>",
    "preference_key": "response.length",
    "category": "response",
    "value": { "target": "concise" },
    "scope": "global",
    "context": null,
    "confidence": 0.85,
    "source_count": 3,
    "positive_evidence_count": 3,
    "negative_evidence_count": 0,
    "status": "active",
    "origin": "extracted",
    "is_pinned": 0,
    "first_seen_at": "2026-06-19T10:00:00",
    "last_seen_at": "2026-06-19T12:00:00",
    "last_confirmed_at": null,
    "last_applied_at": null,
    "decays_after": null,
    "replaces_preference_id": null,
    "created_at": "2026-06-19T10:00:00",
    "updated_at": "2026-06-19T12:00:00"
  }
]
```

`value` and `context` are parsed from JSON columns (`value_json`, `context_json`).

---

### Disable one learned preference

`DELETE /v1/preferences/learned/{preference_id}` — **auth required**

Marks a single learned preference as disabled (suppressed). Does not delete history.

**Response `200`**

```json
{
  "status": "ok",
  "message": "Learned preference disabled."
}
```

Clears the in-memory session cache for the user.

---

## Profile

How the companion addresses you in conversation.

### Get profile

`GET /v1/profile` — **auth required**

**Response `200`**

```json
{
  "address_as": "Sir",
  "name": "You"
}
```

Either field may be `null` if not set.

---

### Update profile

`PATCH /v1/profile` — **auth required**

```json
{
  "address_as": "Sir"
}
```

`address_as` is required, 1–32 characters.

**Response `200`:** same shape as get profile.

`name` is set during onboarding via `display_name` and is not updated by this endpoint.

---

## Chat

Both endpoints require **auth** and completed onboarding.

### Synchronous chat

`POST /v1/chat`

**Request**

```json
{
  "message": "Hello",
  "thread_id": null
}
```

`thread_id` is reserved for future persisted threads (optional, no-op today). Messages are persisted internally; there is no conversations REST API yet.

**Response `200`**

```json
{
  "response": "Good evening, Sir.",
  "intent": "casual",
  "emotion": "neutral",
  "response_time_s": 3.42
}
```

---

### Streaming chat

`POST /v1/chat/stream`

Same request body as synchronous chat. Returns **Server-Sent Events** (`text/event-stream`).

Each event is one line:

```text
data: {"type":"token","content":"Hel"}

data: {"type":"done","content":"Hello, Sir. ...","intent":"casual","emotion":"neutral"}
```

| Event `type` | Fields | Meaning |
|--------------|--------|---------|
| `token` | `content` | Raw LLM token chunk |
| `done` | `content`, `intent`, `emotion?` | Final reply after post-processing |

The UI should render tokens live, then replace with `done.content` when the done event arrives.

Heavy work (prepare, stream, finalize) runs in thread pool workers so the event loop stays responsive.

---

### Errors

| Status | When |
|--------|------|
| `400` | Empty or whitespace-only `message` |
| `409` | Onboarding not complete |

**409 body**

```json
{
  "detail": {
    "code": "needs_onboarding",
    "message": "Complete companion onboarding before chatting."
  }
}
```

---

## Voice

Both endpoints require **auth**. Return **503** when voice is disabled (`VOICE_ENABLED=false`) or required API keys are missing.

### Transcribe

`POST /v1/transcribe`

**Request:** `multipart/form-data` with field `file` (audio: webm, wav, mp3, etc.)

**Response `200`**

```json
{
  "text": "transcribed speech"
}
```

**Errors:** `400` for missing or empty file; `503` when STT is unavailable.

Requires `OPENAI_API_KEY` and `VOICE_ENABLED=true`.

---

### Text-to-speech

`POST /v1/tts`

**Request**

```json
{
  "text": "Good evening, Sir."
}
```

**Response `200`:** `audio/mpeg` bytes.

**Errors:** `400` for empty text; `503` when TTS is unavailable.

Requires `ELEVENLABS_API_KEY` and `VOICE_ENABLED=true`. Optional `ELEVENLABS_VOICE_ID` selects the voice.

Check `GET /health` → `voice` before enabling voice UI controls.

---

## Dev: memory extraction

Development-only endpoints for inspecting background memory-extraction jobs. **Hidden in production** (`ENV=production` returns `404`).

Both require **auth**.

### Extraction health

`GET /v1/dev/memory-extraction/health`

**Response `200`**

```json
{
  "pending": 0,
  "processing": 0,
  "completed": 42,
  "pending_retry": 1,
  "failed_permanently": 2,
  "success_rate": 0.9545,
  "last_failure_reason": "LLM timeout",
  "last_failed_job": {
    "id": 15,
    "message_id": 88,
    "status": "pending_retry",
    "retry_count": 1,
    "error": "LLM timeout",
    "created_at": "2026-06-19T10:00:00",
    "completed_at": null
  },
  "total_jobs_processed": 44,
  "show_warning": false,
  "warning_message": null
}
```

`show_warning` is `true` when `pending_retry > 5`; `warning_message` describes the backlog.

---

### Recent jobs

`GET /v1/dev/memory-extraction/jobs` — **auth required**

**Query parameters**

| Param | Default | Range |
|-------|---------|-------|
| `limit` | `20` | 1–100 |

**Response `200`** — array of job records:

```json
[
  {
    "id": 15,
    "message_id": 88,
    "status": "pending_retry",
    "retry_count": 1,
    "error": "LLM timeout",
    "created_at": "2026-06-19T10:00:00",
    "next_retry_at": "2026-06-19T10:01:00",
    "completed_at": null
  }
]
```

Job statuses: `pending`, `processing`, `completed`, `pending_retry`, `failed_permanently`.

---

## Session model

| Layer | Behavior |
|-------|----------|
| **Database** | Per-user isolation via `user_id` on all memory tables. Conversations, episodes, learned preferences, and extraction jobs persist across restarts. |
| **In-memory** | One `JarvisState` (conversation context + engines) per authenticated user in `state_store`. Server restart clears in-memory history but keeps SQLite data. |
| **Background worker** | Memory extraction worker starts on API startup. After each user message, jobs may be enqueued to extract learned preferences asynchronously. |

Preference or learned-preference changes that affect personality clear the in-memory cache so the next turn picks up new settings.
