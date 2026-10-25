"""Tokens and hashing."""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_pin(pin: str) -> str:
    return _hasher.hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    try:
        return _hasher.verify(pin_hash, pin)
    except (VerificationError, InvalidHashError):
        return False


def _hmac(value: str) -> str:
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def hash_otp(phone: str, code: str) -> str:
    # Bound to the phone so a hash can't be replayed for another number.
    return _hmac(f"otp:{phone}:{code}")


def otp_matches(code_hash: str, phone: str, code: str) -> bool:
    return hmac.compare_digest(code_hash, hash_otp(phone, code))


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return _hmac(f"refresh:{token}")


def create_access_token(claims: dict[str, Any]) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=s.access_token_minutes)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), s.access_token_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    s = get_settings()
    payload: dict[str, Any] = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def create_otp_ticket(phone: str) -> str:
    """Short-lived token proving the phone passed OTP; exchanged for a role session."""
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": phone,
        "typ": "otp_ticket",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_otp_ticket(ticket: str) -> str:
    s = get_settings()
    payload = jwt.decode(ticket, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if payload.get("typ") != "otp_ticket":
        raise jwt.InvalidTokenError("wrong token type")
    return str(payload["sub"])


def mask_phone(phone: str) -> str:
    return "*" * max(len(phone) - 4, 0) + phone[-4:]
