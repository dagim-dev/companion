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
        created_at TEXT,
        resolved INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS followup_state (
        user_id TEXT PRIMARY KEY,
        last_followup_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

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

    for table in (
        "user_profile",
        "emotional_history",
        "personal_memories",
        "reflections",
        "episodes",
        "conversations",
        "memory_extraction_jobs",
        "memory_insights",
        "learned_preferences",
        "learned_preference_evidence",
        "learned_preference_conflicts",
    ):
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)"
        )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_extraction_jobs_status_next_retry
    ON memory_extraction_jobs(status, next_retry_at, created_at)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_insights_user_type_label
    ON memory_insights(user_id, type, label)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_learned_preferences_user_key_status
    ON learned_preferences(user_id, preference_key, status)
    """)

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

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
    )
    if not cursor.fetchone():
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

    cursor.execute("PRAGMA table_info(episodes)")
    episode_cols = {row[1] for row in cursor.fetchall()}
    if "resolved" not in episode_cols:
        cursor.execute(
            "ALTER TABLE episodes ADD COLUMN resolved INTEGER DEFAULT 0"
        )

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='followup_state'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE followup_state (
            user_id TEXT PRIMARY KEY,
            last_followup_at TEXT
        )
        """)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_extraction_jobs'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE memory_extraction_jobs (
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
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_extraction_jobs_user ON memory_extraction_jobs(user_id)"
    )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_extraction_jobs_status_next_retry
    ON memory_extraction_jobs(status, next_retry_at, created_at)
    """)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_insights'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE memory_insights (
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
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_insights_user ON memory_insights(user_id)"
    )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_insights_user_type_label
    ON memory_insights(user_id, type, label)
    """)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learned_preferences'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE learned_preferences (
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
    CREATE INDEX IF NOT EXISTS idx_learned_preferences_user_key_status
    ON learned_preferences(user_id, preference_key, status)
    """)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learned_preference_evidence'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE learned_preference_evidence (
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

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learned_preference_conflicts'"
    )
    if not cursor.fetchone():
        cursor.execute("""
        CREATE TABLE learned_preference_conflicts (
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
        "CREATE INDEX IF NOT EXISTS idx_learned_preference_evidence_user ON learned_preference_evidence(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_learned_preference_conflicts_user ON learned_preference_conflicts(user_id)"
    )


# =====================================================
# CONVERSATIONS
# =====================================================


def create_conversation_message(user_id: str, role: str, content: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (user_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, role, content, str(datetime.now())),
    )
    message_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return message_id


def save_conversation_message(user_id: str, role: str, content: str) -> None:
    create_conversation_message(user_id, role, content)


def get_recent_conversations(
    user_id: str, limit: int = 20
) -> list[dict[str, str]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT role, content FROM conversations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


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
