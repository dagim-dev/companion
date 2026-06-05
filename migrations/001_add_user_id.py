"""
One-shot migration for existing single-user memory.db.
Run: python migrations/001_add_user_id.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

LEGACY_USER_ID = "legacy-local"


def _table_has_column(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _drop_new_tables(cursor):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_new'"
    )
    for (name,) in cursor.fetchall():
        cursor.execute(f"DROP TABLE IF EXISTS {name}")


def _migrate():
    db_path = config.DATABASE_PATH
    if not os.path.exists(db_path):
        print(f"No database at {db_path}; nothing to migrate.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if _table_has_column(cursor, "user_profile", "user_id"):
        print("Migration already applied (user_id present).")
        conn.close()
        return

    print(f"Migrating {db_path} to multi-user schema...")
    _drop_new_tables(cursor)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # user_profile
    cursor.execute("""
    CREATE TABLE user_profile_new (
        user_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        PRIMARY KEY (user_id, key)
    )
    """)
    cursor.execute(
        """
        INSERT INTO user_profile_new (user_id, key, value)
        SELECT ?, key, value FROM user_profile
        """,
        (LEGACY_USER_ID,),
    )
    cursor.execute("DROP TABLE user_profile")
    cursor.execute("ALTER TABLE user_profile_new RENAME TO user_profile")

    # emotional_state
    if _table_has_column(cursor, "emotional_state", "id"):
        cursor.execute("""
        CREATE TABLE emotional_state_new (
            user_id TEXT PRIMARY KEY,
            current TEXT,
            intensity REAL,
            last_updated TEXT
        )
        """)
        cursor.execute(
            """
            INSERT INTO emotional_state_new (user_id, current, intensity, last_updated)
            SELECT ?, current, intensity, last_updated FROM emotional_state WHERE id = 1
            """,
            (LEGACY_USER_ID,),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO emotional_state_new (user_id, current, intensity, last_updated)
                VALUES (?, 'neutral', 0.0, datetime('now'))
                """,
                (LEGACY_USER_ID,),
            )
        cursor.execute("DROP TABLE emotional_state")
        cursor.execute("ALTER TABLE emotional_state_new RENAME TO emotional_state")

    # emotional_history
    if not _table_has_column(cursor, "emotional_history", "user_id"):
        cursor.execute("""
        CREATE TABLE emotional_history_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            emotion TEXT,
            intensity REAL,
            timestamp TEXT
        )
        """)
        cursor.execute(
            """
            INSERT INTO emotional_history_new (id, user_id, emotion, intensity, timestamp)
            SELECT id, ?, emotion, intensity, timestamp FROM emotional_history
            """,
            (LEGACY_USER_ID,),
        )
        cursor.execute("DROP TABLE emotional_history")
        cursor.execute("ALTER TABLE emotional_history_new RENAME TO emotional_history")

    # personal_memories (dedupe by category+key, keep latest id)
    if not _table_has_column(cursor, "personal_memories", "user_id"):
        cursor.execute("""
        CREATE TABLE personal_memories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            category TEXT,
            key TEXT,
            value TEXT,
            embedding TEXT,
            importance REAL DEFAULT 0.5,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(user_id, category, key)
        )
        """)
        cursor.execute(
            """
            INSERT INTO personal_memories_new
            (id, user_id, category, key, value, embedding, importance, created_at, updated_at)
            SELECT pm.id, ?, pm.category, pm.key, pm.value, pm.embedding,
                   pm.importance, pm.created_at, pm.updated_at
            FROM personal_memories pm
            INNER JOIN (
                SELECT category, key, MAX(id) AS max_id
                FROM personal_memories
                GROUP BY category, key
            ) latest ON pm.id = latest.max_id
            """,
            (LEGACY_USER_ID,),
        )
        cursor.execute("DROP TABLE personal_memories")
        cursor.execute("ALTER TABLE personal_memories_new RENAME TO personal_memories")

    # reflections
    if not _table_has_column(cursor, "reflections", "user_id"):
        cursor.execute("""
        CREATE TABLE reflections_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
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
        """)
        cursor.execute(
            """
            INSERT INTO reflections_new
            (id, user_id, topic, content, embedding, emotion, intensity,
             reflection_count, salience, resolved, created_at, last_mentioned)
            SELECT id, ?, topic, content, embedding, emotion, intensity,
                   reflection_count, salience, resolved, created_at, last_mentioned
            FROM reflections
            """,
            (LEGACY_USER_ID,),
        )
        cursor.execute("DROP TABLE reflections")
        cursor.execute("ALTER TABLE reflections_new RENAME TO reflections")

    # episodes
    if not _table_has_column(cursor, "episodes", "user_id"):
        cursor.execute("""
        CREATE TABLE episodes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            summary TEXT,
            emotion TEXT,
            importance REAL,
            created_at TEXT
        )
        """)
        cursor.execute(
            """
            INSERT INTO episodes_new (id, user_id, summary, emotion, importance, created_at)
            SELECT id, ?, summary, emotion, importance, created_at FROM episodes
            """,
            (LEGACY_USER_ID,),
        )
        cursor.execute("DROP TABLE episodes")
        cursor.execute("ALTER TABLE episodes_new RENAME TO episodes")

    for table in (
        "user_profile",
        "emotional_history",
        "personal_memories",
        "reflections",
        "episodes",
    ):
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)"
        )

    cursor.execute(
        "SELECT 1 FROM users WHERE id = ?",
        (LEGACY_USER_ID,),
    )
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (
                LEGACY_USER_ID,
                "legacy@local.dev",
                "!",
            ),
        )

    conn.commit()
    conn.close()
    print(f"Migration complete. Legacy data assigned to user_id={LEGACY_USER_ID!r}")


if __name__ == "__main__":
    _migrate()
