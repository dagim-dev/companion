# response_controller.py
import re


# =========================================================
# TONE VIOLATION DETECTION
# =========================================================

def detect_tone_violation(response, intent):

    lower = response.lower()

    # Stress mode should stay calm and grounded
    if intent == "anxiety_stress":

        banned = [
            "idiot",
            "dummy",
            "stupid",
            "shut up",
            "obviously",
            "skill issue",
            "moron"
        ]

        return any(word in lower for word in banned)

    return False


# =========================================================
# SOFTEN RESPONSE
# =========================================================

def soften_response(response):
    """
    Removes excessive aggression or chaotic phrasing.
    """

    replacements = {
        "obviously": "",
        "shut up": "",
        "idiot": "Sir",
        "dummy": "Sir",
        "stupid": "unwise",
        "moron": "Sir"
    }

    for old, new in replacements.items():

        response = re.sub(
            rf"\b{re.escape(old)}\b",
            new,
            response,
            flags=re.IGNORECASE
        )

    return re.sub(r"\s+", " ", response).strip()


# =========================================================
# MAIN REFINEMENT
# =========================================================

def refine_response(response, intent, behavior):

    tone = behavior.get("tone", "composed")

    # -----------------------------------------------------
    # STRESS MODE
    # -----------------------------------------------------

    if intent == "anxiety_stress":

        response = soften_response(response)

        return (
            "Alright, Sir. One step at a time. "
            + response
        )

    # -----------------------------------------------------
    # EXPAND WEAK HELP RESPONSES
    # -----------------------------------------------------

    if len(response) < 60 and intent == "help_request":

        response += (
            " Let me know if you'd like "
            "a deeper breakdown."
        )

    # -----------------------------------------------------
    # JARVIS POLISH LAYER
    # -----------------------------------------------------

    if tone == "composed":

        fillers = [
            "oh wow",
            "listen",
            "literally",
            "bro",
            "dude"
        ]

        # Remove fillers WITHOUT destroying capitalization
        for filler in fillers:

            response = re.sub(
                rf"\b{re.escape(filler)}\b",
                "",
                response,
                flags=re.IGNORECASE
            )

        # Clean extra spaces
        response = re.sub(r"\s+", " ", response).strip()

    return response.strip()


# =========================================================
# FINAL CONTROLLER
# =========================================================

def control_response(response, behavior, intent):

    # 1. Refine response
    response = refine_response(
        response,
        intent,
        behavior
    )

    # 2. Detect violations
    if detect_tone_violation(response, intent):

        response = soften_response(response)

    return response