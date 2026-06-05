from datetime import datetime


class InternalState:

    def __init__(self):

        self.focus = "balanced"

        self.energy = 0.85
        self.curiosity = 0.55
        self.concern = 0.0

        self.mood = "neutral"
        self.trust = 0.5
        self.cognitive_load = 0.2
        self.social_sync = 0.5

        self.last_update = datetime.now()

    # =====================================================
    # MAIN UPDATE
    # =====================================================

    def update(self, emotion, intent):

        # ---------------------------------------------
        # EMOTIONAL REACTION
        # ---------------------------------------------

        if emotion in ["stress", "anxiety"]:

            self.concern = min(1.0, self.concern + 0.15)
            self.focus = "supportive"
            self.mood = "alert"

            self.social_sync += 0.03

        elif emotion == "sad":

            self.concern = min(1.0, self.concern + 0.1)
            self.focus = "gentle"
            self.mood = "reflective"

        elif emotion == "positive":

            self.concern *= 0.9
            self.mood = "engaged"
            self.social_sync += 0.02

        # ---------------------------------------------
        # INTENT REACTION
        # ---------------------------------------------

        if intent == "technical_problem":

            self.focus = "analytical"
            self.curiosity = min(1.0, self.curiosity + 0.05)
            self.cognitive_load += 0.04

        elif intent == "reflection":

            self.focus = "philosophical"
            self.curiosity += 0.03

        elif intent == "casual_talk":

            self.cognitive_load *= 0.95

        # ---------------------------------------------
        # LONG-TERM STABILITY
        # ---------------------------------------------

        self.energy *= 0.997

        self.concern = max(0.0, min(1.0, self.concern))
        self.curiosity = max(0.0, min(1.0, self.curiosity))
        self.social_sync = max(0.0, min(1.0, self.social_sync))
        self.cognitive_load = max(0.0, min(1.0, self.cognitive_load))

    # =====================================================
    # SNAPSHOT FOR LLM
    # =====================================================

    def snapshot(self):

        return {
            "focus": self.focus,
            "energy": round(self.energy, 2),
            "curiosity": round(self.curiosity, 2),
            "concern": round(self.concern, 2),
            "mood": self.mood,
            "trust": round(self.trust, 2),
            "cognitive_load": round(self.cognitive_load, 2),
            "social_sync": round(self.social_sync, 2)
        }