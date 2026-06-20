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

def soften_response(response, address_as: str | None = None):
    """
    Removes excessive aggression or chaotic phrasing.
    """

    address = (address_as or "").strip() or "there"
    replacements = {
        "obviously": "",
        "shut up": "",
        "idiot": address,
        "dummy": address,
        "stupid": "unwise",
        "moron": address,
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

def refine_response(response, intent, behavior, address_as: str | None = None):

    tone = behavior.get("tone", "composed")

    # -----------------------------------------------------
    # STRESS MODE
    # -----------------------------------------------------

    if intent == "anxiety_stress":

        response = soften_response(response, address_as=address_as)
        address_prefix = f"{address_as.strip()}, " if (address_as or "").strip() else ""

        return (
            f"Alright, {address_prefix}one step at a time. "
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
    # NOVA POLISH LAYER
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

def control_response(response, behavior, intent, address_as: str | None = None):

    # 1. Refine response
    response = refine_response(
        response,
        intent,
            behavior,
            address_as=address_as,
    )

    # 2. Detect violations
    if detect_tone_violation(response, intent):

        response = soften_response(response, address_as=address_as)

    return response