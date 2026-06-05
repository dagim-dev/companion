"""Voice feature availability — keys, env flag, and stable API errors."""

from __future__ import annotations

from config import (
    ELEVENLABS_API_KEY,
    OPENAI_API_KEY,
    VOICE_ENABLED,
)


class VoiceUnavailableError(Exception):
    """Raised when voice cannot run; map to HTTP 503 with a safe message."""

    def __init__(self, message: str, *, reason: str = "unavailable") -> None:
        super().__init__(message)
        self.reason = reason


def voice_status() -> dict[str, bool | str]:
    """For /health and frontend — no secrets."""
    enabled = VOICE_ENABLED
    stt_ready = bool(OPENAI_API_KEY)
    tts_ready = bool(ELEVENLABS_API_KEY)
    return {
        "enabled": enabled,
        "stt_configured": stt_ready,
        "tts_configured": tts_ready,
        "available": enabled and stt_ready and tts_ready,
    }


def require_voice_enabled() -> None:
    if not VOICE_ENABLED:
        raise VoiceUnavailableError(
            "Voice is disabled on this server.",
            reason="disabled",
        )


def require_stt() -> None:
    require_voice_enabled()
    if not OPENAI_API_KEY:
        raise VoiceUnavailableError(
            "Speech-to-text is unavailable (OPENAI_API_KEY not configured).",
            reason="missing_openai_key",
        )


def require_tts() -> None:
    require_voice_enabled()
    if not ELEVENLABS_API_KEY:
        raise VoiceUnavailableError(
            "Text-to-speech is unavailable (ELEVENLABS_API_KEY not configured).",
            reason="missing_elevenlabs_key",
        )
