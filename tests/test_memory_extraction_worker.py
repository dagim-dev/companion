import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from memory import create_conversation_message, get_connection, init_db  # noqa: E402
from learned_preferences import get_active_learned_preferences  # noqa: E402
from memory_extraction_worker import (  # noqa: E402
    _claim_any_due_job,
    process_next_available_job,
)
from memory_intelligence import ExtractedInsight  # noqa: E402
from memory_insights import get_recent_insights  # noqa: E402
from memory_extraction_jobs import (  # noqa: E402
    enqueue_extraction_job,
    get_extraction_health,
    list_recent_jobs,
    mark_job_completed,
    mark_job_failed,
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

    def test_process_next_available_job_returns_false_when_no_jobs(self):
        self.assertFalse(process_next_available_job())

    def test_process_next_available_job_saves_valid_insights_and_completes_job(self):
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
            processed = process_next_available_job()

        with user_scope("user-123"):
            health = get_extraction_health()
            insights = get_recent_insights()

        self.assertTrue(processed)
        self.assertEqual(health["completed"], 1)
        self.assertEqual(health["pending_retry"], 0)
        self.assertEqual(insights[0]["label"], "Become a software engineer")

    def test_process_next_available_job_failure_retries_without_saving_insights(self):
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
            processed = process_next_available_job()

        with user_scope("user-123"):
            health = get_extraction_health()
            insights = get_recent_insights()

        self.assertTrue(processed)
        self.assertEqual(health["pending_retry"], 1)
        self.assertEqual(health["completed"], 0)
        self.assertEqual(health["last_failure_reason"], "LLM unavailable")
        self.assertEqual(insights, [])

    def test_process_next_available_job_aggregates_preference_insights(self):
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
            processed = process_next_available_job()

        with user_scope("user-123"):
            prefs = get_active_learned_preferences()

        self.assertTrue(processed)
        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0]["preference_key"], "response.length")

    def test_claim_any_due_job_orders_by_created_at_across_users(self):
        msg_a = create_conversation_message("user-A", "user", "Message A")
        msg_b = create_conversation_message("user-B", "user", "Message B")
        with user_scope("user-A"):
            enqueue_extraction_job(msg_a, "Message A")
        with user_scope("user-B"):
            enqueue_extraction_job(msg_b, "Message B")

        first = _claim_any_due_job()
        self.assertIsNotNone(first)
        user_id_a, job_a = first
        self.assertEqual(user_id_a, "user-A")

        with user_scope("user-A"):
            mark_job_completed(job_a["id"])

        second = _claim_any_due_job()
        self.assertIsNotNone(second)
        user_id_b, _job_b = second
        self.assertEqual(user_id_b, "user-B")

    def test_process_next_available_job_processes_users_in_fifo_order(self):
        msg_a = create_conversation_message("user-A", "user", "Content A")
        msg_b = create_conversation_message("user-B", "user", "Content B")
        with user_scope("user-A"):
            enqueue_extraction_job(msg_a, "Content A")
        with user_scope("user-B"):
            enqueue_extraction_job(msg_b, "Content B")

        seen_messages: list[str] = []

        def fake_extract(**kwargs):
            seen_messages.append(kwargs["latest_user_message"])
            return [
                ExtractedInsight(
                    label="stub",
                    type="goal",
                    confidence=0.9,
                    evidence=kwargs["latest_user_message"],
                    source="latest_user_message",
                    stability="long_term",
                )
            ]

        with mock.patch(
            "memory_extraction_worker.extract_insights_from_message",
            side_effect=fake_extract,
        ):
            self.assertTrue(process_next_available_job())
            self.assertTrue(process_next_available_job())

        self.assertEqual(seen_messages, ["Content A", "Content B"])

        with user_scope("user-A"):
            health_a = get_extraction_health()
        with user_scope("user-B"):
            health_b = get_extraction_health()
        self.assertEqual(health_a["completed"], 1)
        self.assertEqual(health_b["completed"], 1)

    def test_pending_retry_job_not_claimed_before_next_retry_at(self):
        message_id = create_conversation_message(
            "user-123",
            "user",
            "Retry timing test",
        )
        with user_scope("user-123"):
            enqueue_extraction_job(message_id, "Retry timing test")

        claimed = _claim_any_due_job()
        self.assertIsNotNone(claimed)
        _user_id, job = claimed
        with user_scope("user-123"):
            mark_job_failed(job["id"], "transient error")

        self.assertIsNone(_claim_any_due_job())

        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE memory_extraction_jobs
                SET next_retry_at = '2000-01-01T00:00:00'
                WHERE id = ?
                """,
                (job["id"],),
            )
            conn.commit()
        finally:
            conn.close()

        reclaimed = _claim_any_due_job()
        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed[1]["id"], job["id"])

    def test_process_next_available_job_logs_and_retries_on_extractor_failure(self):
        message_id = create_conversation_message(
            "user-123",
            "user",
            "Failure retry counts",
        )
        with user_scope("user-123"):
            enqueue_extraction_job(message_id, "Failure retry counts")

        with self.assertLogs("memory_extraction_worker", level="ERROR"), \
                mock.patch(
                    "memory_extraction_worker.extract_insights_from_message",
                    side_effect=RuntimeError("LLM unavailable"),
                ):
            self.assertTrue(process_next_available_job())

        with user_scope("user-123"):
            jobs = list_recent_jobs(limit=1)
        self.assertEqual(len(jobs), 1)
        self.assertIsNotNone(jobs[0]["next_retry_at"])
        self.assertEqual(jobs[0]["retry_count"], 1)

        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE memory_extraction_jobs
                SET next_retry_at = '2000-01-01T00:00:00'
                WHERE id = ?
                """,
                (jobs[0]["id"],),
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertLogs("memory_extraction_worker", level="ERROR"), \
                mock.patch(
                    "memory_extraction_worker.extract_insights_from_message",
                    side_effect=RuntimeError("LLM unavailable"),
                ):
            self.assertTrue(process_next_available_job())

        with user_scope("user-123"):
            jobs = list_recent_jobs(limit=1)
        self.assertEqual(jobs[0]["retry_count"], 2)


if __name__ == "__main__":
    unittest.main()
