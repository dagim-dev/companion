from learned_preferences import get_active_learned_preferences


def retrieve_style_preference_memories(user_input, limit: int = 3):
    """Recall learned preferences for personality layer."""
    _ = user_input  # reserved for future semantic recall over insights
    return [
        {
            "category": "learned_preference",
            "key": pref["preference_key"],
            "value": f"{pref['preference_key']} -> {pref['value']}",
            "score": pref["confidence"],
            "preference_id": pref["id"],
        }
        for pref in get_active_learned_preferences(limit=limit)
    ]
