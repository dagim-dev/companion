from memory import get_connection
from memory_scope import require_user_id


# =====================================================
# CONSOLIDATE REFLECTIONS
# =====================================================


def consolidate_memories():
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE reflections
    SET salience = MIN(
        salience + 0.03,
        1.0
    )
    WHERE user_id = ?
        AND (
        reflection_count >= 3
        OR intensity >= 0.75
        )
    """,
        (uid,),
    )

    cursor.execute(
        """
    UPDATE reflections
    SET salience = salience * 0.96
    WHERE user_id = ?
        AND reflection_count <= 1
        AND intensity < 0.45
    """,
        (uid,),
    )

    cursor.execute(
        """
    UPDATE reflections
    SET resolved = 1
    WHERE user_id = ?
        AND salience < 0.15
    """,
        (uid,),
    )

    conn.commit()
    conn.close()
