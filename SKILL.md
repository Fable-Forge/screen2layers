---
name: screen2layers
description: Convert UI screenshots or generated game UI effect images into Figma-ready layered design kits. Use when the user asks to split a flat PNG/JPG UI screenshot into editable or movable assets, make something "like SVG layers", create transparent UI slices, generate a Figma importable SVG layout, extract UI panels/buttons/cards from a screenshot, or build a screen-to-layers kit for game UI, app UI, mockups, or image-to-design workflows.
---

# screen2layers

Use this skill to turn a flat UI screenshot into a practical layered kit for Figma or game UI production.

It does **not** recover true original vector layers from a raster image. It reconstructs a usable kit:

- `background_working.png`: screenshot with detected UI regions softly filled or blurred as a rough background plate.
- `slices/*.png`: independent cropped UI pieces with transparent canvas padding.
- `layout.svg`: Figma-importable layout that places the background and slices at their original coordinates.
- `manifest.json`: coordinates, sizes, names, and type guesses for every layer.
- `preview.html`: browser preview of the reconstructed stack.
- `debug/detected_boxes.png`: visual QA overlay for detected slices.

## Quick Workflow

1. Locate the input screenshot. Prefer the highest-resolution PNG available.
2. Run the bundled script:

```powershell
& "<python>" "<skill>/scripts/screen2layers.py" `
  "path/to/screen.png" `
  --out "path/to/screen2layers-output"
```

Use the Codex bundled Python if system `python` is unavailable:

```powershell
& "python" `
  "~/.codex/skills\screen2layers\scripts\screen2layers.py" `
  "path/to/screen.png" `
  --out "path/to/screen2layers-output"
```

3. Inspect `debug/detected_boxes.png` and `preview.html`.
4. If the auto split misses pieces or groups too much together, create a manual boxes file and rerun:

```powershell
& "<python>" "<skill>/scripts/screen2layers.py" `
  "path/to/screen.png" `
  --out "path/to/screen2layers-output-v2" `
  --boxes "path/to/boxes.json"
```

5. Import into Figma:
   - Drag `layout.svg` into Figma for a positioned layer stack.
   - Or drag `background_working.png` plus individual `slices/*.png`.
   - Recreate text as Figma/Cocos text layers when precision matters.

## Manual Boxes

Use manual boxes when the screenshot has complex illustration, dense text, or generated UI where auto-detection is noisy.

Format:

```json
[
  {"name": "top_hud", "type": "hud", "x": 86, "y": 210, "w": 910, "h": 96},
  {"name": "letter_card_highschool", "type": "card", "x": 124, "y": 1120, "w": 380, "h": 430}
]
```

Coordinates are pixels in the input image. The script clips boxes to image bounds and writes one slice per box.

## Use Image Generation For Clean Backgrounds

The script's background is a working plate, not a perfect inpaint. If the user needs a polished background with UI removed, use `imagegen` first to create a clean background plate, then use screen2layers for the foreground UI pieces.

Recommended pipeline for polished game UI:

1. Use `imagegen` to remove UI and produce `background_clean.png`.
2. Run `screen2layers.py` on the original screenshot to extract foreground slices.
3. Replace `background_working.png` in the output with `background_clean.png`.
4. Open `layout.svg` or `preview.html` and verify alignment.

## Quality Bar

Before delivering:

- Confirm `layout.svg`, `manifest.json`, `preview.html`, and at least one slice exist.
- Open or inspect `debug/detected_boxes.png`.
- Mention that raster slices are movable in Figma but are not true editable vector primitives.
- Recommend manually rebuilding text in Figma/Cocos if the screenshot text must be editable.

## References

Read `references/output-format.md` when you need exact output details or examples of Figma import behavior.
