from memory import get_connection
from memory_scope import require_user_id


def decay_memories():
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE reflections
    SET salience = salience * 0.995
    WHERE resolved = 0 AND user_id = ?
    """,
        (uid,),
    )

    conn.commit()
    conn.close()
