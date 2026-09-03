# Verified full sample result

Generated from all seven images in `DJI_202507021616_left03` with the verified AUG512 checkpoint and `daecheong_dam_epsg5186_zup.obj`.

- Images: 7
- SAM3 tiles: 616 (`88 × 7`)
- Damage rows: 718
- CRC: 110
- DLM: 338
- SPL: 270
- Valid OBJ center hits: 718/718
- Valid local GSD measurements: 718/718
- CRC total observed length: 18.01982464 m
- DLM total observed area: 1.2406479929 m²
- SPL total observed area: 1.0527978736 m²
- Mask output shape: 5280×3956 for every class/image
- Source resize: false
- Minimum retained component area: 8 pixels

The full local run, including 35 masks and seven overlays, is under `04_Output/runs/left03_aug512_simple_final` and is intentionally ignored by Git. This public example directory contains only the requested 13-column CSV and its single-sheet Excel version.

CRC/DLM/SPL are independent multilabel masks; overlapping DLM/SPL pixels must not be summed as unique damaged surface area. Rows are per-image observations, not cross-image-deduplicated physical defects.
