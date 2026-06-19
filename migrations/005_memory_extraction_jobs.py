"""
Add memory extraction job tracking and structured insight storage.
Run: python migrations/005_memory_extraction_jobs.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def _ensure_learned_preferences_columns(cursor) -> None:
    cursor.execute("PRAGMA table_info(learned_preferences)")
    cols = {row[1] for row in cursor.fetchall()}
    additions = {
        "category": "ALTER TABLE learned_preferences ADD COLUMN category TEXT NOT NULL DEFAULT 'response'",
        "scope": "ALTER TABLE learned_preferences ADD COLUMN scope TEXT NOT NULL DEFAULT 'global'",
        "context_json": "ALTER TABLE learned_preferences ADD COLUMN context_json TEXT",
        "source_count": "ALTER TABLE learned_preferences ADD COLUMN source_count INTEGER NOT NULL DEFAULT 1",
        "positive_evidence_count": "ALTER TABLE learned_preferences ADD COLUMN positive_evidence_count INTEGER NOT NULL DEFAULT 1",
        "negative_evidence_count": "ALTER TABLE learned_preferences ADD COLUMN negative_evidence_count INTEGER NOT NULL DEFAULT 0",
        "status": "ALTER TABLE learned_preferences ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
        "origin": "ALTER TABLE learned_preferences ADD COLUMN origin TEXT NOT NULL DEFAULT 'extracted'",
        "is_pinned": "ALTER TABLE learned_preferences ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0",
        "first_seen_at": "ALTER TABLE learned_preferences ADD COLUMN first_seen_at TEXT NOT NULL DEFAULT ''",
        "last_seen_at": "ALTER TABLE learned_preferences ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''",
        "last_confirmed_at": "ALTER TABLE learned_preferences ADD COLUMN last_confirmed_at TEXT",
        "last_applied_at": "ALTER TABLE learned_preferences ADD COLUMN last_applied_at TEXT",
        "decays_after": "ALTER TABLE learned_preferences ADD COLUMN decays_after TEXT",
        "replaces_preference_id": "ALTER TABLE learned_preferences ADD COLUMN replaces_preference_id INTEGER",
        "created_at": "ALTER TABLE learned_preferences ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
        "updated_at": "ALTER TABLE learned_preferences ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    }
    for column, ddl in additions.items():
        if column not in cols:
            cursor.execute(ddl)


def migrate() -> None:
    db_path = config.DATABASE_PATH
    if not os.path.exists(db_path):
        print(f"No database at {db_path}; init_db will create schema on startup.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory_extraction_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        message_id INTEGER NOT NULL,
        message_content TEXT NOT NULL,
        status TEXT NOT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        created_at TEXT NOT NULL,
        next_retry_at TEXT,
        completed_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        message_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        type TEXT NOT NULL,
        confidence REAL NOT NULL,
        evidence TEXT NOT NULL,
        source TEXT NOT NULL,
        stability TEXT NOT NULL,
        preference_key TEXT,
        preference_value_json TEXT,
        scope TEXT,
        context_json TEXT,
        evidence_polarity TEXT,
        embedding TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, type, label, evidence)
    )
    """)
    cursor.execute("PRAGMA table_info(memory_insights)")
    insight_cols = {row[1] for row in cursor.fetchall()}
    for column, ddl in {
        "preference_key": "ALTER TABLE memory_insights ADD COLUMN preference_key TEXT",
        "preference_value_json": "ALTER TABLE memory_insights ADD COLUMN preference_value_json TEXT",
        "scope": "ALTER TABLE memory_insights ADD COLUMN scope TEXT",
        "context_json": "ALTER TABLE memory_insights ADD COLUMN context_json TEXT",
        "evidence_polarity": "ALTER TABLE memory_insights ADD COLUMN evidence_polarity TEXT",
    }.items():
        if column not in insight_cols:
            cursor.execute(ddl)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learned_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        preference_key TEXT NOT NULL,
        category TEXT NOT NULL,
        value_json TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT 'global',
        context_json TEXT,
        confidence REAL NOT NULL,
        source_count INTEGER NOT NULL DEFAULT 1,
        positive_evidence_count INTEGER NOT NULL DEFAULT 1,
        negative_evidence_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        origin TEXT NOT NULL DEFAULT 'extracted',
        is_pinned INTEGER NOT NULL DEFAULT 0,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        last_confirmed_at TEXT,
        last_applied_at TEXT,
        decays_after TEXT,
        replaces_preference_id INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    _ensure_learned_preferences_columns(cursor)
    cursor.execute("DROP INDEX IF EXISTS idx_learned_preferences_unique_active")
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_learned_preferences_unique_active
    ON learned_preferences(user_id, preference_key, scope, context_json, value_json)
    WHERE status = 'active'
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learned_preference_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        preference_id INTEGER,
        memory_insight_id INTEGER,
        message_id INTEGER NOT NULL,
        evidence_text TEXT NOT NULL,
        evidence_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        polarity TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learned_preference_conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        preference_key TEXT NOT NULL,
        preference_a_id INTEGER NOT NULL,
        preference_b_id INTEGER NOT NULL,
        resolution_strategy TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL,
        resolved_at TEXT
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_extraction_jobs_user ON memory_extraction_jobs(user_id)"
    )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_extraction_jobs_status_next_retry
    ON memory_extraction_jobs(status, next_retry_at, created_at)
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_insights_user ON memory_insights(user_id)"
    )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_insights_user_type_label
    ON memory_insights(user_id, type, label)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_learned_preferences_user_key_status
    ON learned_preferences(user_id, preference_key, status)
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_learned_preference_evidence_user ON learned_preference_evidence(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_learned_preference_conflicts_user ON learned_preference_conflicts(user_id)"
    )

    conn.commit()
    conn.close()
    print("Migration 005 complete.")


if __name__ == "__main__":
    migrate()
