"""Strict image and archive validation before durable storage."""

from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image, UnidentifiedImageError

SUPPORTED_FORMATS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


class UploadRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    content: bytes
    display_name: str
    mime_type: str
    extension: str
    width: int
    height: int
    sha256: str


def safe_display_name(filename: str | None) -> str:
    name = (filename or "image").replace("\\", "/").split("/")[-1]
    name = _SAFE_FILENAME.sub("_", name).strip(" .")
    return (name[:255] or "image")


def sniff_image_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "WEBP"
    return None


def validate_image(
    content: bytes,
    filename: str | None,
    declared_content_type: str | None,
    *,
    max_bytes: int,
    max_pixels: int,
) -> ValidatedImage:
    if not content or len(content) > max_bytes:
        raise UploadRejected("image is empty or exceeds the byte limit")
    sniffed = sniff_image_format(content)
    if sniffed is None:
        raise UploadRejected("only decoded JPEG, PNG, and WebP images are supported")
    expected_mime, extension = SUPPORTED_FORMATS[sniffed]
    if declared_content_type and declared_content_type.lower() not in {expected_mime, "application/octet-stream"}:
        raise UploadRejected("declared content type does not match image bytes")
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != sniffed:
                raise UploadRejected("image signature and decoded format differ")
            if getattr(image, "n_frames", 1) != 1:
                raise UploadRejected("animated or multi-frame images are not supported")
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise UploadRejected("image exceeds the decoded pixel limit")
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise UploadRejected("image could not be decoded safely") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit
    return ValidatedImage(
        content=content,
        display_name=safe_display_name(filename),
        mime_type=expected_mime,
        extension=extension,
        width=width,
        height=height,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def validated_zip_images(
    content: bytes,
    *,
    max_archive_bytes: int,
    max_entries: int = 200,
    max_expanded_bytes: int = 200 * 1024 * 1024,
    max_ratio: int = 100,
) -> list[tuple[str, bytes]]:
    if not content or len(content) > max_archive_bytes:
        raise UploadRejected("archive is empty or exceeds the byte limit")
    result: list[tuple[str, bytes]] = []
    expanded = 0
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except (zipfile.BadZipFile, OSError) as exc:
        raise UploadRejected("invalid ZIP archive") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > max_entries:
            raise UploadRejected("archive has too many entries")
        for info in infos:
            path = PurePosixPath(info.filename.replace("\\", "/"))
            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                raise UploadRejected("encrypted archive entries are not supported")
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                raise UploadRejected("archive symbolic links are not supported")
            if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
                raise UploadRejected("archive entries must be flat safe filenames")
            if info.filename.lower().endswith((".zip", ".tar", ".gz", ".7z", ".rar")):
                raise UploadRejected("nested archives are not supported")
            if info.file_size < 0 or info.compress_size < 0:
                raise UploadRejected("invalid archive entry sizes")
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > max_ratio:
                raise UploadRejected("archive compression ratio exceeds the safety limit")
            expanded += info.file_size
            if expanded > max_expanded_bytes:
                raise UploadRejected("archive expands beyond the safety limit")
            data = archive.read(info)
            if sniff_image_format(data):
                result.append((safe_display_name(path.name), data))
    return result

