from memory import get_connection
from memory_scope import require_user_id
from datetime import datetime


# =====================================================
# CREATE EPISODE
# =====================================================


def create_episode(summary, emotion, importance):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO episodes
    (user_id, summary, emotion, importance, created_at)
    VALUES (?, ?, ?, ?, ?)
    """,
        (
            uid,
            summary,
            emotion,
            importance,
            str(datetime.now()),
        ),
    )

    conn.commit()
    conn.close()


# =====================================================
# RETRIEVE EPISODES
# =====================================================


def retrieve_recent_episodes(limit=5):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT summary, emotion, importance
    FROM episodes
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """,
        (uid, limit),
    )

    rows = cursor.fetchall()

    conn.close()

    formatted = []

    for row in rows:
        formatted.append({
            "summary": row[0],
            "emotion": row[1],
            "importance": row[2],
        })

    return formatted
