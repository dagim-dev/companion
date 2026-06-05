"""Consolidate interaction patterns into interaction_style memories."""

from __future__ import annotations

from datetime import datetime

from companion_prefs import get_companion_preferences, save_companion_preferences
from memory import get_connection
from memory_scope import require_user_id
from personal_memory import save_personal_memory

# Rule-based style signals from traits (memory_intelligence) and behavior
TRAIT_TO_STYLE = {
    "habit-driven": "User values routines and consistency",
    "overthinker": "User appreciates structured, clear guidance over vague reassurance",
    "procrastinator": "User benefits from gentle accountability and small next steps",
    "self-aware": "User responds well to direct, honest feedback",
}


def maybe_consolidate_preferences(
    conversation_length: int,
    insights: dict | None = None,
    companion_prefs=None,
) -> None:
    """Every ~20 turns, persist stable style hints to personal_memories."""
    if conversation_length < 20 or conversation_length % 20 != 0:
        return

    uid = require_user_id()
    insights = insights or {}
    traits = insights.get("traits") or []

    for trait in traits:
        hint = TRAIT_TO_STYLE.get(trait)
        if not hint:
            continue
        save_personal_memory({
            "category": "interaction_style",
            "key": f"trait_{trait}",
            "value": hint,
            "importance": 0.75,
        })

    # Nudge runtime sliders slightly from explicit prefs (clamped)
    if companion_prefs is None:
        companion_prefs = get_companion_preferences(uid)
    if not companion_prefs:
        return

    prefs = companion_prefs
    if "overthinker" in traits or "self-aware" in traits:
        prefs.sliders.directness = min(1.0, prefs.sliders.directness + 0.02)
    if "procrastinator" in traits:
        prefs.sliders.accountability = min(1.0, prefs.sliders.accountability + 0.02)

    prefs.sliders.clamp()
    save_companion_preferences(prefs)


def count_interaction_style_memories() -> int:
    uid = require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM personal_memories
        WHERE user_id = ? AND category = 'interaction_style'
        """,
        (uid,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count
