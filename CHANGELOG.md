# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Version numbers below are inferred from git history — the repo has no release tags yet.

## [Unreleased]

### Added

- `personality_composer.py` — composes effective personality from onboarding sliders, learned modifiers, and runtime adaptation
- `learned_preferences.py` — aggregates memory-extraction insights into persistent style modifiers
- Async memory extraction: `memory_extraction_jobs.py`, `memory_extraction_worker.py`, `memory_insights.py` (background worker started on API startup)
- Migration `005_memory_extraction_jobs.py`
- Dev memory tooling: `api/routers/dev_memory.py`, `frontend/src/app/dev/memory-extraction/page.tsx`
- V2 preference fields in onboarding and settings (challenge, detail, examples, accountability)
- `POST /v1/preferences/reset-learned` — clear learned style modifiers
- Test suite expanded to 103 tests (cognition, follow-ups, extraction, preferences, message processor, personality)
- Documentation overhaul: `docs/ARCHITECTURE.md`, ADRs in `docs/decisions/`, `.env.example`, this changelog

### Changed

- Companion personality: slider-based prefs (`template_version: "2"`) replace six fixed YAML role templates
- `companion_prefs.py`, `prompt_builder.py`, `OnboardingWizard`, `SettingsPanel` updated for v2 preference model
- `memory_intelligence.py` — expanded insight extraction; hot path enqueues jobs instead of blocking on extraction
- `message_processor.py` — integrates personality composer and extraction job enqueue on finalize

### Removed

- Six YAML role templates in `prompts/roles/`
- `preference_consolidation.py` — replaced by `learned_preferences.py`

### Deprecated

- `role_id` on onboarding/preferences APIs — accepted for backward compatibility but always stored as `general_nova`; use sliders and learned preferences to shape personality

## [0.3.0] - 2026-06-12

### Added

- Unified `cognition_engine.py` — rules-first cognition, optional mini-LLM reasoning, behavior nudges, gated follow-up questions
- Tests for cognition engine (`tests/test_cognition_engine.py`)

### Changed

- `message_processor.py` — integrated cognition engine into turn pipeline
- `decision_engine.py` — added `apply_cognition_to_behavior()` for cognition-driven behavior knobs
- `llm.py` — system prompt now consumes `CognitionResult`
- `classifier.py` — extended signals for cognition heuristics

### Removed

- `thought_engine.py` — replaced by cognition engine
- `reasoning_engine.py` — replaced by cognition engine

## [0.2.1] - 2026-06-11

### Changed

- Episode resolution in `conversation_summarizer.py` — uses summary LLM to mark episodes as resolved/unresolved
- `episodic_memory.py` — improved episode lifecycle handling

## [0.2.0] - 2026-06-11

### Added

- `memory_followups.py` — gated follow-up question pipeline (policy in code, LLM for surface wording)
- Async SSE threading — `asyncio.to_thread()` offloading in `api/routers/chat.py` for non-blocking streams
- Migrations `003_conversations.py`, `004_followups.py`
- `Future change1.md` — SSE decision log and scaling roadmap
- Tests: `test_chat_stream_threading.py`, `test_memory_followups.py`, `test_internal_state.py`
- Expanded `internal_state.py` and `state_store.py` for V3 session improvements
- Conversation and followup tables in SQLite

### Changed

- `episodic_memory.py` — expanded episode handling
- `memory.py` — new tables and query paths for conversations and followups
- `curiosity_engine.py`, `memory_intelligence.py`, `message_processor.py` — integrated follow-up pipeline
- `api/routers/chat.py` — thread offloading for prepare, stream, finalize phases

### Removed

- `conversation_manager.py` — replaced by memory follow-ups
- `initiative_engine.py` — replaced by memory follow-ups
- `self_model.py` — replaced by internal state improvements
- `response_controller.py` — logic consolidated elsewhere
- `V1_IMPLEMENTATION_NOTES.md` — superseded by architecture docs

## [0.1.1] - 2026-06-05

### Added

- V2 multi-user platform: JWT auth, `/v1/*` API routers, onboarding, role-based prompts, settings UI
- `auth_jwt.py`, `auth_store.py` — user accounts and token handling
- `api/` package with routers: auth, chat, onboarding, preferences, profile, voice, health
- `companion_prefs.py`, `prompt_builder.py` — six companion roles via YAML templates
- `memory_scope.py`, `state_store.py` — per-user DB scoping and session cache
- Migrations `001_add_user_id.py`, `002_companion_preferences.py`
- Next.js frontend: auth gate, onboarding wizard, settings panel, voice controls
- Voice gating via `voice_capabilities.py` and expanded `/health` payload
- Structured logging (`logging_config.py`)

### Changed

- API routes moved under `/v1/*` (health stays at `/health`)
- SQLite schema: `user_id` on all memory tables
- Personality: from fixed `SYSTEM_PERSONALITY` to YAML roles + slider preferences

## [0.1.0] - 2026-06-05

### Added

- Initial NOVA Companion V1
- Terminal CLI (`main.py`) and monolithic HTTP API
- Turn pipeline: `message_processor.py` (prepare → LLM → finalize)
- Cognitive engines: classifier, decision engine, reflection, curiosity, meta-cognition, rhythm
- SQLite memory: profiles, personal memories, emotional history, reflections, episodes
- OpenAI integration for chat and streaming
- Optional voice: Whisper STT, ElevenLabs TTS

[Unreleased]: https://github.com/dagim-dev/companion/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/dagim-dev/companion/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/dagim-dev/companion/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dagim-dev/companion/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/dagim-dev/companion/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dagim-dev/companion/releases/tag/v0.1.0
