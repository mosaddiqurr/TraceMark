"""Concise verification exports with authenticated JSON evidence snapshots."""

from __future__ import annotations

import hashlib
import hmac
import json
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore[import-untyped]


def seal(evidence: dict[str, Any], key: str) -> bytes:
    snapshot = {"schema_version": 1, "title": "TraceMark Verification Report", **evidence}
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    signature = hmac.new(key.encode(), canonical, hashlib.sha256).hexdigest()
    return json.dumps(
        {**snapshot, "authentication": {"scheme": "HMAC-SHA256", "key_version": 1, "signature": signature}},
        indent=2,
        ensure_ascii=True,
    ).encode()


def unseal(content: bytes, key: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = json.loads(content)
    authentication = snapshot.pop("authentication")
    if authentication.get("scheme") != "HMAC-SHA256" or authentication.get("key_version") != 1:
        raise ValueError("unsupported report authentication")
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    expected = hmac.new(key.encode(), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, authentication["signature"]):
        raise ValueError("report integrity check failed")
    return snapshot


def pdf(snapshot: dict[str, Any]) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=(595.28, 841.89),
        rightMargin=48,
        leftMargin=48,
        topMargin=42,
        bottomMargin=42,
        title="TraceMark Verification Report",
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontSize = 18
    styles["Title"].textColor = colors.HexColor("#102b48")
    body = ParagraphStyle("Evidence", fontName="Helvetica", fontSize=9, leading=13, spaceAfter=6)

    def text(value: object) -> str:
        # Built-in PDF fonts cover Latin-1; escape other characters visibly rather than lose them.
        safe = str(value).encode("latin-1", errors="backslashreplace").decode("latin-1")
        return escape(safe)

    file = snapshot["file"]
    watermark = snapshot["watermark"]
    visual = snapshot.get("visual")
    rows = [
        ("Result", "VERIFIED" if snapshot["verified"] else "NOT VERIFIED"),
        ("Finding", snapshot["classification"].replace("_", " ")),
        ("Identifier", snapshot["identifier"] or "No private identifier resolved"),
        ("Reference / recipient", snapshot["reference_label"] or "None"),
        ("Source file", snapshot["source_filename"] or "No private source resolved"),
        ("Submitted file", file["filename"]),
        *([("Found at", snapshot["source_url"])] if snapshot.get("source_url") else []),
        ("Image", f"{file['width']} x {file['height']} pixels; {file['media_type']}; {file['size_bytes']} bytes"),
        ("SHA-256", file["sha256"]),
        ("Watermark integrity", watermark["integrity_state"].replace("_", " ")),
        ("Exact hash", snapshot["exact_hash"]["kind"] or "No exact match"),
        (
            "Visual evidence",
            f"pHash distance {visual['phash_distance']}/64; ORB matches {visual['orb_match_count']}; RANSAC inliers {visual['ransac_inliers']}"
            if visual
            else "No private reference available",
        ),
        ("Provenance", snapshot["provenance"]["state"].replace("_", " ")),
        ("Verified at (UTC)", snapshot["created_at"]),
    ]
    table = Table([[Paragraph(text(k), body), Paragraph(text(v), body)] for k, v in rows], colWidths=[126, 373])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f2f7fa"), colors.white]),
            ]
        )
    )
    story = [
        Paragraph("TraceMark Verification Report", styles["Title"]),
        Spacer(1, 0.14 * inch),
        table,
        Spacer(1, 0.2 * inch),
        Paragraph("Limitations", styles["Heading2"]),
    ]
    story.extend(Paragraph(text(value), body) for value in snapshot["limitations"])
    story.append(
        Paragraph(
            "The JSON export contains the full evidence and a service-authenticated HMAC snapshot. This PDF is a readable summary.",
            body,
        )
    )
    document.build(story)
    return output.getvalue()
