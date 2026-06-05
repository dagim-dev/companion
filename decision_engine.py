def decide_behavior(intent, emotional_profile, internal_state):

    state = emotional_profile["state"]["current"]
    intensity = emotional_profile["state"]["intensity"]
    baseline = emotional_profile["baseline"]
    state_focus = internal_state.get("focus")
    state_mood = internal_state.get("mood")
    concern = internal_state.get("concern")

    # --- Default Jarvis behavior ---
    behavior = {
        "tone": "composed",
        "verbosity": "medium",
        "style": "sharp",
        "coping": None,
        "sarcasm": 0.25,
        "warmth": 0.5,
        "confidence": 0.85
    }

    # =========================================================
    # ANXIETY / STRESS
    # =========================================================

    if intent == "anxiety_stress":

        behavior["tone"] = "grounded"
        behavior["verbosity"] = "short"
        behavior["style"] = "supportive"

        behavior["sarcasm"] = 0.0
        behavior["warmth"] = 0.95
        behavior["confidence"] = 0.7

        if intensity > 0.7:

            behavior["verbosity"] = "medium"
            behavior["style"] = "very_supportive"
            behavior["coping"] = "breathing"

        if baseline in ["anxiety", "stress"]:

            behavior["coping"] = "grounding"

    # =========================================================
    # HELP REQUESTS
    # =========================================================

    elif intent == "help_request":

        behavior["tone"] = "clear"
        behavior["verbosity"] = "medium"
        behavior["style"] = "solution_oriented"

        behavior["sarcasm"] = 0.1
        behavior["warmth"] = 0.55

    # =========================================================
    # TECHNICAL / CODING / LOGIC
    # =========================================================

    elif intent == "technical_problem":

        behavior["tone"] = "analytical"
        behavior["verbosity"] = "medium"
        behavior["style"] = "precise"

        behavior["sarcasm"] = 0.05
        behavior["warmth"] = 0.4

    # =========================================================
    # REFLECTION / DEEP TALKS
    # =========================================================

    elif intent == "reflection":

        behavior["tone"] = "thoughtful"
        behavior["verbosity"] = "long"
        behavior["style"] = "introspective"

        behavior["sarcasm"] = 0.1
        behavior["warmth"] = 0.75

    # =========================================================
    # CASUAL CONVERSATION
    # =========================================================

    elif intent == "casual_talk":

        behavior["tone"] = "dry_humor"
        behavior["verbosity"] = "medium"
        behavior["style"] = "conversational"

        behavior["sarcasm"] = 0.4
        behavior["warmth"] = 0.65

    # =========================================================
    # SOCIAL / INTRODUCTIONS
    # =========================================================

    elif intent == "social_interaction":

        behavior["tone"] = "welcoming"
        behavior["verbosity"] = "medium"
        behavior["style"] = "social"

        behavior["sarcasm"] = 0.2
        behavior["warmth"] = 0.8

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