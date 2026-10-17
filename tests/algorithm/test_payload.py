from __future__ import annotations

import os

import pytest
from tracemark_watermark import (
    CODEWORD_BYTES,
    PayloadError,
    PayloadType,
    WatermarkPayload,
    decode_payload,
    encode_payload,
)

MASTER_KEY = bytes(range(32))


def test_payload_round_trip_has_fixed_rs_58_38_shape() -> None:
    payload = WatermarkPayload(
        payload_type=PayloadType.DISTRIBUTION,
        algorithm_version=2,
        key_version=7,
        token=bytes.fromhex("00112233445566778899aabbccddeeff"),
    )

    codeword = encode_payload(payload, MASTER_KEY)
    decoded = decode_payload(codeword, MASTER_KEY, key_version=7)

    assert len(codeword) == CODEWORD_BYTES == 58
    assert decoded.payload == payload
    assert decoded.corrected_symbols == 0


def test_payload_corrects_ten_corrupt_symbols() -> None:
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 1, 3, os.urandom(16))
    damaged = bytearray(encode_payload(payload, MASTER_KEY))
    for index in (0, 3, 7, 12, 18, 25, 31, 39, 48, 57):
        damaged[index] ^= 0xA5

    decoded = decode_payload(bytes(damaged), MASTER_KEY, key_version=3)

    assert decoded.payload == payload
    assert decoded.corrected_symbols == 10


def test_payload_rejects_wrong_key_and_wrong_candidate_version() -> None:
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 1, 3, os.urandom(16))
    codeword = encode_payload(payload, MASTER_KEY)

    with pytest.raises(PayloadError):
        decode_payload(codeword, b"x" * 32, key_version=3)
    with pytest.raises(PayloadError):
        decode_payload(codeword, MASTER_KEY, key_version=4)


def test_payload_refuses_non_opaque_token_size() -> None:
    with pytest.raises(PayloadError, match="128 bits"):
        WatermarkPayload(PayloadType.OWNERSHIP, 1, 1, b"too-short")
