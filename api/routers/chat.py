import json
import traceback
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import get_state
from api.schemas import ChatRequest, ChatResponse
from companion_prefs import is_onboarding_complete
from memory_scope import user_scope
from message_processor import (
    PreparedTurn,
    finalize_response,
    prepare_turn,
    process_message,
    stream_llm_tokens,
)
from session_state import JarvisState

router = APIRouter(prefix="/v1", tags=["chat"])


def _require_onboarding(user_id: str) -> None:
    if not is_onboarding_complete(user_id):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "needs_onboarding",
                "message": "Complete companion onboarding before chatting.",
            },
        )


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _chat_stream_events(state: JarvisState, message: str) -> AsyncIterator[str]:
    # ContextVar must be set in the same execution context as sync pipeline code.
    with user_scope(state.user_id):
        async for event in _chat_stream_events_scoped(state, message):
            yield event


async def _chat_stream_events_scoped(
    state: JarvisState, message: str
) -> AsyncIterator[str]:
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


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    body: ChatRequest,
    state: Annotated[JarvisState, Depends(get_state)],
) -> ChatResponse:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    _require_onboarding(state.user_id)

    try:
        with user_scope(state.user_id):
            result = process_message(state, body.message, echo_to_terminal=False)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        response=result["response"],
        intent=result.get("intent"),
        emotion=result.get("emotion"),
        response_time_s=result.get("response_time_s"),
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(
    body: ChatRequest,
    state: Annotated[JarvisState, Depends(get_state)],
) -> StreamingResponse:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    _require_onboarding(state.user_id)

    return StreamingResponse(
        _chat_stream_events(state, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
