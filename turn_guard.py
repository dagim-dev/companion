from __future__ import annotations

import threading


class UserTurnBusyError(RuntimeError):
    def __init__(self, user_id: str):
        super().__init__(f"turn already in progress for user {user_id}")
        self.user_id = user_id


_active_users: set[str] = set()
_active_users_lock = threading.Lock()


class TurnLease:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        with _active_users_lock:
            _active_users.discard(self.user_id)
        self._released = True

    def __enter__(self) -> TurnLease:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def acquire_user_turn(user_id: str) -> TurnLease:
    with _active_users_lock:
        if user_id in _active_users:
            raise UserTurnBusyError(user_id)
        _active_users.add(user_id)
    return TurnLease(user_id)


def reset_turn_guards_for_tests() -> None:
    with _active_users_lock:
        _active_users.clear()
