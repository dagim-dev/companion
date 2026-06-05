"""
Add companion_preferences table and users.onboarding_completed.
Run: python migrations/002_companion_preferences.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate() -> None:
    db_path = config.DATABASE_PATH
    if not os.path.exists(db_path):
        print(f"No database at {db_path}; init_db will create schema on startup.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if _table_exists(cursor, "companion_preferences"):
        print("Migration 002 already applied (companion_preferences exists).")
        conn.close()
        return

    print(f"Migrating {db_path}: companion_preferences + onboarding_completed...")

    if not _column_exists(cursor, "users", "onboarding_completed"):
        cursor.execute(
            "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0"
        )

    cursor.execute("""
    CREATE TABLE companion_preferences (
        user_id TEXT PRIMARY KEY,
        role_id TEXT NOT NULL,
        prefs_json TEXT NOT NULL,
        custom_notes TEXT,
        template_version TEXT NOT NULL DEFAULT '1',
        runtime_json TEXT,
        onboarding_completed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("Migration 002 complete.")


if __name__ == "__main__":
    migrate()
