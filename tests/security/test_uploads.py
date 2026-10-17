from __future__ import annotations

import zipfile
from io import BytesIO

import pytest
from PIL import Image
from tracemark_api.uploads import UploadRejected, safe_display_name, validate_image, validated_zip_images


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


def test_image_validation_uses_decoded_bytes_and_sanitizes_display_names() -> None:
    payload = _png()
    validated = validate_image(
        payload,
        "../../unsafe\r\nname.jpg",
        "application/octet-stream",
        max_bytes=1024 * 1024,
        max_pixels=10_000,
    )
    assert validated.mime_type == "image/png"
    assert validated.extension == "png"
    assert validated.display_name == "unsafe_name.jpg"
    assert safe_display_name('..\\..\\quote".png') == "quote_.png"


@pytest.mark.parametrize(
    ("payload", "declared_type", "max_pixels"),
    (
        (b"not an image", "image/png", 10_000),
        (b"\x89PNG\r\n\x1a\ncorrupt", "image/png", 10_000),
        (_png(), "image/jpeg", 10_000),
        (_png(), "image/png", 100),
    ),
    ids=("unsupported", "corrupt", "mismatched-mime", "pixel-limit"),
)
def test_image_validation_rejects_spoofed_corrupt_mismatched_or_oversized_content(
    payload: bytes, declared_type: str, max_pixels: int
) -> None:
    with pytest.raises(UploadRejected):
        validate_image(
            payload,
            "fixture.png",
            declared_type,
            max_bytes=1024 * 1024,
            max_pixels=max_pixels,
        )


@pytest.mark.parametrize(("format_name", "mime"), (("JPEG", "image/jpeg"), ("WEBP", "image/webp")))
def test_supported_still_formats_are_decoded(format_name: str, mime: str) -> None:
    output = BytesIO()
    Image.new("RGB", (32, 32), (20, 80, 140)).save(output, format=format_name)
    image = validate_image(output.getvalue(), "image", mime, max_bytes=1024 * 1024, max_pixels=10_000)
    assert image.mime_type == mime
    assert (image.width, image.height) == (32, 32)


def test_dimensions_animation_and_decompression_bombs_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(UploadRejected, match="dimension"):
        validate_image(_png(), "wide.png", "image/png", max_bytes=1024 * 1024, max_pixels=10_000, max_dimension=16)
    animated = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(
        animated, format="PNG", save_all=True, append_images=[Image.new("RGB", (32, 32), "red")], duration=100
    )
    with pytest.raises(UploadRejected, match="animated"):
        validate_image(animated.getvalue(), "animated.png", "image/png", max_bytes=1024 * 1024, max_pixels=10_000)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(UploadRejected, match="decoded safely"):
        validate_image(_png(), "bomb.png", "image/png", max_bytes=1024 * 1024, max_pixels=10_000)
