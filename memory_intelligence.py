import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from config import OPENAI_API_KEY

InsightType = Literal[
    "trait",
    "interest",
    "goal",
    "preference",
    "project",
    "skill",
    "constraint",
    "issue",
    "emotional_state",
]
Stability = Literal["temporary", "long_term"]

ALLOWED_TYPES = {
    "trait",
    "interest",
    "goal",
    "preference",
    "project",
    "skill",
    "constraint",
    "issue",
    "emotional_state",
}
ALLOWED_STABILITIES = {"temporary", "long_term"}
CONFIDENCE_THRESHOLD = 0.75
RECENT_CONTEXT_WINDOW = 6
EXTRACTION_MODEL = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)


class ExtractionFailure(Exception):
    """Raised when the LLM output cannot be trusted."""


@dataclass(frozen=True)
class ExtractedInsight:
    label: str
    type: InsightType
    confidence: float
    evidence: str
    source: str
    stability: Stability
    preference_key: str | None = None
    preference_value: dict[str, Any] | None = None
    scope: str = "global"
    context: dict[str, Any] | None = None
    evidence_polarity: str = "positive"


EXTRACTION_SYSTEM_PROMPT = """
You extract durable user insights for a multi-user assistant.
Return only JSON with this shape:
{
  "insights": [
    {
      "label": "short human-readable insight",
      "type": "trait|interest|goal|preference|project|skill|constraint|issue|emotional_state",
      "preference_key": "response.length|response.examples|response.simplicity|response.directness|response.challenge_level|response.emotional_support|response.accountability|null",
      "preference_value": {"target": "concise|detailed|examples|simple|direct|gentle|high|medium|low|firm|light"} or null,
      "scope": "global|domain|task",
      "context": {"domain": "coding"} or null,
      "evidence_polarity": "positive|negative|correction",
      "confidence": 0.0,
      "evidence": "exact user wording that supports the insight",
      "source": "latest_user_message",
      "stability": "temporary|long_term"
    }
  ]
}

Rules:
- Analyze only user messages.
- Use the latest user message as the primary source.
- Use recent user context only to disambiguate, not to invent insights.
- Extract only meaningful insights with clear evidence.
- Do not guess.
- For type=preference, include preference_key and preference_value when the user states a durable communication preference.
- Use response.length for concise/detailed preferences.
- Use response.examples for example preferences.
- Use response.simplicity for simple/plain-language preferences.
- Use response.directness for direct/gentle/blunt preferences.
- Use response.challenge_level for challenge/pushback preferences.
- Use response.emotional_support for support/reassurance preferences.
- Use response.accountability for accountability/nudge preferences.
- Mark emotions as emotional_state and temporary unless the user clearly states a durable issue.
- Do not turn temporary emotions into personality traits.
- Use broad categories that apply to many users.
- Return an empty insights array when nothing is worth saving.
""".strip()


def _user_context(recent_context: list[dict] | None) -> list[dict]:
    messages = recent_context or []
    return [
        {
            "role": "user",
            "content": str(message.get("content", "")),
        }
        for message in messages[-RECENT_CONTEXT_WINDOW:]
        if message.get("role") == "user" and str(message.get("content", "")).strip()
    ]


def _build_extraction_payload(
    latest_user_message: str,
    recent_context: list[dict] | None,
) -> str:
    payload = {
        "latest_user_message": latest_user_message,
        "recent_user_context": _user_context(recent_context),
    }
    return json.dumps(payload, ensure_ascii=False)


def _required_string(data: dict, field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExtractionFailure(f"Insight missing required field: {field}")
    return value.strip()


def _parse_confidence(value) -> float:
    if not isinstance(value, (int, float)):
        raise ExtractionFailure("Insight confidence must be numeric")
    confidence = float(value)
    if confidence < 0.0 or confidence > 1.0:
        raise ExtractionFailure("Insight confidence must be between 0 and 1")
    return confidence


def _parse_insight(data: dict) -> ExtractedInsight:
    label = _required_string(data, "label")
    insight_type = _required_string(data, "type")
    evidence = _required_string(data, "evidence")
    source = _required_string(data, "source")
    stability = _required_string(data, "stability")
    confidence = _parse_confidence(data.get("confidence"))

    if insight_type not in ALLOWED_TYPES:
        raise ExtractionFailure(f"Unsupported insight type: {insight_type}")
    if stability not in ALLOWED_STABILITIES:
        raise ExtractionFailure(f"Unsupported insight stability: {stability}")
    if source != "latest_user_message":
        raise ExtractionFailure("Insight source must be latest_user_message")

    preference_value = data.get("preference_value")
    if preference_value is not None and not isinstance(preference_value, dict):
        raise ExtractionFailure("preference_value must be an object when provided")
    context = data.get("context")
    if context is not None and not isinstance(context, dict):
        raise ExtractionFailure("context must be an object when provided")
    preference_key = data.get("preference_key")
    if preference_key is not None and not isinstance(preference_key, str):
        raise ExtractionFailure("preference_key must be a string when provided")
    scope = data.get("scope", "global")
    if not isinstance(scope, str) or not scope.strip():
        raise ExtractionFailure("scope must be a non-empty string")
    evidence_polarity = data.get("evidence_polarity", "positive")
    if evidence_polarity not in {"positive", "negative", "correction"}:
        raise ExtractionFailure("Unsupported evidence_polarity")

    return ExtractedInsight(
        label=label,
        type=insight_type,
        confidence=confidence,
        evidence=evidence,
        source=source,
        stability=stability,
        preference_key=preference_key.strip() if preference_key else None,
        preference_value=preference_value,
        scope=scope.strip(),
        context=context,
        evidence_polarity=evidence_polarity,
    )


def parse_insight_response(content) -> list[ExtractedInsight]:
    raw = (content or "").strip()
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExtractionFailure("LLM returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise ExtractionFailure("LLM response must be a JSON object")
    items = data.get("insights")
    if not isinstance(items, list):
        raise ExtractionFailure("LLM response must include an insights array")

    parsed = []
    for item in items:
        if not isinstance(item, dict):
            raise ExtractionFailure("Each insight must be a JSON object")
        insight = _parse_insight(item)
        if insight.confidence >= CONFIDENCE_THRESHOLD:
            parsed.append(insight)
    return parsed


def extract_insights_from_message(
    *,
    latest_user_message: str,
    recent_context: list[dict] | None = None,
    client: OpenAI | None = None,
) -> list[ExtractedInsight]:
    if not latest_user_message.strip():
        return []

    llm_client = client or globals()["client"]
    response = llm_client.chat.completions.create(
        model=EXTRACTION_MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_extraction_payload(
                    latest_user_message,
                    recent_context,
                ),
            },
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return parse_insight_response(response.choices[0].message.content)


def extract_user_insights(conversation, emotional_state=None):
    """Compatibility wrapper: expose structured user-only insights for prompts."""
    user_messages = [
        message
        for message in conversation
        if message.get("role") == "user" and message.get("content")
    ]
    if not user_messages:
        return []
    latest = user_messages[-1]["content"]
    recent = user_messages[:-1][-RECENT_CONTEXT_WINDOW:]
    return extract_insights_from_message(
        latest_user_message=latest,
        recent_context=recent,
    )