"""Credential hashing and normalization."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if len(normalized) > 320 or not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("invalid email address")
    return normalized


def validate_password(password: str) -> None:
    if len(password) < 12 or len(password) > 1024:
        raise ValueError("password must be between 12 and 1024 characters")


def hash_password(password: str) -> str:
    validate_password(password)
    return _hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(encoded: str) -> bool:
    try:
        return _hasher.check_needs_rehash(encoded)
    except InvalidHashError:
        return True

