def decide_behavior(intent, emotional_profile, internal_state, companion_prefs=None):
    state = emotional_profile["state"]["current"]
    intensity = emotional_profile["state"]["intensity"]
    baseline = emotional_profile["baseline"]
    state_focus = internal_state.get("focus")
    state_mood = internal_state.get("mood")
    concern = internal_state.get("concern")

    support_level = 0.5
    role_id = "general_jarvis"
    if companion_prefs is not None:
        support_level = companion_prefs.sliders.emotional_support_level
        role_id = companion_prefs.role_id

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
    if companion_prefs is not None:
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
            support_level >= 0.65 or role_id == "calm_companion"
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
            # Lighter touch for fitness_coach, strategic_partner, etc.
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

    # Role-specific nudges
    if role_id == "fitness_coach" and intent in ("help_request", "casual_talk"):
        behavior["style"] = "accountable"
        behavior["tone"] = "direct"
    if role_id == "productivity_operator" and intent == "help_request":
        behavior["style"] = "structured"
        behavior["verbosity"] = "medium"

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
