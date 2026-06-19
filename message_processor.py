import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from classifier import classify_intent, detect_emotion, intent_confidence
from context_builder import build_context
from cognition_engine import CognitionResult, generate_cognition
from memory_followups import generate_followup
from conversation_summarizer import summarize_recent
from decision_engine import apply_cognition_to_behavior, decide_behavior
from episodic_memory import create_episode
from curiosity_engine import maybe_add_initiative
from llm import chat, chat_stream
from memory import (
    add_emotional_history,
    create_conversation_message,
    detect_emotional_patterns,
    get_emotional_profile,
    get_profile,
    set_emotional_state,
)
from companion_prefs import get_companion_preferences, save_runtime_personality
from persistence_policy import (
    PersistenceCycleClock,
    FREE_PERSIST_INTERVAL_TURNS,
    cycle_timestamp,
    get_persist_interval_turns,
    log_persistence_status,
)
from memory_recall import (
    retrieve_relevant_personal_memories,
    retrieve_style_preference_memories,
)
from memory_retriever import retrieve_relevant_reflections
from memory_insights import get_recent_insights
from learned_preferences import get_active_learned_preferences
from memory_extraction_jobs import enqueue_extraction_job
from personality_composer import (
    compose_effective_personality,
    runtime_modifiers_for_turn,
)
from reflection_engine import (
    detect_reflection_topic,
    generate_checkin,
    update_reflection,
)
from response_controller import control_response
from rhythm_engine import apply_rhythm
from session_state import JarvisState
from memory_decay import decay_memories
from memory_consolidation import consolidate_memories


@dataclass
class PreparedTurn:
    user_input: str
    intent: str
    emotion: str
    intensity: float
    profile: dict
    personal_memories: list
    emotional_profile: dict
    behavior: dict
    patterns: dict
    context: dict
    insights: dict
    cognition: CognitionResult
    initiative_question: Optional[str]
    followup: Optional[str]
    companion_prefs: Any = None
    learned_preference_memories: list = field(default_factory=list)
    effective_personality: Any = None


def prepare_turn(state: JarvisState, user_input: str) -> Optional[PreparedTurn]:
    """Run pre-LLM pipeline. Returns None if turn should be skipped (uncertain intent)."""
    decay_memories()
    consolidate_memories()

    if state.companion_prefs is None:
        state.companion_prefs = get_companion_preferences(state.user_id)

    state.conversation.append({"role": "user", "content": user_input})
    state.turn_count += 1

    sentiment = state.analyzer.polarity_scores(user_input)
    emotion, intensity = detect_emotion(user_input, sentiment)
    intent = classify_intent(user_input)
    intent_score = intent_confidence(user_input, intent)
    emotion_confidence = intensity

    state.internal_state.update(emotion, intent)
    state.personality_state.update(emotion, intent, len(state.conversation))
    state.self_perception.update(
        emotion, intensity, intent, len(state.conversation)
    )

    reflection_topic = detect_reflection_topic(user_input)
    if reflection_topic:
        update_reflection(
            topic=reflection_topic,
            content=user_input,
            emotion=emotion,
            intensity=intensity,
        )

    set_emotional_state(emotion, intensity)
    add_emotional_history(emotion, intensity)

    profile = get_profile()
    emotional_profile = get_emotional_profile()

    if intent == "uncertain":
        state.conversation.pop()
        return None

    patterns = detect_emotional_patterns()

    if intent in ("reflection", "anxiety_stress", "help_request"):
        relevant_reflections = retrieve_relevant_reflections(user_input)
    else:
        relevant_reflections = []

    context = build_context(profile, emotional_profile, patterns, state.conversation)
    personal_memories = retrieve_relevant_personal_memories(user_input)
    learned_preference_memories = retrieve_style_preference_memories(user_input)
    context["personal_memories"] = personal_memories
    context["relevant_reflections"] = relevant_reflections

    cognition = generate_cognition(
        user_input=user_input,
        conversation=state.conversation,
        emotion=emotion,
        intensity=intensity,
        intent=intent,
        intent_confidence=intent_score,
        emotion_confidence=emotion_confidence,
        sentiment=sentiment,
        patterns=patterns,
        style_memories=learned_preference_memories,
    )
    if cognition.memory_to_surface:
        context["cognition_memory_hint"] = cognition.memory_to_surface

    insights = get_recent_insights(limit=20)
    active_learned_preferences = get_active_learned_preferences(limit=8)
    runtime_modifiers = runtime_modifiers_for_turn(
        emotion=emotion,
        intent=intent,
        intensity=intensity,
        patterns=patterns,
    )
    effective_personality = compose_effective_personality(
        companion_prefs=state.companion_prefs,
        learned_preferences=active_learned_preferences,
        runtime_modifiers=runtime_modifiers,
    )

    checkin = generate_checkin()
    if checkin:
        context["reflection_checkin"] = checkin

    behavior = decide_behavior(
        intent,
        emotional_profile,
        state.internal_state.snapshot(),
        companion_prefs=state.companion_prefs,
        effective_personality=effective_personality,
    )
    behavior = apply_cognition_to_behavior(behavior, cognition)

    initiative_question = None
    followup = None
    if cognition.ask_question:
        initiative_question = state.curiosity_engine.generate_question(
            intent,
            emotion,
            intensity,
            state.personality_state.relationship_depth,
        )

        followup = generate_followup(
            emotional_profile,
            patterns,
            state.personality_state.relationship_depth,
        )

    return PreparedTurn(
        user_input=user_input,
        intent=intent,
        emotion=emotion,
        intensity=intensity,
        profile=profile,
        personal_memories=personal_memories,
        emotional_profile=emotional_profile,
        behavior=behavior,
        patterns=patterns,
        context=context,
        insights=insights,
        cognition=cognition,
        initiative_question=initiative_question,
        followup=followup,
        companion_prefs=state.companion_prefs,
        learned_preference_memories=learned_preference_memories,
        effective_personality=effective_personality,
    )


def finalize_response(
    state: JarvisState,
    turn: PreparedTurn,
    raw_response: str,
) -> str:
    response = control_response(raw_response, turn.behavior, turn.intent)
    response = apply_rhythm(response, turn.intent, turn.intensity)

    state.meta_cognition.evaluate_interaction(
        user_input=turn.user_input,
        response=response,
        emotion=turn.emotion,
        intensity=turn.intensity,
        intent=turn.intent,
    )

    initiative = maybe_add_initiative(turn.intent, turn.intensity)
    if initiative:
        response += f"\n\n{initiative}"
    if turn.initiative_question:
        response += f"\n\n{turn.initiative_question}"
    if turn.followup:
        response += f"\n\n{turn.followup}"

    state.conversation.append({"role": "assistant", "content": response})
    user_message_id = create_conversation_message(
        state.user_id,
        "user",
        turn.user_input,
    )
    create_conversation_message(
        state.user_id,
        "assistant",
        response,
    )
    enqueue_extraction_job(
        message_id=user_message_id,
        message_content=turn.user_input,
    )
    _maybe_create_episode(state, turn)
    _maybe_persist_runtime(state)
    return response


# Re-export for tests/docs; actual interval comes from persistence_policy per user tier.
RUNTIME_PERSIST_EVERY_N_TURNS = FREE_PERSIST_INTERVAL_TURNS


def _persistence_clock(state: JarvisState) -> PersistenceCycleClock:
    interval = get_persist_interval_turns(state.user_id)
    return PersistenceCycleClock(
        interval_turns=interval,
        cycle_start_turn=state.persistence_cycle_start_turn,
    )


def _maybe_persist_runtime(state: JarvisState) -> None:
    clock = _persistence_clock(state)
    log_persistence_status(state.user_id, state.turn_count, clock)

    if not clock.should_persist(state.turn_count):
        return

    save_runtime_personality(
        state.personality_state.snapshot(),
        user_id=state.user_id,
    )
    clock.complete_cycle(state.turn_count)
    state.persistence_cycle_start_turn = clock.cycle_start_turn
    # cycle_timestamp() reserved for future tier/analytics when persisting metadata
    _ = cycle_timestamp()


def _maybe_create_episode(state: JarvisState, turn: PreparedTurn) -> None:
    if len(state.conversation) % 12 != 0:
        return
    episode_summary = summarize_recent(state.conversation)
    if not episode_summary:
        return
    importance = 0.5
    if turn.intensity > 0.7:
        importance += 0.3
    # The summarizer returns unresolved=True for open outcomes; DB resolved is inverse.
    create_episode(
        summary=episode_summary.summary,
        emotion=turn.emotion,
        importance=importance,
        resolved=not episode_summary.unresolved,
    )


def _llm_kwargs(state: JarvisState, turn: PreparedTurn) -> dict[str, Any]:
    return {
        "conversation": state.conversation,
        "profile": turn.profile,
        "personal_memories": turn.personal_memories,
        "emotional_profile": turn.emotional_profile,
        "intent": turn.intent,
        "behavior": turn.behavior,
        "patterns": turn.patterns,
        "context": turn.context,
        "insights": turn.insights,
        "cognition": turn.cognition,
        "internal_state": state.internal_state.snapshot(),
        "meta_cognition": state.meta_cognition.snapshot(),
        "personality_state": state.personality_state.snapshot(),
        "self_perception": state.self_perception.snapshot(),
        "companion_prefs": turn.companion_prefs,
        "learned_preference_memories": turn.learned_preference_memories or [],
        "effective_personality": turn.effective_personality,
    }


def stream_llm_tokens(
    state: JarvisState,
    turn: PreparedTurn,
    *,
    echo_to_terminal: bool = False,
) -> Iterator[str]:
    yield from chat_stream(**_llm_kwargs(state, turn), echo_to_terminal=echo_to_terminal)


def process_message(
    state: JarvisState,
    user_input: str,
    *,
    echo_to_terminal: bool = True,
) -> dict[str, Any]:
    """
    Full synchronous turn: prepare -> LLM -> finalize.
    Returns metadata including response and timing.
    """
    start_time = time.time()

    turn = prepare_turn(state, user_input)
    if turn is None:
        return {
            "response": (
                "I'm not entirely sure what you're aiming for there. "
                "Clarify, or should I take an educated guess?"
            ),
            "intent": "uncertain",
            "skipped": True,
            "response_time_s": round(time.time() - start_time, 2),
        }

    raw_response = chat(**_llm_kwargs(state, turn), echo_to_terminal=echo_to_terminal)
    response = finalize_response(state, turn, raw_response)

    elapsed = round(time.time() - start_time, 2)
    return {
        "response": response,
        "intent": turn.intent,
        "emotion": turn.emotion,
        "intensity": turn.intensity,
        "skipped": False,
        "response_time_s": elapsed,
    }
