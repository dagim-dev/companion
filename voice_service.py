import traceback
from io import BytesIO

import httpx
from openai import OpenAI

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY
from voice_capabilities import VoiceUnavailableError, require_stt, require_tts

MIN_AUDIO_BYTES = 256

_openai_client: OpenAI | None = None


def _elevenlabs_error_message(response: httpx.Response) -> str | None:
    try:
        body = response.json()
        detail = body.get("detail")
        if isinstance(detail, dict) and detail.get("message"):
            return str(detail["message"])
        if isinstance(detail, str):
            return detail
    except Exception:
        pass
    return None


def _openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    require_stt()
    if len(file_bytes) < MIN_AUDIO_BYTES:
        raise VoiceUnavailableError(
            "Audio recording is too short or invalid.",
            reason="invalid_audio",
        )

    buffer = BytesIO(file_bytes)
    buffer.name = filename

    try:
        result = _openai().audio.transcriptions.create(
            model="whisper-1",
            file=buffer,
        )
        return (result.text or "").strip()
    except Exception as exc:
        print("[TRANSCRIBE ERROR]")
        traceback.print_exc()
        raise VoiceUnavailableError(
            "Transcription failed. Check audio format and OPENAI_API_KEY.",
            reason="transcribe_failed",
        ) from exc


def _validate_voice_id() -> None:
    vid = (ELEVENLABS_VOICE_ID or "").strip()
    if not vid:
        raise VoiceUnavailableError(
            "ELEVENLABS_VOICE_ID is not set in .env.",
            reason="missing_voice_id",
        )
    if vid.startswith("sk_"):
        raise VoiceUnavailableError(
            "ELEVENLABS_VOICE_ID looks like an API key (starts with sk_). "
            "Put the API key in ELEVENLABS_API_KEY only. "
            "Set ELEVENLABS_VOICE_ID to a voice ID from ElevenLabs → Voices → Copy voice ID.",
            reason="voice_id_is_api_key",
        )


def synthesize_speech(text: str) -> bytes:
    require_tts()
    _validate_voice_id()
    if not text.strip():
        raise VoiceUnavailableError("text is empty", reason="invalid_text")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as exc:
        print("[TTS ERROR]")
        traceback.print_exc()
        api_message = _elevenlabs_error_message(exc.response)
        if exc.response.status_code in (401, 403):
            if api_message:
                raise VoiceUnavailableError(api_message, reason="tts_auth_failed") from exc
            raise VoiceUnavailableError(
                "Text-to-speech rejected your ElevenLabs API key (401/403). "
                "Create a new key at elevenlabs.io → Profile → API keys with "
                "Text-to-Speech enabled, update ELEVENLABS_API_KEY, restart uvicorn.",
                reason="tts_auth_failed",
            ) from exc
        if exc.response.status_code == 404:
            raise VoiceUnavailableError(
                "Voice not found (404). ELEVENLABS_VOICE_ID must be a voice ID "
                "(from ElevenLabs → Voices → ⋮ → Copy voice ID), not your API key. "
                "Example format: onwK4e9ZLuTAKqWW03F9. Restart uvicorn after fixing .env.",
                reason="voice_not_found",
            ) from exc
        raise VoiceUnavailableError(
            f"Text-to-speech failed (HTTP {exc.response.status_code}).",
            reason="tts_failed",
        ) from exc
    except Exception as exc:
        print("[TTS ERROR]")
        traceback.print_exc()
        raise VoiceUnavailableError(
            "Text-to-speech failed. Check ELEVENLABS_API_KEY and voice ID.",
            reason="tts_failed",
        ) from exc
