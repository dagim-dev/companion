"""
Add `resolved` column to episodes and a `followup_state` table for the
memory follow-up cooldown.
Run: python migrations/004_followups.py
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
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    changed = False

    if _table_exists(cursor, "episodes") and not _column_exists(
        cursor, "episodes", "resolved"
    ):
        print(f"Migrating {db_path}: episodes.resolved column...")
        cursor.execute("ALTER TABLE episodes ADD COLUMN resolved INTEGER DEFAULT 0")
        changed = True

    if not _table_exists(cursor, "followup_state"):
        print(f"Migrating {db_path}: followup_state table...")
        cursor.execute("""
        CREATE TABLE followup_state (
            user_id TEXT PRIMARY KEY,
            last_followup_at TEXT
        )
        """)
        changed = True

    if changed:
        conn.commit()
        print("Migration 004 complete.")
    else:
        print("Migration 004 already applied.")

    conn.close()


if __name__ == "__main__":
    migrate()
