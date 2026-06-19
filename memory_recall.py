from memory import get_connection
from memory_scope import require_user_id
from embedding_engine import (
    create_embedding,
    cosine_similarity,
)
from learned_preferences import get_active_learned_preferences

import json


def retrieve_relevant_personal_memories(user_input):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT category, key, value, embedding, importance
    FROM personal_memories
    WHERE user_id = ?
    """,
        (uid,),
    )

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        return []

    input_embedding = create_embedding(user_input)

    if input_embedding is None:
        return []

    scored = []

    for row in rows:

        embedding_json = row["embedding"]

        if not embedding_json:
            continue

        memory_embedding = json.loads(embedding_json)

        if memory_embedding is None:
            continue

        similarity = cosine_similarity(
            input_embedding,
            memory_embedding,
        )

        score = similarity + (row["importance"] * 0.35)

        scored.append({
            "category": row["category"],
            "key": row["key"],
            "value": row["value"],
            "score": score,
        })

    scored.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return scored[:5]


def retrieve_style_preference_memories(user_input, limit: int = 3):
    """Recall interaction_style and preference memories for personality layer."""
    learned = [
        {
            "category": "learned_preference",
            "key": pref["preference_key"],
            "value": f"{pref['preference_key']} -> {pref['value']}",
            "score": pref["confidence"],
            "preference_id": pref["id"],
        }
        for pref in get_active_learned_preferences(limit=limit)
    ]
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT category, key, value, embedding, importance
        FROM personal_memories
        WHERE user_id = ? AND category IN ('interaction_style', 'preference')
        ORDER BY importance DESC, updated_at DESC
        LIMIT 30
        """,
        (uid,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return learned[:limit]

    input_embedding = create_embedding(user_input)
    if input_embedding is None:
        legacy = [
            {
                "category": row["category"],
                "key": row["key"],
                "value": row["value"],
                "score": row["importance"],
            }
            for row in rows[:limit]
        ]
        return (learned + legacy)[:limit]

    scored = []
    for row in rows:
        embedding_json = row["embedding"]
        if not embedding_json:
            continue
        memory_embedding = json.loads(embedding_json)
        if memory_embedding is None:
            continue
        similarity = cosine_similarity(input_embedding, memory_embedding)
        boost = 0.2 if row["category"] == "interaction_style" else 0.1
        score = similarity + (row["importance"] * 0.35) + boost
        scored.append({
            "category": row["category"],
            "key": row["key"],
            "value": row["value"],
            "score": score,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return (learned + scored)[:limit]
