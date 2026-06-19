import unittest

from companion_prefs import SliderPrefs
from types import SimpleNamespace
from personality_composer import EffectivePersonality, RuntimeModifier
from prompt_builder import build_personality_layer


class PromptBuilderV2Tests(unittest.TestCase):
    def test_effective_personality_prompt_has_jarvis_identity_without_role_sections(self):
        effective = EffectivePersonality(
            identity="jarvis",
            baseline_sliders=SliderPrefs().to_dict(),
            learned_modifiers=[
                {
                    "id": 1,
                    "preference_key": "response.length",
                    "directives": ["prefer concise responses"],
                }
            ],
            runtime_modifiers=[
                RuntimeModifier(
                    key="distress_support",
                    deltas={"warmth": 0.2},
                    directives=["validate first"],
                    reason="emotion=sad intensity=0.90",
                    ttl_turns=3,
                )
            ],
            final_sliders={
                "directness": 0.65,
                "warmth": 0.78,
                "humor": 0.2,
                "verbosity": 0.4,
                "accountability": 0.45,
                "emotional_support": 0.85,
            },
            directives=["prefer concise responses", "validate first"],
            audit_reasons=["baseline:companion_preferences", "runtime:distress_support"],
        )

        prompt = build_personality_layer(effective_personality=effective)

        self.assertIn("J.A.R.V.I.S.", prompt)
        self.assertIn("USER BASELINE STYLE", prompt)
        self.assertIn("LEARNED USER PREFERENCES", prompt)
        self.assertIn("CURRENT CONTEXT ADAPTATION", prompt)
        self.assertIn("prefer concise responses", prompt)
        self.assertIn("validate first", prompt)
        self.assertNotIn("COMPANION ROLE", prompt)
        self.assertNotIn("ROLE EMPHASIS", prompt)

    def test_legacy_prompt_path_does_not_load_role_templates(self):
        prompt = build_personality_layer()

        self.assertIn("J.A.R.V.I.S.", prompt)
        self.assertNotIn("COMPANION ROLE", prompt)
        self.assertNotIn("ROLE EMPHASIS", prompt)

    def test_effective_personality_prompt_preserves_custom_notes(self):
        effective = EffectivePersonality(
            identity="jarvis",
            baseline_sliders={},
            learned_modifiers=[],
            runtime_modifiers=[],
            final_sliders={
                "directness": 0.6,
                "warmth": 0.55,
                "humor": 0.35,
                "verbosity": 0.5,
                "accountability": 0.5,
                "emotional_support": 0.5,
            },
        )
        prefs = SimpleNamespace(custom_notes="Prefer blunt feedback on workouts.")

        prompt = build_personality_layer(prefs=prefs, effective_personality=effective)

        self.assertIn("USER CUSTOM NOTES", prompt)
        self.assertIn("Prefer blunt feedback on workouts.", prompt)


if __name__ == "__main__":
    unittest.main()
