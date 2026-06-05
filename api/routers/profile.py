from typing import Annotated

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.schemas import ProfileResponse, ProfileUpdateRequest
from memory import get_profile, set_profile
from memory_scope import user_scope

router = APIRouter(prefix="/v1/profile", tags=["profile"])

MAX_ADDRESS_AS_LEN = 32


def _profile_response() -> ProfileResponse:
    profile = get_profile()
    address_as = profile.get("address_as")
    name = profile.get("name")
    return ProfileResponse(
        address_as=address_as if address_as else None,
        name=name if name else None,
    )


@router.get("", response_model=ProfileResponse)
def get_user_profile(
    user_id: Annotated[str, Depends(get_current_user)],
) -> ProfileResponse:
    with user_scope(user_id):
        return _profile_response()


@router.patch("", response_model=ProfileResponse)
def patch_user_profile(
    body: ProfileUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> ProfileResponse:
    address_as = body.address_as.strip()[:MAX_ADDRESS_AS_LEN]
    with user_scope(user_id):
        set_profile("address_as", address_as)
        return _profile_response()
