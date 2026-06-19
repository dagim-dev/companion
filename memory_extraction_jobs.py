from datetime import datetime, timedelta
from typing import Any

from memory import get_connection
from memory_scope import require_user_id

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_PENDING_RETRY = "pending_retry"
STATUS_FAILED_PERMANENTLY = "failed_permanently"

MAX_RETRIES = 3
RETRY_DELAYS_SECONDS = (60, 300, 900)


def _now() -> datetime:
    return datetime.now()


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _retry_at(retry_count: int) -> str:
    index = min(max(retry_count - 1, 0), len(RETRY_DELAYS_SECONDS) - 1)
    return _iso(_now() + timedelta(seconds=RETRY_DELAYS_SECONDS[index]))


def enqueue_extraction_job(message_id: int, message_content: str) -> int:
    uid = require_user_id()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory_extraction_jobs (
                user_id,
                message_id,
                message_content,
                status,
                retry_count,
                error,
                created_at,
                next_retry_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, 0, NULL, ?, NULL, NULL)
            """,
            (uid, message_id, message_content, STATUS_PENDING, _iso()),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def claim_next_job() -> dict[str, Any] | None:
    uid = require_user_id()
    now = _iso()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            """
            SELECT *
            FROM memory_extraction_jobs
            WHERE user_id = ?
              AND (
                status = ?
                OR (status = ? AND (next_retry_at IS NULL OR next_retry_at <= ?))
              )
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (uid, STATUS_PENDING, STATUS_PENDING_RETRY, now),
        ).fetchone()
        if row is None:
            return None

        cursor.execute(
            """
            UPDATE memory_extraction_jobs
            SET status = ?, error = NULL
            WHERE id = ?
            """,
            (STATUS_PROCESSING, row["id"]),
        )
        conn.commit()
        return dict(row) | {"status": STATUS_PROCESSING}
    finally:
        conn.close()


def mark_job_completed(job_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE memory_extraction_jobs
            SET status = ?, completed_at = ?, next_retry_at = NULL
            WHERE id = ?
            """,
            (STATUS_COMPLETED, _iso(), job_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_job_failed(job_id: int, error: str, *, max_retries: int = MAX_RETRIES) -> None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT retry_count FROM memory_extraction_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return
        retry_count = int(row["retry_count"]) + 1
        status = (
            STATUS_FAILED_PERMANENTLY
            if retry_count >= max_retries
            else STATUS_PENDING_RETRY
        )
        next_retry_at = None if status == STATUS_FAILED_PERMANENTLY else _retry_at(retry_count)
        completed_at = _iso() if status == STATUS_FAILED_PERMANENTLY else None
        conn.execute(
            """
            UPDATE memory_extraction_jobs
            SET status = ?,
                retry_count = ?,
                error = ?,
                next_retry_at = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (status, retry_count, error, next_retry_at, completed_at, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_extraction_health() -> dict[str, Any]:
    uid = require_user_id()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM memory_extraction_jobs
            WHERE user_id = ?
            GROUP BY status
            """,
            (uid,),
        ).fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        last_failed = conn.execute(
            """
            SELECT id, message_id, status, retry_count, error, created_at, completed_at
            FROM memory_extraction_jobs
            WHERE user_id = ? AND error IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (uid,),
        ).fetchone()
    finally:
        conn.close()

    completed = int(counts.get(STATUS_COMPLETED, 0))
    failed = int(counts.get(STATUS_FAILED_PERMANENTLY, 0))
    total_processed = completed + failed
    success_rate = completed / total_processed if total_processed else 0.0
    pending_retry = int(counts.get(STATUS_PENDING_RETRY, 0))

    return {
        "pending": int(counts.get(STATUS_PENDING, 0)),
        "processing": int(counts.get(STATUS_PROCESSING, 0)),
        "completed": completed,
        "pending_retry": pending_retry,
        "failed_permanently": failed,
        "success_rate": round(success_rate, 4),
        "last_failure_reason": last_failed["error"] if last_failed else None,
        "last_failed_job": dict(last_failed) if last_failed else None,
        "total_jobs_processed": total_processed,
        "show_warning": pending_retry > 5,
        "warning_message": (
            f"Memory extraction backlog detected. {pending_retry} jobs waiting for retry."
            if pending_retry > 5
            else None
        ),
    }


def list_recent_jobs(limit: int = 20) -> list[dict[str, Any]]:
    uid = require_user_id()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, message_id, status, retry_count, error, created_at,
                   next_retry_at, completed_at
            FROM memory_extraction_jobs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (uid, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
