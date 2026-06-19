import json
from dataclasses import dataclass

from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


# Structured summary data keeps the LLM's open/closed judgment with the text.
@dataclass(frozen=True)
class EpisodeSummary:
    summary: str
    unresolved: bool


# Safe parsing prevents malformed model output from breaking episode creation.
def parse_episode_summary_response(content) -> EpisodeSummary:
    raw = (content or "").strip()
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return EpisodeSummary(summary=raw, unresolved=False)

    if not isinstance(data, dict):
        return EpisodeSummary(summary=raw, unresolved=False)

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = raw

    return EpisodeSummary(
        summary=summary.strip(),
        unresolved=data.get("unresolved") is True,
    )


def summarize_recent(conversation):

    if len(conversation) < 15:
        return None

    recent = conversation[-15:]

    messages = [
        {
            "role": "system",
            "content": (
                "Return only JSON with this shape: "
                '{"summary": "...", "unresolved": true|false}. '
                "The summary should cover the recent conversation period "
                "in 2-3 concise sentences, focusing on emotional themes, "
                "important concerns, changes in mindset, and meaningful "
                "developments. Set unresolved true only when the user is "
                "waiting on an external outcome, such as interview results, "
                "medical news, a decision, deadline, reply, or similar. "
                "Do not mark general goals or already-finished past events "
                "as unresolved."
            )
        }
    ] + recent

    # JSON mode keeps the existing single LLM call but makes parsing reliable.
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    # The caller now receives both the summary and the unresolved flag.
    return parse_episode_summary_response(response.choices[0].message.content)