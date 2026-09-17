from context_builder import (
    build_context,
    format_memory,
    select_relevant_memory,
)


def test_select_relevant_memory_ignores_profile_history():
    profile = {
        "history": [
            {
                "emotion": "anxiety",
                "intensity": 0.9,
                "content": "big exam tomorrow",
            }
        ]
    }
    conversation = [{"role": "user", "content": "hello"}]

    memory = select_relevant_memory(profile, conversation)

    assert all(item["type"] == "recent_message" for item in memory)
    assert not any(item["type"] == "emotional_memory" for item in memory)


def test_select_relevant_memory_caps_at_five_items():
    conversation = [{"role": "user", "content": f"msg-{i}"} for i in range(10)]

    memory = select_relevant_memory({}, conversation)

    assert len(memory) == 3
    assert memory[0]["content"]["content"] == "msg-7"
    assert memory[-1]["content"]["content"] == "msg-9"


def test_format_memory_renders_recent_messages_only():
    memory = [
        {"type": "recent_message", "content": {"content": "first"}},
        {"type": "recent_message", "content": {"content": "second"}},
    ]

    assert format_memory(memory) == "Recent: first\nRecent: second"


def test_build_context_smoke():
    profile = {"name": "Ada"}
    emotional_profile = {
        "state": {"current": "calm", "intensity": 0.2},
        "baseline": "neutral",
    }
    patterns = {"repeated_stress": False}
    conversation = [{"role": "user", "content": "hi"}]

    context = build_context(profile, emotional_profile, patterns, conversation)

    assert set(context.keys()) == {
        "user_state",
        "relevant_memory",
        "patterns",
        "conversation_context",
    }
    assert context["user_state"]["current_emotion"] == "calm"
    assert not any(
        item.get("type") == "emotional_memory" for item in context["relevant_memory"]
    )
