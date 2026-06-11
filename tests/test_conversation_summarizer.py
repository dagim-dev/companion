import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import conversation_summarizer as cs  # noqa: E402


def _completion(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content))
        ]
    )


class ConversationSummarizerTests(unittest.TestCase):
    def test_parses_pending_external_outcome_as_unresolved(self):
        # New structured summary parsing lets the LLM flag open outcomes directly.
        result = cs.parse_episode_summary_response(
            '{"summary": "The user is anxious while waiting to hear back from '
            'their landlord.", "unresolved": true}'
        )

        self.assertEqual(
            result.summary,
            "The user is anxious while waiting to hear back from their landlord.",
        )
        self.assertTrue(result.unresolved)

    def test_parses_finished_event_as_resolved(self):
        # Finished events should not remain open just because they mention keywords.
        result = cs.parse_episode_summary_response(
            '{"summary": "The interview was yesterday, and the user is moving '
            'on.", "unresolved": false}'
        )

        self.assertFalse(result.unresolved)

    def test_parses_emotional_but_closed_situation_as_resolved(self):
        # Emotional weight alone is not an unresolved external outcome.
        result = cs.parse_episode_summary_response(
            '{"summary": "The user felt sad about an old argument but has '
            'processed it.", "unresolved": false}'
        )

        self.assertFalse(result.unresolved)

    def test_parses_no_keyword_open_situation_as_unresolved(self):
        # Open situations can lack the old keyword list entirely.
        result = cs.parse_episode_summary_response(
            '{"summary": "The user is nervous about tomorrow and expects to '
            'hear back soon.", "unresolved": true}'
        )

        self.assertTrue(result.unresolved)

    def test_malformed_response_falls_back_to_resolved_summary_text(self):
        # Malformed model output should not create sticky unresolved follow-ups.
        result = cs.parse_episode_summary_response("not json but still a summary")

        self.assertEqual(result.summary, "not json but still a summary")
        self.assertFalse(result.unresolved)

    def test_summarize_recent_returns_structured_result_from_llm_json(self):
        # The existing LLM call now carries both summary text and open/closed state.
        conversation = [
            {"role": "user", "content": f"message {idx}"}
            for idx in range(15)
        ]

        class FakeCompletions:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return _completion(
                    '{"summary": "The user is waiting for news.", '
                    '"unresolved": true}'
                )

        fake_completions = FakeCompletions()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        )

        original_client = cs.client
        try:
            cs.client = fake_client
            result = cs.summarize_recent(conversation)
        finally:
            cs.client = original_client

        self.assertEqual(result.summary, "The user is waiting for news.")
        self.assertTrue(result.unresolved)
        self.assertEqual(
            fake_completions.kwargs["response_format"],
            {"type": "json_object"},
        )


if __name__ == "__main__":
    unittest.main()
