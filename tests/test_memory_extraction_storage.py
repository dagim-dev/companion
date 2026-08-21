import os
import importlib.util
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from memory import create_conversation_message, get_connection, init_db  # noqa: E402
from memory_scope import user_scope  # noqa: E402
from memory_insights import get_recent_insights, save_insights  # noqa: E402
from memory_intelligence import ExtractedInsight  # noqa: E402
from memory_extraction_jobs import (  # noqa: E402
    enqueue_extraction_job,
    get_extraction_health,
    mark_job_failed,
    mark_job_completed,
    claim_next_job,
)


class MemoryExtractionStorageTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_init_db_creates_memory_extraction_tables_and_indexes(self):
        conn = get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                ).fetchall()
            }
        finally:
            conn.close()

        self.assertIn("memory_extraction_jobs", tables)
        self.assertIn("memory_insights", tables)
        self.assertIn("idx_memory_extraction_jobs_user", indexes)
        self.assertIn("idx_memory_extraction_jobs_status_next_retry", indexes)
        self.assertIn("idx_memory_insights_user", indexes)
        self.assertIn("idx_memory_insights_user_type_label", indexes)

    def test_migration_005_creates_v2_preference_learning_schema(self):
        os.remove(self.db_path)
        open(self.db_path, "a").close()
        migration_path = os.path.join(
            os.getcwd(),
            "migrations",
            "005_memory_extraction_jobs.py",
        )
        spec = importlib.util.spec_from_file_location("migration_005", migration_path)
        migration = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(migration)

        migration.migrate()

        conn = get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            insight_cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(memory_insights)").fetchall()
            }
        finally:
            conn.close()

        self.assertIn("learned_preferences", tables)
        self.assertIn("learned_preference_evidence", tables)
        self.assertIn("learned_preference_conflicts", tables)
        self.assertIn("preference_key", insight_cols)
        self.assertIn("preference_value_json", insight_cols)

    def test_init_db_upgrades_partial_learned_preferences_table(self):
        os.remove(self.db_path)
        conn = get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE learned_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

        init_db()

        conn = get_connection()
        try:
            cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(learned_preferences)").fetchall()
            }
        finally:
            conn.close()

        self.assertIn("status", cols)
        self.assertIn("scope", cols)
        self.assertIn("context_json", cols)
        self.assertIn("source_count", cols)

    def test_init_db_quarantines_legacy_personal_memories_table(self):
        os.remove(self.db_path)
        conn = get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE personal_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    key TEXT,
                    value TEXT,
                    embedding TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO personal_memories (category, key, value, importance)
                VALUES ('identity', 'age', '32', 0.9)
                """
            )
            conn.commit()
        finally:
            conn.close()

        init_db()

        conn = get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            legacy_rows = conn.execute(
                "SELECT category, key, value FROM legacy_personal_memories_v3"
            ).fetchall()
        finally:
            conn.close()

        self.assertNotIn("personal_memories", tables)
        self.assertIn("legacy_personal_memories_v3", tables)
        self.assertEqual(len(legacy_rows), 1)
        self.assertEqual(legacy_rows[0]["category"], "identity")
        self.assertEqual(legacy_rows[0]["key"], "age")
        self.assertEqual(legacy_rows[0]["value"], "32")

    def test_migration_001_quarantines_legacy_personal_memories(self):
        os.remove(self.db_path)
        conn = get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE user_profile (
                    key TEXT NOT NULL,
                    value TEXT,
                    PRIMARY KEY (key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE emotional_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    current TEXT,
                    intensity REAL,
                    last_updated TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE emotional_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emotion TEXT,
                    intensity REAL,
                    timestamp TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE personal_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    key TEXT,
                    value TEXT,
                    embedding TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    content TEXT,
                    embedding TEXT,
                    emotion TEXT,
                    intensity REAL,
                    reflection_count INTEGER DEFAULT 1,
                    salience REAL DEFAULT 0.5,
                    resolved INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_mentioned TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT,
                    emotion TEXT,
                    importance REAL,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO personal_memories (category, key, value, importance)
                VALUES ('explicit', 'memory_1', 'remember this fact', 0.95)
                """
            )
            conn.commit()
        finally:
            conn.close()

        migration_path = os.path.join(
            os.getcwd(),
            "migrations",
            "001_add_user_id.py",
        )
        spec = importlib.util.spec_from_file_location("migration_001", migration_path)
        migration = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(migration)

        migration._migrate()

        conn = get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            legacy_rows = conn.execute(
                "SELECT category, key, value FROM legacy_personal_memories_v3"
            ).fetchall()
        finally:
            conn.close()

        self.assertNotIn("personal_memories", tables)
        self.assertIn("legacy_personal_memories_v3", tables)
        self.assertEqual(len(legacy_rows), 1)
        self.assertEqual(legacy_rows[0]["value"], "remember this fact")

    def test_create_conversation_message_returns_message_id(self):
        message_id = create_conversation_message(
            user_id="user-123",
            role="user",
            content="I want to become a software engineer",
        )

        self.assertIsInstance(message_id, int)
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT role, content FROM conversations WHERE id = ?",
                (message_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["role"], "user")
        self.assertEqual(row["content"], "I want to become a software engineer")

    def test_save_insights_persists_structured_high_confidence_records(self):
        message_id = create_conversation_message(
            user_id="user-123",
            role="user",
            content="I want to become a software engineer",
        )
        insight = ExtractedInsight(
            label="Become a software engineer",
            type="goal",
            confidence=0.92,
            evidence="I want to become a software engineer",
            source="latest_user_message",
            stability="long_term",
        )

        with user_scope("user-123"):
            save_insights(message_id=message_id, insights=[insight])
            saved = get_recent_insights(limit=5)

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["label"], "Become a software engineer")
        self.assertEqual(saved[0]["type"], "goal")
        self.assertEqual(saved[0]["stability"], "long_term")

    def test_jobs_track_retry_and_health_metrics(self):
        message_id = create_conversation_message(
            user_id="user-123",
            role="user",
            content="I prefer concise answers",
        )

        with user_scope("user-123"):
            job_id = enqueue_extraction_job(
                message_id=message_id,
                message_content="I prefer concise answers",
            )
            job = claim_next_job()
            self.assertEqual(job["id"], job_id)
            mark_job_failed(job_id, "LLM timeout")
            mark_job_completed(job_id)
            health = get_extraction_health()

        self.assertEqual(health["pending"], 0)
        self.assertEqual(health["pending_retry"], 0)
        self.assertEqual(health["completed"], 1)
        self.assertEqual(health["total_jobs_processed"], 1)
        self.assertEqual(health["success_rate"], 1.0)
        self.assertEqual(health["last_failure_reason"], "LLM timeout")


if __name__ == "__main__":
    unittest.main()
