from memory import get_connection
from memory_scope import require_user_id
from datetime import datetime
import re
from embedding_engine import create_embedding
import json


# ======================================================
# MEMORY PATTERNS
# ======================================================

MEMORY_PATTERNS = [

    # =====================================================
    # AGE / IDENTITY
    # =====================================================

    {
        "category": "identity",
        "pattern": r"(?:i am|i'm|im)\s+(\d{1,3})\s*(?:years old|yo|y\.?o\.?)?",
        "key": "age"
    },

    {
        "category": "identity",
        "pattern": r"(?:just\s+)?turned\s+(\d{1,3})",
        "key": "age"
    },

    # =====================================================
    # LIKES
    # =====================================================

    {
        "category": "preference",
        "pattern": r"(?:i love|i enjoy|i really like|i like|i'm into|im into|i'm really into|im really into)\s+([^.!?\n]+)",
        "key": "likes"
    },

    # =====================================================
    # DISLIKES
    # =====================================================

    {
        "category": "preference",
        "pattern": r"(?:i hate|i dislike|i can't stand|i dont like|i don't like)\s+([^.!?\n]+)",
        "key": "dislikes"
    },

    # =====================================================
    # GOALS / ASPIRATIONS
    # =====================================================

    {
        "category": "goal",
        "pattern": r"(?:i want to become|my dream is to become|i hope to become)\s+([^.!?\n]+)",
        "key": "aspiration"
    },

    {
        "category": "goal",
        "pattern": r"(?:i want to|i plan to|i hope to|i'm trying to|im trying to)\s+([^.!?\n]+)",
        "key": "goal"
    },

    # =====================================================
    # LIFE EVENTS
    # =====================================================

    {
        "category": "life_event",
        "pattern": r"(?:today i|this week i|recently i)\s+([^.!?\n]+)",
        "key": "recent_event"
    },

    {
        "category": "relationship",
        "pattern": r"(?:i met|i started talking to|i like|i have feelings for)\s+([^.!?\n]+)",
        "key": "person_interest"
    },

    # =====================================================
    # EXPLICIT MEMORY COMMANDS
    # =====================================================

    {
        "category": "explicit_memory",
        "pattern": r"(?:remember that|remember this|don't forget that|dont forget that)\s+([^.!?\n]+)",
        "key": "explicit"
    },

    # =====================================================
    # INTERACTION STYLE
    # =====================================================

    {
        "category": "interaction_style",
        "pattern": r"(?:i prefer|i'd prefer|id prefer|i like when you|please be)\s+([^.!?\n]+)",
        "key": "response_preference"
    },
    {
        "category": "interaction_style",
        "pattern": r"(?:don't be so|dont be so|stop being so|less|more)\s+([^.!?\n]+)",
        "key": "style_adjustment"
    },
]


# ======================================================
# EXPLICIT MEMORY DETECTION
# ======================================================

def detect_explicit_memory(text):

    triggers = [
        # remember variants
        "remember this",
        "remember that",
        "make sure you remember",
        "don't forget this",
        "don't forget that",
        "never forget",

        # note-taking phrasing
        "make a note",
        "take note",
        "note this",
        "note that",
        "write this down",
        "jot this down",

        # save phrasing
        "save this",
        "keep this",
        "store this",
        "log this",

        # keep in mind variants
        "keep this in mind",
        "keep that in mind",
        "bear this in mind",
        "bear that in mind",
    ]

    lower = text.lower()

    return any(trigger in lower for trigger in triggers)


# ======================================================
# EXTRACT MEMORIES
# ======================================================

def extract_personal_memories(text):

    text_lower = text.lower()

    memories = []

    for item in MEMORY_PATTERNS:

        match = re.search(
            item["pattern"],
            text_lower
        )

        if match:

            value = match.group(1).strip()

            memories.append({

                "category": item["category"],

                "key": item["key"],

                "value": value,

                "importance": 0.75
            })

    # explicit memory command
    if detect_explicit_memory(text):

        memories.append({

            "category": "explicit",

            "key": f"memory_{datetime.now().timestamp()}",

            "value": text,

            "importance": 0.95
        })

    return memories


# ======================================================
# SAVE MEMORIES
# ======================================================

def save_personal_memory(memory):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    embedding = create_embedding(memory["value"])
    embedding_json = json.dumps(embedding)

    cursor.execute(
        """
        INSERT OR REPLACE INTO personal_memories (
            user_id,
            category,
            key,
            value,
            embedding,
            importance,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            memory["category"],
            memory["key"],
            memory["value"],
            embedding_json,
            memory["importance"],
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


# ======================================================
# RETRIEVE MEMORIES
# ======================================================

def get_personal_memories(limit=20):
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT category, key, value, importance
    FROM personal_memories
    WHERE user_id = ?
    ORDER BY importance DESC, updated_at DESC
    LIMIT ?
    """,
        (uid, limit),
    )

    rows = cursor.fetchall()

    conn.close()

    memories = []

    for row in rows:

        memories.append({

            "category": row[0],
            "key": row[1],
            "value": row[2],
            "importance": row[3]
        })

    return memories