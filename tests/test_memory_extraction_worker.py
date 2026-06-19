import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from memory import create_conversation_message, init_db  # noqa: E402
from learned_preferences import get_active_learned_preferences  # noqa: E402
from memory_extraction_worker import process_next_job  # noqa: E402
from memory_intelligence import ExtractedInsight  # noqa: E402
from memory_insights import get_recent_insights  # noqa: E402
from memory_extraction_jobs import (  # noqa: E402
    enqueue_extraction_job,
    get_extraction_health,
)
from memory_scope import user_scope  # noqa: E402


class MemoryExtractionWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_process_next_job_saves_valid_insights_and_completes_job(self):
        create_conversation_message(
            "user-123",
            "user",
            "Earlier user context",
        )
        create_conversation_message(
            "user-123",
            "assistant",
            "Assistant context should not be analyzed",
        )
        message_id = create_conversation_message(
            "user-123",
            "user",
            "I want to become a software engineer",
        )
        with user_scope("user-123"):
            enqueue_extraction_job(message_id, "I want to become a software engineer")

        def fake_extract(**_kwargs):
            context = _kwargs["recent_context"]
            self.assertEqual(
                context,
                [{"role": "user", "content": "Earlier user context"}],
            )
            return [
                ExtractedInsight(
                    label="Become a software engineer",
                    type="goal",
                    confidence=0.92,
                    evidence="I want to become a software engineer",
                    source="latest_user_message",
                    stability="long_term",
                )
            ]

        with mock.patch(
            "memory_extraction_worker.extract_insights_from_message",
            side_effect=fake_extract,
        ):
            processed = process_next_job("user-123")

        with user_scope("user-123"):
            health = get_extraction_health()
            insights = get_recent_insights()

        self.assertTrue(processed)
        self.assertEqual(health["completed"], 1)
        self.assertEqual(health["pending_retry"], 0)
        self.assertEqual(insights[0]["label"], "Become a software engineer")

    def test_process_next_job_failure_retries_without_saving_insights(self):
        message_id = create_conversation_message(
            "user-123",
            "user",
            "I prefer concise answers",
        )
        with user_scope("user-123"):
            enqueue_extraction_job(message_id, "I prefer concise answers")

        with self.assertLogs("memory_extraction_worker", level="ERROR"), \
                mock.patch(
                    "memory_extraction_worker.extract_insights_from_message",
                    side_effect=RuntimeError("LLM unavailable"),
                ):
            processed = process_next_job("user-123")

        with user_scope("user-123"):
            health = get_extraction_health()
            insights = get_recent_insights()

        self.assertTrue(processed)
        self.assertEqual(health["pending_retry"], 1)
        self.assertEqual(health["completed"], 0)
        self.assertEqual(health["last_failure_reason"], "LLM unavailable")
        self.assertEqual(insights, [])

    def test_process_next_job_aggregates_preference_insights(self):
        message_id = create_conversation_message(
            "user-123",
            "user",
            "I like shorter answers.",
        )
        with user_scope("user-123"):
            enqueue_extraction_job(message_id, "I like shorter answers.")

        def fake_extract(**_kwargs):
            return [
                ExtractedInsight(
                    label="User prefers shorter answers",
                    type="preference",
                    confidence=0.94,
                    evidence="I like shorter answers.",
                    source="latest_user_message",
                    stability="long_term",
                    preference_key="response.length",
                    preference_value={"target": "concise"},
                    scope="global",
                )
            ]

        with mock.patch(
            "memory_extraction_worker.extract_insights_from_message",
            side_effect=fake_extract,
        ):
            processed = process_next_job("user-123")

        with user_scope("user-123"):
            prefs = get_active_learned_preferences()

        self.assertTrue(processed)
        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0]["preference_key"], "response.length")


if __name__ == "__main__":
    unittest.main()
