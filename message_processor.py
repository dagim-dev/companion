import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from classifier import classify_intent, detect_emotion
from context_builder import build_context
from conversation_manager import generate_followup
from conversation_summarizer import summarize_recent
from decision_engine import decide_behavior
from episodic_memory import create_episode
from initiative_engine import maybe_add_initiative
from llm import chat, chat_stream
from memory import (
    add_emotional_history,
    detect_emotional_patterns,
    get_emotional_profile,
    get_profile,
    set_emotional_state,
)
from memory_intelligence import extract_user_insights
from memory_recall import retrieve_relevant_personal_memories
from memory_retriever import retrieve_relevant_reflections
from personal_memory import extract_personal_memories, save_personal_memory
from reasoning_engine import generate_internal_reasoning
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
    internal_reasoning: str
    initiative_question: Optional[str]
    followup: Optional[str]


def prepare_turn(state: JarvisState, user_input: str) -> Optional[PreparedTurn]:
    """Run pre-LLM pipeline. Returns None if turn should be skipped (uncertain intent)."""
    decay_memories()
    consolidate_memories()

    state.conversation.append({"role": "user", "content": user_input})

    for memory_item in extract_personal_memories(user_input):
        save_personal_memory(memory_item)

    sentiment = state.analyzer.polarity_scores(user_input)
    emotion, intensity = detect_emotion(user_input, sentiment)
    intent = classify_intent(user_input)

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

    state.thought_engine.generate(intent, emotion, patterns)

    if intent in ("reflection", "anxiety_stress", "help_request"):
        relevant_reflections = retrieve_relevant_reflections(user_input)
    else:
        relevant_reflections = []

    context = build_context(profile, emotional_profile, patterns, state.conversation)
    personal_memories = retrieve_relevant_personal_memories(user_input)
    context["personal_memories"] = personal_memories
    context["relevant_reflections"] = relevant_reflections

    insights = extract_user_insights(
        state.conversation, emotional_profile["state"]
    )
    internal_reasoning = generate_internal_reasoning(
        state.conversation, emotion, intent
    )

    checkin = generate_checkin()
    if checkin:
        context["reflection_checkin"] = checkin

    behavior = decide_behavior(
        intent, emotional_profile, state.internal_state.snapshot()
    )

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
        internal_reasoning=internal_reasoning,
        initiative_question=initiative_question,
        followup=followup,
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
    _maybe_create_episode(state, turn)
    return response


def _maybe_create_episode(state: JarvisState, turn: PreparedTurn) -> None:
    if len(state.conversation) % 12 != 0:
        return
    summary = summarize_recent(state.conversation)
    if not summary:
        return
    importance = 0.5
    if turn.intensity > 0.7:
        importance += 0.3
    create_episode(summary=summary, emotion=turn.emotion, importance=importance)


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
        "internal_reasoning": turn.internal_reasoning,
        "internal_state": state.internal_state.snapshot(),
        "meta_cognition": state.meta_cognition.snapshot(),
        "personality_state": state.personality_state.snapshot(),
        "self_perception": state.self_perception.snapshot(),
        "thought_state": state.thought_engine.snapshot(),
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
