def generate_internal_reasoning(
    conversation,
    emotion,
    intent
):

    reasoning = []

    if emotion in ["stress", "anxiety"]:
        reasoning.append(
            "User may need grounding."
        )

    if intent == "reflection":
        reasoning.append(
            "User is emotionally introspective."
        )

    if len(conversation) > 12:
        reasoning.append(
            "Long-term conversational continuity active."
        )

    if not reasoning:
        reasoning.append(
            "Maintain composed conversational flow."
        )

    return reasoning