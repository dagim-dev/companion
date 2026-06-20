import asyncio
import json
import traceback
from typing import Annotated, AsyncIterator, Callable, Iterator, TypeVar, cast

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
from session_state import NovaState

router = APIRouter(prefix="/v1", tags=["chat"])

T = TypeVar("T")
_STREAM_END = object()


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


async def _to_thread_with_user_scope(
    user_id: str,
    func: Callable[..., T],
    *args,
    **kwargs,
) -> T:
    def run_scoped() -> T:
        with user_scope(user_id):
            return func(*args, **kwargs)

    return await asyncio.to_thread(run_scoped)


def _next_llm_token_scoped(
    user_id: str,
    tokens: Iterator[str],
) -> str | object:
    with user_scope(user_id):
        return next(tokens, _STREAM_END)


async def _stream_llm_tokens_threaded(
    state: NovaState,
    turn: PreparedTurn,
) -> AsyncIterator[str]:
    tokens = stream_llm_tokens(state, turn, echo_to_terminal=False)

    while True:
        item = await asyncio.to_thread(
            _next_llm_token_scoped,
            state.user_id,
            tokens,
        )
        if item is _STREAM_END:
            return
        yield cast(str, item)


async def _chat_stream_events(state: NovaState, message: str) -> AsyncIterator[str]:
    async for event in _chat_stream_events_scoped(state, message):
        yield event


async def _chat_stream_events_scoped(
    state: NovaState, message: str
) -> AsyncIterator[str]:
    turn: PreparedTurn | None = await _to_thread_with_user_scope(
        state.user_id,
        prepare_turn,
        state,
        message,
    )

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
    async for token in _stream_llm_tokens_threaded(state, turn):
        raw_parts.append(token)
        yield _sse_event({"type": "token", "content": token})

    raw_response = "".join(raw_parts)
    final_response = await _to_thread_with_user_scope(
        state.user_id,
        finalize_response,
        state,
        turn,
        raw_response,
    )

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
    state: Annotated[NovaState, Depends(get_state)],
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
    state: Annotated[NovaState, Depends(get_state)],
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
