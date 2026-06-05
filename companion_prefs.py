"""Per-user companion preferences: onboarding, sliders, runtime personality."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from memory import get_connection, set_profile
from memory_scope import require_user_id

TEMPLATE_VERSION = "1"
MAX_CUSTOM_NOTES_LEN = 300

VALID_ROLE_IDS = frozenset({
    "strategic_partner",
    "fitness_coach",
    "calm_companion",
    "creative_sparring",
    "productivity_operator",
    "general_jarvis",
})

VALID_COMMUNICATION = frozenset({"direct", "balanced", "gentle"})
VALID_ENERGY = frozenset({"calm", "upbeat"})


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
        return asdict(self)

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
                data.get("emotional_support_level", 0.5)
            ),
        )


@dataclass
class CompanionPreferences:
    user_id: str
    role_id: str = "general_jarvis"
    communication: str = "balanced"
    energy: str = "calm"
    sliders: SliderPrefs = field(default_factory=SliderPrefs)
    custom_notes: str = ""
    template_version: str = TEMPLATE_VERSION
    runtime_json: dict[str, Any] | None = None
    onboarding_completed: bool = False
    updated_at: str = ""

    def prefs_dict(self) -> dict[str, Any]:
        return {
            "communication": self.communication,
            "energy": self.energy,
            "sliders": self.sliders.to_dict(),
        }


def communication_energy_to_sliders(
    communication: str,
    energy: str,
    role_id: str,
) -> SliderPrefs:
    """Map onboarding choices to slider priors."""
    base = SliderPrefs()
    role_biases: dict[str, dict[str, float]] = {
        "strategic_partner": {
            "directness": 0.85,
            "warmth": 0.4,
            "humor": 0.25,
            "verbosity": 0.45,
            "accountability": 0.7,
            "emotional_support_level": 0.35,
        },
        "fitness_coach": {
            "directness": 0.8,
            "warmth": 0.5,
            "humor": 0.3,
            "verbosity": 0.5,
            "accountability": 0.9,
            "emotional_support_level": 0.4,
        },
        "calm_companion": {
            "directness": 0.45,
            "warmth": 0.75,
            "humor": 0.15,
            "verbosity": 0.55,
            "accountability": 0.35,
            "emotional_support_level": 0.85,
        },
        "creative_sparring": {
            "directness": 0.65,
            "warmth": 0.55,
            "humor": 0.65,
            "verbosity": 0.6,
            "accountability": 0.45,
            "emotional_support_level": 0.4,
        },
        "productivity_operator": {
            "directness": 0.75,
            "warmth": 0.45,
            "humor": 0.2,
            "verbosity": 0.4,
            "accountability": 0.85,
            "emotional_support_level": 0.35,
        },
        "general_jarvis": {
            "directness": 0.6,
            "warmth": 0.55,
            "humor": 0.35,
            "verbosity": 0.5,
            "accountability": 0.5,
            "emotional_support_level": 0.5,
        },
    }
    bias = role_biases.get(role_id, role_biases["general_jarvis"])
    for k, v in bias.items():
        setattr(base, k, v)

    comm_adj = {
        "direct": {"directness": 0.15, "warmth": -0.1, "verbosity": -0.1},
        "balanced": {},
        "gentle": {"directness": -0.2, "warmth": 0.15, "emotional_support_level": 0.15},
    }
    for k, delta in comm_adj.get(communication, {}).items():
        setattr(base, k, min(1.0, max(0.0, getattr(base, k) + delta)))

    if energy == "upbeat":
        base.humor = min(1.0, base.humor + 0.15)
        base.warmth = min(1.0, base.warmth + 0.1)
    else:
        base.humor = max(0.0, base.humor - 0.05)

    base.clamp()
    return base


def _row_to_prefs(row) -> CompanionPreferences:
    prefs_data = json.loads(row["prefs_json"]) if row["prefs_json"] else {}
    sliders = SliderPrefs.from_dict(prefs_data.get("sliders"))
    runtime = None
    if row["runtime_json"]:
        try:
            runtime = json.loads(row["runtime_json"])
        except json.JSONDecodeError:
            runtime = None

    return CompanionPreferences(
        user_id=row["user_id"],
        role_id=row["role_id"],
        communication=prefs_data.get("communication", "balanced"),
        energy=prefs_data.get("energy", "calm"),
        sliders=sliders,
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
) -> CompanionPreferences:
    uid = user_id or require_user_id()
    if role_id not in VALID_ROLE_IDS:
        raise ValueError(f"Invalid role_id: {role_id}")
    if communication not in VALID_COMMUNICATION:
        raise ValueError(f"Invalid communication: {communication}")
    if energy not in VALID_ENERGY:
        raise ValueError(f"Invalid energy: {energy}")

    sliders = communication_energy_to_sliders(communication, energy, role_id)
    prefs = CompanionPreferences(
        user_id=uid,
        role_id=role_id,
        communication=communication,
        energy=energy,
        sliders=sliders,
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
        existing.role_id = role_id
    if communication is not None:
        if communication not in VALID_COMMUNICATION:
            raise ValueError(f"Invalid communication: {communication}")
        existing.communication = communication
    if energy is not None:
        if energy not in VALID_ENERGY:
            raise ValueError(f"Invalid energy: {energy}")
        existing.energy = energy

    if communication or energy or role_id:
        existing.sliders = communication_energy_to_sliders(
            existing.communication,
            existing.energy,
            existing.role_id,
        )

    if sliders:
        merged = existing.sliders.to_dict()
        merged.update(sliders)
        existing.sliders = SliderPrefs.from_dict(merged)

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
    prefs.runtime_json = {"personality_state": personality_snapshot}
    save_companion_preferences(prefs)


def clear_learned_style(user_id: str | None = None) -> None:
    """Clear runtime_json and interaction_style memories; keep onboarding prefs."""
    uid = user_id or require_user_id()
    prefs = get_companion_preferences(uid)
    if prefs:
        prefs.runtime_json = None
        save_companion_preferences(prefs)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM personal_memories
        WHERE user_id = ? AND category = 'interaction_style'
        """,
        (uid,),
    )
    conn.commit()
    conn.close()


def list_role_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": "general_jarvis",
            "title": "General JARVIS",
            "description": "Balanced, capable companion for everyday use",
        },
        {
            "id": "strategic_partner",
            "title": "Strategic Partner",
            "description": "Analytical, proactive, low fluff",
        },
        {
            "id": "fitness_coach",
            "title": "Fitness Coach",
            "description": "Goals, accountability, direct feedback",
        },
        {
            "id": "calm_companion",
            "title": "Calm Companion",
            "description": "Steady, grounding, low sarcasm",
        },
        {
            "id": "creative_sparring",
            "title": "Creative Sparring",
            "description": "Ideas, challenge assumptions, more humor",
        },
        {
            "id": "productivity_operator",
            "title": "Productivity Operator",
            "description": "Tasks, prioritization, check-ins",
        },
    ]
