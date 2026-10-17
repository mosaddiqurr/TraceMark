"""Package the supplied brand and reproducible sample without changing the source logo."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from generate_dataset import SEED, texture
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    public = ROOT / "apps/web/public"
    brand = public / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    with Image.open(ROOT / "assets/logo-tracemark.png") as source:
        image = source.convert("RGBA")
    # The provided PNG has a large transparent canvas and near-transparent stray pixels.
    bounds = image.getchannel("A").point(lambda value: 255 if value > 8 else 0).getbbox()
    if bounds is None:
        raise ValueError("the supplied logo is empty")
    wordmark = image.crop((bounds[0] - 4, bounds[1] - 4, bounds[2] + 4, bounds[3] + 4))
    wordmark.thumbnail((950, 250), Image.Resampling.LANCZOS)
    wordmark.save(brand / "tracemark-logo.png", optimize=True)
    # Extract the existing circuit symbol for small-size favicons; do not redraw it.
    symbol = image.crop((32, 480, 378, 785))
    square = Image.new("RGBA", (370, 370))
    square.alpha_composite(symbol, ((370 - symbol.width) // 2, (370 - symbol.height) // 2))
    square.save(brand / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    square.resize((180, 180), Image.Resampling.LANCZOS).save(brand / "apple-touch-icon.png", optimize=True)
    sample = texture(768, 768, np.random.default_rng(SEED))
    values = np.asarray(sample).astype(np.float32) / 255
    # Tint the existing procedural fixture with the application's blue/aqua palette.
    rgb = np.stack((15 + values[..., 0] * 65, 55 + values[..., 1] * 155, 80 + values[..., 2] * 150), axis=2)
    Image.fromarray(rgb.astype(np.uint8)).save(public / "sample.png", optimize=True)
    print("Prepared supplied logo, circuit-symbol favicon and deterministic sample.")


if __name__ == "__main__":
    main()
