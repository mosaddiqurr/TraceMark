"""Run a repeatable local TraceMark robustness benchmark."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import perf_counter

from PIL import Image
from tracemark_watermark import (
    LSBWatermarkEngine,
    PayloadType,
    RobustWatermarkEngine,
    WatermarkPayload,
    measure_quality,
)

KEY = b"TraceMark deterministic local benchmark key v1"
SEED = 20260720


def transformed(image: Image.Image, attack: str) -> Image.Image:
    if attack == "clean":
        return image.copy()
    if attack.startswith("jpeg"):
        quality = int(attack.removeprefix("jpeg"))
        stream = BytesIO()
        image.convert("RGB").save(stream, format="JPEG", quality=quality)
        return Image.open(BytesIO(stream.getvalue())).copy()
    if attack == "resize75":
        smaller = image.resize(
            (int(image.width * 0.75), int(image.height * 0.75)),
            Image.Resampling.LANCZOS,
        )
        return smaller
    raise ValueError(attack)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("quick", "standard"), default="quick")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/generated"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark-results.json"))
    args = parser.parse_args()

    attacks = ["clean", "jpeg85", "resize75"]
    if args.profile == "standard":
        attacks.extend(["jpeg60"])
    paths = sorted(
        path for path in args.dataset.iterdir() if path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if args.profile == "quick":
        paths = paths[:2]

    records: list[dict[str, object]] = []
    negatives = {"robust": 0, "lsb": 0}
    engines = {
        "robust": (RobustWatermarkEngine(), 2),
        "lsb": (LSBWatermarkEngine(), 1),
    }
    for path in paths:
        original = Image.open(path).copy()
        for name, (engine, algorithm_version) in engines.items():
            negative = engine.extract(original, KEY, key_versions=[1])
            negatives[name] += int(negative.valid)
            token = sha256(f"{path.name}:{name}:{SEED}".encode()).digest()[:16]
            payload = WatermarkPayload(PayloadType.OWNERSHIP, algorithm_version, 1, token)
            protected = engine.embed(original, payload, KEY).image
            for attack in attacks:
                candidate = transformed(protected, attack)
                started = perf_counter()
                result = engine.extract(candidate, KEY, key_versions=[1])
                duration_ms = (perf_counter() - started) * 1000
                quality = None
                if candidate.size == protected.size:
                    measured = measure_quality(protected, candidate)
                    quality = {
                        "ssim": measured.ssim if math.isfinite(measured.ssim) else None,
                        "psnr_db": measured.psnr_db if math.isfinite(measured.psnr_db) else None,
                    }
                records.append(
                    {
                        "image": path.name,
                        "engine": name,
                        "attack": attack,
                        "detected": result.valid,
                        "integrity_valid": result.valid,
                        "corrected_symbols": result.corrected_symbols,
                        "repetitions_found": result.repetitions_found,
                        "duration_ms": duration_ms,
                        "quality": quality,
                        "failure_reason": result.integrity_error,
                    }
                )

    grouped: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"detected": 0, "total": 0})
    )
    for record in records:
        cell = grouped[str(record["engine"])][str(record["attack"])]
        cell["total"] += 1
        cell["detected"] += int(bool(record["detected"]))
    summary = {
        engine: {
            attack: {**counts, "survival_rate": counts["detected"] / counts["total"]}
            for attack, counts in attacks_summary.items()
        }
        for engine, attacks_summary in grouped.items()
    }
    output = {
        "schema_version": 1,
        "profile": args.profile,
        "seed": SEED,
        "dataset_files": [path.name for path in paths],
        "negative_false_positives": negatives,
        "summary": summary,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": summary, "negative_false_positives": negatives}, indent=2))


if __name__ == "__main__":
    main()
