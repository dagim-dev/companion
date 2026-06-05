from memory import get_connection


# =====================================================
# CONSOLIDATE REFLECTIONS
# =====================================================

def consolidate_memories():

    conn = get_connection()
    cursor = conn.cursor()

    # =====================================================
    # STRENGTHEN IMPORTANT MEMORIES
    # =====================================================

    cursor.execute("""

    UPDATE reflections

    SET salience = MIN(
        salience + 0.03,
        1.0
    )

    WHERE

        reflection_count >= 3

        OR intensity >= 0.75

    """)

    # =====================================================
    # WEAKEN UNUSED MEMORIES
    # =====================================================

    cursor.execute("""

    UPDATE reflections

    SET salience = salience * 0.96

    WHERE

        reflection_count <= 1

        AND intensity < 0.45

    """)

    # =====================================================
    # AUTO-RESOLVE DEAD MEMORIES
    # =====================================================

    cursor.execute("""

    UPDATE reflections

    SET resolved = 1

    WHERE

        salience < 0.15

    """)

    conn.commit()
    conn.close()