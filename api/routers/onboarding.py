from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from api.schemas import OnboardingCompleteRequest, PreferencesResponse, RoleCatalogItem
from companion_prefs import (
    complete_onboarding,
    get_companion_preferences,
    list_role_catalog,
)
from memory_scope import user_scope

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


def _prefs_to_response(prefs) -> PreferencesResponse:
    return PreferencesResponse(
        role_id=prefs.role_id,
        communication=prefs.communication,
        energy=prefs.energy,
        sliders=prefs.sliders.to_dict(),
        custom_notes=prefs.custom_notes,
        onboarding_completed=prefs.onboarding_completed,
        template_version=prefs.template_version,
    )


@router.get("/roles", response_model=list[RoleCatalogItem])
def list_roles() -> list[RoleCatalogItem]:
    return [RoleCatalogItem(**r) for r in list_role_catalog()]


@router.post("/complete", response_model=PreferencesResponse)
def onboarding_complete(
    body: OnboardingCompleteRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> PreferencesResponse:
    with user_scope(user_id):
        try:
            prefs = complete_onboarding(
                role_id=body.role_id,
                communication=body.communication,
                energy=body.energy,
                address_as=body.address_as,
                display_name=body.display_name,
                custom_notes=body.custom_notes,
                user_id=user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _prefs_to_response(prefs)
