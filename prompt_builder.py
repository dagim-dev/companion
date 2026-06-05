"""Assemble per-user personality layers for the system prompt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from companion_prefs import CompanionPreferences, MAX_CUSTOM_NOTES_LEN
from prompts.core import JARVIS_CORE

_ROLES_DIR = Path(__file__).resolve().parent / "prompts" / "roles"  # companion/prompts/roles
_role_cache: dict[str, dict[str, Any]] = {}


def _load_role_template(role_id: str) -> dict[str, Any]:
    if role_id in _role_cache:
        return _role_cache[role_id]

    path = _ROLES_DIR / f"{role_id}.yaml"
    if not path.exists():
        path = _ROLES_DIR / "general_jarvis.yaml"
        role_id = "general_jarvis"

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    _role_cache[role_id] = data
    return data


def _slider_instructions(sliders: dict[str, float]) -> str:
    lines = [
        "USER STYLE PREFERENCES (0.0 = low, 1.0 = high — follow closely):",
        f"- Directness: {sliders.get('directness', 0.6):.2f}",
        f"- Warmth: {sliders.get('warmth', 0.55):.2f}",
        f"- Humor: {sliders.get('humor', 0.35):.2f}",
        f"- Verbosity: {sliders.get('verbosity', 0.5):.2f}",
        f"- Accountability: {sliders.get('accountability', 0.5):.2f}",
        f"- Emotional support level: {sliders.get('emotional_support_level', 0.5):.2f}",
    ]
    d = sliders.get("directness", 0.6)
    h = sliders.get("humor", 0.35)
    v = sliders.get("verbosity", 0.5)
    if d >= 0.75:
        lines.append("- Be blunt but respectful; skip filler.")
    if h <= 0.2:
        lines.append("- Avoid sarcasm and teasing.")
    if v <= 0.35:
        lines.append("- Keep responses short unless asked for detail.")
    if sliders.get("accountability", 0.5) >= 0.75:
        lines.append("- Hold the user accountable to stated goals when relevant.")
    return "\n".join(lines)


def _format_learned_preferences(memories: list[dict[str, Any]], max_items: int = 5) -> str:
    if not memories:
        return ""

    lines = ["LEARNED PREFERENCES (from past interactions — apply subtly):"]
    for m in memories[:max_items]:
        cat = m.get("category", "")
        val = m.get("value", "")
        if val:
            lines.append(f"- [{cat}] {val}")
    return "\n".join(lines)


def build_personality_layer(
    prefs: CompanionPreferences | None,
    learned_snippets: list[dict[str, Any]] | None = None,
    runtime_personality: dict[str, float] | None = None,
) -> str:
    if prefs is None:
        prefs_data = _load_role_template("general_jarvis")
        parts = [
            JARVIS_CORE,
            f"COMPANION ROLE: {prefs_data.get('title', 'General JARVIS')}",
            prefs_data.get("stance", "").strip(),
        ]
        return "\n\n".join(p for p in parts if p)

    role = _load_role_template(prefs.role_id)
    sliders = prefs.sliders.to_dict()

    parts = [
        JARVIS_CORE,
        f"COMPANION ROLE: {role.get('title', prefs.role_id)}",
        (role.get("stance") or "").strip(),
    ]

    emphasis = role.get("emphasis") or []
    if emphasis:
        parts.append("ROLE EMPHASIS:\n" + "\n".join(f"- {e}" for e in emphasis))

    parts.append(_slider_instructions(sliders))

    if prefs.custom_notes.strip():
        note = prefs.custom_notes.strip()[:MAX_CUSTOM_NOTES_LEN]
        parts.append(
            "USER CUSTOM NOTES (follow unless unsafe):\n" + note
        )

    learned = _format_learned_preferences(learned_snippets or [])
    if learned:
        parts.append(learned)

    if runtime_personality:
        parts.append(
            "RUNTIME ADAPTATION (session-evolved — interpret internally):\n"
            f"- Formality: {runtime_personality.get('formality', 0.75)}\n"
            f"- Warmth: {runtime_personality.get('warmth', 0.55)}\n"
            f"- Humor: {runtime_personality.get('humor', 0.35)}\n"
            f"- Initiative: {runtime_personality.get('initiative', 0.4)}\n"
            f"- Relationship depth: {runtime_personality.get('relationship_depth', 0.3)}"
        )

    return "\n\n".join(p for p in parts if p)
