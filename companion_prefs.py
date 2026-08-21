"""Per-user companion preferences: onboarding, sliders, runtime personality."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from memory import get_connection, set_profile
from memory_scope import require_user_id
from learned_preferences import clear_learned_preferences

TEMPLATE_VERSION = "2"
MAX_CUSTOM_NOTES_LEN = 300

VALID_ROLE_IDS = frozenset({
    "strategic_partner",
    "fitness_coach",
    "calm_companion",
    "creative_sparring",
    "productivity_operator",
    "general_nova",
})

VALID_COMMUNICATION = frozenset({"direct", "balanced", "gentle"})
VALID_ENERGY = frozenset({"calm", "upbeat"})
VALID_CHALLENGE_LEVEL = frozenset({"low", "medium", "high"})
VALID_EMOTIONAL_SUPPORT = frozenset({"low", "medium", "high"})
VALID_DETAIL_LEVEL = frozenset({"concise", "normal", "detailed"})
VALID_EXAMPLES_PREFERENCE = frozenset({"few", "when_useful", "often"})
VALID_ACCOUNTABILITY_STYLE = frozenset({"light", "steady", "firm"})


@dataclass
class SliderPrefs:
    directness: float = 0.6
    warmth: float = 0.55
    humor: float = 0.35
    verbosity: float = 0.5
    accountability: float = 0.5
    emotional_support_level: float = 0.5

    def clamp(self) -> None:
        for key in (
            "directness",
            "warmth",
            "humor",
            "verbosity",
            "accountability",
            "emotional_support_level",
        ):
            v = getattr(self, key)
            setattr(self, key, min(1.0, max(0.0, float(v))))

    def to_dict(self) -> dict[str, float]:
        self.clamp()
        data = asdict(self)
        data["emotional_support"] = data["emotional_support_level"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SliderPrefs:
        if not data:
            return cls()
        return cls(
            directness=float(data.get("directness", 0.6)),
            warmth=float(data.get("warmth", 0.55)),
            humor=float(data.get("humor", 0.35)),
            verbosity=float(data.get("verbosity", 0.5)),
            accountability=float(data.get("accountability", 0.5)),
            emotional_support_level=float(
                data.get("emotional_support_level", data.get("emotional_support", 0.5))
            ),
        )

    @property
    def emotional_support(self) -> float:
        return self.emotional_support_level


@dataclass
class BaselinePersonality:
    sliders: SliderPrefs
    directives: dict[str, str]


@dataclass
class CompanionPreferences:
    user_id: str
    role_id: str = "general_nova"
    communication: str = "balanced"
    energy: str = "calm"
    challenge_level: str = "medium"
    emotional_support: str = "medium"
    detail_level: str = "normal"
    examples_preference: str = "when_useful"
    accountability_style: str = "steady"
    sliders: SliderPrefs = field(default_factory=SliderPrefs)
    baseline_directives: dict[str, str] = field(default_factory=dict)
    preferences_version: int = 1
    custom_notes: str = ""
    template_version: str = TEMPLATE_VERSION
    runtime_json: dict[str, Any] | None = None
    onboarding_completed: bool = False
    updated_at: str = ""

    def prefs_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "baseline": {
                "communication_style": self.communication,
                "energy_level": self.energy,
                "challenge_level": self.challenge_level,
                "emotional_support": self.emotional_support,
                "detail_level": self.detail_level,
                "examples_preference": self.examples_preference,
                "accountability_style": self.accountability_style,
            },
            "baseline_sliders": self.sliders.to_dict(),
            "baseline_directives": dict(self.baseline_directives),
            "preferences_version": self.preferences_version,
            # Compatibility fields for old clients during the migration window.
            "communication": self.communication,
            "energy": self.energy,
            "sliders": self.sliders.to_dict(),
        }


def _adjust(value: float, delta: float) -> float:
    return min(1.0, max(0.0, value + delta))


def onboarding_answers_to_baseline(
    *,
    communication_style: str = "balanced",
    energy_level: str = "calm",
    challenge_level: str = "medium",
    emotional_support: str = "medium",
    detail_level: str = "normal",
    examples_preference: str = "when_useful",
    accountability_style: str = "steady",
) -> BaselinePersonality:
    """Map NOVA onboarding answers to stable baseline sliders and directives."""
    if communication_style not in VALID_COMMUNICATION:
        raise ValueError(f"Invalid communication: {communication_style}")
    if energy_level not in VALID_ENERGY:
        raise ValueError(f"Invalid energy: {energy_level}")
    if challenge_level not in VALID_CHALLENGE_LEVEL:
        raise ValueError(f"Invalid challenge_level: {challenge_level}")
    if emotional_support not in VALID_EMOTIONAL_SUPPORT:
        raise ValueError(f"Invalid emotional_support: {emotional_support}")
    if detail_level not in VALID_DETAIL_LEVEL:
        raise ValueError(f"Invalid detail_level: {detail_level}")
    if examples_preference not in VALID_EXAMPLES_PREFERENCE:
        raise ValueError(f"Invalid examples_preference: {examples_preference}")
    if accountability_style not in VALID_ACCOUNTABILITY_STYLE:
        raise ValueError(f"Invalid accountability_style: {accountability_style}")

    sliders = SliderPrefs()
    if communication_style == "direct":
        sliders.directness = _adjust(sliders.directness, 0.18)
        sliders.warmth = _adjust(sliders.warmth, -0.05)
        sliders.verbosity = _adjust(sliders.verbosity, -0.05)
    elif communication_style == "gentle":
        sliders.directness = _adjust(sliders.directness, -0.18)
        sliders.warmth = _adjust(sliders.warmth, 0.12)
        sliders.emotional_support_level = _adjust(sliders.emotional_support_level, 0.12)

    if energy_level == "upbeat":
        sliders.humor = _adjust(sliders.humor, 0.12)
        sliders.warmth = _adjust(sliders.warmth, 0.08)
    else:
        sliders.humor = _adjust(sliders.humor, -0.05)

    if challenge_level == "high":
        sliders.directness = _adjust(sliders.directness, 0.08)
        sliders.accountability = _adjust(sliders.accountability, 0.12)
    elif challenge_level == "low":
        sliders.directness = _adjust(sliders.directness, -0.08)
        sliders.accountability = _adjust(sliders.accountability, -0.12)

    if emotional_support == "high":
        sliders.emotional_support_level = _adjust(sliders.emotional_support_level, 0.25)
        sliders.warmth = _adjust(sliders.warmth, 0.12)
    elif emotional_support == "low":
        sliders.emotional_support_level = _adjust(sliders.emotional_support_level, -0.20)

    if detail_level == "concise":
        sliders.verbosity = _adjust(sliders.verbosity, -0.20)
    elif detail_level == "detailed":
        sliders.verbosity = _adjust(sliders.verbosity, 0.20)

    if accountability_style == "firm":
        sliders.accountability = _adjust(sliders.accountability, 0.20)
        sliders.directness = _adjust(sliders.directness, 0.05)
    elif accountability_style == "light":
        sliders.accountability = _adjust(sliders.accountability, -0.18)

    sliders.clamp()
    return BaselinePersonality(
        sliders=sliders,
        directives={"examples_frequency": examples_preference},
    )


def communication_energy_to_sliders(
    communication: str,
    energy: str,
    role_id: str,
) -> SliderPrefs:
    """Compatibility wrapper for v1 callers; roles no longer affect sliders."""
    _ = role_id
    return onboarding_answers_to_baseline(
        communication_style=communication,
        energy_level=energy,
    ).sliders


def _row_to_prefs(row) -> CompanionPreferences:
    prefs_data = json.loads(row["prefs_json"]) if row["prefs_json"] else {}
    schema_version = int(prefs_data.get("schema_version", 1))
    baseline = prefs_data.get("baseline") if schema_version >= 2 else {}
    baseline = baseline or {}
    sliders = SliderPrefs.from_dict(
        prefs_data.get("baseline_sliders") or prefs_data.get("sliders")
    )
    runtime = None
    if row["runtime_json"]:
        try:
            runtime = json.loads(row["runtime_json"])
        except json.JSONDecodeError:
            runtime = None

    return CompanionPreferences(
        user_id=row["user_id"],
        role_id="general_nova",
        communication=baseline.get(
            "communication_style", prefs_data.get("communication", "balanced")
        ),
        energy=baseline.get("energy_level", prefs_data.get("energy", "calm")),
        challenge_level=baseline.get("challenge_level", "medium"),
        emotional_support=baseline.get("emotional_support", "medium"),
        detail_level=baseline.get("detail_level", "normal"),
        examples_preference=baseline.get("examples_preference", "when_useful"),
        accountability_style=baseline.get("accountability_style", "steady"),
        sliders=sliders,
        baseline_directives=prefs_data.get("baseline_directives") or {},
        preferences_version=int(prefs_data.get("preferences_version", 1)),
        custom_notes=row["custom_notes"] or "",
        template_version=row["template_version"] or TEMPLATE_VERSION,
        runtime_json=runtime,
        onboarding_completed=bool(row["onboarding_completed"]),
        updated_at=row["updated_at"] or "",
    )


def get_companion_preferences(user_id: str | None = None) -> CompanionPreferences | None:
    uid = user_id or require_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_id, role_id, prefs_json, custom_notes, template_version,
               runtime_json, onboarding_completed, updated_at
        FROM companion_preferences
        WHERE user_id = ?
        """,
        (uid,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_prefs(row)


def is_onboarding_complete(user_id: str | None = None) -> bool:
    prefs = get_companion_preferences(user_id)
    return bool(prefs and prefs.onboarding_completed)


def save_companion_preferences(prefs: CompanionPreferences) -> None:
    prefs.sliders.clamp()
    uid = prefs.user_id or require_user_id()
    now = datetime.utcnow().isoformat()
    prefs.updated_at = now

    runtime_str = None
    if prefs.runtime_json is not None:
        runtime_str = json.dumps(prefs.runtime_json)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO companion_preferences (
            user_id, role_id, prefs_json, custom_notes, template_version,
            runtime_json, onboarding_completed, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            prefs.role_id,
            json.dumps(prefs.prefs_dict()),
            (prefs.custom_notes or "")[:MAX_CUSTOM_NOTES_LEN],
            prefs.template_version,
            runtime_str,
            1 if prefs.onboarding_completed else 0,
            now,
        ),
    )
    cursor.execute(
        """
        UPDATE users SET onboarding_completed = ?
        WHERE id = ?
        """,
        (1 if prefs.onboarding_completed else 0, uid),
    )
    conn.commit()
    conn.close()


def complete_onboarding(
    role_id: str,
    communication: str,
    energy: str,
    address_as: str,
    display_name: str | None = None,
    custom_notes: str | None = None,
    user_id: str | None = None,
    challenge_level: str = "medium",
    emotional_support: str = "medium",
    detail_level: str = "normal",
    examples_preference: str = "when_useful",
    accountability_style: str = "steady",
) -> CompanionPreferences:
    uid = user_id or require_user_id()
    if role_id not in VALID_ROLE_IDS:
        raise ValueError(f"Invalid role_id: {role_id}")

    baseline = onboarding_answers_to_baseline(
        communication_style=communication,
        energy_level=energy,
        challenge_level=challenge_level,
        emotional_support=emotional_support,
        detail_level=detail_level,
        examples_preference=examples_preference,
        accountability_style=accountability_style,
    )
    prefs = CompanionPreferences(
        user_id=uid,
        role_id="general_nova",
        communication=communication,
        energy=energy,
        challenge_level=challenge_level,
        emotional_support=emotional_support,
        detail_level=detail_level,
        examples_preference=examples_preference,
        accountability_style=accountability_style,
        sliders=baseline.sliders,
        baseline_directives=baseline.directives,
        custom_notes=(custom_notes or "")[:MAX_CUSTOM_NOTES_LEN],
        template_version=TEMPLATE_VERSION,
        onboarding_completed=True,
    )
    save_companion_preferences(prefs)

    address = (address_as or "").strip()[:32]
    if address:
        set_profile("address_as", address)

    if display_name and display_name.strip():
        set_profile("name", display_name.strip())

    return prefs


def update_companion_preferences(
    role_id: str | None = None,
    communication: str | None = None,
    energy: str | None = None,
    challenge_level: str | None = None,
    emotional_support: str | None = None,
    detail_level: str | None = None,
    examples_preference: str | None = None,
    accountability_style: str | None = None,
    custom_notes: str | None = None,
    sliders: dict[str, float] | None = None,
    user_id: str | None = None,
) -> CompanionPreferences:
    uid = user_id or require_user_id()
    existing = get_companion_preferences(uid)
    if not existing:
        raise ValueError("No companion preferences found")

    if role_id is not None:
        if role_id not in VALID_ROLE_IDS:
            raise ValueError(f"Invalid role_id: {role_id}")
        existing.role_id = "general_nova"
    if communication is not None:
        if communication not in VALID_COMMUNICATION:
            raise ValueError(f"Invalid communication: {communication}")
        existing.communication = communication
    if energy is not None:
        if energy not in VALID_ENERGY:
            raise ValueError(f"Invalid energy: {energy}")
        existing.energy = energy
    if challenge_level is not None:
        existing.challenge_level = challenge_level
    if emotional_support is not None:
        existing.emotional_support = emotional_support
    if detail_level is not None:
        existing.detail_level = detail_level
    if examples_preference is not None:
        existing.examples_preference = examples_preference
    if accountability_style is not None:
        existing.accountability_style = accountability_style

    if any(
        value is not None
        for value in (
            communication,
            energy,
            role_id,
            challenge_level,
            emotional_support,
            detail_level,
            examples_preference,
            accountability_style,
        )
    ):
        baseline = onboarding_answers_to_baseline(
            communication_style=existing.communication,
            energy_level=existing.energy,
            challenge_level=existing.challenge_level,
            emotional_support=existing.emotional_support,
            detail_level=existing.detail_level,
            examples_preference=existing.examples_preference,
            accountability_style=existing.accountability_style,
        )
        existing.sliders = baseline.sliders
        existing.baseline_directives = baseline.directives
        existing.preferences_version += 1

    if sliders:
        merged = existing.sliders.to_dict()
        merged.update(sliders)
        existing.sliders = SliderPrefs.from_dict(merged)
        existing.preferences_version += 1

    if custom_notes is not None:
        existing.custom_notes = custom_notes[:MAX_CUSTOM_NOTES_LEN]

    save_companion_preferences(existing)
    return existing


def save_runtime_personality(
    personality_snapshot: dict[str, Any],
    user_id: str | None = None,
) -> None:
    uid = user_id or require_user_id()
    prefs = get_companion_preferences(uid)
    if not prefs:
        return
    runtime_state: dict[str, Any] = {}
    for key in (
        "relationship_depth",
        "rapport_level",
        "last_emotional_context",
        "last_high_intensity_at",
        "active_modifier_summary",
    ):
        if key in personality_snapshot:
            runtime_state[key] = personality_snapshot[key]
    prefs.runtime_json = {
        "schema_version": 2,
        "runtime_state": runtime_state,
    }
    save_companion_preferences(prefs)


def clear_learned_style(user_id: str | None = None) -> None:
    """Clear runtime_json and learned preferences; keep onboarding prefs."""
    uid = user_id or require_user_id()
    prefs = get_companion_preferences(uid)
    if prefs:
        prefs.runtime_json = None
        save_companion_preferences(prefs)

    clear_learned_preferences(uid)


def list_role_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": "general_nova",
            "title": "General NOVA",
            "description": "Balanced, capable companion for everyday use",
        },
    ]
