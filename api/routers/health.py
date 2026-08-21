from fastapi import APIRouter
from fastapi.responses import JSONResponse

from memory import get_connection
from voice_capabilities import voice_status

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health():
    voice = voice_status()
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "db": "ok", "voice": voice}
    except Exception as exc:
        db_status = f"error: {exc}"
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": db_status, "voice": voice},
        )
