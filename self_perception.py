class SelfPerception:

    def __init__(self):

        self.self_confidence = 0.72

        self.user_understanding = 0.45

        self.conversation_stability = 0.7

        self.perceived_connection = 0.4

        self.adaptation_pressure = 0.2

    # =====================================================
    # UPDATE MODEL
    # =====================================================

    def update(

        self,
        emotion,
        intensity,
        intent,
        conversation_length

    ):

        # ---------------------------------------------
        # USER UNDERSTANDING
        # ---------------------------------------------

        if intent in [

            "reflection",
            "help_request"

        ]:

            self.user_understanding += 0.03

        if conversation_length > 12:

            self.user_understanding += 0.015

        # ---------------------------------------------
        # STABILITY ANALYSIS
        # ---------------------------------------------

        if emotion in [

            "stress",
            "anxiety",
            "sad"

        ]:

            self.conversation_stability -= (
                intensity * 0.05
            )

        else:

            self.conversation_stability += 0.01

        # ---------------------------------------------
        # SELF CONFIDENCE
        # ---------------------------------------------

        if intensity > 0.85:

            self.self_confidence -= 0.04

        if intent == "technical_problem":

            self.self_confidence += 0.03

        # ---------------------------------------------
        # CONNECTION ESTIMATION
        # ---------------------------------------------

        if conversation_length > 15:

            self.perceived_connection += 0.02

        # ---------------------------------------------
        # ADAPTATION LOAD
        # ---------------------------------------------

        if emotion in [

            "stress",
            "anxiety"

        ]:

            self.adaptation_pressure += 0.03

        else:

            self.adaptation_pressure *= 0.98

        # ---------------------------------------------
        # NORMALIZATION
        # ---------------------------------------------

        self.self_confidence = min(
            1.0,
            max(0.0, self.self_confidence)
        )

        self.user_understanding = min(
            1.0,
            max(0.0, self.user_understanding)
        )

        self.conversation_stability = min(
            1.0,
            max(0.0, self.conversation_stability)
        )

        self.perceived_connection = min(
            1.0,
            max(0.0, self.perceived_connection)
        )

        self.adaptation_pressure = min(
            1.0,
            max(0.0, self.adaptation_pressure)
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        return {

            "self_confidence":
                round(self.self_confidence, 2),

            "user_understanding":
                round(self.user_understanding, 2),

            "conversation_stability":
                round(self.conversation_stability, 2),

            "perceived_connection":
                round(self.perceived_connection, 2),

            "adaptation_pressure":
                round(self.adaptation_pressure, 2)
        }