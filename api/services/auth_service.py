from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import settings
from api.services.email_service import EmailServiceError, send_email
from api.services.sqlite_db import get_db_connection


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
security_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    user_id: int
    email: str
    is_vip: bool
    vip_valid_until: Optional[str]


class AuthServiceError(RuntimeError):
    """Domain-level auth error for safe user-facing messages."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _normalize_email(email: str) -> str:
    normalized = (email or "").strip().lower()
    if not EMAIL_RE.match(normalized):
        raise AuthServiceError("Invalid email format.")
    return normalized


def _hash_password(password: str) -> str:
    rounds = max(4, settings.password_bcrypt_rounds)
    encoded = password.encode("utf-8")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


def _require_jwt_secret() -> str:
    key = settings.jwt_secret_key.strip()
    if not key:
        raise AuthServiceError("JWT_SECRET_KEY is not configured.")
    return key


def create_access_token(*, user_id: int, email: str) -> str:
    secret = _require_jwt_secret()
    expire_at = _utc_now() + timedelta(minutes=max(5, settings.jwt_expire_minutes))
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(_utc_now().timestamp()),
        "exp": int(expire_at.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    secret = _require_jwt_secret()
    try:
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        if "sub" not in decoded:
            raise AuthServiceError("Invalid token payload.")
        return decoded
    except jwt.ExpiredSignatureError as exc:
        raise AuthServiceError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthServiceError("Invalid token.") from exc


def _query_membership(conn: sqlite3.Connection, user_id: int) -> tuple[bool, Optional[str]]:
    row = conn.execute(
        """
        SELECT valid_until
        FROM membership_entitlements
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return False, None
    valid_until = str(row["valid_until"])
    is_active = valid_until > _dt_to_db(_utc_now())
    return is_active, valid_until


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_expired(expires_at: str) -> bool:
    expires = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return expires <= _utc_now()


def _create_auth_token(*, user_id: int, email: str, purpose: str, expire_minutes: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _dt_to_db(_utc_now())
    expires_at = _dt_to_db(_utc_now() + timedelta(minutes=max(5, expire_minutes)))
    token_hash = _hash_token(token)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO auth_tokens(user_id, email, token_hash, purpose, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, token_hash, purpose, expires_at, now),
        )
    return token


def _build_action_link(token: str) -> str:
    base = settings.app_public_base_url.rstrip("/")
    return f"{base}/?action=reset_password&token={token}"


def _send_password_reset_email(email: str, token: str) -> None:
    link = _build_action_link(token)
    send_email(
        to_email=email,
        subject="[万能视频下载器] 密码重置",
        body=(
            "你好，\n\n"
            "请点击下面的链接重置密码（30分钟内有效）：\n"
            f"{link}\n\n"
            "如果不是你本人操作，请忽略此邮件。"
        ),
    )


def register_user(email: str, password: str) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    if len(password) < 8:
        raise AuthServiceError("Password must be at least 8 characters.")

    password_hash = _hash_password(password)
    now = _dt_to_db(_utc_now())
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO users(email, password_hash, is_active, email_verified, created_at, updated_at)
                VALUES (?, ?, 1, 1, ?, ?)
                """,
                (normalized_email, password_hash, now, now),
            )
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise AuthServiceError("Email already registered.") from exc

    return {"user_id": user_id, "email": normalized_email}


def request_password_reset(email: str) -> None:
    normalized_email = _normalize_email(email)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email
            FROM users
            WHERE email = ? AND is_active = 1
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()

    if not row:
        # Keep response generic to avoid account enumeration.
        return

    try:
        token = _create_auth_token(
            user_id=int(row["id"]),
            email=str(row["email"]),
            purpose="password_reset",
            expire_minutes=settings.password_reset_token_expire_minutes,
        )
        _send_password_reset_email(str(row["email"]), token)
    except EmailServiceError as exc:
        raise AuthServiceError(str(exc)) from exc


def reset_password(token: str, new_password: str) -> None:
    if len(new_password or "") < 8:
        raise AuthServiceError("Password must be at least 8 characters.")
    token_hash = _hash_token((token or "").strip())
    if not token_hash:
        raise AuthServiceError("Invalid reset token.")
    now = _dt_to_db(_utc_now())
    new_password_hash = _hash_password(new_password)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, expires_at, used_at
            FROM auth_tokens
            WHERE token_hash = ? AND purpose = 'password_reset'
            LIMIT 1
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            raise AuthServiceError("Reset token is invalid.")
        if row["used_at"]:
            raise AuthServiceError("Reset token already used.")
        if _token_expired(str(row["expires_at"])):
            raise AuthServiceError("Reset token has expired.")

        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_password_hash, now, int(row["user_id"])),
        )
        conn.execute(
            "UPDATE auth_tokens SET used_at = ? WHERE id = ?",
            (now, int(row["id"])),
        )


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, password_hash, is_active
            FROM users
            WHERE email = ?
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()

    if not row:
        raise AuthServiceError("Invalid email or password.")
    if int(row["is_active"]) != 1:
        raise AuthServiceError("Account is inactive.")
    if not _verify_password(password, str(row["password_hash"])):
        raise AuthServiceError("Invalid email or password.")

    user_id = int(row["id"])
    token = create_access_token(user_id=user_id, email=str(row["email"]))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": max(5, settings.jwt_expire_minutes),
        "user": {"user_id": user_id, "email": str(row["email"])},
    }


def get_user_by_id(user_id: int) -> AuthUser:
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, email_verified
            FROM users
            WHERE id = ? AND is_active = 1
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if not row:
            raise AuthServiceError("User not found.")
        is_vip, vip_valid_until = _query_membership(conn, user_id)
        return AuthUser(
            user_id=int(row["id"]),
            email=str(row["email"]),
            is_vip=is_vip,
            vip_valid_until=vip_valid_until,
        )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> AuthUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(str(payload["sub"]))
        return get_user_by_id(user_id)
    except AuthServiceError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
