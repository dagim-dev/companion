from datetime import datetime, timedelta, timezone

import jwt

import config

LOCAL_DEV_JWT_SECRET = "local-dev-secret"


def get_jwt_secret() -> str:
    if config.JWT_SECRET:
        return config.JWT_SECRET
    if config.ENV == "development":
        return LOCAL_DEV_JWT_SECRET
    raise RuntimeError("JWT_SECRET is not configured")


def create_access_token(user_id: str) -> str:
    secret = get_jwt_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, secret, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[config.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload")
    return str(user_id)
