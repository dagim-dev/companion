import os
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import message_processor as mp  # noqa: E402
from cognition_engine import CognitionResult  # noqa: E402
from conversation_summarizer import EpisodeSummary  # noqa: E402


def _cognition():
    return CognitionResult(
        approach="stay_brief",
        priorities=[],
        risks=[],
        ask_question=True,
        tone_override="none",
        response_goal="maintain composed flow",
        memory_to_surface=None,
        emotional_signal=None,
        source="rules",
    )


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
        cognition=_cognition(),
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


class LlmKwargsTests(unittest.TestCase):
    def test_llm_kwargs_passes_cognition_without_old_reasoning_fields(self):
        state = SimpleNamespace(
            conversation=[],
            internal_state=SimpleNamespace(snapshot=lambda: {}),
            meta_cognition=SimpleNamespace(
                snapshot=lambda: {
                    "response_confidence": 0.8,
                    "user_stability": 0.8,
                    "conversation_quality": 0.8,
                }
            ),
            personality_state=SimpleNamespace(snapshot=lambda: {}),
            self_perception=SimpleNamespace(snapshot=lambda: {}),
        )
        turn = _turn()

        kwargs = mp._llm_kwargs(state, turn)

        self.assertIs(kwargs["cognition"], turn.cognition)
        self.assertNotIn("internal_reasoning", kwargs)
        self.assertNotIn("thought_state", kwargs)


class PrepareTurnCognitionWiringTests(unittest.TestCase):
    def test_prepare_turn_applies_cognition_before_questions_and_behavior(self):
        call_order = []
        cognition = CognitionResult(
            approach="validate_first",
            priorities=["acknowledge worry"],
            risks=[],
            ask_question=False,
            tone_override="warmer",
            response_goal="make user feel heard",
            memory_to_surface="prefers concise reassurance",
            emotional_signal=None,
            source="rules",
        )
        curiosity_engine = SimpleNamespace(generate_question=mock.Mock())
        state = SimpleNamespace(
            user_id="user-123",
            companion_prefs=SimpleNamespace(),
            conversation=[],
            turn_count=0,
            analyzer=SimpleNamespace(polarity_scores=lambda _message: {"compound": -0.2}),
            internal_state=SimpleNamespace(
                update=lambda _emotion, _intent: None,
                snapshot=lambda: {},
            ),
            personality_state=SimpleNamespace(
                relationship_depth=0.4,
                update=lambda _emotion, _intent, _turns: None,
            ),
            self_perception=SimpleNamespace(
                update=lambda _emotion, _intensity, _intent, _turns: None,
                snapshot=lambda: {},
            ),
            curiosity_engine=curiosity_engine,
        )

        def fake_generate_cognition(**kwargs):
            call_order.append("cognition")
            self.assertEqual(kwargs["style_memories"], [{"category": "preference"}])
            return cognition

        def fake_decide_behavior(*_args, **_kwargs):
            call_order.append("behavior")
            return {
                "tone": "composed",
                "verbosity": "medium",
                "style": "sharp",
                "coping": None,
                "sarcasm": 0.4,
                "warmth": 0.5,
            }

        patches = [
            mock.patch.object(mp, "decay_memories"),
            mock.patch.object(mp, "consolidate_memories"),
            mock.patch.object(mp, "extract_personal_memories", return_value=[]),
            mock.patch.object(mp, "detect_emotion", return_value=("sad", 0.8)),
            mock.patch.object(mp, "classify_intent", return_value="reflection"),
            mock.patch.object(mp, "intent_confidence", return_value=0.9),
            mock.patch.object(mp, "detect_reflection_topic", return_value=None),
            mock.patch.object(mp, "set_emotional_state"),
            mock.patch.object(mp, "add_emotional_history"),
            mock.patch.object(mp, "get_profile", return_value={}),
            mock.patch.object(
                mp,
                "get_emotional_profile",
                return_value={"state": {"current": "sad", "intensity": 0.8}, "baseline": "neutral"},
            ),
            mock.patch.object(
                mp,
                "detect_emotional_patterns",
                return_value={
                    "repeated_stress": False,
                    "high_intensity": True,
                    "dominant_emotion": "sad",
                },
            ),
            mock.patch.object(mp, "retrieve_relevant_reflections", return_value=[]),
            mock.patch.object(mp, "build_context", return_value={}),
            mock.patch.object(mp, "retrieve_relevant_personal_memories", return_value=[]),
            mock.patch.object(
                mp,
                "retrieve_style_preference_memories",
                return_value=[{"category": "preference"}],
            ),
            mock.patch.object(mp, "generate_cognition", side_effect=fake_generate_cognition),
            mock.patch.object(mp, "extract_user_insights", return_value={}),
            mock.patch.object(mp, "maybe_consolidate_preferences"),
            mock.patch.object(mp, "generate_checkin", return_value=None),
            mock.patch.object(mp, "decide_behavior", side_effect=fake_decide_behavior),
            mock.patch.object(mp, "generate_followup"),
        ]

        with ExitStack() as stack:
            started_patches = [stack.enter_context(patch) for patch in patches]
            followup = started_patches[-1]
            turn = mp.prepare_turn(state, "I feel off today")

        self.assertEqual(call_order, ["cognition", "behavior"])
        self.assertIs(turn.cognition, cognition)
        self.assertEqual(turn.context["cognition_memory_hint"], "prefers concise reassurance")
        self.assertEqual(turn.behavior["verbosity"], "short")
        self.assertEqual(turn.behavior["warmth"], 0.75)
        self.assertEqual(turn.behavior["sarcasm"], 0.2)
        self.assertIsNone(turn.initiative_question)
        self.assertIsNone(turn.followup)
        curiosity_engine.generate_question.assert_not_called()
        followup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
