import random

from episodic_memory import retrieve_recent_episodes


FOLLOWUP_OPENERS = [

    "Earlier, you mentioned",
    "You've brought up",
    "I remember you mentioning",
    "You seemed affected by"
]


def generate_followup(

    emotional_profile,
    patterns,
    relationship_depth

):

    # =====================================================
    # RELATIONSHIP REQUIREMENT
    # =====================================================

    if relationship_depth < 0.35:
        return None

    # =====================================================
    # RANDOM CONTROL
    # =====================================================

    if random.random() > 0.22:
        return None

    episodes = retrieve_recent_episodes()

    if not episodes:
        return None

    chosen = random.choice(episodes)

    summary = chosen["summary"]
    emotion = chosen["emotion"]

    opener = random.choice(FOLLOWUP_OPENERS)

    # =====================================================
    # EMOTIONAL FOLLOWUPS
    # =====================================================

    if emotion in [

        "stress",
        "anxiety",
        "sad"

    ]:

        return (
            f"{opener} something emotionally heavy recently. "
            f"How has that been sitting with you?"
        )

    # =====================================================
    # GENERAL FOLLOWUP
    # =====================================================

    return (
        f"{opener} {summary.lower()}. "
        f"Has your perspective changed at all?"
    )