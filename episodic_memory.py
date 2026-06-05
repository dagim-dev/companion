from memory import get_connection
from datetime import datetime


# =====================================================
# CREATE EPISODE
# =====================================================

def create_episode(summary, emotion, importance):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT,
        emotion TEXT,
        importance REAL,
        created_at TEXT
    )
    """)

    cursor.execute("""
    INSERT INTO episodes
    (summary, emotion, importance, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        summary,
        emotion,
        importance,
        str(datetime.now())
    ))

    conn.commit()
    conn.close()


# =====================================================
# RETRIEVE EPISODES
# =====================================================

def retrieve_recent_episodes(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT summary, emotion, importance
    FROM episodes
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()
    
    formatted = []

    for row in rows:

        formatted.append({

            "summary": row[0],
            "emotion": row[1],
            "importance": row[2]
        })

    return formatted
