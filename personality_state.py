class PersonalityState:

    def __init__(self):

        self.formality = 0.75
        self.warmth = 0.55
        self.humor = 0.35
        self.initiative = 0.4

        self.relationship_depth = 0.3

    # =====================================================
    # EVOLUTION ENGINE
    # =====================================================

    def update(

        self,
        emotion,
        intent,
        conversation_length

    ):

        # ---------------------------------------------
        # RELATIONSHIP DEPTH
        # ---------------------------------------------

        if conversation_length > 8:

            self.relationship_depth += 0.02

        # ---------------------------------------------
        # EMOTIONAL OPENNESS
        # ---------------------------------------------

        if intent == "reflection":

            self.warmth += 0.02

        if emotion in ["stress", "anxiety", "sad"]:

            self.formality -= 0.015
            self.warmth += 0.03

        # ---------------------------------------------
        # CASUAL INTERACTION
        # ---------------------------------------------

        if intent == "casual_talk":

            self.humor += 0.015

        # ---------------------------------------------
        # LONG-TERM ADAPTATION
        # ---------------------------------------------

        self.initiative += 0.005

        # ---------------------------------------------
        # NORMALIZATION
        # ---------------------------------------------

        self.formality = min(1.0, max(0.0, self.formality))
        self.warmth = min(1.0, max(0.0, self.warmth))
        self.humor = min(1.0, max(0.0, self.humor))
        self.initiative = min(1.0, max(0.0, self.initiative))

        self.relationship_depth = min(
            1.0,
            max(0.0, self.relationship_depth)
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        return {

            "formality": round(self.formality, 2),
            "warmth": round(self.warmth, 2),
            "humor": round(self.humor, 2),
            "initiative": round(self.initiative, 2),

            "relationship_depth":
                round(self.relationship_depth, 2)
        }