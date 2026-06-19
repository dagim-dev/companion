import asyncio
import logging
from contextlib import suppress

from memory import get_connection
from memory_extraction_jobs import claim_next_job, mark_job_completed, mark_job_failed
from memory_insights import save_insights
from memory_intelligence import RECENT_CONTEXT_WINDOW
from memory_intelligence import extract_insights_from_message
from memory_scope import user_scope
from learned_preferences import aggregate_preference_insights

logger = logging.getLogger(__name__)

_worker_task: asyncio.Task | None = None
_POLL_SECONDS = 5.0


def _recent_user_context(user_id: str, before_message_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT role, content
            FROM conversations
            WHERE user_id = ?
              AND id < ?
              AND role = 'user'
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, before_message_id, RECENT_CONTEXT_WINDOW),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"role": row["role"], "content": row["content"]}
        for row in reversed(rows)
    ]


def process_next_job(user_id: str) -> bool:
    """Process one due job for a user. Returns True when a job was claimed."""
    with user_scope(user_id):
        job = claim_next_job()
        if job is None:
            return False

    try:
        insights = extract_insights_from_message(
            latest_user_message=job["message_content"],
            recent_context=_recent_user_context(user_id, job["message_id"]),
        )
        with user_scope(user_id):
            save_insights(message_id=job["message_id"], insights=insights)
            aggregate_preference_insights(message_id=job["message_id"])
            mark_job_completed(job["id"])
        logger.info("Memory extraction job completed: %s", job["id"])
        return True
    except Exception as exc:
        logger.exception("Memory extraction job failed: %s", job["id"])
        with user_scope(user_id):
            mark_job_failed(job["id"], str(exc))
        return True


def _claim_any_due_job() -> tuple[str, dict] | None:
    from memory_extraction_jobs import STATUS_PENDING, STATUS_PENDING_RETRY
    from datetime import datetime

    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT user_id
            FROM memory_extraction_jobs
            WHERE status = ?
               OR (status = ? AND (next_retry_at IS NULL OR next_retry_at <= ?))
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (STATUS_PENDING, STATUS_PENDING_RETRY, now),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    user_id = row["user_id"]
    with user_scope(user_id):
        job = claim_next_job()
    if job is None:
        return None
    return user_id, job


def process_next_available_job() -> bool:
    claimed = _claim_any_due_job()
    if claimed is None:
        return False
    user_id, job = claimed
    try:
        insights = extract_insights_from_message(
            latest_user_message=job["message_content"],
            recent_context=_recent_user_context(user_id, job["message_id"]),
        )
        with user_scope(user_id):
            save_insights(message_id=job["message_id"], insights=insights)
            aggregate_preference_insights(message_id=job["message_id"])
            mark_job_completed(job["id"])
        logger.info("Memory extraction job completed: %s", job["id"])
        return True
    except Exception as exc:
        logger.exception("Memory extraction job failed: %s", job["id"])
        with user_scope(user_id):
            mark_job_failed(job["id"], str(exc))
        return True


async def _worker_loop() -> None:
    while True:
        processed = await asyncio.to_thread(process_next_available_job)
        if not processed:
            await asyncio.sleep(_POLL_SECONDS)


def start_worker() -> None:
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("Memory extraction worker requires a running event loop")
        return
    _worker_task = loop.create_task(_worker_loop())
    logger.info("Memory extraction worker started")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await _worker_task
    _worker_task = None
    logger.info("Memory extraction worker stopped")
