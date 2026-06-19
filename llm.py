# llm.py
import traceback
from typing import Iterator

from openai import OpenAI
from config import OPENAI_API_KEY
from cognition_engine import CognitionResult
from companion_prefs import CompanionPreferences
from prompt_builder import build_personality_layer

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=60.0,
)


def build_system_message(
    profile,
    personal_memories,
    emotional_profile,
    intent,
    behavior,
    patterns,
    context,
    insights,
    cognition: CognitionResult,
    internal_state,
    meta_cognition,
    personality_state,
    self_perception,
    companion_prefs: CompanionPreferences | None = None,
    learned_preference_memories: list | None = None,
    effective_personality=None,
):
    personality_layer = build_personality_layer(
        companion_prefs,
        learned_snippets=learned_preference_memories,
        runtime_personality=personality_state,
        effective_personality=effective_personality,
    )

    personal_from_context = context.get("personal_memories", personal_memories)

    return f"""
{personality_layer}

USER PROFILE:
{profile}

EMOTIONAL STATE:
- Current: {emotional_profile["state"]["current"]}
- Intensity: {emotional_profile["state"]["intensity"]}
- Baseline: {emotional_profile["baseline"]}

CURRENT MODE:
{intent}

BEHAVIOR SETTINGS:
- Tone: {behavior["tone"]}
- Verbosity: {behavior["verbosity"]}
- Style: {behavior["style"]}

COPING STRATEGY:
- Strategy: {behavior["coping"]}

If coping = "breathing":
- Guide the user through a very short breathing step (1–2 sentences max)

If coping = "grounding":
- Suggest a simple grounding action (e.g., focus on surroundings)

If coping is None:
- Do not force coping techniques

INSTRUCTIONS:
- Follow BEHAVIOR SETTINGS strictly
- Adapt response length to verbosity
- Match emotional state appropriately

MEMORY AWARENESS:
- If the user shows repeated anxiety or stress in recent history,
  acknowledge it subtly and naturally
- Do NOT overemphasize it
- Do not mention the mode explicitly
- Relevant memories are ranked by emotional significance and recurrence
- Only reference memories if they naturally fit the conversation

PATTERN AWARENESS:
- Repeated Stress: {patterns["repeated_stress"]}
- High Intensity: {patterns["high_intensity"]}
- Dominant Emotion: {patterns["dominant_emotion"]}

If repeated stress is true:
- Occasionally acknowledge recurring stress naturally
- Do NOT imply a long-term pattern unless clearly supported

If high intensity is true:
- Be more careful, grounding, and steady in tone

CONTEXT SUMMARY:
{context}

RELEVANT PERSONAL MEMORIES (this turn):
{personal_from_context}

REFLECTION CHECK-IN:
{context.get("reflection_checkin", "None")}

IMPORTANT CONTINUITY MEMORIES:
{context.get("relevant_reflections", [])}

Use memories subtly. Avoid robotic memory dumps.

USER INSIGHTS:
{insights}

INTERNAL STATE:
{internal_state}

META-COGNITIVE STATE:
- Response Confidence: {meta_cognition["response_confidence"]}
- User Stability: {meta_cognition["user_stability"]}
- Conversation Quality: {meta_cognition["conversation_quality"]}

SELF PERCEPTION:
{self_perception}

Interpret meta-cognitive and self-perception signals internally.
Do not quote internal thoughts directly.

COGNITION (private — use silently, never quote):
- Approach: {cognition.approach}
- Priorities: {cognition.priorities}
- Risks: {cognition.risks}
- Response goal: {cognition.response_goal}
- Emotional signal: {cognition.emotional_signal or "none"}
- Memory to surface: {cognition.memory_to_surface or "none"}
"""


def build_chat_messages(
    conversation,
    profile,
    personal_memories,
    emotional_profile,
    intent,
    behavior,
    patterns,
    context,
    insights,
    cognition,
    internal_state,
    meta_cognition,
    personality_state,
    self_perception,
    companion_prefs=None,
    learned_preference_memories=None,
    effective_personality=None,
):
    system_message = build_system_message(
        profile,
        personal_memories,
        emotional_profile,
        intent,
        behavior,
        patterns,
        context,
        insights,
        cognition,
        internal_state,
        meta_cognition,
        personality_state,
        self_perception,
        companion_prefs=companion_prefs,
        learned_preference_memories=learned_preference_memories,
        effective_personality=effective_personality,
    )
    recent_conversation = _compress_conversation_for_llm(conversation, max_recent=6)
    return [{"role": "system", "content": system_message}] + recent_conversation


def _compress_conversation_for_llm(
    conversation: list,
    max_recent: int = 6,
) -> list:
    """Keep recent turns verbatim; summarize older turns into one compact message."""
    if len(conversation) <= max_recent:
        return conversation[-max_recent:]

    older = conversation[:-max_recent]
    snippets = [
        f"{m.get('role', 'unknown')}: {str(m.get('content', ''))[:100]}"
        for m in older[-8:]
    ]
    summary = " | ".join(snippets)
    compressed_prefix = {
        "role": "user",
        "content": (
            "[Earlier conversation — use for continuity only, do not quote verbatim: "
            f"{summary}]"
        ),
    }
    return [compressed_prefix] + conversation[-max_recent:]


FALLBACK_RESPONSE = (
    "Apologies. "
    "The connection to my higher cognitive functions "
    "appears temporarily unstable."
)


def chat_stream(
    conversation,
    profile,
    personal_memories,
    emotional_profile,
    intent,
    behavior,
    patterns,
    context,
    insights,
    cognition,
    internal_state,
    meta_cognition,
    personality_state,
    self_perception,
    *,
    companion_prefs=None,
    learned_preference_memories=None,
    effective_personality=None,
    echo_to_terminal: bool = False,
) -> Iterator[str]:
    messages = build_chat_messages(
        conversation,
        profile,
        personal_memories,
        emotional_profile,
        intent,
        behavior,
        patterns,
        context,
        insights,
        cognition,
        internal_state,
        meta_cognition,
        personality_state,
        self_perception,
        companion_prefs=companion_prefs,
        learned_preference_memories=learned_preference_memories,
        effective_personality=effective_personality,
    )

    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                if echo_to_terminal:
                    print(delta, end="", flush=True)
                yield delta

        if echo_to_terminal:
            print()

    except Exception:
        print("[LLM ERROR]")
        traceback.print_exc()
        yield FALLBACK_RESPONSE


def chat(
    conversation,
    profile,
    personal_memories,
    emotional_profile,
    intent,
    behavior,
    patterns,
    context,
    insights,
    cognition,
    internal_state,
    meta_cognition,
    personality_state,
    self_perception,
    *,
    companion_prefs=None,
    learned_preference_memories=None,
    effective_personality=None,
    echo_to_terminal: bool = True,
):
    full_response = ""
    for delta in chat_stream(
        conversation,
        profile,
        personal_memories,
        emotional_profile,
        intent,
        behavior,
        patterns,
        context,
        insights,
        cognition,
        internal_state,
        meta_cognition,
        personality_state,
        self_perception,
        companion_prefs=companion_prefs,
        learned_preference_memories=learned_preference_memories,
        effective_personality=effective_personality,
        echo_to_terminal=echo_to_terminal,
    ):
        full_response += delta
    return full_response
