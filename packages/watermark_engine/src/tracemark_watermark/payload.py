"""Authenticated opaque TraceMark watermark payload.

Wire format (38 bytes before error correction)::

    magic[2] | payload_version[1] | payload_type[1] | algorithm_version[1]
    | key_version[1] | token[16] | crc32[4] | hmac_sha256[12]

RS(58,38) adds 20 parity bytes.  A deterministic key-derived permutation
spreads adjacent codeword symbols before embedding.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum

from reedsolo import ReedSolomonError, RSCodec  # type: ignore[import-untyped]

from .crypto import derive_subkey, deterministic_seed

MAGIC = b"TM"
PAYLOAD_VERSION = 1
RAW_PAYLOAD_BYTES = 38
CODEWORD_BYTES = 58
ECC_BYTES = CODEWORD_BYTES - RAW_PAYLOAD_BYTES
TOKEN_BYTES = 16
TAG_BYTES = 12
_HEADER = struct.Struct(">2sBBBB16s")
_CRC = struct.Struct(">I")
_RS = RSCodec(ECC_BYTES, nsize=255)


class PayloadType(IntEnum):
    OWNERSHIP = 1
    DISTRIBUTION = 2


class PayloadError(ValueError):
    """Base class for malformed or unauthentic watermark payloads."""


class PayloadCorrectionError(PayloadError):
    """The Reed-Solomon codeword could not be recovered."""


class PayloadIntegrityError(PayloadError):
    """The payload was recovered but CRC or HMAC validation failed."""


@dataclass(frozen=True, slots=True)
class WatermarkPayload:
    payload_type: PayloadType
    algorithm_version: int
    key_version: int
    token: bytes
    payload_version: int = PAYLOAD_VERSION

    def __post_init__(self) -> None:
        if len(self.token) != TOKEN_BYTES:
            raise PayloadError("token must be exactly 128 bits")
        for name, value in (
            ("payload_version", self.payload_version),
            ("algorithm_version", self.algorithm_version),
            ("key_version", self.key_version),
        ):
            if not 0 <= value <= 255:
                raise PayloadError(f"{name} must fit in one byte")


@dataclass(frozen=True, slots=True)
class DecodedPayload:
    payload: WatermarkPayload
    corrected_symbols: int


def _permutation(master_key: bytes, key_version: int) -> list[int]:
    key = derive_subkey(master_key, "payload-interleave", key_version=key_version)
    values = list(range(CODEWORD_BYTES))
    random.Random(deterministic_seed(key, b"RS(58,38)")).shuffle(values)
    return values


def _interleave(codeword: bytes, master_key: bytes, key_version: int) -> bytes:
    order = _permutation(master_key, key_version)
    return bytes(codeword[index] for index in order)


def _deinterleave(data: bytes, master_key: bytes, key_version: int) -> bytes:
    order = _permutation(master_key, key_version)
    restored = bytearray(CODEWORD_BYTES)
    for shuffled_index, original_index in enumerate(order):
        restored[original_index] = data[shuffled_index]
    return bytes(restored)


def encode_payload(payload: WatermarkPayload, master_key: bytes) -> bytes:
    """Authenticate, RS-encode, and deterministically interleave a payload."""

    header = _HEADER.pack(
        MAGIC,
        payload.payload_version,
        int(payload.payload_type),
        payload.algorithm_version,
        payload.key_version,
        payload.token,
    )
    crc = _CRC.pack(zlib.crc32(header) & 0xFFFFFFFF)
    auth_key = derive_subkey(
        master_key, "payload-authentication", key_version=payload.key_version
    )
    tag = hmac.new(auth_key, header + crc, hashlib.sha256).digest()[:TAG_BYTES]
    raw = header + crc + tag
    if len(raw) != RAW_PAYLOAD_BYTES:  # defensive wire-format invariant
        raise AssertionError("payload wire format changed unexpectedly")
    encoded = bytes(_RS.encode(raw))
    return _interleave(encoded, master_key, payload.key_version)


def decode_payload(
    codeword: bytes,
    master_key: bytes,
    *,
    key_version: int,
) -> DecodedPayload:
    """Recover and authenticate a codeword for one candidate key version.

    Callers must never use token data when this function raises.  In particular,
    successful CRC validation alone is deliberately insufficient.
    """

    if len(codeword) != CODEWORD_BYTES:
        raise PayloadCorrectionError(f"codeword must be {CODEWORD_BYTES} bytes")
    deinterleaved = _deinterleave(codeword, master_key, key_version)
    try:
        decoded_result = _RS.decode(deinterleaved)
    except (ReedSolomonError, IndexError, ValueError) as exc:
        raise PayloadCorrectionError("Reed-Solomon correction failed") from exc
    raw = bytes(decoded_result[0])
    errata = decoded_result[2] if len(decoded_result) > 2 else ()
    if len(raw) != RAW_PAYLOAD_BYTES:
        raise PayloadCorrectionError("unexpected decoded payload length")

    header = raw[: _HEADER.size]
    crc_bytes = raw[_HEADER.size : _HEADER.size + _CRC.size]
    supplied_tag = raw[-TAG_BYTES:]
    expected_crc = zlib.crc32(header) & 0xFFFFFFFF
    if not hmac.compare_digest(crc_bytes, _CRC.pack(expected_crc)):
        raise PayloadIntegrityError("payload CRC validation failed")

    magic, payload_version, raw_type, algorithm_version, embedded_version, token = (
        _HEADER.unpack(header)
    )
    auth_key = derive_subkey(
        master_key, "payload-authentication", key_version=key_version
    )
    expected_tag = hmac.new(auth_key, header + crc_bytes, hashlib.sha256).digest()[
        :TAG_BYTES
    ]
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise PayloadIntegrityError("payload HMAC validation failed")
    if magic != MAGIC or payload_version != PAYLOAD_VERSION:
        raise PayloadIntegrityError("unsupported payload header")
    if embedded_version != key_version:
        raise PayloadIntegrityError("embedded key version does not match candidate")
    try:
        payload_type = PayloadType(raw_type)
    except ValueError as exc:
        raise PayloadIntegrityError("unknown payload type") from exc
    return DecodedPayload(
        payload=WatermarkPayload(
            payload_type=payload_type,
            algorithm_version=algorithm_version,
            key_version=embedded_version,
            token=token,
            payload_version=payload_version,
        ),
        corrected_symbols=len(errata),
    )

