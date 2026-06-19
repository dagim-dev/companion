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
from memory_scope import current_user_id  # noqa: E402


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
                personal_memories=[],
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
                personal_memories=[],
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


if __name__ == "__main__":
    unittest.main()
