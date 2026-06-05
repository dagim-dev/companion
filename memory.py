import sqlite3
from datetime import datetime

import config
from memory_scope import require_user_id

# =====================================================
# CONNECTION HELPER
# =====================================================


def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


# =====================================================
# INIT DATABASE
# =====================================================


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        onboarding_completed INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companion_preferences (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        user_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        PRIMARY KEY (user_id, key)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotional_state (
        user_id TEXT PRIMARY KEY,
        current TEXT,
        intensity REAL,
        last_updated TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotional_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        emotion TEXT,
        intensity REAL,
        timestamp TEXT
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_memories (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reflections (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        summary TEXT,
        emotion TEXT,
        importance REAL,
        created_at TEXT
    )
    """)

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

    _ensure_schema_upgrades(cursor)
    conn.commit()
    conn.close()


def _ensure_schema_upgrades(cursor) -> None:
    """Add columns/tables for existing DBs created before latest schema."""
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cursor.fetchall()}
    if "onboarding_completed" not in user_cols:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0"
        )

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='companion_preferences'"
    )
    if not cursor.fetchone():
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


# =====================================================
# PROFILE
# =====================================================


def set_profile(key, value):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO user_profile (user_id, key, value)
    VALUES (?, ?, ?)
    """,
        (uid, key, value),
    )
    conn.commit()
    conn.close()


def get_profile():
    uid = require_user_id()
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key, value FROM user_profile WHERE user_id = ?",
            (uid,),
        )
        rows = cursor.fetchall()
        return dict(rows)

    finally:
        conn.close()


# =====================================================
# EMOTIONAL STATE
# =====================================================


def set_emotional_state(emotion, intensity):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO emotional_state (user_id, current, intensity, last_updated)
    VALUES (?, ?, ?, ?)
    """,
        (uid, emotion, intensity, str(datetime.now())),
    )
    conn.commit()
    conn.close()


def get_emotional_state():
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT current, intensity FROM emotional_state WHERE user_id = ?
    """,
        (uid,),
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"current": result[0], "intensity": result[1]}

    return {"current": "neutral", "intensity": 0.0}


# =====================================================
# EMOTIONAL HISTORY
# =====================================================


def add_emotional_history(emotion, intensity):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO emotional_history (user_id, emotion, intensity, timestamp)
    VALUES (?, ?, ?, ?)
    """,
        (uid, emotion, intensity, str(datetime.now())),
    )
    conn.commit()
    conn.close()


def get_emotional_history(limit=20):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT emotion, intensity FROM emotional_history
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """,
        (uid, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


# =====================================================
# EMOTIONAL BASELINE + PROFILE
# =====================================================


def get_emotional_baseline():
    history = get_emotional_history()

    if not history:
        return "neutral"

    counts = {}
    for row in history:
        emotion = row[0]
        counts[emotion] = counts.get(emotion, 0) + 1

    return max(counts, key=counts.get)


def get_emotional_profile():
    return {
        "state": get_emotional_state(),
        "baseline": get_emotional_baseline(),
    }


# =====================================================
# EMOTIONAL PATTERNS
# =====================================================


def detect_emotional_patterns(window=10):
    history = get_emotional_history(limit=window)

    if not history:
        return {
            "repeated_stress": False,
            "high_intensity": False,
            "dominant_emotion": "neutral",
        }

    stress_count = 0
    high_intensity_count = 0
    emotion_counts = {}

    for row in history:
        emotion = row[0]
        intensity = row[1]

        if emotion in ["anxiety", "stress", "overwhelmed"]:
            stress_count += 1

        if intensity > 0.7:
            high_intensity_count += 1

        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

    dominant_emotion = max(emotion_counts, key=emotion_counts.get)

    return {
        "repeated_stress": stress_count >= 3,
        "high_intensity": high_intensity_count >= 2,
        "dominant_emotion": dominant_emotion,
    }
