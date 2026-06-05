import traceback
from io import BytesIO

import httpx
from openai import OpenAI

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY

_openai_client: OpenAI | None = None


def _openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    buffer = BytesIO(file_bytes)
    buffer.name = filename

    try:
        result = _openai().audio.transcriptions.create(
            model="whisper-1",
            file=buffer,
        )
        return (result.text or "").strip()
    except Exception:
        print("[TRANSCRIBE ERROR]")
        traceback.print_exc()
        raise


def synthesize_speech(text: str) -> bytes:
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY is not set")
    if not text.strip():
        raise ValueError("text is empty")

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
    except Exception:
        print("[TTS ERROR]")
        traceback.print_exc()
        raise
