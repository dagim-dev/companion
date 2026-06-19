from memory import get_connection
from memory_scope import require_user_id
from datetime import datetime


# =====================================================
# CREATE EPISODE
# =====================================================


def create_episode(summary, emotion, importance, resolved):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    # The summarizer now decides open/closed state; persistence stores it verbatim.
    resolved_value = 1 if resolved else 0

    cursor.execute(
        """
    INSERT INTO episodes
    (user_id, summary, emotion, importance, created_at, resolved)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            uid,
            summary,
            emotion,
            importance,
            str(datetime.now()),
            resolved_value,
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


def retrieve_followup_candidates(limit=12):
    """Return recent episodes with the fields the follow-up engine needs to
    rank candidates (id, timestamp, and resolved status included)."""
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT id, summary, emotion, importance, created_at, resolved
    FROM episodes
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """,
        (uid, limit),
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "summary": row[1],
            "emotion": row[2],
            "importance": row[3],
            "created_at": row[4],
            "resolved": row[5],
        }
        for row in rows
    ]


def mark_episode_resolved(episode_id):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE episodes
    SET resolved = 1
    WHERE id = ? AND user_id = ?
    """,
        (episode_id, uid),
    )

    conn.commit()
    conn.close()


# =====================================================
# FOLLOW-UP COOLDOWN STATE
# =====================================================
# Session state is in-memory with a short TTL, so the proactive follow-up
# cooldown is persisted in the DB to survive restarts / state eviction.


def get_last_followup_at(user_id=None):
    uid = user_id or require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT last_followup_at FROM followup_state WHERE user_id = ?",
        (uid,),
    )
    row = cursor.fetchone()

    conn.close()

    if not row or not row[0]:
        return None

    try:
        return datetime.fromisoformat(row[0])
    except ValueError:
        return None


def set_last_followup_at(user_id=None, when=None):
    uid = user_id or require_user_id()
    timestamp = (when or datetime.now()).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO followup_state (user_id, last_followup_at)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET last_followup_at = excluded.last_followup_at
    """,
        (uid, timestamp),
    )

    conn.commit()
    conn.close()
