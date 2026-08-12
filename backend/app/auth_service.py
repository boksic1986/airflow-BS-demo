from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuditLog, AuthSession, UserAccount


ROLES = {"viewer", "operator", "admin"}
ROLE_LEVEL = {"viewer": 1, "operator": 2, "admin": 3}
PASSWORD_N = 2**14
PASSWORD_R = 8
PASSWORD_P = 1


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    role: str
    csrf_token: str


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=PASSWORD_N, r=PASSWORD_R, p=PASSWORD_P)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derived).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_value, hash_value = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(hash_value.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(*, session: Session, username: str, password: str, ttl_hours: int = 8) -> tuple[AuthenticatedUser, str]:
    account = session.scalar(select(UserAccount).where(UserAccount.username == username))
    if account is None or not account.enabled or not verify_password(password, account.password_hash):
        raise ValueError("Invalid username or password.")
    raw_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    session.add(
        AuthSession(
            user_id=account.id,
            token_hash=_token_hash(raw_token),
            csrf_token=csrf_token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=max(1, ttl_hours)),
        )
    )
    session.commit()
    return AuthenticatedUser(account.id, account.username, account.role, csrf_token), raw_token


def authenticate_session(*, session: Session, raw_token: str | None) -> AuthenticatedUser | None:
    if not raw_token:
        return None
    row = session.execute(
        select(AuthSession, UserAccount)
        .join(UserAccount, UserAccount.id == AuthSession.user_id)
        .where(AuthSession.token_hash == _token_hash(raw_token), UserAccount.enabled.is_(True))
    ).first()
    if row is None:
        return None
    auth_session, account = row
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        session.delete(auth_session)
        session.commit()
        return None
    return AuthenticatedUser(account.id, account.username, account.role, auth_session.csrf_token)


def revoke_session(*, session: Session, raw_token: str | None) -> None:
    if raw_token:
        session.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(raw_token)))
        session.commit()


def require_role(user: AuthenticatedUser, minimum: str) -> None:
    if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL[minimum]:
        raise PermissionError(f"Role {minimum} or higher is required.")


def create_user(*, session: Session, username: str, password: str, role: str) -> UserAccount:
    username = username.strip()
    if not username or len(username) > 128:
        raise ValueError("Username is required and must not exceed 128 characters.")
    if role not in ROLES:
        raise ValueError("Role must be viewer, operator, or admin.")
    if session.scalar(select(UserAccount).where(UserAccount.username == username)) is not None:
        raise ValueError("Username already exists.")
    account = UserAccount(username=username, password_hash=hash_password(password), role=role)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def list_users(*, session: Session) -> list[dict[str, object]]:
    return [
        {"id": row.id, "username": row.username, "role": row.role, "enabled": row.enabled, "created_at": row.created_at.isoformat()}
        for row in session.scalars(select(UserAccount).order_by(UserAccount.username)).all()
    ]


def audit(*, session: Session, username: str | None, action: str, analysis_id: str | None = None, payload: dict | None = None) -> None:
    session.add(AuditLog(username=username, action=action, analysis_id=analysis_id, payload_json=payload or {}))
    session.commit()


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

