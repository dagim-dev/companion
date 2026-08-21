import json
import os
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from api.routers import chat as chat_router  # noqa: E402
from cognition_engine import CognitionResult  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from memory_scope import current_user_id  # noqa: E402
from turn_guard import UserTurnBusyError, acquire_user_turn  # noqa: E402


def _cognition():
    return CognitionResult(
        approach="stay_brief",
        priorities=[],
        risks=[],
        ask_question=True,
        tone_override="none",
        response_goal="maintain composed flow",
        memory_to_surface=None,
        emotional_signal=None,
        source="rules",
    )


class ChatStreamThreadingTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_offloads_blocking_pipeline_without_changing_sse_order(self):
        loop_thread_id = threading.get_ident()
        call_order: list[str] = []
        state = SimpleNamespace(user_id="user-123")

        def record_worker_call(name: str) -> None:
            self.assertNotEqual(threading.get_ident(), loop_thread_id)
            self.assertEqual(current_user_id.get(), "user-123")
            call_order.append(name)

        def fake_prepare(_state, message):
            record_worker_call("prepare")
            return chat_router.PreparedTurn(
                user_input=message,
                intent="help_request",
                emotion="neutral",
                intensity=0.2,
                profile={},
                emotional_profile={},
                behavior={},
                patterns={},
                context={},
                insights={},
                cognition=_cognition(),
                initiative_question=None,
                followup=None,
            )

        def fake_stream(_state, _turn, *, echo_to_terminal=False):
            self.assertFalse(echo_to_terminal)
            for token in ("hel", "lo"):
                record_worker_call(f"stream:{token}")
                yield token

        def fake_finalize(_state, _turn, raw_response):
            record_worker_call("finalize")
            return f"{raw_response}!"

        with (
            patch.object(chat_router, "prepare_turn", fake_prepare),
            patch.object(chat_router, "stream_llm_tokens", fake_stream),
            patch.object(chat_router, "finalize_response", fake_finalize),
        ):
            raw_events = [
                event
                async for event in chat_router._chat_stream_events(state, "hello")
            ]

        events = [
            json.loads(event.removeprefix("data: ").strip()) for event in raw_events
        ]

        self.assertEqual(
            events,
            [
                {"type": "token", "content": "hel"},
                {"type": "token", "content": "lo"},
                {
                    "type": "done",
                    "content": "hello!",
                    "intent": "help_request",
                    "emotion": "neutral",
                },
            ],
        )
        self.assertEqual(
            call_order,
            ["prepare", "stream:hel", "stream:lo", "finalize"],
        )

    async def test_stream_tokens_are_requested_as_sse_consumer_advances(self):
        loop_thread_id = threading.get_ident()
        call_order: list[str] = []
        state = SimpleNamespace(user_id="user-123")

        def record_worker_call(name: str) -> None:
            self.assertNotEqual(threading.get_ident(), loop_thread_id)
            self.assertEqual(current_user_id.get(), "user-123")
            call_order.append(name)

        def fake_prepare(_state, message):
            record_worker_call("prepare")
            return chat_router.PreparedTurn(
                user_input=message,
                intent="help_request",
                emotion="neutral",
                intensity=0.2,
                profile={},
                emotional_profile={},
                behavior={},
                patterns={},
                context={},
                insights={},
                cognition=_cognition(),
                initiative_question=None,
                followup=None,
            )

        def fake_stream(_state, _turn, *, echo_to_terminal=False):
            self.assertFalse(echo_to_terminal)
            for token in ("one", "two"):
                record_worker_call(f"stream:{token}")
                yield token

        def fake_finalize(_state, _turn, raw_response):
            record_worker_call("finalize")
            return raw_response

        with (
            patch.object(chat_router, "prepare_turn", fake_prepare),
            patch.object(chat_router, "stream_llm_tokens", fake_stream),
            patch.object(chat_router, "finalize_response", fake_finalize),
        ):
            events = chat_router._chat_stream_events(state, "hello")
            first_event = await anext(events)
            await asyncio.sleep(0.05)
            await events.aclose()

        self.assertEqual(
            json.loads(first_event.removeprefix("data: ").strip()),
            {"type": "token", "content": "one"},
        )
        self.assertEqual(call_order, ["prepare", "stream:one"])

    async def test_stream_prepare_failure_emits_structured_error_event(self):
        state = SimpleNamespace(user_id="user-123")

        with patch.object(chat_router, "prepare_turn", side_effect=RuntimeError("db down")):
            raw_events = [
                event
                async for event in chat_router._chat_stream_events(state, "hello")
            ]

        self.assertEqual(
            [json.loads(event.removeprefix("data: ").strip()) for event in raw_events],
            [
                {
                    "type": "error",
                    "code": chat_router.STREAM_ERROR_CODE,
                    "message": chat_router.STREAM_ERROR_MESSAGE,
                }
            ],
        )

    async def test_stream_midflight_failure_emits_error_after_partial_tokens(self):
        state = SimpleNamespace(user_id="user-123")

        def fake_prepare(_state, message):
            return chat_router.PreparedTurn(
                user_input=message,
                intent="help_request",
                emotion="neutral",
                intensity=0.2,
                profile={},
                emotional_profile={},
                behavior={},
                patterns={},
                context={},
                insights={},
                cognition=_cognition(),
                initiative_question=None,
                followup=None,
            )

        async def fake_stream(_state, _turn):
            yield "hel"
            raise RuntimeError("socket closed")

        with (
            patch.object(chat_router, "prepare_turn", fake_prepare),
            patch.object(chat_router, "_stream_llm_tokens_threaded", fake_stream),
        ):
            raw_events = [
                event
                async for event in chat_router._chat_stream_events(state, "hello")
            ]

        self.assertEqual(
            [json.loads(event.removeprefix("data: ").strip()) for event in raw_events],
            [
                {"type": "token", "content": "hel"},
                {
                    "type": "error",
                    "code": chat_router.STREAM_ERROR_CODE,
                    "message": chat_router.STREAM_ERROR_MESSAGE,
                },
            ],
        )

    async def test_stream_endpoint_returns_409_when_same_user_turn_is_active(self):
        state = SimpleNamespace(user_id="user-123")

        with (
            patch.object(chat_router, "_require_onboarding"),
            patch.object(
                chat_router,
                "acquire_user_turn",
                side_effect=UserTurnBusyError("user-123"),
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await chat_router.chat_stream_endpoint(
                    SimpleNamespace(message="hello"),
                    state,
                )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, chat_router.TURN_IN_PROGRESS_DETAIL)

    async def test_sync_chat_endpoint_returns_409_when_same_user_turn_is_active(self):
        state = SimpleNamespace(user_id="user-123")

        with (
            patch.object(chat_router, "_require_onboarding"),
            patch.object(
                chat_router,
                "acquire_user_turn",
                side_effect=UserTurnBusyError("user-123"),
            ),
            patch.object(chat_router, "process_message") as process_message,
        ):
            with self.assertRaises(HTTPException) as ctx:
                chat_router.chat_endpoint(
                    SimpleNamespace(message="hello"),
                    state,
                )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, chat_router.TURN_IN_PROGRESS_DETAIL)
        process_message.assert_not_called()

    async def test_stream_close_releases_turn_guard(self):
        state = SimpleNamespace(user_id="user-123")
        lease = acquire_user_turn(state.user_id)

        def fake_prepare(_state, message):
            return chat_router.PreparedTurn(
                user_input=message,
                intent="help_request",
                emotion="neutral",
                intensity=0.2,
                profile={},
                emotional_profile={},
                behavior={},
                patterns={},
                context={},
                insights={},
                cognition=_cognition(),
                initiative_question=None,
                followup=None,
            )

        async def fake_stream(_state, _turn):
            yield "one"
            await asyncio.sleep(1)

        with (
            patch.object(chat_router, "prepare_turn", fake_prepare),
            patch.object(chat_router, "_stream_llm_tokens_threaded", fake_stream),
        ):
            events = chat_router._chat_stream_events(state, "hello", lease)
            first_event = await anext(events)
            await events.aclose()

        self.assertEqual(
            json.loads(first_event.removeprefix("data: ").strip()),
            {"type": "token", "content": "one"},
        )
        reacquired = acquire_user_turn(state.user_id)
        reacquired.release()


if __name__ == "__main__":
    unittest.main()
