from contextlib import contextmanager
from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def set_user_id(user_id: str | None) -> None:
    current_user_id.set(user_id)


def require_user_id() -> str:
    uid = current_user_id.get()
    if not uid:
        raise RuntimeError(
            "user_id not set in request context; use user_scope() before DB access"
        )
    return uid


@contextmanager
def user_scope(user_id: str):
    token = current_user_id.set(user_id)
    try:
        yield user_id
    finally:
        current_user_id.reset(token)
