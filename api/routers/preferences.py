from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.schemas import (
    PersonalityResetRequest,
    PreferencesResponse,
    PreferencesUpdateRequest,
)
from companion_prefs import (
    clear_learned_style,
    get_companion_preferences,
    save_companion_preferences,
    update_companion_preferences,
)
from learned_preferences import (
    disable_learned_preference,
    get_active_learned_preferences,
)
from memory_scope import user_scope
from state_store import clear_state

router = APIRouter(prefix="/v1/preferences", tags=["preferences"])


def _prefs_to_response(prefs) -> PreferencesResponse:
    return PreferencesResponse(
        role_id=prefs.role_id,
        communication=prefs.communication,
        energy=prefs.energy,
        challenge_level=prefs.challenge_level,
        emotional_support=prefs.emotional_support,
        detail_level=prefs.detail_level,
        examples_preference=prefs.examples_preference,
        accountability_style=prefs.accountability_style,
        sliders=prefs.sliders.to_dict(),
        baseline_directives=prefs.baseline_directives,
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
                challenge_level=body.challenge_level,
                emotional_support=body.emotional_support,
                detail_level=body.detail_level,
                examples_preference=body.examples_preference,
                accountability_style=body.accountability_style,
                sliders=body.sliders,
                custom_notes=body.custom_notes,
                user_id=user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    clear_state(user_id)
    return _prefs_to_response(prefs)


@router.get("/learned")
def list_learned_preferences(
    user_id: Annotated[str, Depends(get_current_user)],
) -> list[dict]:
    with user_scope(user_id):
        return get_active_learned_preferences(limit=50)


@router.delete("/learned/{preference_id}")
def delete_learned_preference(
    preference_id: int,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict[str, str]:
    with user_scope(user_id):
        disable_learned_preference(preference_id)
    clear_state(user_id)
    return {"status": "ok", "message": "Learned preference disabled."}


@router.post("/reset-learned")
def reset_learned_preferences(
    user_id: Annotated[str, Depends(get_current_user)],
    body: PersonalityResetRequest | None = None,
) -> dict[str, str]:
    scope = (body or PersonalityResetRequest()).scope
    with user_scope(user_id):
        if scope in ("learned", "all_personality"):
            clear_learned_style(user_id)
        elif scope == "runtime":
            prefs = get_companion_preferences(user_id)
            if prefs:
                prefs.runtime_json = None
                save_companion_preferences(prefs)
        elif scope == "baseline":
            update_companion_preferences(
                communication="balanced",
                energy="calm",
                challenge_level="medium",
                emotional_support="medium",
                detail_level="normal",
                examples_preference="when_useful",
                accountability_style="steady",
                user_id=user_id,
            )

        if scope == "all_personality":
            update_companion_preferences(
                communication="balanced",
                energy="calm",
                challenge_level="medium",
                emotional_support="medium",
                detail_level="normal",
                examples_preference="when_useful",
                accountability_style="steady",
                user_id=user_id,
            )
    clear_state(user_id)
    return {"status": "ok", "message": f"Personality reset applied: {scope}."}
