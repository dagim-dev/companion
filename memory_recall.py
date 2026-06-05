from memory import get_connection
from embedding_engine import (
    create_embedding,
    cosine_similarity
)

import json


def retrieve_relevant_personal_memories(user_input):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT category, key, value, embedding, importance
    FROM personal_memories
    """)

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
            memory_embedding
        )

        score = similarity + (row["importance"] * 0.35)

        scored.append({

            "category": row["category"],
            "key": row["key"],
            "value": row["value"],
            "score": score
        })

    scored.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return scored[:5]