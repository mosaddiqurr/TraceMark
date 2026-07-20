"""Optional visible text/logo compositor with explicit alpha handling."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True, slots=True)
class VisibleWatermarkOptions:
    opacity: int = 112
    margin: int = 16
    position: str = "bottom-right"
    scale: float = 0.18

    def __post_init__(self) -> None:
        if not 0 <= self.opacity <= 255:
            raise ValueError("opacity must be between 0 and 255")
        if self.margin < 0:
            raise ValueError("margin cannot be negative")
        if not 0.01 <= self.scale <= 1.0:
            raise ValueError("scale must be between 0.01 and 1.0")


def _position(canvas: tuple[int, int], overlay: tuple[int, int], options: VisibleWatermarkOptions) -> tuple[int, int]:
    width, height = canvas
    mark_width, mark_height = overlay
    positions = {
        "top-left": (options.margin, options.margin),
        "top-right": (width - mark_width - options.margin, options.margin),
        "bottom-left": (options.margin, height - mark_height - options.margin),
        "bottom-right": (
            width - mark_width - options.margin,
            height - mark_height - options.margin,
        ),
        "center": ((width - mark_width) // 2, (height - mark_height) // 2),
    }
    if options.position not in positions:
        raise ValueError("unsupported visible watermark position")
    x, y = positions[options.position]
    return max(0, int(x)), max(0, int(y))


def add_visible_text(
    image: Image.Image,
    text: str,
    *,
    options: VisibleWatermarkOptions | None = None,
) -> Image.Image:
    if not text or len(text) > 200 or any(ord(character) < 32 for character in text):
        raise ValueError("visible watermark text must be 1-200 printable characters")
    settings = options or VisibleWatermarkOptions()
    base = image.convert("RGBA")
    original_alpha = base.getchannel("A").copy() if "A" in image.getbands() else None
    font = ImageFont.load_default(size=max(10, int(min(image.size) * settings.scale / 2)))
    probe = ImageDraw.Draw(base)
    bounds = probe.textbbox((0, 0), text, font=font, stroke_width=1)
    mark_size = (int(bounds[2] - bounds[0] + 12), int(bounds[3] - bounds[1] + 10))
    mark = Image.new("RGBA", mark_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(mark)
    draw.rounded_rectangle((0, 0, mark.width - 1, mark.height - 1), radius=4, fill=(0, 0, 0, settings.opacity))
    draw.text((6, 4 - bounds[1]), text, font=font, fill=(255, 255, 255, settings.opacity), stroke_width=1)
    base.alpha_composite(mark, _position(base.size, mark.size, settings))
    if original_alpha is not None:
        base.putalpha(original_alpha)
    return base if "A" in image.getbands() else base.convert("RGB")


def add_visible_logo(
    image: Image.Image,
    logo: Image.Image,
    *,
    options: VisibleWatermarkOptions | None = None,
) -> Image.Image:
    settings = options or VisibleWatermarkOptions()
    base = image.convert("RGBA")
    original_alpha = base.getchannel("A").copy() if "A" in image.getbands() else None
    mark = logo.convert("RGBA")
    maximum_width = max(1, int(base.width * settings.scale))
    if mark.width > maximum_width:
        ratio = maximum_width / mark.width
        mark = mark.resize(
            (maximum_width, max(1, int(mark.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    alpha = mark.getchannel("A").point(lambda value: value * settings.opacity // 255)
    mark.putalpha(alpha)
    base.alpha_composite(mark, _position(base.size, mark.size, settings))
    if original_alpha is not None:
        base.putalpha(original_alpha)
    return base if "A" in image.getbands() else base.convert("RGB")

