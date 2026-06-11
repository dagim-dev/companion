import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
import episodic_memory as em  # noqa: E402
from memory import init_db  # noqa: E402
from memory_scope import user_scope  # noqa: E402


class EpisodicMemoryCreateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def _stored_resolved_values(self):
        conn = em.get_connection()
        try:
            rows = conn.execute(
                "SELECT resolved FROM episodes ORDER BY id"
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def test_create_episode_stores_explicit_unresolved_flag(self):
        # create_episode now trusts the caller's LLM-derived resolution state.
        with user_scope("user-123"):
            em.create_episode(
                summary="The user is waiting to hear back from the landlord.",
                emotion="anxiety",
                importance=0.7,
                resolved=False,
            )

        self.assertEqual(self._stored_resolved_values(), [0])

    def test_create_episode_stores_explicit_resolved_flag(self):
        # Resolved episodes stay closed even if the summary mentions old keywords.
        with user_scope("user-123"):
            em.create_episode(
                summary="The interview was yesterday, and the user moved on.",
                emotion="neutral",
                importance=0.5,
                resolved=True,
            )

        self.assertEqual(self._stored_resolved_values(), [1])

    def test_keyword_inference_is_removed(self):
        # The open/closed decision belongs to the summarizer, not this module.
        self.assertFalse(hasattr(em, "infer_unresolved"))
        self.assertFalse(hasattr(em, "UNRESOLVED_KEYWORDS"))


if __name__ == "__main__":
    unittest.main()
