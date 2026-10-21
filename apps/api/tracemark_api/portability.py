"""Signed export and import of a workspace's private trace records.

An export lets a person move their private labels to another browser or keep
a backup beyond the cookie's lifetime.  The file is authenticated with a
domain-separated HMAC so imports cannot inject crafted descriptors, and it is
a bearer secret: anyone holding it can resolve those marks on this deployment.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any
from uuid import UUID

EXPORT_KIND = "tracemark-trace-export"
EXPORT_VERSION = 1
MAX_EXPORT_BYTES = 2 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN = b"tracemark/trace-export/v1\x00"


class ImportRejected(ValueError):
    pass


def _signature(body: dict[str, Any], key: str) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hmac.new(key.encode(), _DOMAIN + canonical, hashlib.sha256).hexdigest()


def seal(traces: list[dict[str, Any]], exported_at: str, key: str) -> bytes:
    body = {"kind": EXPORT_KIND, "version": EXPORT_VERSION, "exported_at": exported_at, "traces": traces}
    return json.dumps(
        {**body, "authentication": {"scheme": "HMAC-SHA256", "signature": _signature(body, key)}},
        indent=2,
        ensure_ascii=True,
    ).encode()


def _validated_trace(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ImportRejected("a trace record is malformed")
    try:
        identifier = str(UUID(str(item["id"])))
        source_name = str(item["source_name"])[:255] or "image"
        label = item.get("reference_label")
        payload_type = item["payload_type"]
        source_sha256 = item["source_sha256"]
        output_sha256 = item["output_sha256"]
        descriptor = item["descriptor"]
        created_at = float(item["created_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ImportRejected("a trace record is malformed") from exc
    if label is not None and (not isinstance(label, str) or len(label) > 120):
        raise ImportRejected("a trace label is invalid")
    if payload_type not in {"ownership", "distribution"}:
        raise ImportRejected("a trace type is invalid")
    if not all(isinstance(v, str) and _SHA256.match(v) for v in (source_sha256, output_sha256)):
        raise ImportRejected("a trace hash is invalid")
    if not isinstance(descriptor, dict):
        raise ImportRejected("a trace descriptor is invalid")
    return {
        "id": identifier,
        "source_name": source_name,
        "reference_label": label,
        "payload_type": payload_type,
        "source_sha256": source_sha256,
        "output_sha256": output_sha256,
        "descriptor": descriptor,
        "created_at": created_at,
    }


def unseal(content: bytes, key: str) -> list[dict[str, Any]]:
    if len(content) > MAX_EXPORT_BYTES:
        raise ImportRejected("the export file is too large")
    try:
        document = json.loads(content)
        authentication = document.pop("authentication")
        signature = authentication["signature"]
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ImportRejected("this is not a TraceMark trace export") from exc
    if document.get("kind") != EXPORT_KIND or document.get("version") != EXPORT_VERSION:
        raise ImportRejected("this is not a supported TraceMark trace export")
    if authentication.get("scheme") != "HMAC-SHA256" or not isinstance(signature, str):
        raise ImportRejected("the export authentication is unsupported")
    if not hmac.compare_digest(_signature(document, key), signature):
        raise ImportRejected("the export was modified or belongs to another TraceMark deployment")
    traces = document.get("traces")
    if not isinstance(traces, list):
        raise ImportRejected("the export contains no trace list")
    return [_validated_trace(item) for item in traces]
