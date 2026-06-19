from datetime import datetime
import json

from memory import get_connection
from memory_scope import require_user_id
from memory_intelligence import CONFIDENCE_THRESHOLD, ExtractedInsight


def _now() -> str:
    return datetime.now().isoformat()


def save_insights(message_id: int, insights: list[ExtractedInsight]) -> int:
    """Persist validated long-term insights for the scoped user."""
    uid = require_user_id()
    high_confidence = [
        insight
        for insight in insights
        if insight.confidence >= CONFIDENCE_THRESHOLD
        and insight.stability == "long_term"
    ]
    if not high_confidence:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    try:
        for insight in high_confidence:
            timestamp = _now()
            cursor.execute(
                """
                INSERT OR REPLACE INTO memory_insights (
                    user_id,
                    message_id,
                    label,
                    type,
                    confidence,
                    evidence,
                    source,
                    stability,
                    preference_key,
                    preference_value_json,
                    scope,
                    context_json,
                    evidence_polarity,
                    embedding,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    message_id,
                    insight.label,
                    insight.type,
                    insight.confidence,
                    insight.evidence,
                    insight.source,
                    insight.stability,
                    insight.preference_key,
                    json.dumps(insight.preference_value) if insight.preference_value else None,
                    insight.scope,
                    json.dumps(insight.context) if insight.context else None,
                    insight.evidence_polarity,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
            saved += 1
        conn.commit()
        return saved
    finally:
        conn.close()


def get_recent_insights(limit: int = 20) -> list[dict]:
    uid = require_user_id()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, message_id, label, type, confidence, evidence, source,
                   stability, preference_key, preference_value_json, scope,
                   context_json, evidence_polarity
            FROM memory_insights
            WHERE user_id = ? AND stability = 'long_term'
            ORDER BY confidence DESC, updated_at DESC
            LIMIT ?
            """,
            (uid, limit),
        ).fetchall()
    finally:
        conn.close()
    insights = []
    for row in rows:
        item = dict(row)
        if item.get("preference_value_json"):
            item["preference_value"] = json.loads(item["preference_value_json"])
        if item.get("context_json"):
            item["context"] = json.loads(item["context_json"])
        insights.append(item)
    return insights
