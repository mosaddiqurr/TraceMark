from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from tracemark_api.safe_fetch import validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/image.png",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/image.png",
        "http://user:pass@example.com/image.png",
    ],
)
def test_url_validator_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(HTTPException):
        validate_public_url(url)


def test_url_validator_accepts_only_public_resolution() -> None:
    records = [(2, 1, 6, "", ("93.184.216.34", 443))]
    with patch("socket.getaddrinfo", return_value=records):
        host, addresses = validate_public_url("https://example.test/image.png")
    assert host == "example.test"
    assert addresses == ("93.184.216.34",)
