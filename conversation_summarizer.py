from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def summarize_recent(conversation):

    if len(conversation) < 15:
        return None

    recent = conversation[-15:]

    messages = [
        {
            "role": "system",
            "content": (
                "Summarize the recent conversation period "
                "in 2-3 concise sentences. "
                "Focus on emotional themes, "
                "important concerns, changes in mindset, "
                "and meaningful developments."
            )
        }
    ] + recent

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4
    )

    return response.choices[0].message.content