def build_context(profile, emotional_profile, patterns, conversation):
    context = {}

    context["user_state"] = extract_user_state(emotional_profile)
    context["relevant_memory"] = select_relevant_memory(profile, conversation)
    context["patterns"] = patterns
    context["conversation_context"] = build_conversation_context(conversation)

    return context


# -------------------------
# USER STATE
# -------------------------
def extract_user_state(emotional_profile):

    state = emotional_profile.get("state", {})

    return {
        "current_emotion": state.get("current", "neutral"),
        "intensity": state.get("intensity", 0.0),
        "trend": emotional_profile.get("baseline", "neutral")
    }


# -------------------------
# MEMORY SELECTION
# -------------------------
def select_relevant_memory(profile, conversation):
    memory = []

    # recent conversation (structured)
    for msg in conversation[-3:]:
        memory.append({
            "type": "recent_message",
            "content": msg
        })

    # emotionally important past memories
    for entry in profile.get("history", []):
        if entry.get("intensity", 0) > 0.7:
            memory.append({
                "type": "emotional_memory",
                "content": entry
            })

    return memory[-5:]


# -------------------------
# CONVERSATION CONTEXT
# -------------------------
def build_conversation_context(conversation):
    return {
        "recent_messages": conversation[-4:],
        "summary": summarize_conversation(conversation),
    }


def summarize_conversation(conversation):
    if not conversation:
        return ""

    last_messages = conversation[-3:]
    return " | ".join([msg.get("content", "") for msg in last_messages])


# -------------------------
# FORMATTING FOR LLM
# -------------------------
def format_context_for_llm(context):
    return f"""
User Emotional State:
- Emotion: {context['user_state']['current_emotion']}
- Intensity: {context['user_state']['intensity']}
- Trend: {context['user_state']['trend']}

Patterns:
{format_patterns(context['patterns'])}

Relevant Memory:
{format_memory(context['relevant_memory'])}

Recent Conversation:
{context['conversation_context']['summary']}
"""


def format_memory(memory):
    lines = []

    for item in memory:
        if item["type"] == "recent_message":
            lines.append(f"Recent: {item['content'].get('content', '')}")

        elif item["type"] == "emotional_memory":
            lines.append(
                f"Past ({item['content'].get('emotion')}): "
                f"{item['content'].get('content', '')}"
            )

    return "\n".join(lines)


def format_patterns(patterns):
    return "\n".join([f"- {key}: {value}" for key, value in patterns.items()])