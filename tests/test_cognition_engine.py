import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import cognition_engine as ce  # noqa: E402
from decision_engine import apply_cognition_to_behavior  # noqa: E402


def _completion(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content))
        ]
    )


class CognitionEngineTests(unittest.TestCase):
    def test_parse_valid_json_applies_schema_fields(self):
        result = ce.parse_cognition_response(
            """
            {
              "approach": "validate_first",
              "priorities": ["acknowledge worry", "normalize the feeling"],
              "risks": ["don't lecture"],
              "ask_question": false,
              "tone_override": "warmer",
              "response_goal": "make user feel heard",
              "memory_to_surface": "user mentioned sister's surgery",
              "emotional_signal": "user is deflecting"
            }
            """
        )

        self.assertEqual(result.approach, "validate_first")
        self.assertEqual(result.priorities, ["acknowledge worry", "normalize the feeling"])
        self.assertEqual(result.risks, ["don't lecture"])
        self.assertFalse(result.ask_question)
        self.assertEqual(result.tone_override, "warmer")
        self.assertEqual(result.response_goal, "make user feel heard")
        self.assertEqual(result.memory_to_surface, "user mentioned sister's surgery")
        self.assertEqual(result.emotional_signal, "user is deflecting")
        self.assertEqual(result.source, "llm")

    def test_parse_malformed_json_returns_safe_rules_default(self):
        result = ce.parse_cognition_response("not json")

        self.assertEqual(result.source, "rules")
        self.assertEqual(result.approach, "stay_brief")
        self.assertTrue(result.ask_question)

    def test_parse_partial_json_fills_defaults(self):
        result = ce.parse_cognition_response('{"approach": "grounding"}')

        self.assertEqual(result.source, "llm")
        self.assertEqual(result.approach, "grounding")
        self.assertEqual(result.priorities, [])
        self.assertEqual(result.risks, [])
        self.assertEqual(result.tone_override, "none")

    def test_should_use_llm_cognition_trigger_matrix(self):
        base = {
            "intent": "casual_talk",
            "emotion": "neutral",
            "intent_confidence": 0.9,
            "emotion_confidence": 0.8,
            "sentiment": {"compound": 0.0},
            "patterns": {"repeated_stress": False},
            "conversation": [],
        }

        self.assertFalse(ce.should_use_llm_cognition(**base))
        self.assertTrue(ce.should_use_llm_cognition(**{**base, "intent_confidence": 0.4}))
        self.assertTrue(ce.should_use_llm_cognition(**{**base, "emotion_confidence": 0.2}))
        self.assertTrue(
            ce.should_use_llm_cognition(
                **{**base, "sentiment": {"compound": -0.4}}
            )
        )
        self.assertTrue(
            ce.should_use_llm_cognition(
                **{**base, "patterns": {"repeated_stress": True}}
            )
        )
        self.assertTrue(ce.should_use_llm_cognition(**{**base, "intent": "reflection"}))
        self.assertTrue(
            ce.should_use_llm_cognition(
                **{**base, "conversation": [{"role": "user", "content": "x"}] * 11}
            )
        )

    def test_rule_fallback_produces_valid_cognition_result(self):
        result = ce.generate_cognition_rules(
            user_input="I am overwhelmed",
            conversation=[{"role": "user", "content": "older"}] * 11,
            emotion="stress",
            intensity=0.8,
            intent="reflection",
            patterns={
                "repeated_stress": True,
                "high_intensity": True,
                "dominant_emotion": "stress",
            },
            style_memories=[],
        )

        self.assertEqual(result.source, "rules")
        self.assertEqual(result.approach, "grounding")
        self.assertFalse(result.ask_question)
        self.assertIn("user may need grounding", result.priorities)
        self.assertIn("stress patterns recurring", result.risks)
        self.assertIn("emotional intensity elevated", result.priorities)
        self.assertIn("maintain long-term continuity", result.priorities)

    def test_apply_cognition_to_behavior_mappings(self):
        behavior = {
            "tone": "composed",
            "verbosity": "medium",
            "style": "sharp",
            "coping": None,
            "sarcasm": 0.4,
            "warmth": 0.65,
        }
        cognition = ce.CognitionResult(
            approach="validate_first",
            priorities=[],
            risks=[],
            ask_question=True,
            tone_override="warmer",
            response_goal="",
            memory_to_surface=None,
            emotional_signal=None,
            source="rules",
        )

        result = apply_cognition_to_behavior(behavior, cognition)

        self.assertEqual(result["verbosity"], "short")
        self.assertEqual(result["warmth"], 0.8)
        self.assertEqual(result["sarcasm"], 0.2)

    def test_generate_cognition_llm_uses_json_mode_and_timeout(self):
        class FakeCompletions:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return _completion(
                    '{"approach": "solution_focus", "ask_question": false, '
                    '"response_goal": "answer directly"}'
                )

        fake_completions = FakeCompletions()
        original_client = ce.client
        try:
            ce.client = SimpleNamespace(
                chat=SimpleNamespace(completions=fake_completions)
            )
            result = ce.generate_cognition_llm({"latest_user_message": "fix this"})
        finally:
            ce.client = original_client

        self.assertEqual(result.source, "llm")
        self.assertEqual(result.approach, "solution_focus")
        self.assertFalse(result.ask_question)
        self.assertEqual(fake_completions.kwargs["model"], "gpt-4o-mini")
        self.assertEqual(fake_completions.kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(fake_completions.kwargs["temperature"], 0.3)
        self.assertEqual(fake_completions.kwargs["timeout"], 8)

    def test_generate_cognition_error_returns_rules_result(self):
        class BrokenCompletions:
            def create(self, **kwargs):
                raise TimeoutError("slow")

        original_client = ce.client
        try:
            ce.client = SimpleNamespace(
                chat=SimpleNamespace(completions=BrokenCompletions())
            )
            result = ce.generate_cognition(
                user_input="I need help",
                conversation=[],
                emotion="neutral",
                intensity=0.3,
                intent="help_request",
                intent_confidence=0.9,
                emotion_confidence=0.9,
                sentiment={"compound": 0.0},
                patterns={"repeated_stress": False, "high_intensity": False},
                style_memories=[],
            )
        finally:
            ce.client = original_client

        self.assertEqual(result.source, "rules")


if __name__ == "__main__":
    unittest.main()
