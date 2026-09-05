import asyncio
import json
import logging
from typing import Annotated, AsyncIterator, Callable, Iterator, TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.deps import get_current_user, get_state
from api.schemas import ChatRequest, ChatResponse, RecentConversationMessage
from companion_prefs import is_onboarding_complete
from llm import LLMRequestError
from memory import get_recent_conversations
from memory_scope import user_scope
from message_processor import (
    PreparedTurn,
    finalize_response,
    persist_user_turn,
    prepare_turn,
    process_message,
    stream_llm_tokens,
)
from session_state import NovaState
from turn_guard import TurnLease, UserTurnBusyError, acquire_user_turn

router = APIRouter(prefix="/v1", tags=["chat"])
logger = logging.getLogger(__name__)

T = TypeVar("T")
_STREAM_END = object()
TURN_IN_PROGRESS_DETAIL = {
    "code": "turn_in_progress",
    "message": "Another turn is already running for this user. Please wait and retry.",
}
STREAM_ERROR_CODE = "stream_failed"
STREAM_ERROR_MESSAGE = "NOVA could not finish that streamed reply. Please retry."
CHAT_UNAVAILABLE_DETAIL = {
    "code": "llm_unavailable",
    "message": "NOVA could not finish that reply. Please retry.",
}


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


def _stream_error_event() -> str:
    return _sse_event(
        {
            "type": "error",
            "code": STREAM_ERROR_CODE,
            "message": STREAM_ERROR_MESSAGE,
        }
    )


def _acquire_turn_or_409(user_id: str) -> TurnLease:
    try:
        return acquire_user_turn(user_id)
    except UserTurnBusyError as exc:
        raise HTTPException(status_code=409, detail=TURN_IN_PROGRESS_DETAIL) from exc


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


async def _chat_stream_events(
    state: NovaState,
    message: str,
    lease: TurnLease | None = None,
) -> AsyncIterator[str]:
    try:
        async for event in _chat_stream_events_scoped(state, message):
            yield event
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("chat_stream_failed user_id=%s", state.user_id)
        yield _stream_error_event()
    finally:
        if lease is not None:
            lease.release()


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

    await _to_thread_with_user_scope(
        state.user_id,
        persist_user_turn,
        state,
        turn,
    )

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
        with _acquire_turn_or_409(state.user_id):
            with user_scope(state.user_id):
                result = process_message(state, body.message, echo_to_terminal=False)
    except HTTPException:
        raise
    except LLMRequestError as exc:
        logger.exception("chat_request_llm_failed user_id=%s", state.user_id)
        raise HTTPException(status_code=503, detail=CHAT_UNAVAILABLE_DETAIL) from exc
    except Exception as exc:
        logger.exception("chat_request_failed user_id=%s", state.user_id)
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
    lease = _acquire_turn_or_409(state.user_id)

    return StreamingResponse(
        _chat_stream_events(state, body.message, lease),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/recent", response_model=list[RecentConversationMessage])
def recent_conversations_endpoint(
    user_id: Annotated[str, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[RecentConversationMessage]:
    conversations = get_recent_conversations(user_id, limit=limit)
    return [
        RecentConversationMessage(role=item["role"], content=item["content"])
        for item in conversations
    ]
