from companion_prefs import get_companion_preferences
from session_state import JarvisState, create_state

_states: dict[str, JarvisState] = {}


def _hydrate_state(state: JarvisState) -> None:
    prefs = get_companion_preferences(state.user_id)
    state.companion_prefs = prefs
    if prefs and prefs.runtime_json:
        ps = prefs.runtime_json.get("personality_state")
        if ps:
            state.personality_state.load_snapshot(ps)


def get_jarvis_state(user_id: str) -> JarvisState:
    if user_id not in _states:
        state = create_state(user_id)
        _hydrate_state(state)
        _states[user_id] = state
    return _states[user_id]


def clear_state(user_id: str) -> None:
    _states.pop(user_id, None)
