import random


CURIOSITY_QUESTIONS = {

    "stress": [

        "What's been causing the most pressure lately?",
        "Is this mainly mental exhaustion or workload overload?",
        "Has this been building for a while?"

    ],

    "reflection": [

        "What do you think is sitting underneath that?",
        "Do you think you've changed recently?",
        "What's been on your mind the most?"

    ],

    "relationships": [

        "That situation seems emotionally complicated.",
        "Do you trust your instincts on this?",
        "How long has this been affecting you?"

    ],

    "casual_talk": [

        "Oddly specific, Sir. There's a story there.",
        "You seem unusually interested in that topic.",
        "That caught your attention for a reason."
    ]
}


class CuriosityEngine:

    def __init__(self):

        self.last_question = None

    # =====================================================
    # DECIDE INITIATIVE
    # =====================================================

    def generate_question(

        self,
        intent,
        emotion,
        intensity,
        relationship_depth

    ):

        # ---------------------------------------------
        # LOW EMOTIONAL SIGNAL
        # ---------------------------------------------

        if intensity < 0.45:

            return None

        # ---------------------------------------------
        # RANDOMNESS CONTROL
        # ---------------------------------------------

        chance = 0.18 + (relationship_depth * 0.25)

        if random.random() > chance:

            return None

        # ---------------------------------------------
        # CATEGORY
        # ---------------------------------------------

        category = None

        if emotion in ["stress", "anxiety"]:

            category = "stress"

        elif intent == "reflection":

            category = "reflection"

        elif intent == "casual_talk":

            category = "casual_talk"

        if not category:

            return None

        question = random.choice(
            CURIOSITY_QUESTIONS[category]
        )

        self.last_question = question

        return question


OBSERVATIONS = [
    "You seem more focused today.",
    "Your tone is calmer than earlier.",
    "You sound mentally exhausted, Sir.",
    "You're thinking several steps ahead again.",
    "That seems unusually important to you.",
]


def maybe_add_initiative(intent, intensity):
    if intent == "casual_talk":
        return None

    if intensity < 0.5:
        return None

    if random.random() > 0.18:
        return None

    return random.choice(OBSERVATIONS)