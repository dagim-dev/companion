import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from fastapi.testclient import TestClient  # noqa: E402

import config  # noqa: E402
from api.deps import get_current_user, get_state  # noqa: E402
from api.main import app  # noqa: E402
from api.routers import chat as chat_router  # noqa: E402
from api.routers import health as health_router  # noqa: E402
from api.routers import voice as voice_router  # noqa: E402
from api.schemas import MAX_CHAT_MESSAGE_CHARS, MAX_TTS_TEXT_CHARS  # noqa: E402
from llm import LLMRequestError  # noqa: E402
from memory import create_conversation_message, get_recent_conversations, init_db  # noqa: E402
from memory_scope import user_scope  # noqa: E402
from session_state import NovaState  # noqa: E402
import message_processor as mp_module  # noqa: E402


class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.env_patch = mock.patch.object(config, "ENV", "development")
        self.config_patch.start()
        self.env_patch.start()
        init_db()
        app.dependency_overrides[get_current_user] = lambda: "user-123"
        app.dependency_overrides[get_state] = lambda: SimpleNamespace(user_id="user-123")
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.env_patch.stop()
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_recent_conversations_endpoint_returns_persisted_messages(self):
        create_conversation_message("user-123", "user", "hello")
        create_conversation_message("user-123", "assistant", "hi there")
        create_conversation_message("user-123", "user", "remember this")

        response = self.client.get("/v1/chat/recent?limit=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"role": "assistant", "content": "hi there"},
                {"role": "user", "content": "remember this"},
            ],
        )

    def test_health_returns_503_when_sqlite_is_unreachable(self):
        with mock.patch.object(
            health_router,
            "get_connection",
            side_effect=sqlite3.OperationalError("database is locked"),
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("database is locked", response.json()["db"])

    def test_chat_rejects_messages_above_release_limit(self):
        with (
            mock.patch.object(chat_router, "is_onboarding_complete", return_value=True),
            mock.patch.object(
                chat_router,
                "process_message",
                return_value={"response": "ok", "response_time_s": 0.1},
            ),
        ):
            response = self.client.post(
                "/v1/chat",
                json={"message": "x" * (MAX_CHAT_MESSAGE_CHARS + 1)},
            )

        self.assertEqual(response.status_code, 422)

    def test_sync_chat_returns_503_when_llm_fails_without_assistant_row(self):
        state = NovaState(user_id="user-123")
        app.dependency_overrides[get_state] = lambda: state

        def fake_prepare(_state, user_input):
            _state.conversation.append({"role": "user", "content": user_input})
            return mp_module.PreparedTurn(
                user_input=user_input,
                intent="help_request",
                emotion="neutral",
                intensity=0.2,
                profile={},
                emotional_profile={},
                behavior={},
                patterns={},
                context={},
                insights={},
                cognition=mock.Mock(),
                initiative_question=None,
                followup=None,
            )

        with (
            mock.patch.object(chat_router, "is_onboarding_complete", return_value=True),
            mock.patch.object(mp_module, "prepare_turn", side_effect=fake_prepare),
            mock.patch.object(
                mp_module,
                "chat",
                side_effect=LLMRequestError("OpenAI chat stream failed"),
            ),
        ):
            with user_scope("user-123"):
                response = self.client.post(
                    "/v1/chat",
                    json={"message": "hello there"},
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], chat_router.CHAT_UNAVAILABLE_DETAIL)
        with user_scope("user-123"):
            self.assertEqual(
                get_recent_conversations("user-123"),
                [{"role": "user", "content": "hello there"}],
            )

    def test_tts_rejects_text_above_release_limit(self):
        response = self.client.post(
            "/v1/tts",
            json={"text": "x" * (MAX_TTS_TEXT_CHARS + 1)},
        )

        self.assertEqual(response.status_code, 422)

    def test_transcribe_rejects_audio_above_release_limit(self):
        response = self.client.post(
            "/v1/transcribe",
            files={
                "file": (
                    "recording.webm",
                    b"x" * (voice_router.MAX_AUDIO_UPLOAD_BYTES + 1),
                    "audio/webm",
                )
            },
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn(str(voice_router.MAX_AUDIO_UPLOAD_BYTES), response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
