import unittest
from types import SimpleNamespace

from decision_engine import decide_behavior


class DecisionEngineV2Tests(unittest.TestCase):
    def test_effective_personality_controls_support_without_role_identity(self):
        companion_prefs = SimpleNamespace(role_id="calm_companion")
        effective = SimpleNamespace(
            final_sliders={
                "directness": 0.8,
                "warmth": 0.45,
                "humor": 0.2,
                "verbosity": 0.4,
                "accountability": 0.8,
                "emotional_support": 0.3,
            },
            directives=[],
        )

        behavior = decide_behavior(
            "anxiety_stress",
            {"state": {"current": "anxiety", "intensity": 0.6}, "baseline": "neutral"},
            {"focus": None, "mood": None, "concern": 0.0},
            companion_prefs=companion_prefs,
            effective_personality=effective,
        )

        self.assertEqual(behavior["tone"], "grounded")
        self.assertNotEqual(behavior["style"], "very_supportive")
        self.assertLess(behavior["warmth"], 0.95)

    def test_effective_personality_runtime_support_can_trigger_full_support(self):
        effective = SimpleNamespace(
            final_sliders={
                "directness": 0.4,
                "warmth": 0.78,
                "humor": 0.0,
                "verbosity": 0.4,
                "accountability": 0.4,
                "emotional_support": 0.85,
            },
            directives=["validate first"],
        )

        behavior = decide_behavior(
            "anxiety_stress",
            {"state": {"current": "anxiety", "intensity": 0.9}, "baseline": "neutral"},
            {"focus": None, "mood": None, "concern": 0.0},
            effective_personality=effective,
        )

        self.assertEqual(behavior["style"], "very_supportive")
        self.assertEqual(behavior["coping"], "breathing")
        self.assertGreaterEqual(behavior["warmth"], 0.95)

    def test_legacy_role_id_no_longer_changes_help_behavior(self):
        behavior = decide_behavior(
            "help_request",
            {"state": {"current": "neutral", "intensity": 0.2}, "baseline": "neutral"},
            {"focus": None, "mood": None, "concern": 0.0},
            companion_prefs=SimpleNamespace(
                role_id="fitness_coach",
                sliders=SimpleNamespace(
                    emotional_support_level=0.5,
                    humor=0.2,
                    warmth=0.5,
                    verbosity=0.5,
                ),
            ),
        )

        self.assertEqual(behavior["style"], "solution_oriented")
        self.assertEqual(behavior["tone"], "clear")


if __name__ == "__main__":
    unittest.main()
