"""Assemble per-user personality layers for the system prompt."""

from __future__ import annotations

from typing import Any

from companion_prefs import CompanionPreferences, MAX_CUSTOM_NOTES_LEN
from personality_composer import EffectivePersonality
from prompts.core import NOVA_CORE

def _slider_instructions(sliders: dict[str, float]) -> str:
    support = sliders.get("emotional_support_level", sliders.get("emotional_support", 0.5))
    lines = [
        "USER STYLE PREFERENCES (0.0 = low, 1.0 = high — follow closely):",
        f"- Directness: {sliders.get('directness', 0.6):.2f}",
        f"- Warmth: {sliders.get('warmth', 0.55):.2f}",
        f"- Humor: {sliders.get('humor', 0.35):.2f}",
        f"- Verbosity: {sliders.get('verbosity', 0.5):.2f}",
        f"- Accountability: {sliders.get('accountability', 0.5):.2f}",
        f"- Emotional support level: {support:.2f}",
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


def _format_effective_personality(
    effective: EffectivePersonality,
    prefs: CompanionPreferences | None = None,
) -> str:
    sliders = effective.final_sliders
    parts = [
        NOVA_CORE,
        "NOVA IDENTITY:\n- NOVA remains one consistent assistant; never imply a companion role switch.",
        "USER BASELINE STYLE:\n"
        f"- Directness: {sliders.get('directness', 0.6):.2f}\n"
        f"- Warmth: {sliders.get('warmth', 0.55):.2f}\n"
        f"- Humor: {sliders.get('humor', 0.35):.2f}\n"
        f"- Verbosity: {sliders.get('verbosity', 0.5):.2f}\n"
        f"- Accountability: {sliders.get('accountability', 0.5):.2f}\n"
        f"- Emotional support: {sliders.get('emotional_support', 0.5):.2f}",
    ]

    learned_directives = [
        directive
        for modifier in effective.learned_modifiers
        for directive in modifier.get("directives", [])
    ]
    if learned_directives:
        parts.append(
            "LEARNED USER PREFERENCES (durable — apply subtly):\n"
            + "\n".join(f"- {directive}" for directive in learned_directives[:5])
        )

    runtime_directives = [
        directive
        for modifier in effective.runtime_modifiers
        for directive in modifier.directives
    ]
    if runtime_directives:
        parts.append(
            "CURRENT CONTEXT ADAPTATION (temporary — do not treat as identity):\n"
            + "\n".join(f"- {directive}" for directive in runtime_directives[:5])
        )

    if effective.directives:
        parts.append(
            "STYLE DIRECTIVES:\n"
            + "\n".join(f"- {directive}" for directive in effective.directives[:8])
        )

    custom_notes = getattr(prefs, "custom_notes", "") if prefs is not None else ""
    if custom_notes.strip():
        note = custom_notes.strip()[:MAX_CUSTOM_NOTES_LEN]
        parts.append("USER CUSTOM NOTES (follow unless unsafe):\n" + note)

    parts.append(
        "STYLE BOUNDARIES:\n"
        "- Do not mention modes, layers, scores, or internal adaptation unless asked.\n"
        "- Adapt delivery without changing who NOVA is."
    )
    return "\n\n".join(p for p in parts if p)


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
    prefs: CompanionPreferences | None = None,
    learned_snippets: list[dict[str, Any]] | None = None,
    runtime_personality: dict[str, float] | None = None,
    effective_personality: EffectivePersonality | None = None,
) -> str:
    if effective_personality is not None:
        return _format_effective_personality(effective_personality, prefs)

    if prefs is None:
        parts = [
            NOVA_CORE,
            "NOVA IDENTITY:\n- NOVA remains one consistent assistant; adapt delivery, not identity.",
        ]
        return "\n\n".join(p for p in parts if p)

    sliders = prefs.sliders.to_dict()

    parts = [
        NOVA_CORE,
        "NOVA IDENTITY:\n- NOVA remains one consistent assistant; adapt delivery, not identity.",
    ]

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
