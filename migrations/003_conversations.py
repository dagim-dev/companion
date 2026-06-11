"""
Add conversations table for message persistence.
Run: python migrations/003_conversations.py
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


def migrate() -> None:
    db_path = config.DATABASE_PATH
    if not os.path.exists(db_path):
        print(f"No database at {db_path}; init_db will create schema on startup.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    if _table_exists(cursor, "conversations"):
        print("Migration 003 already applied (conversations exists).")
        conn.close()
        return

    print(f"Migrating {db_path}: conversations table...")

    cursor.execute("""
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
    )

    conn.commit()
    conn.close()
    print("Migration 003 complete.")


if __name__ == "__main__":
    migrate()
