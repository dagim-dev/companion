import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import message_processor as mp  # noqa: E402
from conversation_summarizer import EpisodeSummary  # noqa: E402


def _turn(intensity=0.2, emotion="neutral"):
    return mp.PreparedTurn(
        user_input="hello",
        intent="help_request",
        emotion=emotion,
        intensity=intensity,
        profile={},
        personal_memories=[],
        emotional_profile={},
        behavior={},
        patterns={},
        context={},
        insights={},
        internal_reasoning="",
        initiative_question=None,
        followup=None,
    )


class MaybeCreateEpisodeTests(unittest.TestCase):
    def _state_with_message_count(self, count):
        return SimpleNamespace(
            conversation=[
                {"role": "user", "content": f"message {idx}"}
                for idx in range(count)
            ]
        )

    def test_unresolved_summary_creates_open_episode(self):
        # _maybe_create_episode converts summarizer unresolved=True to resolved=False.
        state = self._state_with_message_count(24)
        summary = EpisodeSummary("The user is waiting on news.", unresolved=True)

        with mock.patch.object(mp, "summarize_recent", return_value=summary), \
                mock.patch.object(mp, "create_episode") as create_episode:
            mp._maybe_create_episode(state, _turn(emotion="anxiety"))

        create_episode.assert_called_once_with(
            summary="The user is waiting on news.",
            emotion="anxiety",
            importance=0.5,
            resolved=False,
        )

    def test_resolved_summary_creates_closed_episode(self):
        # _maybe_create_episode keeps closed summaries closed in storage.
        state = self._state_with_message_count(24)
        summary = EpisodeSummary("The user moved on after the interview.", unresolved=False)

        with mock.patch.object(mp, "summarize_recent", return_value=summary), \
                mock.patch.object(mp, "create_episode") as create_episode:
            mp._maybe_create_episode(state, _turn(intensity=0.8, emotion="relief"))

        create_episode.assert_called_once_with(
            summary="The user moved on after the interview.",
            emotion="relief",
            importance=0.8,
            resolved=True,
        )

    def test_non_cycle_turn_does_not_summarize(self):
        # The existing modulo-12 gate should remain unchanged.
        state = self._state_with_message_count(23)

        with mock.patch.object(mp, "summarize_recent") as summarize_recent, \
                mock.patch.object(mp, "create_episode") as create_episode:
            mp._maybe_create_episode(state, _turn())

        summarize_recent.assert_not_called()
        create_episode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
