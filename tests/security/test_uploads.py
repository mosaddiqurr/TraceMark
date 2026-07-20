from __future__ import annotations

import zipfile
from io import BytesIO

import pytest
from PIL import Image
from tracemark_api.uploads import UploadRejected, validated_zip_images


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), (20, 80, 140)).save(output, format="PNG")
    return output.getvalue()


def _archive(name: str, payload: bytes) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return output.getvalue()


def test_zip_image_is_extracted_once_with_complete_bytes() -> None:
    payload = _png()
    result = validated_zip_images(_archive("fixture.png", payload), max_archive_bytes=1024 * 1024)
    assert result == [("fixture.png", payload)]


@pytest.mark.parametrize("name", ("../escape.png", "nested/fixture.png", "archive.zip"))
def test_zip_rejects_unsafe_or_nested_entries(name: str) -> None:
    with pytest.raises(UploadRejected):
        validated_zip_images(_archive(name, _png()), max_archive_bytes=1024 * 1024)