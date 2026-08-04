import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import (
    Analysis,
    CategoryLearning,
    LoginThrottle,
    Statement,
    Transaction,
    User,
    UserSession,
)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SESSION_HOURS = 24 * 7
LOGIN_WINDOW_MINUTES = 15
MAX_LOGIN_FAILURES = 5
DUMMY_PASSWORD_HASH = (
    "scrypt$16384$8$1$00000000000000000000000000000000$"
    "b50ff693c9f9f34c5c2f5bbf6f557bddf031815b03740f1f362e5665f7f2cbbb"
)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address")
    return normalized


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters")


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(derived.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_session(db: Session, user: User) -> str:
    db.query(UserSession).filter(
        UserSession.expires_at <= datetime.now(timezone.utc)
    ).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS),
        )
    )
    db.flush()
    return token


def user_for_session(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = (
        db.query(UserSession)
        .filter(UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest())
        .first()
    )
    if not session:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session.user


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.query(UserSession).filter(
        UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
    ).delete()
    db.commit()


def login_allowed(db: Session, email: str) -> bool:
    key = hashlib.sha256(email.encode()).hexdigest()
    throttle = (
        db.query(LoginThrottle).filter(LoginThrottle.identifier_hash == key).first()
    )
    if not throttle:
        return True
    now = datetime.now(timezone.utc)
    locked_until = throttle.locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return not locked_until or locked_until <= now


def record_login_failure(db: Session, email: str) -> None:
    key = hashlib.sha256(email.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    throttle = (
        db.query(LoginThrottle).filter(LoginThrottle.identifier_hash == key).first()
    )
    if not throttle:
        throttle = LoginThrottle(
            identifier_hash=key, failure_count=1, window_started_at=now
        )
        db.add(throttle)
    else:
        started = throttle.window_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started + timedelta(minutes=LOGIN_WINDOW_MINUTES) <= now:
            throttle.failure_count = 1
            throttle.window_started_at = now
            throttle.locked_until = None
        else:
            throttle.failure_count += 1
    if throttle.failure_count >= MAX_LOGIN_FAILURES:
        throttle.locked_until = now + timedelta(minutes=LOGIN_WINDOW_MINUTES)
    db.commit()


def clear_login_failures(db: Session, email: str) -> None:
    db.query(LoginThrottle).filter(
        LoginThrottle.identifier_hash == hashlib.sha256(email.encode()).hexdigest()
    ).delete()
    db.flush()


def claim_legacy_data(db: Session, user_id: int) -> None:
    """Assign pre-account data to the first registered account."""
    for model in (Statement, Transaction, Analysis, CategoryLearning):
        db.query(model).filter(model.user_id.is_(None)).update(
            {model.user_id: user_id}, synchronize_session=False
        )
