import json
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)

Approach = Literal[
    "validate_first",
    "listen_first",
    "grounding",
    "solution_focus",
    "lighten",
    "stay_brief",
]
ToneOverride = Literal["warmer", "grounded", "clear", "thoughtful", "none"]
Source = Literal["rules", "llm"]

ALLOWED_APPROACHES = {
    "validate_first",
    "listen_first",
    "grounding",
    "solution_focus",
    "lighten",
    "stay_brief",
}
ALLOWED_TONE_OVERRIDES = {"warmer", "grounded", "clear", "thoughtful", "none"}


@dataclass(frozen=True)
class CognitionResult:
    approach: Approach
    priorities: list[str]
    risks: list[str]
    ask_question: bool
    tone_override: ToneOverride
    response_goal: str
    memory_to_surface: str | None
    emotional_signal: str | None
    source: Source


def _default_cognition(source: Source = "rules") -> CognitionResult:
    return CognitionResult(
        approach="stay_brief",
        priorities=[],
        risks=[],
        ask_question=True,
        tone_override="none",
        response_goal="maintain composed flow",
        memory_to_surface=None,
        emotional_signal=None,
        source=source,
    )


def _short_strings(value, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        if len(result) >= limit:
            break
    return result


def _nullable_string(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_cognition_response(content) -> CognitionResult:
    raw = (content or "").strip()
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return _default_cognition()

    if not isinstance(data, dict):
        return _default_cognition()

    defaults = _default_cognition(source="llm")
    approach = data.get("approach", defaults.approach)
    if approach not in ALLOWED_APPROACHES:
        approach = defaults.approach

    tone_override = data.get("tone_override", defaults.tone_override)
    if tone_override not in ALLOWED_TONE_OVERRIDES:
        tone_override = defaults.tone_override

    response_goal = data.get("response_goal", defaults.response_goal)
    if not isinstance(response_goal, str) or not response_goal.strip():
        response_goal = defaults.response_goal

    ask_question = data.get("ask_question", defaults.ask_question)
    if not isinstance(ask_question, bool):
        ask_question = defaults.ask_question

    return CognitionResult(
        approach=approach,
        priorities=_short_strings(data.get("priorities")),
        risks=_short_strings(data.get("risks")),
        ask_question=ask_question,
        tone_override=tone_override,
        response_goal=response_goal.strip(),
        memory_to_surface=_nullable_string(data.get("memory_to_surface")),
        emotional_signal=_nullable_string(data.get("emotional_signal")),
        source="llm",
    )


def _compact_style_memories(style_memories: list | None) -> list:
    memories = style_memories or []
    interaction = [
        memory for memory in memories
        if isinstance(memory, dict) and memory.get("category") == "interaction_style"
    ]
    preferences = [
        memory for memory in memories
        if isinstance(memory, dict) and memory.get("category") == "preference"
    ][:3]
    other = [
        memory for memory in memories
        if not isinstance(memory, dict)
        or memory.get("category") not in ("interaction_style", "preference")
    ][:3]
    return interaction + preferences + other


def build_cognition_snapshot(
    *,
    user_input: str,
    conversation: list,
    emotion: str,
    intensity: float,
    intent: str,
    intent_confidence: float,
    emotion_confidence: float,
    sentiment: dict,
    patterns: dict,
    style_memories: list | None,
) -> dict:
    return {
        "latest_user_message": user_input,
        "recent_conversation": conversation[-6:],
        "emotion": emotion,
        "intent": intent,
        "intensity": intensity,
        "intent_confidence": intent_confidence,
        "emotion_confidence": emotion_confidence,
        "sentiment": sentiment,
        "style_memories": _compact_style_memories(style_memories),
        "patterns": {
            "repeated_stress": patterns.get("repeated_stress", False),
            "high_intensity": patterns.get("high_intensity", False),
            "dominant_emotion": patterns.get("dominant_emotion"),
        },
    }


def generate_cognition_rules(
    *,
    user_input: str,
    conversation: list,
    emotion: str,
    intensity: float,
    intent: str,
    patterns: dict,
    style_memories: list | None = None,
) -> CognitionResult:
    priorities: list[str] = []
    risks: list[str] = []
    approach: Approach = "stay_brief"
    response_goal = "maintain composed flow"

    if emotion in ("stress", "anxiety"):
        approach = "grounding"
        priorities.append("user may need grounding")
        response_goal = "steady the user without overexplaining"

    if intent == "reflection" and approach != "grounding":
        approach = "validate_first"
        priorities.append("user is introspective")
        response_goal = "make user feel heard"
    elif intent == "reflection":
        priorities.append("user is introspective")

    if patterns.get("repeated_stress"):
        risks.append("stress patterns recurring")

    if patterns.get("high_intensity"):
        priorities.append("emotional intensity elevated")

    if len(conversation) > 10:
        priorities.append("maintain long-term continuity")

    if not priorities:
        priorities.append("maintain composed flow")

    ask_question = not (
        approach in ("validate_first", "grounding") and intensity > 0.7
    )

    return CognitionResult(
        approach=approach,
        priorities=priorities,
        risks=risks,
        ask_question=ask_question,
        tone_override="none",
        response_goal=response_goal,
        memory_to_surface=None,
        emotional_signal=None,
        source="rules",
    )


def should_use_llm_cognition(
    *,
    intent: str,
    emotion: str,
    intent_confidence: float,
    emotion_confidence: float,
    sentiment: dict,
    patterns: dict,
    conversation: list,
) -> bool:
    mixed_casual = (
        intent == "casual_talk"
        and sentiment.get("compound", 0.0) < -0.25
    )
    emotional_mismatch = (
        emotion in ("anxiety", "stress", "sad", "negative")
        and intent in ("casual_talk", "technical_problem")
    )

    if intent_confidence < 0.65 or emotion_confidence < 0.45:
        return True
    if mixed_casual or emotional_mismatch:
        return True
    if patterns.get("repeated_stress"):
        return True
    if intent in ("reflection", "anxiety_stress", "help_request"):
        return True
    if len(conversation) > 10:
        return True
    return False


COGNITION_SYSTEM_PROMPT = """You are the companion's private cognition layer. Given a compact turn snapshot, return ONLY JSON matching this schema:
{
  "approach": "<validate_first|listen_first|grounding|solution_focus|lighten|stay_brief>",
  "priorities": ["..."],
  "risks": ["..."],
  "ask_question": true|false,
  "tone_override": "<warmer|grounded|clear|thoughtful|none>",
  "response_goal": "<short phrase>",
  "memory_to_surface": "<optional string or null>",
  "emotional_signal": "<optional string or null>"
}
Rules:
- priorities/risks: 1-3 short imperative phrases each
- Detect nuance rules miss: deflection, mixed tone, closing vs opening emotionally
- memory_to_surface: only if a recalled style/preference memory or recent turn clearly matters this reply; else null
- ask_question: false when user needs space, validation, or a direct answer more than a question
- tone_override "none" when default behavior is fine
- Do not produce the user-facing reply"""


def generate_cognition_llm(snapshot: dict) -> CognitionResult | None:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COGNITION_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(snapshot)},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=8,
        )
    except Exception:
        return None

    result = parse_cognition_response(response.choices[0].message.content)
    if result.source != "llm":
        return None
    return result


def generate_cognition(
    *,
    user_input: str,
    conversation: list,
    emotion: str,
    intensity: float,
    intent: str,
    intent_confidence: float,
    emotion_confidence: float,
    sentiment: dict,
    patterns: dict,
    style_memories: list | None,
) -> CognitionResult:
    rules_result = generate_cognition_rules(
        user_input=user_input,
        conversation=conversation,
        emotion=emotion,
        intensity=intensity,
        intent=intent,
        patterns=patterns,
        style_memories=style_memories,
    )

    if not should_use_llm_cognition(
        intent=intent,
        emotion=emotion,
        intent_confidence=intent_confidence,
        emotion_confidence=emotion_confidence,
        sentiment=sentiment,
        patterns=patterns,
        conversation=conversation,
    ):
        return rules_result

    snapshot = build_cognition_snapshot(
        user_input=user_input,
        conversation=conversation,
        emotion=emotion,
        intensity=intensity,
        intent=intent,
        intent_confidence=intent_confidence,
        emotion_confidence=emotion_confidence,
        sentiment=sentiment,
        patterns=patterns,
        style_memories=style_memories,
    )
    return generate_cognition_llm(snapshot) or rules_result
