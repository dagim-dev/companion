from datetime import datetime, timezone


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

        self.last_update = datetime.now(timezone.utc)

    # =====================================================
    # MAIN UPDATE
    # =====================================================

    def update(self, emotion, intent):

        # =====================================================
        # TIME DECAY
        # =====================================================

        now = datetime.now(timezone.utc)

        hours = max(
            0.0,
            (now - self.last_update).total_seconds() / 3600
        )

        self.last_update = now

        self.concern *= (0.985 ** hours)
        self.cognitive_load *= (0.97 ** hours)
        self.curiosity *= (0.998 ** hours)

        self.trust += (0.5 - self.trust) * (1 - (0.99 ** hours))
        self.energy += (1.0 - self.energy) * (1 - (0.98 ** hours))
        self.social_sync += (0.5 - self.social_sync) * (1 - (0.995 ** hours))

        # =====================================================
        # FOCUS SCORING
        # =====================================================

        focus_scores = {
            "balanced": 0.0,
            "supportive": 0.0,
            "gentle": 0.0,
            "analytical": 0.0,
            "philosophical": 0.0
        }

        # =====================================================
        # EMOTION EFFECTS
        # =====================================================

        if emotion in ["stress", "anxiety"]:

            self.concern += 0.15
            self.social_sync += 0.03

            focus_scores["supportive"] += 3

        elif emotion == "sad":

            self.concern += 0.10
            self.trust += 0.02

            focus_scores["gentle"] += 3

        elif emotion == "positive":

            self.concern *= 0.90
            self.trust += 0.015
            self.social_sync += 0.02
            self.energy += 0.03

        # =====================================================
        # INTENT EFFECTS
        # =====================================================

        if intent == "technical_problem":

            self.curiosity += 0.05
            self.cognitive_load += 0.04
            self.social_sync -= 0.01

            focus_scores["analytical"] += 2

        elif intent == "reflection":

            self.curiosity += 0.03
            self.trust += 0.02

            focus_scores["philosophical"] += 2

        elif intent == "casual_talk":

            self.cognitive_load *= 0.95
            self.social_sync += 0.01

            focus_scores["balanced"] += 1

        elif intent == "help_request":

            self.cognitive_load += 0.02
            self.energy -= 0.01

            focus_scores["supportive"] += 1

        # =====================================================
        # DETERMINE FOCUS
        # =====================================================

        if max(focus_scores.values()) == 0.0:
            self.focus = "balanced"
        else:
            self.focus = max(
                focus_scores,
                key=focus_scores.get
            )

        # =====================================================
        # CLAMP VALUES
        # =====================================================

        for attr in [
            "energy",
            "curiosity",
            "concern",
            "trust",
            "social_sync",
            "cognitive_load"
        ]:

            setattr(
                self,
                attr,
                max(
                    0.0,
                    min(1.0, getattr(self, attr))
                )
            )

        # =====================================================
        # STATE-DERIVED MOOD OVERRIDES
        # =====================================================

        if self.concern > 0.7:
            self.mood = "worried"

        elif self.cognitive_load > 0.8:
            self.mood = "focused"

        elif self.energy > 0.8 and self.trust > 0.7:
            self.mood = "engaged"

        elif self.concern < 0.2 and self.cognitive_load < 0.3:
            self.mood = "calm"

        else:
            self.mood = "neutral"

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
