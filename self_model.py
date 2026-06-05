class SelfModel:

    def __init__(self):

        self.user_model = {

            "emotional_stability": 0.5,
            "openness": 0.5,
            "stress_level": 0.5,
            "trust_level": 0.5,
            "intellectual_style": "balanced"

        }

    # =====================================================
    # UPDATE USER MODEL
    # =====================================================

    def update(

        self,
        emotion,
        intent,
        intensity,
        conversation_length

    ):

        # ---------------------------------------------
        # STRESS MODELING
        # ---------------------------------------------

        if emotion in ["stress", "anxiety"]:

            self.user_model["stress_level"] = min(
                1.0,
                self.user_model["stress_level"] + 0.04
            )

            self.user_model["emotional_stability"] *= 0.98

        # ---------------------------------------------
        # TRUST DEVELOPMENT
        # ---------------------------------------------

        if intent in [

            "reflection",
            "help_request"

        ]:

            self.user_model["trust_level"] = min(
                1.0,
                self.user_model["trust_level"] + 0.03
            )

        # ---------------------------------------------
        # OPENNESS
        # ---------------------------------------------

        if conversation_length > 20:

            self.user_model["openness"] = min(
                1.0,
                self.user_model["openness"] + 0.02
            )

        # ---------------------------------------------
        # INTELLECTUAL STYLE
        # ---------------------------------------------

        if intent == "technical_problem":

            self.user_model["intellectual_style"] = "analytical"

        elif intent == "reflection":

            self.user_model["intellectual_style"] = "philosophical"

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        return self.user_model