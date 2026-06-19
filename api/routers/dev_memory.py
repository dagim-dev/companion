from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

import config
from api.deps import get_current_user
from memory_extraction_jobs import get_extraction_health, list_recent_jobs
from memory_scope import user_scope

router = APIRouter(prefix="/v1/dev/memory-extraction", tags=["dev-memory"])


def _require_dev_environment() -> None:
    if config.ENV == "production":
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/health")
def memory_extraction_health(
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    _require_dev_environment()
    with user_scope(user_id):
        return get_extraction_health()


@router.get("/jobs")
def memory_extraction_jobs(
    user_id: Annotated[str, Depends(get_current_user)],
    limit: int = 20,
) -> list[dict]:
    _require_dev_environment()
    bounded_limit = max(1, min(limit, 100))
    with user_scope(user_id):
        return list_recent_jobs(limit=bounded_limit)
