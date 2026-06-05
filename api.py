import json
import traceback
from typing import AsyncIterator

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from memory import get_connection, init_db
from message_processor import (
    PreparedTurn,
    finalize_response,
    prepare_turn,
    process_message,
    stream_llm_tokens,
)
from session_state import JarvisState, create_state
from voice_service import synthesize_speech, transcribe_audio

app = FastAPI(title="JARVIS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: JarvisState | None = None


def get_state() -> JarvisState:
    global _state
    if _state is None:
        _state = create_state()
    return _state


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Apologies, Sir. An internal fault occurred. "
                "Please try again shortly."
            ),
        },
    )


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str | None = None
    emotion: str | None = None
    response_time_s: float | None = None


class TTSRequest(BaseModel):
    text: str


class TranscribeResponse(BaseModel):
    text: str


@app.get("/health")
def health() -> dict:
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok", "db": db_status}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest) -> ChatResponse:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    try:
        result = process_message(get_state(), body.message, echo_to_terminal=False)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        response=result["response"],
        intent=result.get("intent"),
        emotion=result.get("emotion"),
        response_time_s=result.get("response_time_s"),
    )


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _chat_stream_events(message: str) -> AsyncIterator[str]:
    state = get_state()
    turn: PreparedTurn | None = prepare_turn(state, message)

    if turn is None:
        text = (
            "I'm not entirely sure what you're aiming for there. "
            "Clarify, or should I take an educated guess?"
        )
        yield _sse_event({"type": "token", "content": text})
        yield _sse_event(
            {
                "type": "done",
                "content": text,
                "intent": "uncertain",
            }
        )
        return

    raw_parts: list[str] = []
    for token in stream_llm_tokens(state, turn, echo_to_terminal=False):
        raw_parts.append(token)
        yield _sse_event({"type": "token", "content": token})

    raw_response = "".join(raw_parts)
    final_response = finalize_response(state, turn, raw_response)

    yield _sse_event(
        {
            "type": "done",
            "content": final_response,
            "intent": turn.intent,
            "emotion": turn.emotion,
        }
    )


@app.post("/chat/stream")
async def chat_stream_endpoint(body: ChatRequest) -> StreamingResponse:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    return StreamingResponse(
        _chat_stream_events(body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(file: UploadFile = File(...)) -> TranscribeResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="audio file is required")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty audio file")

    try:
        text = transcribe_audio(data, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Transcription failed",
        ) from exc

    return TranscribeResponse(text=text)


@app.post("/tts")
async def tts_endpoint(body: TTSRequest) -> Response:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    try:
        audio = synthesize_speech(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="TTS failed") from exc

    return Response(content=audio, media_type="audio/mpeg")
