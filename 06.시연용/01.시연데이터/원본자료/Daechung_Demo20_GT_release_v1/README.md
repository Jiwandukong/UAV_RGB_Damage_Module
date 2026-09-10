# Daechung Dam UAV Demo20 Human-Reviewed 3-Class Ground Truth

This distribution contains 20 UAV RGB images of Daechung Dam and their final human-reviewed Labelme annotations. The JSON files are byte-for-byte copies of the authoritative frozen GT. Model outputs were used only to generate candidates for human review.

## Dataset

- UAV RGB images: 20
- Resolution: 5280 x 3956 pixels, RGB
- 2025 acquisition: 8 images
- 2026 acquisition: 12 images
- Acquisition years are identified from DJI filenames.

| Label | Class | Labelme geometry | Final annotation count |
|---|---|---|---:|
| CRC | Crack | linestrip | 312 |
| DLM | Delamination | polygon | 86 |
| SPL | Spalling | polygon | 231 |
| Total | | | 629 |

DELETE_ROI shapes and other labels: 0.

## Package layout and image pairing

```text
01_Dataset/images/   20 original JPG files
01_Dataset/labels/   20 final Labelme JSON files
02_Previews/        20 overlays rendered from the final reviewed JSON files
03_Docs/            Three byte-identical copies of the original freeze audit documents
README.md
SHA256SUMS.txt
RELEASE_AUDIT.md
```

Pair images and labels by the same filename stem. JSON `imagePath` values remain the original JPG basenames. In this split-directory distribution, resolve those values against `01_Dataset/images/`; they are not relative paths from `01_Dataset/labels/` to its sibling directory. No JSON has been rewritten to change imagePath.

For a Labelme workflow that expects each JSON beside its image, make a separate working directory and copy the paired JPG and JSON files together there. Keep this release unchanged. Tools processing the split layout should accept separate image and label roots.

## Annotation workflow

CRC: DamSegment NEW Stage A based automatic crack candidates → mask threshold 0.60 → skeleton centerline / min_path_length 100 px / RDP epsilon 0.5 → DELETE_ROI based bulk cleanup (Pass 1 and Pass 2) → human review. The frozen CRC count and geometry remained unchanged during Stage C and DLM/SPL review.

DLM/SPL: Stage C based automatic candidates → human review / deletion / boundary correction / missing-object addition.

Distributed JSON files are the final human-reviewed annotations. CRC candidates came from DamSegment NEW Stage A; DLM/SPL candidates came from Stage C. Neither model checkpoint is required or included in this GT distribution.

## Interpretation notes

- `min_path_length = 100 px` filters skeleton centerline length; it is not a crack-width threshold. This filter and RDP were not reapplied after cleanup or during this distribution build.
- SAM prediction mask thickness must not be interpreted as physical crack opening width.
- A physical crack criterion of approximately 1 mm was not quantitatively enforced in this Demo20 GT because per-image GSD/standoff has not yet been established.
- CRC and SPL are not separated by a simple width threshold.
- A spalling perimeter itself is not labeled CRC. An actual crack continuing outside a spalled region may be labeled CRC for that external crack segment.
- These are visually human-reviewed annotations; the release audit checks file integrity, pairing and geometry, rather than independently reassessing every semantic annotation decision.

## Previews

Each image has one `_final_overlay.jpg` visualization based on its final reviewed JSON. CRC linestrips are green, DLM polygons blue, and SPL polygons yellow. Polygon fill opacity is approximately 18%, with distinct outlines. Counts and the original filename appear in the header.

Only preview copies are downsampled to a 2200-pixel-wide image area, with an added header/footer. Dataset JPG files retain their original bytes and 5280 x 3956 resolution. Previews are viewing aids, not ground truth and not suitable for extracting original annotation coordinates.

## Integrity and provenance

From the release root, verify the distribution with:

```sh
sha256sum -c SHA256SUMS.txt
```

`SHA256SUMS.txt` contains release-relative paths for all 65 other files, including RELEASE_AUDIT.md, and excludes itself. The copied `03_Docs/final_3class_sha256.txt` is an unchanged historical manifest whose basenames refer to the original co-located dataset. Use the root SHA256SUMS.txt to verify this split-directory release.

The three documents in `03_Docs/` preserve the original freeze audit exactly; historical server paths in them describe provenance. This package can be processed using its relative directory layout without access to those server paths. See RELEASE_AUDIT.md for the source/copy comparison, all validation results, and the complete generated-file inventory.
