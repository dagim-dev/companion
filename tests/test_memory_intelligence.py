import unittest

from memory_intelligence import (
    ExtractionFailure,
    extract_insights_from_message,
    parse_insight_response,
)


class ParseInsightResponseTests(unittest.TestCase):
    def test_parses_valid_structured_insights(self):
        content = """
        {
          "insights": [
            {
              "label": "Become a software engineer",
              "type": "goal",
              "confidence": 0.92,
              "evidence": "I want to become a software engineer",
              "source": "latest_user_message",
              "stability": "long_term"
            }
          ]
        }
        """

        insights = parse_insight_response(content)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].label, "Become a software engineer")
        self.assertEqual(insights[0].type, "goal")
        self.assertEqual(insights[0].confidence, 0.92)

    def test_invalid_json_raises_extraction_failure(self):
        with self.assertRaises(ExtractionFailure):
            parse_insight_response("not json")

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(ExtractionFailure):
            parse_insight_response('{"insights": [{"label": "Curious"}]}')

    def test_filters_low_confidence_insights(self):
        content = """
        {
          "insights": [
            {
              "label": "Likes programming",
              "type": "interest",
              "confidence": 0.4,
              "evidence": "Maybe I like programming",
              "source": "latest_user_message",
              "stability": "long_term"
            }
          ]
        }
        """

        self.assertEqual(parse_insight_response(content), [])

    def test_temporary_emotions_parse_but_remain_temporary(self):
        content = """
        {
          "insights": [
            {
              "label": "Frustrated",
              "type": "emotional_state",
              "confidence": 0.91,
              "evidence": "I'm frustrated right now",
              "source": "latest_user_message",
              "stability": "temporary"
            }
          ]
        }
        """

        insights = parse_insight_response(content)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].type, "emotional_state")
        self.assertEqual(insights[0].stability, "temporary")

    def test_parses_normalized_preference_metadata(self):
        content = """
        {
          "insights": [
            {
              "label": "User prefers direct answers",
              "type": "preference",
              "preference_key": "response.directness",
              "preference_value": {"target": "direct"},
              "scope": "global",
              "context": null,
              "evidence_polarity": "positive",
              "confidence": 0.91,
              "evidence": "Be direct with me.",
              "source": "latest_user_message",
              "stability": "long_term"
            }
          ]
        }
        """

        insights = parse_insight_response(content)

        self.assertEqual(insights[0].preference_key, "response.directness")
        self.assertEqual(insights[0].preference_value, {"target": "direct"})
        self.assertEqual(insights[0].scope, "global")

    def test_extraction_uses_latest_user_message_and_recent_context(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                message = type(
                    "Message",
                    (),
                    {
                        "content": (
                            '{"insights":[{"label":"Prefers concise answers",'
                            '"type":"preference","confidence":0.9,'
                            '"evidence":"I prefer concise answers",'
                            '"source":"latest_user_message","stability":"long_term"}]}'
                        )
                    },
                )
                choice = type("Choice", (), {"message": message})
                return type("Response", (), {"choices": [choice]})

        class FakeClient:
            chat = type(
                "Chat",
                (),
                {"completions": FakeCompletions()},
            )

        insights = extract_insights_from_message(
            latest_user_message="I prefer concise answers",
            recent_context=[
                {"role": "assistant", "content": "I can be concise."},
                {"role": "user", "content": "Earlier user context"},
            ],
            client=FakeClient(),
        )

        self.assertEqual(len(insights), 1)
        payload = calls[0]["messages"][1]["content"]
        self.assertIn("I prefer concise answers", payload)
        self.assertIn("Earlier user context", payload)
        self.assertNotIn("I can be concise.", payload)


if __name__ == "__main__":
    unittest.main()
