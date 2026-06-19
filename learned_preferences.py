from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from memory import get_connection
from memory_scope import require_user_id

ACTIVE_STATUS = "active"
CONFLICTED_STATUS = "conflicted"
SUPPRESSED_STATUS = "suppressed"


def _now() -> str:
    return datetime.now().isoformat()


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


def _infer_preference_key(label: str) -> str | None:
    lower = label.lower()
    if any(word in lower for word in ("short", "concise", "brief")):
        return "response.length"
    if any(word in lower for word in ("detail", "detailed", "thorough")):
        return "response.length"
    if "example" in lower:
        return "response.examples"
    if any(word in lower for word in ("simple", "simpler", "plain")):
        return "response.simplicity"
    if any(word in lower for word in ("direct", "blunt", "gentle")):
        return "response.directness"
    if any(word in lower for word in ("challenge", "push back", "pushback")):
        return "response.challenge_level"
    if any(word in lower for word in ("support", "reassurance", "reassure")):
        return "response.emotional_support"
    if any(word in lower for word in ("accountability", "accountable", "nudge")):
        return "response.accountability"
    return None


def _infer_preference_value(label: str, evidence: str) -> dict[str, str] | None:
    text = f"{label} {evidence}".lower()
    if any(word in text for word in ("short", "concise", "brief")):
        return {"target": "concise"}
    if any(word in text for word in ("detail", "detailed", "thorough")):
        return {"target": "detailed"}
    if "example" in text:
        return {"target": "examples"}
    if any(word in text for word in ("simple", "simpler", "plain")):
        return {"target": "simple"}
    if any(word in text for word in ("direct", "blunt")):
        return {"target": "direct"}
    if "gentle" in text:
        return {"target": "gentle"}
    if any(word in text for word in ("high challenge", "challenge me", "push back")):
        return {"target": "high"}
    if any(word in text for word in ("low challenge", "don't challenge", "dont challenge")):
        return {"target": "low"}
    if any(word in text for word in ("more support", "supportive", "reassure")):
        return {"target": "high"}
    if any(word in text for word in ("less support", "less reassurance")):
        return {"target": "low"}
    if any(word in text for word in ("firm accountability", "hold me accountable")):
        return {"target": "firm"}
    if any(word in text for word in ("light accountability", "gentle nudge")):
        return {"target": "light"}
    return None


def _normalize_insight(row: dict[str, Any]) -> dict[str, Any] | None:
    if row["type"] != "preference" or row["stability"] != "long_term":
        return None
    key = row.get("preference_key") or _infer_preference_key(row["label"])
    value = _json_loads(row.get("preference_value_json")) or _infer_preference_value(
        row["label"],
        row["evidence"],
    )
    if not key or not value:
        return None
    polarity = row.get("evidence_polarity") or "positive"
    value = _apply_polarity(key, value, polarity)
    return {
        "memory_insight_id": row["id"],
        "message_id": row["message_id"],
        "preference_key": key,
        "value_json": _json_dumps(value),
        "value": value,
        "scope": row.get("scope") or "global",
        "context_json": row.get("context_json"),
        "confidence": float(row["confidence"]),
        "evidence_text": row["evidence"],
        "polarity": polarity,
    }


def _apply_polarity(key: str, value: dict[str, Any], polarity: str) -> dict[str, Any]:
    if polarity != "negative":
        return value
    target = value.get("target")
    inversions = {
        "response.examples": {"examples": "few", "often": "few"},
        "response.length": {"detailed": "concise", "concise": "detailed"},
        "response.directness": {"direct": "gentle", "gentle": "direct"},
        "response.challenge_level": {"high": "low", "low": "high"},
        "response.emotional_support": {"high": "low", "low": "high"},
        "response.accountability": {"firm": "light", "light": "firm"},
    }
    inverted = inversions.get(key, {}).get(target)
    if inverted:
        updated = dict(value)
        updated["target"] = inverted
        return updated
    return value


def _record_evidence(
    cursor,
    *,
    uid: str,
    preference_id: int,
    item: dict[str, Any],
) -> None:
    cursor.execute(
        """
        INSERT INTO learned_preference_evidence (
            user_id,
            preference_id,
            memory_insight_id,
            message_id,
            evidence_text,
            evidence_type,
            confidence,
            polarity,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            preference_id,
            item["memory_insight_id"],
            item["message_id"],
            item["evidence_text"],
            "explicit_statement",
            item["confidence"],
            item["polarity"],
            _now(),
        ),
    )


def _find_existing(cursor, uid: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    rows = cursor.execute(
        """
        SELECT *
        FROM learned_preferences
        WHERE user_id = ?
          AND preference_key = ?
          AND scope = ?
          AND COALESCE(context_json, '') = COALESCE(?, '')
          AND status IN (?, ?)
        ORDER BY id
        """,
        (
            uid,
            item["preference_key"],
            item["scope"],
            item["context_json"],
            ACTIVE_STATUS,
            CONFLICTED_STATUS,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def _insert_preference(cursor, uid: str, item: dict[str, Any], status: str = ACTIVE_STATUS) -> int:
    timestamp = _now()
    positive_count = 1 if item["polarity"] != "negative" else 0
    negative_count = 1 if item["polarity"] == "negative" else 0
    cursor.execute(
        """
        INSERT INTO learned_preferences (
            user_id,
            preference_key,
            category,
            value_json,
            scope,
            context_json,
            confidence,
            source_count,
            positive_evidence_count,
            negative_evidence_count,
            status,
            origin,
            is_pinned,
            first_seen_at,
            last_seen_at,
            last_confirmed_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, 'extracted', 0, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            item["preference_key"],
            item["preference_key"].split(".", 1)[0],
            item["value_json"],
            item["scope"],
            item["context_json"],
            item["confidence"],
            positive_count,
            negative_count,
            status,
            timestamp,
            timestamp,
            timestamp,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def _update_matching_preference(cursor, existing: dict[str, Any], item: dict[str, Any]) -> int:
    timestamp = _now()
    confidence = max(float(existing["confidence"]), item["confidence"])
    positive_delta = 1 if item["polarity"] != "negative" else 0
    negative_delta = 1 if item["polarity"] == "negative" else 0
    cursor.execute(
        """
        UPDATE learned_preferences
        SET confidence = ?,
            source_count = source_count + 1,
            positive_evidence_count = positive_evidence_count + ?,
            negative_evidence_count = negative_evidence_count + ?,
            status = ?,
            last_seen_at = ?,
            last_confirmed_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            confidence,
            positive_delta,
            negative_delta,
            ACTIVE_STATUS,
            timestamp,
            timestamp,
            timestamp,
            existing["id"],
        ),
    )
    return int(existing["id"])


def _mark_conflict(cursor, uid: str, existing: dict[str, Any], new_id: int, key: str) -> None:
    timestamp = _now()
    cursor.execute(
        "UPDATE learned_preferences SET status = ?, updated_at = ? WHERE id = ?",
        (CONFLICTED_STATUS, timestamp, existing["id"]),
    )
    cursor.execute(
        """
        INSERT INTO learned_preference_conflicts (
            user_id,
            preference_key,
            preference_a_id,
            preference_b_id,
            resolution_strategy,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            uid,
            key,
            existing["id"],
            new_id,
            "latest_explicit_wins",
            timestamp,
        ),
    )


def aggregate_preference_insights(message_id: int | None = None) -> int:
    """Promote raw memory_insights preference rows into canonical learned prefs."""
    uid = require_user_id()
    conn = get_connection()
    saved = 0
    try:
        params: list[Any] = [uid]
        message_filter = ""
        if message_id is not None:
            message_filter = "AND message_id = ?"
            params.append(message_id)
        rows = conn.execute(
            f"""
            SELECT *
            FROM memory_insights
            WHERE user_id = ?
              AND type = 'preference'
              AND stability = 'long_term'
              {message_filter}
            ORDER BY id
            """,
            params,
        ).fetchall()

        cursor = conn.cursor()
        for row in rows:
            item = _normalize_insight(dict(row))
            if item is None:
                continue
            existing_items = _find_existing(cursor, uid, item)
            matching = next(
                (
                    existing
                    for existing in existing_items
                    if existing["value_json"] == item["value_json"]
                ),
                None,
            )
            if matching:
                pref_id = _update_matching_preference(cursor, matching, item)
            else:
                pref_id = _insert_preference(cursor, uid, item)
                for existing in existing_items:
                    if existing["value_json"] != item["value_json"]:
                        _mark_conflict(cursor, uid, existing, pref_id, item["preference_key"])
            _record_evidence(cursor, uid=uid, preference_id=pref_id, item=item)
            saved += 1
        conn.commit()
        return saved
    finally:
        conn.close()


def get_active_learned_preferences(limit: int = 10) -> list[dict[str, Any]]:
    uid = require_user_id()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM learned_preferences
            WHERE user_id = ? AND status = ?
            ORDER BY is_pinned DESC, confidence DESC, last_seen_at DESC
            LIMIT ?
            """,
            (uid, ACTIVE_STATUS, limit),
        ).fetchall()
    finally:
        conn.close()
    prefs = []
    for row in rows:
        item = dict(row)
        item["value"] = _json_loads(item.get("value_json"), {})
        item["context"] = _json_loads(item.get("context_json"), None)
        prefs.append(item)
    return prefs


def disable_learned_preference(preference_id: int) -> None:
    uid = require_user_id()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE learned_preferences
            SET status = ?, updated_at = ?
            WHERE user_id = ? AND id = ?
            """,
            (SUPPRESSED_STATUS, _now(), uid, preference_id),
        )
        conn.commit()
    finally:
        conn.close()


def clear_learned_preferences(user_id: str | None = None) -> None:
    uid = user_id or require_user_id()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM learned_preference_conflicts WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM learned_preference_evidence WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM learned_preferences WHERE user_id = ?", (uid,))
        conn.execute(
            """
            DELETE FROM memory_insights
            WHERE user_id = ? AND type = 'preference'
            """,
            (uid,),
        )
        conn.commit()
    finally:
        conn.close()
