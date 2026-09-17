"""
Cap oversized reflections.content rows to the bounded helper limits.
Run: python migrations/006_cap_reflection_content.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from reflection_content import (
    MAX_REFLECTION_CONTENT_CHARS,
    MAX_REFLECTION_CONTENT_FRAGMENTS,
    count_reflection_fragments,
    normalize_reflection_content,
)


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _needs_normalization(content: str | None) -> bool:
    if not content:
        return False
    if len(content) > MAX_REFLECTION_CONTENT_CHARS:
        return True
    return count_reflection_fragments(content) > MAX_REFLECTION_CONTENT_FRAGMENTS


def migrate(db_path: str | None = None) -> int:
    target_path = db_path or config.DATABASE_PATH
    if not os.path.exists(target_path):
        print(f"No database at {target_path}; nothing to migrate.")
        return 0

    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    if not _table_exists(cursor, "reflections"):
        print("No reflections table found; nothing to migrate.")
        conn.close()
        return 0

    cursor.execute(
        """
        SELECT id, content
        FROM reflections
        WHERE content IS NOT NULL
        """
    )
    rows = cursor.fetchall()

    updated = 0
    for row_id, content in rows:
        if not _needs_normalization(content):
            continue

        normalized = normalize_reflection_content(content)
        if normalized == content:
            continue

        cursor.execute(
            "UPDATE reflections SET content = ? WHERE id = ?",
            (normalized, row_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Normalized {updated} reflection row(s) in {target_path}.")
    return updated


if __name__ == "__main__":
    migrate()
