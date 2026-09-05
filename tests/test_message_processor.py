import os
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import message_processor as mp  # noqa: E402
from cognition_engine import CognitionResult  # noqa: E402
from conversation_summarizer import EpisodeSummary  # noqa: E402
from llm import LLMRequestError  # noqa: E402


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
        self.assertIs(kwargs["effective_personality"], getattr(turn, "effective_personality", None))


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
        effective_personality = SimpleNamespace(final_sliders={}, directives=[])
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
            mock.patch.object(
                mp,
                "retrieve_style_preference_memories",
                return_value=[{"category": "preference"}],
            ),
            mock.patch.object(mp, "generate_cognition", side_effect=fake_generate_cognition),
            mock.patch.object(
                mp,
                "get_active_learned_preferences",
                return_value=[{"preference_key": "response.length"}],
            ),
            mock.patch.object(mp, "runtime_modifiers_for_turn", return_value=[]),
            mock.patch.object(
                mp,
                "compose_effective_personality",
                return_value=effective_personality,
            ),
            mock.patch.object(
                mp,
                "get_recent_insights",
                return_value=[{"label": "Prefers concise answers"}],
            ),
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
        self.assertEqual(turn.insights, [{"label": "Prefers concise answers"}])
        self.assertIs(turn.effective_personality, effective_personality)
        self.assertEqual(turn.behavior["verbosity"], "short")
        self.assertEqual(turn.behavior["warmth"], 0.75)
        self.assertEqual(turn.behavior["sarcasm"], 0.2)
        self.assertIsNone(turn.initiative_question)
        self.assertIsNone(turn.followup)
        curiosity_engine.generate_question.assert_not_called()
        followup.assert_not_called()


class MemoryExtractionQueueFlowTests(unittest.TestCase):
    def test_prepare_turn_does_not_run_memory_extraction_on_request_path(self):
        state = SimpleNamespace(
            user_id="user-123",
            companion_prefs=SimpleNamespace(),
            conversation=[],
            turn_count=0,
            analyzer=SimpleNamespace(polarity_scores=lambda _message: {"compound": 0.1}),
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
            curiosity_engine=SimpleNamespace(generate_question=mock.Mock()),
        )

        patches = [
            mock.patch.object(mp, "decay_memories"),
            mock.patch.object(mp, "consolidate_memories"),
            mock.patch.object(mp, "detect_emotion", return_value=("neutral", 0.2)),
            mock.patch.object(mp, "classify_intent", return_value="help_request"),
            mock.patch.object(mp, "intent_confidence", return_value=0.9),
            mock.patch.object(mp, "detect_reflection_topic", return_value=None),
            mock.patch.object(mp, "set_emotional_state"),
            mock.patch.object(mp, "add_emotional_history"),
            mock.patch.object(mp, "get_profile", return_value={}),
            mock.patch.object(
                mp,
                "get_emotional_profile",
                return_value={"state": {"current": "neutral", "intensity": 0.2}, "baseline": "neutral"},
            ),
            mock.patch.object(
                mp,
                "detect_emotional_patterns",
                return_value={
                    "repeated_stress": False,
                    "high_intensity": False,
                    "dominant_emotion": "neutral",
                },
            ),
            mock.patch.object(mp, "retrieve_relevant_reflections", return_value=[]),
            mock.patch.object(mp, "build_context", return_value={}),
            mock.patch.object(mp, "retrieve_style_preference_memories", return_value=[]),
            mock.patch.object(mp, "generate_cognition", return_value=_cognition()),
            mock.patch.object(mp, "get_active_learned_preferences", return_value=[]),
            mock.patch.object(mp, "runtime_modifiers_for_turn", return_value=[]),
            mock.patch.object(
                mp,
                "compose_effective_personality",
                return_value=SimpleNamespace(final_sliders={}, directives=[]),
            ),
            mock.patch.object(mp, "get_recent_insights", return_value=[]),
            mock.patch.object(mp, "generate_checkin", return_value=None),
            mock.patch.object(
                mp,
                "decide_behavior",
                return_value={
                    "tone": "composed",
                    "verbosity": "medium",
                    "style": "sharp",
                    "coping": None,
                },
            ),
            mock.patch.object(mp, "generate_followup", return_value=None),
        ]

        with ExitStack() as stack, \
                mock.patch("memory_intelligence.extract_insights_from_message") as extractor, \
                mock.patch.object(mp, "enqueue_extraction_job") as enqueue:
            for patch in patches:
                stack.enter_context(patch)
            turn = mp.prepare_turn(state, "I prefer concise answers")

        self.assertIsNotNone(turn)
        extractor.assert_not_called()
        enqueue.assert_not_called()

    def test_finalize_response_persists_only_assistant_row(self):
        state = SimpleNamespace(
            user_id="user-123",
            conversation=[],
            meta_cognition=SimpleNamespace(evaluate_interaction=lambda **_kwargs: None),
            persistence_cycle_start_turn=0,
            turn_count=1,
            personality_state=SimpleNamespace(snapshot=lambda: {}),
        )
        turn = _turn()
        turn.user_message_id = 42
        created_messages = []

        def fake_create_message(user_id, role, content):
            created_messages.append((user_id, role, content))
            return len(created_messages)

        with mock.patch.object(mp, "control_response", return_value="Final answer"), \
                mock.patch.object(mp, "apply_rhythm", return_value="Final answer"), \
                mock.patch.object(mp, "maybe_add_initiative", return_value=None), \
                mock.patch.object(mp, "_maybe_create_episode"), \
                mock.patch.object(mp, "_maybe_persist_runtime"), \
                mock.patch.object(mp, "create_conversation_message", side_effect=fake_create_message), \
                mock.patch.object(mp, "enqueue_extraction_job") as enqueue:
            response = mp.finalize_response(state, turn, "raw answer")

        self.assertEqual(response, "Final answer")
        self.assertEqual(
            created_messages,
            [("user-123", "assistant", "Final answer")],
        )
        enqueue.assert_not_called()

    def test_persist_user_turn_writes_user_and_enqueues_once(self):
        state = SimpleNamespace(user_id="user-123")
        turn = _turn()
        created_messages = []

        def fake_create_message(user_id, role, content):
            created_messages.append((user_id, role, content))
            return 7

        with mock.patch.object(mp, "create_conversation_message", side_effect=fake_create_message), \
                mock.patch.object(mp, "enqueue_extraction_job") as enqueue:
            message_id = mp.persist_user_turn(state, turn)

        self.assertEqual(message_id, 7)
        self.assertEqual(turn.user_message_id, 7)
        self.assertEqual(created_messages, [("user-123", "user", "hello")])
        enqueue.assert_called_once_with(message_id=7, message_content="hello")

    def test_persist_user_turn_is_idempotent(self):
        state = SimpleNamespace(user_id="user-123")
        turn = _turn()
        turn.user_message_id = 11

        with mock.patch.object(mp, "create_conversation_message") as create_message, \
                mock.patch.object(mp, "enqueue_extraction_job") as enqueue:
            message_id = mp.persist_user_turn(state, turn)

        self.assertEqual(message_id, 11)
        create_message.assert_not_called()
        enqueue.assert_not_called()

    def test_process_message_llm_failure_persists_user_without_assistant(self):
        state = SimpleNamespace(
            user_id="user-123",
            conversation=[],
            turn_count=0,
        )
        turn = _turn()

        with mock.patch.object(mp, "prepare_turn", return_value=turn), \
                mock.patch.object(mp, "persist_user_turn", return_value=5) as persist_user, \
                mock.patch.object(mp, "_llm_kwargs", return_value={}), \
                mock.patch.object(mp, "chat", side_effect=LLMRequestError("stream failed")), \
                mock.patch.object(mp, "finalize_response") as finalize:
            with self.assertRaises(LLMRequestError):
                mp.process_message(state, "hello")

        persist_user.assert_called_once_with(state, turn)
        finalize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
