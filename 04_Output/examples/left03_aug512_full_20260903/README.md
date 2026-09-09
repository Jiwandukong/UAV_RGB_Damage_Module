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

The full local run, including 35 masks and seven overlays, is under `04_Output/runs/left03_aug512_simple_final` and is intentionally ignored by Git. This public example directory contains the requested 13-column CSV, its single-sheet Excel version, and copies of all seven original-resolution GPU overlays. No CPU benchmark results are included here.

## 오버레이 사진 보기

아래 사진은 위 CSV·Excel과 같은 GPU 실행에서 생성한 결과입니다. 원본 사진 위에 균열(CRC)은 빨강, 박리(DLM)는 노랑, 박락(SPL)은 파랑으로 표시합니다.

사진을 선택하면 해당 PNG를 확인하거나 다운로드할 수 있습니다. 7장 모두 5280×3956 원본 크기이며, 축소하거나 다시 압축하지 않았습니다. 전체 용량은 약 243MB입니다.

- [DJI_20250702162019_0001_V](overlays/DJI_20250702162019_0001_V_overlay.png)
- [DJI_20250702162023_0005_V](overlays/DJI_20250702162023_0005_V_overlay.png)
- [DJI_20250702162024_0006_V](overlays/DJI_20250702162024_0006_V_overlay.png)
- [DJI_20250702162025_0007_V](overlays/DJI_20250702162025_0007_V_overlay.png)
- [DJI_20250702162031_0013_V](overlays/DJI_20250702162031_0013_V_overlay.png)
- [DJI_20250702162032_0014_V](overlays/DJI_20250702162032_0014_V_overlay.png)
- [DJI_20250702162033_0015_V](overlays/DJI_20250702162033_0015_V_overlay.png)

각 파일의 SHA-256은 `SHA256SUMS`에 기록되어 있습니다. 이미지와 표의 대응 기준은 원본 사진 파일명입니다.

CRC/DLM/SPL are independent multilabel masks; overlapping DLM/SPL pixels must not be summed as unique damaged surface area. Rows are per-image observations, not cross-image-deduplicated physical defects.
