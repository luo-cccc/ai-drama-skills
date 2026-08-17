# Deterministic Visual Layout Contract

Use `scripts/visual_layout_cli.py` only for raster inspection and second-pass labels. It does not generate or redraw artwork.

## Capability And QA

Run `python scripts/visual_layout_cli.py capabilities` before promising a labeled plate. `deterministic_layout` is true only when Pillow and a usable CJK font are both available.

Check each unlettered raster file individually with:

```powershell
python scripts/visual_layout_cli.py verify --input <image.png> --expected-ratio <W:H>
```

Treat nonzero exit as a failed image. This check covers nonblank pixels and aspect ratio; still open that raster and inspect identity, anatomy, topology, panel count, cropping, text pollution, and continuity visually. Repeat for every final raster, including repaired and lettered versions. HTML contact sheets and reports are summary views only and cannot satisfy raster QC.

## Label Specification

Use a UTF-8 JSON file:

```json
{
  "title": "角色四视图",
  "asset_id": "CHAR-001",
  "font_size": 32,
  "padding": 16,
  "labels": [{"text": "正面", "x": 80, "y": 60}],
  "legend": ["已确认", "保守推定", "待确认"]
}
```

Coordinates are integer pixels in the final image. The compositor preserves the original dimensions and paints titles into the reserved top safe area, so the visual brief must keep that area free of faces, silhouettes, geometry, and evidence-critical detail. Keep all other labels within deliberately reserved negative space.

Compose with:

```powershell
python scripts/visual_layout_cli.py compose --input <unlettered.png> --labels <labels.json> --output <plate.png>
```

Run `verify` on the result and proofread every label. If capabilities are unavailable or composition fails, deliver the unlettered image and label JSON/TXT separately and mark the composed plate incomplete.
