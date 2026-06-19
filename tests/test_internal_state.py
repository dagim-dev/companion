import unittest
from datetime import timedelta

from internal_state import InternalState


class InternalStateMoodTests(unittest.TestCase):
    def test_mood_is_recomputed_from_current_state(self):
        state = InternalState()
        state.mood = "reflective"
        state.concern = 0.1
        state.cognitive_load = 0.2
        state.trust = 0.5
        state.energy = 0.6
        state.last_update -= timedelta(hours=12)

        state.update("unknown", "casual_talk")

        self.assertNotEqual(state.mood, "reflective")
        self.assertEqual(state.mood, "calm")

    def test_mood_uses_final_clamped_state_after_updates(self):
        state = InternalState()
        state.concern = 0.69

        state.update("stress", "casual_talk")

        self.assertEqual(state.mood, "worried")


class InternalStateSocialSyncTests(unittest.TestCase):
    def test_social_sync_recenters_toward_neutral_over_time(self):
        state = InternalState()
        state.social_sync = 1.0
        state.last_update -= timedelta(hours=100)

        state.update("unknown", "technical_problem")

        self.assertLess(state.social_sync, 0.9)
        self.assertGreater(state.social_sync, 0.5)


class InternalStateFocusTests(unittest.TestCase):
    def test_unknown_emotion_and_intent_default_focus_to_balanced(self):
        state = InternalState()

        state.update("unexpected", "unknown")

        self.assertEqual(state.focus, "balanced")


if __name__ == "__main__":
    unittest.main()
