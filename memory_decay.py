from memory import get_connection
from datetime import datetime


def decay_memories():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE reflections
    SET salience = salience * 0.995
    WHERE resolved = 0
    """)

    conn.commit()
    conn.close()