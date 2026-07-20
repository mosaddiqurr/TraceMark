"""Small, auditable key-derivation helpers.

The application supplies a high-entropy master key.  Derived keys are scoped by
purpose and key version so a key used for pixel placement is never reused for
payload or report authentication.
"""

from __future__ import annotations

import hashlib
import hmac


class KeyMaterialError(ValueError):
    """Raised when key material or a key version is unsafe."""


def _validate(master_key: bytes, key_version: int) -> None:
    if len(master_key) < 32:
        raise KeyMaterialError("master keys must contain at least 32 bytes")
    if not 0 <= key_version <= 255:
        raise KeyMaterialError("key_version must fit in one byte")


def hkdf_sha256(
    input_key: bytes,
    *,
    salt: bytes,
    info: bytes,
    length: int = 32,
) -> bytes:
    """RFC 5869 HKDF-SHA-256 without requiring an external crypto runtime."""

    if length <= 0 or length > 255 * hashlib.sha256().digest_size:
        raise ValueError("invalid HKDF output length")
    prk = hmac.new(salt, input_key, hashlib.sha256).digest()
    output = bytearray()
    previous = b""
    counter = 1
    while len(output) < length:
        previous = hmac.new(
            prk, previous + info + bytes((counter,)), hashlib.sha256
        ).digest()
        output.extend(previous)
        counter += 1
    return bytes(output[:length])


def derive_subkey(
    master_key: bytes,
    purpose: str,
    *,
    key_version: int,
    length: int = 32,
) -> bytes:
    """Derive a domain-separated, versioned TraceMark subkey."""

    _validate(master_key, key_version)
    if not purpose or not purpose.isascii():
        raise KeyMaterialError("purpose must be non-empty ASCII")
    return hkdf_sha256(
        master_key,
        salt=b"TraceMark/HKDF-SHA256/v1" + bytes((key_version,)),
        info=b"TraceMark/" + purpose.encode("ascii") + b"/v1",
        length=length,
    )


def deterministic_seed(key: bytes, context: bytes) -> int:
    """Return a stable 64-bit seed suitable for a local PRNG."""

    return int.from_bytes(hmac.new(key, context, hashlib.sha256).digest()[:8], "big")

