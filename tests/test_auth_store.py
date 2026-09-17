import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

import config
from auth_store import create_user, get_user_by_id
from memory import init_db


class AuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test_auth_store.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_get_user_by_id_returns_user_with_default_onboarding_flag(self):
        init_db()
        created = create_user("person@example.com", "secret")

        user = get_user_by_id(created["id"])

        self.assertIsNotNone(user)
        self.assertEqual(user["id"], created["id"])
        self.assertEqual(user["email"], "person@example.com")
        self.assertIn("password_hash", user)
        self.assertEqual(user["created_at"], created["created_at"])
        created_at = datetime.fromisoformat(created["created_at"])
        self.assertIsNotNone(created_at.tzinfo)
        self.assertEqual(created_at.utcoffset(), timezone.utc.utcoffset(created_at))
        self.assertIs(user["onboarding_completed"], False)

    def test_get_user_by_id_supports_legacy_users_table_without_onboarding_column(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("legacy-user", "legacy@example.com", "hashed", "2026-01-01T00:00:00"),
        )
        conn.commit()
        conn.close()

        user = get_user_by_id("legacy-user")

        self.assertIsNotNone(user)
        self.assertEqual(user["id"], "legacy-user")
        self.assertEqual(user["email"], "legacy@example.com")
        self.assertEqual(user["password_hash"], "hashed")
        self.assertEqual(user["created_at"], "2026-01-01T00:00:00")
        self.assertIs(user["onboarding_completed"], False)

    def test_get_user_by_id_returns_none_for_unknown_user(self):
        init_db()

        user = get_user_by_id("missing-user")

        self.assertIsNone(user)

    def test_get_user_by_id_propagates_database_errors(self):
        init_db()

        def execute_effect(sql, params=()):
            if sql == "PRAGMA table_info(users)":
                return None
            raise sqlite3.OperationalError("database is locked")

        with mock.patch("auth_store.get_connection") as mock_get_connection:
            mock_conn = mock.Mock()
            mock_cursor = mock.Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_connection.return_value = mock_conn
            mock_cursor.execute.side_effect = execute_effect
            mock_cursor.fetchall.return_value = [
                (0, "id", "TEXT", 1, None, 1),
                (4, "onboarding_completed", "INTEGER", 1, "0", 0),
            ]

            with self.assertRaisesRegex(
                sqlite3.OperationalError, "database is locked"
            ):
                get_user_by_id("user-123")

            calls = mock_cursor.execute.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0], mock.call("PRAGMA table_info(users)"))
            self.assertIn("FROM users WHERE id = ?", calls[1][0][0])
            self.assertEqual(calls[1][0][1], ("user-123",))


if __name__ == "__main__":
    unittest.main()
