import random


THOUGHT_PATTERNS = {

    "stress": [

        "User appears mentally overloaded.",
        "Stress signals are becoming recurrent.",
        "User may need structure more than reassurance.",
        "Emotional fatigue is noticeable."

    ],

    "reflection": [

        "User is in a reflective state.",
        "Conversation depth increasing.",
        "User seems unusually introspective today."

    ],

    "casual_talk": [

        "Interaction feels socially relaxed.",
        "User appears more comfortable.",
        "Conversation rhythm is natural."

    ]
}


class ThoughtEngine:

    def __init__(self):

        self.current_thought = None
        self.thought_history = []

    # =====================================================
    # GENERATE THOUGHT
    # =====================================================

    def generate(

        self,
        intent,
        emotion,
        patterns

    ):

        possible = []

        # ---------------------------------------------
        # INTENT-BASED THOUGHTS
        # ---------------------------------------------

        if intent in THOUGHT_PATTERNS:

            possible.extend(
                THOUGHT_PATTERNS[intent]
            )

        # ---------------------------------------------
        # PATTERN-BASED THOUGHTS
        # ---------------------------------------------

        if patterns["repeated_stress"]:

            possible.append(
                "Certain concerns are resurfacing repeatedly."
            )

            possible.append(
                "Stress patterns appear persistent."
            )

        if patterns["high_intensity"]:

            possible.append(
                "Emotional weight remains unresolved."
            )

            possible.append(
                "Emotional intensity elevated."
            )

        # ---------------------------------------------
        # PICK THOUGHT
        # ---------------------------------------------

        if not possible:

            return None

        thought = random.choice(possible)

        self.current_thought = thought

        self.thought_history.append(thought)

        self.thought_history = self.thought_history[-15:]

        return thought

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        return {

            "current_thought": self.current_thought,

            "recent_thoughts":
                self.thought_history[-5:]
        }