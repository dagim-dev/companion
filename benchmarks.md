# JARVIS response time benchmarks 

End-to-end turn time from `process_message` (`response_time_s` in API or `[RESPONSE TIME]` in terminal).

| Date | Prompt type | Seconds | Notes |
|------|-------------|---------|-------|
| 2026-05-30 | greeting | 1.45 | curl POST /chat — "Hello" |
| 2026-05-30 | emotional | 1.75 | curl POST /chat — stressed about work |
| 2026-05-30 | help_request | 1.28 | curl POST /chat — plan my week |

**Suggested prompts:** short greeting, emotional/stress message, help request.

**Phase 6 latency audit:** also measure STT (`POST /transcribe`), time-to-first-token (`POST /chat/stream`), and TTS (`POST /tts`).
