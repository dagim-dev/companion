import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
import reflection_engine as re  # noqa: E402
from memory import get_connection, init_db  # noqa: E402
from memory_scope import user_scope  # noqa: E402
from reflection_content import (  # noqa: E402
    MAX_REFLECTION_CONTENT_CHARS,
    MAX_REFLECTION_CONTENT_FRAGMENTS,
    REFLECTION_CONTENT_DELIMITER,
    count_reflection_fragments,
)


class UpdateReflectionCapTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()
        self.embedding_patch = mock.patch.object(
            re,
            "create_embedding",
            return_value=[0.1, 0.2, 0.3],
        )
        self.embedding_patch.start()

    def tearDown(self):
        self.embedding_patch.stop()
        self.config_patch.stop()
        self.tempdir.cleanup()

    def _fetch_reflection(self, topic: str):
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT content, reflection_count
                FROM reflections
                WHERE user_id = ? AND topic = ?
                """,
                ("user-123", topic),
            ).fetchone()
            return row
        finally:
            conn.close()

    def test_repeated_updates_keep_content_bounded(self):
        update_count = 25

        with user_scope("user-123"):
            for index in range(update_count):
                re.update_reflection(
                    topic="stress",
                    content=f"stress update {index}",
                    emotion="stress",
                    intensity=0.8,
                )

        row = self._fetch_reflection("stress")
        self.assertIsNotNone(row)
        self.assertEqual(row["reflection_count"], update_count)
        self.assertLessEqual(len(row["content"]), MAX_REFLECTION_CONTENT_CHARS)
        self.assertLessEqual(
            count_reflection_fragments(row["content"]),
            MAX_REFLECTION_CONTENT_FRAGMENTS,
        )
        self.assertTrue(row["content"].endswith(f"stress update {update_count - 1}"))


if __name__ == "__main__":
    unittest.main()
