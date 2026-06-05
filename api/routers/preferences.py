from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.schemas import PreferencesResponse, PreferencesUpdateRequest
from companion_prefs import (
    clear_learned_style,
    get_companion_preferences,
    update_companion_preferences,
)
from memory_scope import user_scope
from state_store import clear_state

router = APIRouter(prefix="/v1/preferences", tags=["preferences"])


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


@router.get("", response_model=PreferencesResponse)
def get_preferences(
    user_id: Annotated[str, Depends(get_current_user)],
) -> PreferencesResponse:
    with user_scope(user_id):
        prefs = get_companion_preferences(user_id)
    if not prefs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found. Complete onboarding first.",
        )
    return _prefs_to_response(prefs)


@router.put("", response_model=PreferencesResponse)
def put_preferences(
    body: PreferencesUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> PreferencesResponse:
    with user_scope(user_id):
        try:
            prefs = update_companion_preferences(
                role_id=body.role_id,
                communication=body.communication,
                energy=body.energy,
                custom_notes=body.custom_notes,
                user_id=user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    clear_state(user_id)
    return _prefs_to_response(prefs)


@router.post("/reset-learned")
def reset_learned_preferences(
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict[str, str]:
    with user_scope(user_id):
        clear_learned_style(user_id)
    clear_state(user_id)
    return {"status": "ok", "message": "Learned style and runtime adaptation cleared."}
