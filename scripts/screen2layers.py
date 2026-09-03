#!/usr/bin/env python3
"""
screen2layers: Convert a flat UI screenshot into a Figma-ready layered kit.

Dependencies: Pillow and numpy.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class Box:
    name: str
    kind: str
    x: int
    y: int
    w: int
    h: int
    score: float = 1.0

    @property
    def area(self) -> int:
        return max(0, self.w) * max(0, self.h)

    @property
    def xyxy(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_\-\u4e00-\u9fff]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "layer"


def clip_box(box: Box, width: int, height: int) -> Box | None:
    x1 = max(0, min(width, box.x))
    y1 = max(0, min(height, box.y))
    x2 = max(0, min(width, box.x + box.w))
    y2 = max(0, min(height, box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return None
    return Box(box.name, box.kind, x1, y1, x2 - x1, y2 - y1, box.score)


def load_manual_boxes(path: Path, width: int, height: int) -> list[Box]:
    data = json.loads(path.read_text(encoding="utf-8"))
    boxes: list[Box] = []
    for i, item in enumerate(data):
        box = Box(
            name=str(item.get("name") or f"manual_{i + 1:02d}"),
            kind=str(item.get("type") or item.get("kind") or "manual"),
            x=int(item["x"]),
            y=int(item["y"]),
            w=int(item["w"]),
            h=int(item["h"]),
            score=float(item.get("score", 1.0)),
        )
        clipped = clip_box(box, width, height)
        if clipped:
            boxes.append(clipped)
    return boxes


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def auto_mask(image: Image.Image, sensitivity: float) -> Image.Image:
    """Heuristic UI mask: find bright panels, dark panels with bright borders, and text-dense regions."""
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba).astype(np.float32)
    rgb = arr[..., :3]
    alpha = arr[..., 3]
    lum = luminance(rgb)
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = maxc - minc

    # UI screenshots often have parchment panels, glowing borders, and high-contrast text.
    bright_panel = (lum > np.percentile(lum, 76 - sensitivity * 10)) & (sat < 100 + sensitivity * 40)
    glow = (lum > np.percentile(lum, 86 - sensitivity * 8)) & (sat > 25)
    dark_plate = (lum < np.percentile(lum, 30 + sensitivity * 8)) & (sat < 95)

    # Simple edge magnitude.
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[:, 1:] = np.abs(lum[:, 1:] - lum[:, :-1])
    gy[1:, :] = np.abs(lum[1:, :] - lum[:-1, :])
    edge = (gx + gy) > (22 - sensitivity * 8)

    mask = ((bright_panel | glow | (dark_plate & edge)) & (alpha > 0)).astype(np.uint8) * 255
    pil = Image.fromarray(mask, "L")
    # Merge fragmented text/borders into panels.
    pil = pil.filter(ImageFilter.MaxFilter(15))
    pil = pil.filter(ImageFilter.MaxFilter(15))
    pil = pil.filter(ImageFilter.MinFilter(9))
    pil = pil.filter(ImageFilter.GaussianBlur(2))
    pil = pil.point(lambda p: 255 if p > 28 else 0)
    return pil


def connected_components(mask: Image.Image, min_area: int, max_area_ratio: float, max_components: int) -> list[Box]:
    arr = np.asarray(mask.convert("L")) > 0
    h, w = arr.shape
    seen = np.zeros_like(arr, dtype=bool)
    boxes: list[Box] = []
    max_area = int(w * h * max_area_ratio)

    for y0 in range(h):
        row = arr[y0]
        for x0 in np.flatnonzero(row & ~seen[y0]):
            if seen[y0, x0] or not arr[y0, x0]:
                continue
            stack = [(x0, y0)]
            seen[y0, x0] = True
            minx = maxx = x0
            miny = maxy = y0
            count = 0
            while stack:
                x, y = stack.pop()
                count += 1
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and arr[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            bw = maxx - minx + 1
            bh = maxy - miny + 1
            area = bw * bh
            if area < min_area or area > max_area:
                continue
            if bw < 24 or bh < 24:
                continue
            aspect = bw / max(1, bh)
            if aspect > 12 or aspect < 0.08:
                continue
            boxes.append(Box("auto", guess_kind(bw, bh, w, h), minx, miny, bw, bh, count / max(1, area)))

    boxes.sort(key=lambda b: b.area, reverse=True)
    return non_max_suppress(boxes[: max_components * 3], max_components)


def guess_kind(w: int, h: int, screen_w: int, screen_h: int) -> str:
    if w > screen_w * 0.65 and h < screen_h * 0.12:
        return "hud"
    if w > screen_w * 0.45 and h > screen_h * 0.16:
        return "panel"
    if h < screen_h * 0.08:
        return "button"
    if w > screen_w * 0.18 and h > screen_h * 0.12:
        return "card"
    return "ui"


def intersection_area(a: Box, b: Box) -> int:
    ax1, ay1, ax2, ay2 = a.xyxy
    bx1, by1, bx2, by2 = b.xyxy
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    return max(0, x2 - x1) * max(0, y2 - y1)


def non_max_suppress(boxes: list[Box], max_components: int) -> list[Box]:
    chosen: list[Box] = []
    for box in boxes:
        keep = True
        for old in chosen:
            inter = intersection_area(box, old)
            if inter / max(1, min(box.area, old.area)) > 0.72:
                keep = False
                break
        if keep:
            chosen.append(box)
        if len(chosen) >= max_components:
            break
    return sorted(chosen, key=lambda b: (b.y, b.x))


def mobile_game_fallback_boxes(width: int, height: int) -> list[Box]:
    """Common regions for portrait game UI screenshots. Useful when visual auto-detection is too conservative."""
    specs = [
        ("top_title", "hud", 0.26, 0.035, 0.48, 0.08),
        ("top_hud", "hud", 0.07, 0.115, 0.86, 0.06),
        ("center_prompt", "label", 0.24, 0.545, 0.52, 0.055),
        ("left_card", "card", 0.105, 0.605, 0.39, 0.255),
        ("right_card", "card", 0.505, 0.605, 0.39, 0.255),
        ("status_legend", "strip", 0.245, 0.875, 0.51, 0.055),
        ("hint_text", "label", 0.24, 0.925, 0.52, 0.035),
        ("back_button", "button", 0.36, 0.955, 0.28, 0.04),
    ]
    boxes: list[Box] = []
    for name, kind, x, y, w, h in specs:
        box = Box(
            name,
            kind,
            int(round(width * x)),
            int(round(height * y)),
            int(round(width * w)),
            int(round(height * h)),
            0.5,
        )
        clipped = clip_box(box, width, height)
        if clipped:
            boxes.append(clipped)
    return boxes


def pad_box(box: Box, pad: int, width: int, height: int) -> Box:
    return clip_box(Box(box.name, box.kind, box.x - pad, box.y - pad, box.w + pad * 2, box.h + pad * 2, box.score), width, height) or box


def make_background(image: Image.Image, boxes: Iterable[Box], blur: int) -> Image.Image:
    base = image.convert("RGBA")
    bg = base.copy()
    draw = ImageDraw.Draw(bg)
    w, h = bg.size
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy
        sx1 = max(0, x1 - 16)
        sy1 = max(0, y1 - 16)
        sx2 = min(w, x2 + 16)
        sy2 = min(h, y2 + 16)
        sample = np.asarray(base.crop((sx1, sy1, sx2, sy2)).convert("RGB"))
        if sample.size:
            color = tuple(int(v) for v in np.median(sample.reshape(-1, 3), axis=0))
        else:
            color = (24, 24, 24)
        draw.rectangle((x1, y1, x2, y2), fill=color + (255,))
    if blur > 0:
        blurred = bg.filter(ImageFilter.GaussianBlur(blur))
        mask = Image.new("L", bg.size, 0)
        md = ImageDraw.Draw(mask)
        for box in boxes:
            md.rounded_rectangle(box.xyxy, radius=max(8, min(box.w, box.h) // 18), fill=210)
        bg = Image.composite(blurred, bg, mask)
    return bg


def write_slices(image: Image.Image, boxes: list[Box], out_dir: Path, pad: int) -> list[dict]:
    slices_dir = out_dir / "slices"
    cropped_dir = out_dir / "slices_cropped"
    slices_dir.mkdir(parents=True, exist_ok=True)
    cropped_dir.mkdir(parents=True, exist_ok=True)
    w, h = image.size
    layers: list[dict] = []
    for idx, raw_box in enumerate(boxes, start=1):
        box = pad_box(raw_box, pad, w, h)
        name = f"{idx:02d}_{slugify(raw_box.name if raw_box.name != 'auto' else raw_box.kind)}"
        cropped = image.crop(box.xyxy).convert("RGBA")

        full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        full.alpha_composite(cropped, (box.x, box.y))

        full_path = slices_dir / f"{name}.png"
        crop_path = cropped_dir / f"{name}.png"
        full.save(full_path)
        cropped.save(crop_path)
        layers.append(
            {
                "id": int(idx),
                "name": name,
                "type": raw_box.kind,
                "x": int(box.x),
                "y": int(box.y),
                "w": int(box.w),
                "h": int(box.h),
                "score": round(raw_box.score, 4),
                "file": str(full_path.relative_to(out_dir)).replace("\\", "/"),
                "cropped_file": str(crop_path.relative_to(out_dir)).replace("\\", "/"),
            }
        )
    return layers


def write_svg(out_dir: Path, width: int, height: int, layers: list[dict]) -> None:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'  <image href="background_working.png" x="0" y="0" width="{width}" height="{height}"/>',
    ]
    for layer in layers:
        href = html.escape(layer["cropped_file"])
        parts.append(
            f'  <image id="{html.escape(layer["name"])}" href="{href}" '
            f'x="{layer["x"]}" y="{layer["y"]}" width="{layer["w"]}" height="{layer["h"]}"/>'
        )
    parts.append("</svg>")
    (out_dir / "layout.svg").write_text("\n".join(parts), encoding="utf-8")


def write_preview(out_dir: Path, width: int, height: int, layers: list[dict]) -> None:
    layer_html = "\n".join(
        f'<img class="layer" src="{html.escape(layer["cropped_file"])}" '
        f'style="left:{layer["x"]}px; top:{layer["y"]}px; width:{layer["w"]}px; height:{layer["h"]}px" '
        f'alt="{html.escape(layer["name"])}">'
        for layer in layers
    )
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>screen2layers preview</title>
<style>
body {{ margin: 0; background: #111; color: #ddd; font-family: system-ui, sans-serif; }}
.wrap {{ display: flex; gap: 24px; padding: 24px; align-items: flex-start; }}
.stage {{ position: relative; width: {width}px; height: {height}px; transform-origin: top left; box-shadow: 0 16px 60px #0008; }}
.stage img {{ position: absolute; display: block; }}
.bg {{ left: 0; top: 0; width: {width}px; height: {height}px; }}
.panel {{ max-width: 360px; line-height: 1.5; }}
code {{ color: #ffd37a; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="stage">
    <img class="bg" src="background_working.png" alt="background">
    {layer_html}
  </div>
  <div class="panel">
    <h1>screen2layers</h1>
    <p>Import <code>layout.svg</code> into Figma for a positioned layer stack.</p>
    <p>Layers: {len(layers)}</p>
  </div>
</div>
</body>
</html>
"""
    (out_dir / "preview.html").write_text(doc, encoding="utf-8")


def write_debug(image: Image.Image, boxes: list[Box], out_dir: Path) -> None:
    debug_dir = out_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay)
    for i, box in enumerate(boxes, start=1):
        color = (255, 205, 80, 255)
        draw.rectangle(box.xyxy, outline=color, width=max(3, math.ceil(image.width / 360)))
        draw.text((box.x + 6, box.y + 6), f"{i} {box.kind}", fill=color)
    overlay.save(debug_dir / "detected_boxes.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a UI screenshot into a layered design kit.")
    parser.add_argument("input", type=Path, help="Input PNG/JPG screenshot")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--boxes", type=Path, help="Optional manual boxes JSON")
    parser.add_argument("--sensitivity", type=float, default=1.0, help="Auto detection sensitivity, usually 0.5-2.0")
    parser.add_argument("--min-area", type=int, default=1800, help="Minimum auto component bbox area")
    parser.add_argument("--max-area-ratio", type=float, default=0.45, help="Ignore auto components larger than this screen ratio")
    parser.add_argument("--max-components", type=int, default=24, help="Maximum auto layers")
    parser.add_argument("--pad", type=int, default=8, help="Padding around slices")
    parser.add_argument("--blur", type=int, default=10, help="Blur radius for rough background fill")
    parser.add_argument(
        "--fallback",
        choices=["auto", "none", "mobile-game"],
        default="auto",
        help="Use portrait game UI fallback boxes when auto detection finds too few layers",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = Image.open(args.input).convert("RGBA")
    width, height = image.size
    args.out.mkdir(parents=True, exist_ok=True)

    if args.boxes:
        boxes = load_manual_boxes(args.boxes, width, height)
        mode = "manual"
    else:
        mask = auto_mask(image, args.sensitivity)
        boxes = connected_components(mask, args.min_area, args.max_area_ratio, args.max_components)
        boxes = [pad_box(b, 0, width, height) for b in boxes]
        mode = "auto"
        if args.fallback in {"auto", "mobile-game"} and (len(boxes) < 3 or args.fallback == "mobile-game"):
            fallback_boxes = mobile_game_fallback_boxes(width, height)
            boxes = non_max_suppress(boxes + fallback_boxes, args.max_components)
            mode = "auto+mobile-game-fallback"

    background = make_background(image, boxes, args.blur)
    background.save(args.out / "background_working.png")
    layers = write_slices(image, boxes, args.out, args.pad)
    write_svg(args.out, width, height, layers)
    write_preview(args.out, width, height, layers)
    write_debug(image, boxes, args.out)

    manifest = {
        "tool": "screen2layers",
        "version": "0.1.0",
        "mode": mode,
        "input": str(args.input),
        "width": int(width),
        "height": int(height),
        "layer_count": len(layers),
        "layers": layers,
        "notes": [
            "Bitmap slices are movable layers, not true recovered vector primitives.",
            "Use imagegen or manual art cleanup for polished background inpainting.",
            "Rebuild important text as editable Figma/Cocos text layers.",
        ],
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "report.md").write_text(
        f"# screen2layers report\n\n"
        f"- Input: `{args.input}`\n"
        f"- Size: `{width}x{height}`\n"
        f"- Mode: `{mode}`\n"
        f"- Layers: `{len(layers)}`\n\n"
        f"Open `debug/detected_boxes.png` for QA and import `layout.svg` into Figma.\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "width": width, "height": height, "layers": len(layers)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
