"""Private object storage interfaces with randomized server-controlled keys."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

ALLOWED_BUCKETS = frozenset({"originals", "protected", "temporary", "thumbnails", "benchmarks", "reports"})


def new_object_key(suffix: str = "bin") -> str:
    clean_suffix = suffix.lower().lstrip(".")
    if not clean_suffix.isalnum() or len(clean_suffix) > 10:
        clean_suffix = "bin"
    token = secrets.token_hex(24)
    return f"{token[:2]}/{token[2:4]}/{token}.{clean_suffix}"


class ObjectStorage(Protocol):
    def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, bucket: str, key: str) -> bytes: ...
    def delete(self, bucket: str, key: str) -> None: ...


def _check_bucket(bucket: str) -> None:
    if bucket not in ALLOWED_BUCKETS:
        raise ValueError("unknown private storage bucket")


def _check_key(key: str) -> None:
    path = Path(key)
    if path.is_absolute() or ".." in path.parts or "\\" in key or not key:
        raise ValueError("unsafe object key")


@dataclass(slots=True)
class LocalObjectStorage:
    root: Path

    def _path(self, bucket: str, key: str) -> Path:
        _check_bucket(bucket)
        _check_key(key)
        root = self.root.resolve()
        target = (root / bucket / Path(key)).resolve()
        if root not in target.parents:
            raise ValueError("object path escapes storage root")
        return target

    def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        del content_type
        target = self._path(bucket, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get(self, bucket: str, key: str) -> bytes:
        return self._path(bucket, key).read_bytes()

    def delete(self, bucket: str, key: str) -> None:
        try:
            self._path(bucket, key).unlink()
        except FileNotFoundError:
            pass


class MinioObjectStorage:
    def __init__(self, client: object):
        self.client = client

    def ensure_buckets(self) -> None:
        for bucket in ALLOWED_BUCKETS:
            if not self.client.bucket_exists(bucket):  # type: ignore[attr-defined]
                self.client.make_bucket(bucket)  # type: ignore[attr-defined]

    def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        _check_bucket(bucket)
        _check_key(key)
        self.client.put_object(  # type: ignore[attr-defined]
            bucket, key, BytesIO(data), len(data), content_type=content_type
        )

    def get(self, bucket: str, key: str) -> bytes:
        _check_bucket(bucket)
        _check_key(key)
        response = self.client.get_object(bucket, key)  # type: ignore[attr-defined]
        try:
            return bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    def delete(self, bucket: str, key: str) -> None:
        _check_bucket(bucket)
        _check_key(key)
        self.client.remove_object(bucket, key)  # type: ignore[attr-defined]

