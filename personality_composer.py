from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from companion_prefs import SliderPrefs


@dataclass(frozen=True)
class RuntimeModifier:
    key: str
    deltas: dict[str, float]
    directives: list[str]
    reason: str
    ttl_turns: int = 1


@dataclass(frozen=True)
class EffectivePersonality:
    identity: str
    baseline_sliders: dict[str, float]
    learned_modifiers: list[dict[str, Any]]
    runtime_modifiers: list[RuntimeModifier]
    final_sliders: dict[str, float]
    directives: list[str] = field(default_factory=list)
    audit_reasons: list[str] = field(default_factory=list)


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _canonical_sliders(sliders: SliderPrefs | dict[str, float] | None) -> dict[str, float]:
    if sliders is None:
        data = SliderPrefs().to_dict()
    elif isinstance(sliders, SliderPrefs):
        data = sliders.to_dict()
    else:
        data = SliderPrefs.from_dict(sliders).to_dict()
    data["emotional_support"] = data.get(
        "emotional_support",
        data.get("emotional_support_level", 0.5),
    )
    return {
        "directness": data.get("directness", 0.6),
        "warmth": data.get("warmth", 0.55),
        "humor": data.get("humor", 0.35),
        "verbosity": data.get("verbosity", 0.5),
        "accountability": data.get("accountability", 0.5),
        "emotional_support": data.get("emotional_support", 0.5),
    }


def _apply_delta(sliders: dict[str, float], key: str, delta: float) -> None:
    if key == "emotional_support_level":
        key = "emotional_support"
    if key not in sliders:
        return
    sliders[key] = _clamp(sliders[key] + delta)


def _learned_delta(preference: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    key = preference.get("preference_key")
    value = preference.get("value") or {}
    target = value.get("target")
    confidence = float(preference.get("confidence", 0.75))
    strength = min(0.18, max(0.08, (confidence - 0.7) * 0.7))

    if key == "response.length" and target == "concise":
        return {"verbosity": -strength}, ["prefer concise responses"]
    if key == "response.length" and target == "detailed":
        return {"verbosity": strength}, ["allow detailed responses when useful"]
    if key == "response.examples" and target in ("examples", "often"):
        return {}, ["include examples when they clarify the answer"]
    if key == "response.examples" and target == "few":
        return {}, ["avoid examples unless asked"]
    if key == "response.simplicity":
        return {"directness": 0.05, "verbosity": -0.08}, ["explain in simple terms"]
    if key == "response.directness" and target == "gentle":
        return {"directness": -strength, "warmth": strength}, ["use a gentler delivery"]
    if key == "response.directness" and target == "direct":
        return {"directness": strength}, ["use direct wording"]
    if key == "response.challenge_level" and target == "high":
        return {"accountability": strength, "directness": strength * 0.5}, ["challenge assumptions when relevant"]
    if key == "response.challenge_level" and target == "low":
        return {"accountability": -strength, "directness": -strength * 0.5}, ["keep challenge level light"]
    if key == "response.emotional_support" and target == "high":
        return {"emotional_support": strength, "warmth": strength * 0.75}, ["offer more emotional support"]
    if key == "response.emotional_support" and target == "low":
        return {"emotional_support": -strength}, ["keep emotional support light unless context requires it"]
    if key == "response.accountability" and target == "firm":
        return {"accountability": strength}, ["hold the user accountable to stated goals"]
    if key == "response.accountability" and target == "light":
        return {"accountability": -strength}, ["use light accountability nudges"]
    return {}, []


def runtime_modifiers_for_turn(
    *,
    emotion: str,
    intent: str,
    intensity: float,
    patterns: dict[str, Any] | None = None,
) -> list[RuntimeModifier]:
    patterns = patterns or {}
    modifiers: list[RuntimeModifier] = []
    high_distress = (
        emotion in {"sad", "stress", "anxiety", "negative"}
        and intensity >= 0.75
    ) or bool(patterns.get("high_intensity"))
    if high_distress:
        modifiers.append(
            RuntimeModifier(
                key="distress_support",
                deltas={
                    "warmth": 0.28,
                    "emotional_support": 0.35,
                    "accountability": -0.25,
                    "directness": -0.10,
                    "humor": -0.20,
                },
                directives=[
                    "validate first",
                    "avoid hard accountability pressure this turn",
                    "keep humor restrained",
                ],
                reason=f"emotion={emotion} intent={intent} intensity={intensity:.2f}",
                ttl_turns=3,
            )
        )
    elif emotion in {"stress", "anxiety"}:
        modifiers.append(
            RuntimeModifier(
                key="steady_support",
                deltas={"warmth": 0.12, "emotional_support": 0.15, "humor": -0.08},
                directives=["stay grounded and concise"],
                reason=f"emotion={emotion} intensity={intensity:.2f}",
                ttl_turns=1,
            )
        )
    return modifiers


def compose_effective_personality(
    *,
    companion_prefs,
    learned_preferences: list[dict[str, Any]] | None,
    runtime_modifiers: list[RuntimeModifier] | None,
) -> EffectivePersonality:
    baseline = _canonical_sliders(getattr(companion_prefs, "sliders", None))
    final = dict(baseline)
    directives: list[str] = []
    audit_reasons: list[str] = ["baseline:companion_preferences"]

    baseline_directives = getattr(companion_prefs, "baseline_directives", {}) or {}
    for key, value in baseline_directives.items():
        directives.append(f"{key}={value}")

    learned_modifiers: list[dict[str, Any]] = []
    for preference in learned_preferences or []:
        deltas, preference_directives = _learned_delta(preference)
        for key, delta in deltas.items():
            _apply_delta(final, key, delta)
        directives.extend(preference_directives)
        learned_modifiers.append(
            {
                "id": preference.get("id"),
                "preference_key": preference.get("preference_key"),
                "deltas": deltas,
                "directives": preference_directives,
            }
        )
        audit_reasons.append(
            f"learned:{preference.get('preference_key')}:{preference.get('confidence')}"
        )

    for modifier in runtime_modifiers or []:
        for key, delta in modifier.deltas.items():
            _apply_delta(final, key, delta)
        directives.extend(modifier.directives)
        audit_reasons.append(f"runtime:{modifier.key}:{modifier.reason}")

    return EffectivePersonality(
        identity="nova",
        baseline_sliders=baseline,
        learned_modifiers=learned_modifiers,
        runtime_modifiers=list(runtime_modifiers or []),
        final_sliders=final,
        directives=list(dict.fromkeys(directives)),
        audit_reasons=audit_reasons,
    )
