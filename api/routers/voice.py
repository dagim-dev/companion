import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from api.deps import get_state
from api.schemas import TranscribeResponse, TTSRequest
from voice_capabilities import VoiceUnavailableError
from voice_service import synthesize_speech, transcribe_audio

VOICE_UNAVAILABLE_DETAIL = "Voice service unavailable"
MAX_AUDIO_UPLOAD_BYTES = 10 * 1024 * 1024
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["voice"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(
    _state: Annotated[object, Depends(get_state)],
    file: UploadFile = File(...),
) -> TranscribeResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="audio file is required")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty audio file")
    if len(data) > MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"audio file exceeds {MAX_AUDIO_UPLOAD_BYTES} bytes",
        )

    try:
        text = transcribe_audio(data, filename=file.filename)
    except VoiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=exc.args[0] if exc.args else VOICE_UNAVAILABLE_DETAIL,
        ) from exc
    except Exception as exc:
        logger.exception("transcribe_request_failed")
        raise HTTPException(
            status_code=503,
            detail=VOICE_UNAVAILABLE_DETAIL,
        ) from exc

    return TranscribeResponse(text=text)


@router.post("/tts")
async def tts_endpoint(
    body: TTSRequest,
    _state: Annotated[object, Depends(get_state)],
) -> Response:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    try:
        audio = synthesize_speech(body.text)
    except VoiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=exc.args[0] if exc.args else VOICE_UNAVAILABLE_DETAIL,
        ) from exc
    except Exception as exc:
        logger.exception("tts_request_failed")
        raise HTTPException(
            status_code=503,
            detail=VOICE_UNAVAILABLE_DETAIL,
        ) from exc

    return Response(content=audio, media_type="audio/mpeg")
