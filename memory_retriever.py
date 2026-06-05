from memory import get_connection
from embedding_engine import (
    create_embedding,
    cosine_similarity
)

import json
from datetime import datetime


# ======================================================
# RETRIEVE MEMORIES
# ======================================================

def retrieve_relevant_reflections(user_input):

    # Skip semantic retrieval for tiny messages
    if len(user_input.split()) < 4:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    input_embedding = create_embedding(user_input)

    if input_embedding is None:
        return []

    cursor.execute("""
    SELECT topic,
           content,
           embedding,
           emotion,
           intensity,
           reflection_count,
           salience,
           last_mentioned
    FROM reflections
    WHERE resolved = 0
    """)

    rows = cursor.fetchall()

    conn.close()

    scored_memories = []

    for row in rows:

        topic = row[0]
        content = row[1]
        embedding_json = row[2]
        emotion = row[3]
        intensity = row[4]
        count = row[5]
        salience = row[6]
        last_mentioned = row[7]

        if not embedding_json:
            continue

        memory_embedding = json.loads(embedding_json)

        similarity = cosine_similarity(
            input_embedding,
            memory_embedding
        )

        # =====================================================
        # BASE SIMILARITY
        # =====================================================

        score = similarity * 0.35

        # =====================================================
        # EMOTIONAL SIGNIFICANCE
        # =====================================================

        score += intensity * 0.15

        # =====================================================
        # MEMORY IMPORTANCE
        # =====================================================

        score += salience * 0.25

        # =====================================================
        # RECURRING THEMES
        # =====================================================

        recurrence_bonus = min(count * 0.04, 0.2)

        score += recurrence_bonus

        # =====================================================
        # RECENCY BOOST
        # =====================================================

        try:

            memory_time = datetime.fromisoformat(
                last_mentioned
            )

            days_old = (
                datetime.now() - memory_time
            ).days

            recency_bonus = max(
                0,
                0.15 - (days_old * 0.01)
            )

            score += recency_bonus

        except Exception:

            pass

        # =====================================================
        # UNRESOLVED EMOTIONAL PRIORITY
        # =====================================================

        if emotion in [

            "stress",
            "anxiety",
            "sad"

        ]:

            score += 0.08

        # =====================================================
        # LONG-TERM PRIORITY BOOST
        # =====================================================

        if count >= 3:

            score += 0.12

        # =====================================================
        # HIGH INTENSITY MEMORIES
        # =====================================================

        if intensity >= 0.75:

            score += 0.1


        scored_memories.append({
            "topic": topic,
            "content": content,
            "emotion": emotion,
            "intensity": intensity,
            "count": count,
            "similarity": similarity,
            "score": score
        })

    scored_memories.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # =====================================================
    # DIVERSITY FILTER
    # =====================================================

    final_memories = []
    used_topics = set()

    for memory in scored_memories:

        topic = memory["topic"]

        if topic in used_topics:
            continue

        final_memories.append(memory)

        used_topics.add(topic)

        if len(final_memories) >= 3:
            break

    return final_memories

