import sqlite3
from datetime import datetime

# =====================================================
# CONNECTION HELPER
# =====================================================

def get_connection():
    conn = sqlite3.connect("memory.db", timeout=30.0)
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
    CREATE TABLE IF NOT EXISTS user_profile (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotional_state (
        id INTEGER PRIMARY KEY,
        current TEXT,
        intensity REAL,
        last_updated TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotional_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emotion TEXT,
        intensity REAL,
        timestamp TEXT
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        key TEXT,
        value TEXT,
        embedding TEXT,
        importance REAL DEFAULT 0.5,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reflections (
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
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT,
        emotion TEXT,
        importance REAL,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

# =====================================================
# PROFILE
# =====================================================

def set_profile(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO user_profile (key, value)
    VALUES (?, ?)
    """, (key, value))
    conn.commit()
    conn.close()

def get_profile():
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_profile")
        rows = cursor.fetchall()
        return dict(rows)
    
    finally:
        conn.close()

# =====================================================
# EMOTIONAL STATE
# =====================================================

def set_emotional_state(emotion, intensity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO emotional_state (id, current, intensity, last_updated)
    VALUES (1, ?, ?, ?)
    """, (emotion, intensity, str(datetime.now())))
    conn.commit()
    conn.close()

def get_emotional_state():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT current, intensity FROM emotional_state WHERE id = 1
    """)
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"current": result[0], "intensity": result[1]}

    return {"current": "neutral", "intensity": 0.0}

# =====================================================
# EMOTIONAL HISTORY
# =====================================================

def add_emotional_history(emotion, intensity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO emotional_history (emotion, intensity, timestamp)
    VALUES (?, ?, ?)
    """, (emotion, intensity, str(datetime.now())))
    conn.commit()
    conn.close()

def get_emotional_history(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT emotion, intensity FROM emotional_history
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
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
        "baseline": get_emotional_baseline()
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
            "dominant_emotion": "neutral"
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
        "dominant_emotion": dominant_emotion
    }