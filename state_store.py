import threading
import time

from companion_prefs import get_companion_preferences
from memory import get_recent_conversations
from session_state import JarvisState, create_state

_STATE_TTL_SECONDS = 3600  # 1 hour

_states: dict[str, tuple[JarvisState, float]] = {}
_states_lock = threading.Lock()


def _is_expired(last_access: float, now: float) -> bool:
    return now - last_access > _STATE_TTL_SECONDS


def _cleanup_expired_states(now: float) -> None:
    """Remove expired entries. Caller must hold _states_lock."""
    expired = [
        uid
        for uid, (_, last_access) in _states.items()
        if _is_expired(last_access, now)
    ]
    for uid in expired:
        del _states[uid]


def _hydrate_state(state: JarvisState) -> None:
    prefs = get_companion_preferences(state.user_id)
    state.companion_prefs = prefs
    if prefs and prefs.runtime_json:
        ps = prefs.runtime_json.get("personality_state")
        if ps:
            state.personality_state.load_snapshot(ps)

    state.conversation = get_recent_conversations(state.user_id, limit=20)


def _create_and_hydrate(user_id: str) -> JarvisState:
    state = create_state(user_id)
    _hydrate_state(state)
    return state


def get_jarvis_state(user_id: str) -> JarvisState:
    now = time.monotonic()
    with _states_lock:
        _cleanup_expired_states(now)

        entry = _states.get(user_id)
        if entry is not None:
            state, last_access = entry
            if _is_expired(last_access, now):
                del _states[user_id]
                state = _create_and_hydrate(user_id)
            _states[user_id] = (state, now)
        else:
            state = _create_and_hydrate(user_id)
            _states[user_id] = (state, now)

        return state


def clear_state(user_id: str) -> None:
    with _states_lock:
        _states.pop(user_id, None)
