import importlib.util
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from memory import init_db  # noqa: E402
from reflection_content import (  # noqa: E402
    MAX_REFLECTION_CONTENT_CHARS,
    MAX_REFLECTION_CONTENT_FRAGMENTS,
    REFLECTION_CONTENT_DELIMITER,
    count_reflection_fragments,
)


def _load_migration_module():
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "006_cap_reflection_content.py",
    )
    spec = importlib.util.spec_from_file_location(
        "migration_006_cap_reflection_content",
        migration_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReflectionContentMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(
            config,
            "DATABASE_PATH",
            self.db_path,
        )
        self.config_patch.start()
        init_db()
        self.migration = _load_migration_module()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def _insert_reflection(self, *, topic: str, content: str, reflection_count: int):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO reflections (
                    user_id,
                    topic,
                    content,
                    embedding,
                    emotion,
                    intensity,
                    reflection_count,
                    salience,
                    resolved,
                    created_at,
                    last_mentioned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "user-123",
                    topic,
                    content,
                    "[0.1, 0.2]",
                    "stress",
                    0.8,
                    reflection_count,
                    0.7,
                    0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _fetch_row(self, topic: str):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            return conn.execute(
                """
                SELECT topic, content, reflection_count, salience, embedding
                FROM reflections
                WHERE user_id = ? AND topic = ?
                """,
                ("user-123", topic),
            ).fetchone()
        finally:
            conn.close()

    def test_migration_trims_oversized_row_and_preserves_bounded_row(self):
        oversized = REFLECTION_CONTENT_DELIMITER.join(
            [f"fragment-{index}" for index in range(1, 8)]
        )
        bounded = REFLECTION_CONTENT_DELIMITER.join(["small-1", "small-2"])

        self._insert_reflection(
            topic="stress",
            content=oversized,
            reflection_count=7,
        )
        self._insert_reflection(
            topic="school",
            content=bounded,
            reflection_count=2,
        )

        updated = self.migration.migrate(self.db_path)
        self.assertEqual(updated, 1)

        stress_row = self._fetch_row("stress")
        school_row = self._fetch_row("school")

        self.assertLessEqual(len(stress_row["content"]), MAX_REFLECTION_CONTENT_CHARS)
        self.assertLessEqual(
            count_reflection_fragments(stress_row["content"]),
            MAX_REFLECTION_CONTENT_FRAGMENTS,
        )
        self.assertEqual(stress_row["reflection_count"], 7)
        self.assertEqual(stress_row["salience"], 0.7)
        self.assertEqual(stress_row["embedding"], "[0.1, 0.2]")

        self.assertEqual(school_row["content"], bounded)
        self.assertEqual(school_row["reflection_count"], 2)


if __name__ == "__main__":
    unittest.main()
