from datetime import datetime, timedelta, timezone

import jwt

import config


def create_access_token(user_id: str) -> str:
    secret = config.JWT_SECRET or "dev-insecure-secret-change-me"
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=config.JWT_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, secret, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    secret = config.JWT_SECRET or "dev-insecure-secret-change-me"
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[config.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload")
    return str(user_id)
