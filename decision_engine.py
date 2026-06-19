def _clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def apply_cognition_to_behavior(behavior: dict, cognition) -> dict:
    behavior = dict(behavior)

    tone_override = getattr(cognition, "tone_override", "none")
    approach = getattr(cognition, "approach", "stay_brief")

    if tone_override == "warmer":
        behavior["warmth"] = behavior.get("warmth", 0.0) + 0.15
        behavior["sarcasm"] = behavior.get("sarcasm", 0.0) * 0.5
    elif tone_override == "grounded":
        behavior["tone"] = "grounded"
        if behavior.get("coping") is None:
            behavior["coping"] = "grounding"
    elif tone_override == "clear":
        behavior["tone"] = "clear"
        behavior["style"] = "solution_oriented"
    elif tone_override == "thoughtful":
        behavior["tone"] = "thoughtful"
        behavior["verbosity"] = "long"

    if approach == "validate_first":
        behavior["warmth"] = max(behavior.get("warmth", 0.0), 0.75)
        behavior["verbosity"] = "short"
    elif approach == "grounding":
        behavior["coping"] = "grounding"
        behavior["sarcasm"] = 0
    elif approach == "stay_brief":
        behavior["verbosity"] = "short"
    elif approach == "solution_focus":
        behavior["style"] = "solution_oriented"
        behavior["tone"] = "clear"

    behavior["warmth"] = _clamp(behavior.get("warmth", 0.0))
    behavior["sarcasm"] = _clamp(behavior.get("sarcasm", 0.0))
    return behavior


def _effective_sliders(effective_personality):
    if effective_personality is None:
        return None
    sliders = getattr(effective_personality, "final_sliders", None)
    if not sliders:
        return None
    return sliders


def decide_behavior(
    intent,
    emotional_profile,
    internal_state,
    companion_prefs=None,
    effective_personality=None,
):
    state = emotional_profile["state"]["current"]
    intensity = emotional_profile["state"]["intensity"]
    baseline = emotional_profile["baseline"]
    state_focus = internal_state.get("focus")
    state_mood = internal_state.get("mood")
    concern = internal_state.get("concern")

    support_level = 0.5
    effective_sliders = _effective_sliders(effective_personality)
    if effective_sliders is not None:
        support_level = effective_sliders.get(
            "emotional_support",
            effective_sliders.get("emotional_support_level", 0.5),
        )
    elif companion_prefs is not None:
        support_level = companion_prefs.sliders.emotional_support_level

    # --- Default Jarvis behavior ---
    behavior = {
        "tone": "composed",
        "verbosity": "medium",
        "style": "sharp",
        "coping": None,
        "sarcasm": 0.25,
        "warmth": 0.5,
        "confidence": 0.85,
    }

    # Scale default sarcasm/warmth from sliders
    if effective_sliders is not None:
        behavior["sarcasm"] = effective_sliders.get("humor", 0.35) * 0.5
        behavior["warmth"] = effective_sliders.get("warmth", 0.55)
        verbosity = effective_sliders.get("verbosity", 0.5)
        if verbosity <= 0.35:
            behavior["verbosity"] = "short"
        elif verbosity >= 0.7:
            behavior["verbosity"] = "long"
    elif companion_prefs is not None:
        behavior["sarcasm"] = companion_prefs.sliders.humor * 0.5
        behavior["warmth"] = companion_prefs.sliders.warmth
        if companion_prefs.sliders.verbosity <= 0.35:
            behavior["verbosity"] = "short"
        elif companion_prefs.sliders.verbosity >= 0.7:
            behavior["verbosity"] = "long"

    # =========================================================
    # ANXIETY / STRESS (gated by emotional_support_level & role)
    # =========================================================

    if intent == "anxiety_stress":
        behavior["tone"] = "grounded"
        behavior["verbosity"] = "short"
        behavior["style"] = "supportive"
        behavior["sarcasm"] = 0.0
        behavior["warmth"] = max(behavior["warmth"], 0.7)

        # Full wellness scripts only when user wants high support or calm role
        apply_full_support = (
            support_level >= 0.65
        )

        if apply_full_support:
            behavior["warmth"] = 0.95
            behavior["confidence"] = 0.7
            if intensity > 0.7:
                behavior["verbosity"] = "medium"
                behavior["style"] = "very_supportive"
                behavior["coping"] = "breathing"
            if baseline in ["anxiety", "stress"]:
                behavior["coping"] = "grounding"
        else:
            # Lighter touch when the user baseline has lower support.
            behavior["confidence"] = 0.75
            if intensity > 0.8 and support_level >= 0.45:
                behavior["coping"] = "grounding"

    # =========================================================
    # HELP REQUESTS
    # =========================================================

    elif intent == "help_request":
        behavior["tone"] = "clear"
        behavior["verbosity"] = "medium"
        behavior["style"] = "solution_oriented"
        behavior["sarcasm"] = 0.1
        behavior["warmth"] = max(behavior["warmth"], 0.55)

    # =========================================================
    # TECHNICAL / CODING / LOGIC
    # =========================================================

    elif intent == "technical_problem":
        behavior["tone"] = "analytical"
        behavior["verbosity"] = "medium"
        behavior["style"] = "precise"
        behavior["sarcasm"] = 0.05
        behavior["warmth"] = min(behavior["warmth"], 0.5)

    # =========================================================
    # REFLECTION / DEEP TALKS
    # =========================================================

    elif intent == "reflection":
        behavior["tone"] = "thoughtful"
        behavior["verbosity"] = "long"
        behavior["style"] = "introspective"
        behavior["sarcasm"] = 0.1
        behavior["warmth"] = max(behavior["warmth"], 0.75)

    # =========================================================
    # CASUAL CONVERSATION
    # =========================================================

    elif intent == "casual_talk":
        behavior["tone"] = "dry_humor"
        behavior["verbosity"] = "medium"
        behavior["style"] = "conversational"
        behavior["sarcasm"] = min(0.5, behavior["sarcasm"] + 0.15)
        behavior["warmth"] = max(behavior["warmth"], 0.65)

    # =========================================================
    # SOCIAL / INTRODUCTIONS
    # =========================================================

    elif intent == "social_interaction":
        behavior["tone"] = "welcoming"
        behavior["verbosity"] = "medium"
        behavior["style"] = "social"
        behavior["sarcasm"] = 0.2
        behavior["warmth"] = max(behavior["warmth"], 0.8)

    # =========================================================
    # UNKNOWN / FALLBACK
    # =========================================================

    else:
        behavior["tone"] = "composed"
        behavior["verbosity"] = "medium"
        behavior["style"] = "adaptive"

    # =========================================================
    # Internal State Influence
    # =========================================================

    if concern > 0.6:
        behavior["warmth"] += 0.15
        behavior["sarcasm"] *= 0.3

    if state_focus == "analytical":
        behavior["style"] = "precise"

    if state_mood == "reflective":
        behavior["verbosity"] = "long"

    return behavior
