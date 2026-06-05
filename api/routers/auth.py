from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserMeResponse
from auth_jwt import create_access_token
from auth_store import create_user, get_user_by_email, get_user_by_id, verify_password
from companion_prefs import is_onboarding_complete

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserMeResponse)
def auth_me(user_id: Annotated[str, Depends(get_current_user)]) -> UserMeResponse:
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    completed = is_onboarding_complete(user_id) or user.get(
        "onboarding_completed", False
    )
    return UserMeResponse(
        user_id=user["id"],
        email=user["email"],
        onboarding_completed=completed,
    )


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest) -> TokenResponse:
    if get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    try:
        user = create_user(body.email, body.password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user_id=user["id"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user_id=user["id"])
