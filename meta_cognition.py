from datetime import datetime


class MetaCognition:

    def __init__(self):

        self.response_confidence = 0.8
        self.user_stability = 0.5
        self.conversation_quality = 0.7

        self.last_reflection = None

    # =====================================================
    # MAIN ANALYSIS
    # =====================================================

    def evaluate_interaction(

        self,
        user_input,
        response,
        emotion,
        intensity,
        intent

    ):

        # ---------------------------------------------
        # USER STABILITY
        # ---------------------------------------------

        if emotion in ["stress", "anxiety", "sad"]:

            self.user_stability -= intensity * 0.08

        elif emotion == "positive":

            self.user_stability += 0.05

        else:

            self.user_stability += 0.01

        # ---------------------------------------------
        # RESPONSE CONFIDENCE
        # ---------------------------------------------

        if intent == "help_request":

            self.response_confidence -= 0.03

        if len(response) < 40:

            self.response_confidence -= 0.05

        if intensity > 0.8:

            self.response_confidence -= 0.07

        # ---------------------------------------------
        # CONVERSATION QUALITY
        # ---------------------------------------------

        if len(user_input.split()) > 12:

            self.conversation_quality += 0.02

        if emotion == "neutral":

            self.conversation_quality -= 0.01

        # ---------------------------------------------
        # NORMALIZATION
        # ---------------------------------------------

        self.user_stability = min(
            1.0,
            max(0.0, self.user_stability)
        )

        self.response_confidence = min(
            1.0,
            max(0.0, self.response_confidence)
        )

        self.conversation_quality = min(
            1.0,
            max(0.0, self.conversation_quality)
        )

        self.last_reflection = datetime.now()

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        return {

            "response_confidence":
                round(self.response_confidence, 2),

            "user_stability":
                round(self.user_stability, 2),

            "conversation_quality":
                round(self.conversation_quality, 2)
        }