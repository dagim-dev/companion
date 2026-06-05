#reflection_engine.py

from memory import get_connection
from datetime import datetime
import random
from embedding_engine import create_embedding
import json


REFLECTION_TOPICS = {
    "school": ["school", "exam", "assignment", "grades", "study"],
    "relationships": ["girlfriend", "relationship", "breakup", "friend"],
    "stress": ["stress", "overwhelmed", "burned out"],
    "sleep": ["sleep", "tired", "exhausted"],
}

def generate_checkin():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT topic, emotion, reflection_count
    FROM reflections
    WHERE resolved = 0
    ORDER BY reflection_count DESC
    LIMIT 1
    ''')

    result = cursor.fetchone()

    conn.close()

    if not result:
        return None

    if random.random() > 0.35:
        return None

    topic, emotion, count = result

    prompts = [
        f"You've mentioned {topic} a few times lately. How have things been going with that?",
        f"Earlier you seemed pretty {emotion} about {topic}. Has anything improved?",
        f"I remember you've been dealing with {topic} recently. How are you feeling about it now?"
    ]

    return random.choice(prompts)


def detect_reflection_topic(user_input):
    user_input = user_input.lower()

    for topic, keywords in REFLECTION_TOPICS.items():
        for keyword in keywords:
            if keyword in user_input:
                return topic

    return None

def update_reflection(topic, content, emotion, intensity):

    conn = get_connection()
    cursor = conn.cursor()

    embedding = create_embedding(content)

    embedding_json = json.dumps(embedding)

    # -------------------------
    # MEMORY SALIENCE
    # -------------------------

    salience = 0.35

    if emotion in ["stress", "anxiety", "sad"]:
        salience += 0.2

    if intensity > 0.7:
        salience += 0.2

    if len(content.split()) > 20:
        salience += 0.1

    if topic in [
        "relationships",
        "stress",
        "school"

    ]:

        salience += 0.1

    salience = min(salience, 1.0)

    cursor.execute(
        "SELECT * FROM reflections WHERE topic = ?",
        (topic,)
    )

    existing = cursor.fetchone()

    if existing:

        cursor.execute('''
        UPDATE reflections
        SET reflection_count = reflection_count + 1,

            salience = MIN(salience + 0.08, 1.0),

            content = content || ' || ' || ?,

            embedding = ?,

            intensity = MAX(intensity, ?),

            emotion = ?,

            last_mentioned = ?

        WHERE topic = ?
        ''', (
            content,
            embedding_json,
            intensity,
            emotion,
            datetime.now(),
            topic
        ))

    else:

        cursor.execute('''
        INSERT INTO reflections
        (
            topic,
            content,
            embedding,
            emotion,
            intensity,
            salience,
            created_at,
            last_mentioned
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            topic,
            content,
            embedding_json,
            emotion,
            intensity,
            salience,
            datetime.now(),
            datetime.now()
        ))


    existing = cursor.fetchone()


    conn.commit()
    conn.close()

