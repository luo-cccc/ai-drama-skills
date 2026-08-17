#!/usr/bin/env python3
"""Inspect raster deliverables and compose deterministic UTF-8 labels."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]


def pillow_modules():
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat
    except ImportError as exc:
        raise RuntimeError("Pillow is required for deterministic raster layout") from exc
    return Image, ImageChops, ImageDraw, ImageFont, ImageStat


def resolve_font(requested: str | None) -> Path | None:
    if requested:
        path = Path(requested).resolve()
        return path if path.is_file() else None
    return next((path for path in FONT_CANDIDATES if path.is_file()), None)


def capabilities(font: str | None = None) -> dict[str, Any]:
    try:
        pillow_modules()
        pillow = True
    except RuntimeError:
        pillow = False
    font_path = resolve_font(font)
    return {
        "pillow": pillow,
        "cjk_font": str(font_path) if font_path else None,
        "deterministic_layout": pillow and font_path is not None,
    }


def inspect_image(path: Path, expected_ratio: str | None = None, tolerance: float = 0.01) -> dict[str, Any]:
    Image, ImageChops, _, _, ImageStat = pillow_modules()
    with Image.open(path) as source:
        image = source.convert("RGB")
        width, height = image.size
        background = Image.new("RGB", image.size, image.getpixel((0, 0)))
        difference = ImageChops.difference(image, background)
        variance = sum(ImageStat.Stat(image.resize((min(width, 256), min(height, 256)))).var)
        nonblank = difference.getbbox() is not None and variance > 1
        result: dict[str, Any] = {"width": width, "height": height, "nonblank": nonblank}
        if expected_ratio:
            match = expected_ratio.split(":")
            if len(match) != 2 or not all(item.strip().isdigit() and int(item) > 0 for item in match):
                raise ValueError("expected ratio must use W:H with positive integers")
            target = int(match[0]) / int(match[1])
            actual = width / height
            result.update({"expected_ratio": expected_ratio, "actual_ratio": actual, "ratio_ok": abs(actual - target) / target <= tolerance})
        return result


def load_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("label specification must be an object")
    allowed = {"title", "asset_id", "font_size", "padding", "labels", "legend"}
    if set(spec) - allowed:
        raise ValueError(f"unknown label specification keys: {sorted(set(spec) - allowed)}")
    for key in ("title", "asset_id"):
        if not isinstance(spec.get(key, ""), str):
            raise ValueError(f"{key} must be a string")
    labels = spec.get("labels", [])
    if not isinstance(labels, list):
        raise ValueError("labels must be an array")
    for item in labels:
        if not isinstance(item, dict) or set(item) != {"text", "x", "y"}:
            raise ValueError("each label must contain only text, x, and y")
        if not isinstance(item["text"], str) or not all(isinstance(item[key], int) for key in ("x", "y")):
            raise ValueError("label text must be a string and x/y must be integer pixels")
    legend = spec.get("legend", [])
    if not isinstance(legend, list) or any(not isinstance(item, str) for item in legend):
        raise ValueError("legend must be an array of strings")
    return spec


def compose(input_path: Path, spec_path: Path, output_path: Path, font_path: Path) -> None:
    Image, _, ImageDraw, ImageFont, _ = pillow_modules()
    spec = load_spec(spec_path)
    size = int(spec.get("font_size", 32))
    padding = int(spec.get("padding", max(12, size // 2)))
    if not 8 <= size <= 256 or not 0 <= padding <= 512:
        raise ValueError("font_size or padding is outside supported range")
    font = ImageFont.truetype(str(font_path), size)
    small_font = ImageFont.truetype(str(font_path), max(12, round(size * 0.72)))
    with Image.open(input_path) as source:
        base = source.convert("RGB")
    header_lines = [value for value in (spec.get("title"), spec.get("asset_id")) if value]
    header_height = padding * 2 + size * len(header_lines) if header_lines else 0
    if header_height > base.height // 3:
        raise ValueError("title area exceeds one third of the image; reduce text or font size")
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    if header_height:
        draw.rectangle((0, 0, canvas.width, header_height), fill="white")
    y = padding
    for line in header_lines:
        draw.text((padding, y), line, fill="black", font=font)
        y += size
    for item in spec.get("labels", []):
        x, label_y = item["x"], item["y"]
        if not 0 <= x < base.width or not 0 <= label_y < canvas.height:
            raise ValueError(f"label is outside image bounds: {item}")
        box = draw.textbbox((x, label_y), item["text"], font=small_font, stroke_width=1)
        draw.rectangle((box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2), fill="white", outline="black")
        draw.text((x, label_y), item["text"], fill="black", font=small_font, stroke_width=1, stroke_fill="white")
    legend = spec.get("legend", [])
    if legend:
        legend_text = " | ".join(legend)
        box = draw.textbbox((padding, canvas.height - size), legend_text, font=small_font)
        draw.rectangle((0, box[1] - 4, canvas.width, canvas.height), fill="white")
        draw.text((padding, box[1]), legend_text, fill="black", font=small_font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower() or ".png"
    handle, temp_name = tempfile.mkstemp(prefix=f".{output_path.stem}.", suffix=suffix, dir=output_path.parent)
    os.close(handle)
    try:
        canvas.save(temp_name)
        os.replace(temp_name, output_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capability = sub.add_parser("capabilities")
    capability.add_argument("--font")
    verify = sub.add_parser("verify")
    verify.add_argument("--input", required=True)
    verify.add_argument("--expected-ratio")
    verify.add_argument("--tolerance", type=float, default=0.01)
    compose_parser = sub.add_parser("compose")
    compose_parser.add_argument("--input", required=True)
    compose_parser.add_argument("--labels", required=True)
    compose_parser.add_argument("--output", required=True)
    compose_parser.add_argument("--font")
    args = parser.parse_args()
    if args.command == "capabilities":
        print(json.dumps(capabilities(args.font), ensure_ascii=False, indent=2))
        return 0
    if args.command == "verify":
        result = inspect_image(Path(args.input), args.expected_ratio, args.tolerance)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["nonblank"] and result.get("ratio_ok", True) else 1
    font = resolve_font(args.font)
    if font is None:
        raise RuntimeError("no deterministic CJK font is available; use the unlettered-image fallback")
    compose(Path(args.input), Path(args.labels), Path(args.output), font)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
