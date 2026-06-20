from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_jwt import decode_token
from auth_store import get_user_by_id
from state_store import get_nova_state
from session_state import NovaState

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    try:
        user_id = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user_id


def get_state(
    user_id: Annotated[str, Depends(get_current_user)],
) -> NovaState:
    """Per-user session; DB scope is set in route handlers via memory_scope.user_scope."""
    return get_nova_state(user_id)
