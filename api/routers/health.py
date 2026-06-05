from fastapi import APIRouter

from memory import get_connection
from voice_capabilities import voice_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok", "db": db_status, "voice": voice_status()}
