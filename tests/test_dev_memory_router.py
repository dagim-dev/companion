import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from fastapi.testclient import TestClient  # noqa: E402

import config  # noqa: E402
from api.deps import get_current_user  # noqa: E402
from api.main import app  # noqa: E402
from memory import create_conversation_message, init_db  # noqa: E402
from memory_extraction_jobs import enqueue_extraction_job, mark_job_failed  # noqa: E402
from memory_scope import user_scope  # noqa: E402


class DevMemoryRouterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.env_patch = mock.patch.object(config, "ENV", "development")
        self.config_patch.start()
        self.env_patch.start()
        init_db()
        app.dependency_overrides[get_current_user] = lambda: "user-123"

    def tearDown(self):
        app.dependency_overrides.clear()
        self.env_patch.stop()
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_health_returns_memory_extraction_metrics(self):
        message_id = create_conversation_message("user-123", "user", "remember this")
        with user_scope("user-123"):
            job_id = enqueue_extraction_job(message_id, "remember this")
            mark_job_failed(job_id, "LLM timeout")

        response = TestClient(app).get("/v1/dev/memory-extraction/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_retry"], 1)
        self.assertEqual(data["last_failure_reason"], "LLM timeout")
        self.assertFalse(data["show_warning"])

    def test_dev_route_is_hidden_in_production(self):
        with mock.patch.object(config, "ENV", "production"):
            response = TestClient(app).get("/v1/dev/memory-extraction/health")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
