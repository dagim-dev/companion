import unittest
from types import SimpleNamespace

from companion_prefs import SliderPrefs
from personality_composer import (
    compose_effective_personality,
    runtime_modifiers_for_turn,
)


class PersonalityComposerTests(unittest.TestCase):
    def test_baseline_only_composition_keeps_jarvis_identity_and_sliders(self):
        prefs = SimpleNamespace(
            sliders=SliderPrefs(directness=0.8, warmth=0.5, verbosity=0.35),
            baseline_directives={"examples_frequency": "when_useful"},
        )

        effective = compose_effective_personality(
            companion_prefs=prefs,
            learned_preferences=[],
            runtime_modifiers=[],
        )

        self.assertEqual(effective.identity, "jarvis")
        self.assertEqual(effective.final_sliders["directness"], 0.8)
        self.assertEqual(effective.final_sliders["verbosity"], 0.35)
        self.assertIn("examples_frequency=when_useful", effective.directives)
        self.assertFalse(any("role" in reason.lower() for reason in effective.audit_reasons))

    def test_learned_concise_preference_boundedly_reduces_verbosity(self):
        prefs = SimpleNamespace(
            sliders=SliderPrefs(verbosity=0.6),
            baseline_directives={},
        )

        effective = compose_effective_personality(
            companion_prefs=prefs,
            learned_preferences=[
                {
                    "id": 1,
                    "preference_key": "response.length",
                    "value": {"target": "concise"},
                    "confidence": 0.95,
                }
            ],
            runtime_modifiers=[],
        )

        self.assertLess(effective.final_sliders["verbosity"], 0.6)
        self.assertGreaterEqual(effective.final_sliders["verbosity"], 0.35)
        self.assertIn("prefer concise responses", effective.directives)

    def test_high_distress_temporarily_increases_support_and_reduces_challenge(self):
        prefs = SimpleNamespace(
            sliders=SliderPrefs(
                directness=0.85,
                warmth=0.45,
                accountability=0.9,
                emotional_support_level=0.25,
            ),
            baseline_directives={},
        )
        modifiers = runtime_modifiers_for_turn(
            emotion="sad",
            intent="reflection",
            intensity=0.9,
            patterns={"high_intensity": True},
        )

        effective = compose_effective_personality(
            companion_prefs=prefs,
            learned_preferences=[],
            runtime_modifiers=modifiers,
        )

        self.assertGreaterEqual(effective.final_sliders["warmth"], 0.7)
        self.assertGreaterEqual(effective.final_sliders["emotional_support"], 0.6)
        self.assertLess(effective.final_sliders["accountability"], 0.9)
        self.assertIn("validate first", effective.directives)
        self.assertTrue(any("runtime:distress_support" in r for r in effective.audit_reasons))

    def test_few_examples_preference_avoids_examples_by_default(self):
        prefs = SimpleNamespace(
            sliders=SliderPrefs(),
            baseline_directives={},
        )

        effective = compose_effective_personality(
            companion_prefs=prefs,
            learned_preferences=[
                {
                    "id": 2,
                    "preference_key": "response.examples",
                    "value": {"target": "few"},
                    "confidence": 0.93,
                }
            ],
            runtime_modifiers=[],
        )

        self.assertIn("avoid examples unless asked", effective.directives)


if __name__ == "__main__":
    unittest.main()
