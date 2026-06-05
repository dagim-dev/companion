import uuid
from datetime import datetime

from passlib.context import CryptContext

from memory import get_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_user(email: str, password: str) -> dict:
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    created_at = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, email.lower().strip(), password_hash, created_at),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()

    return {"id": user_id, "email": email.lower().strip(), "created_at": created_at}


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
        (email.lower().strip(),),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, email, password_hash, created_at, onboarding_completed
            FROM users WHERE id = ?
            """,
            (user_id,),
        )
    except Exception:
        cursor.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE id = ?",
            (user_id,),
        )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    keys = row.keys() if hasattr(row, "keys") else []
    onboarding = 0
    if "onboarding_completed" in keys:
        onboarding = row["onboarding_completed"]
    return {
        "id": row["id"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "created_at": row["created_at"],
        "onboarding_completed": bool(onboarding),
    }
