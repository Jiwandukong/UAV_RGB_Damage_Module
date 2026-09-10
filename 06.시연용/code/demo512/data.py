"""Lossless, coordinate-preserving Demo20 tiles and reviewed GT masks.

CRC vertices use round-half-away-from-zero, then Pillow ImageDraw.line(width=1).
Rasterization happens on the original image grid before any tile is cropped.
There is no resizing, antialiasing, dilation, skeletonization, or width inference.
DLM and SPL are independent filled binary polygon masks. Every original shape
also has its own damage ID and instance masks, even when shapes touch/overlap.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


CLASSES = ("CRC", "DLM", "SPL")
CLASS_COLORS = {"CRC": (0, 255, 0), "DLM": (0, 0, 255), "SPL": (255, 255, 0)}
# Last class wins only in the RGB visualization; binary masks remain independent.
OVERLAY_ORDER = ("DLM", "SPL", "CRC")
OVERLAY_ALPHA = 0.5


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def round_points(points: list[list[float]]) -> list[tuple[int, int]]:
    """Round each original coordinate once, with explicit .5 handling."""
    result = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"Expected an (x, y) point, got {point!r}")
        rounded = []
        for value in point:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Invalid coordinate {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"Non-finite coordinate {value!r}")
            rounded.append(math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5))
        result.append(tuple(rounded))
    return result


def rasterize_annotation(shape: dict[str, Any], size: tuple[int, int]) -> Image.Image:
    """Return a source-size L-mode instance mask containing only 0 and 255."""
    label = shape.get("label")
    if label not in CLASSES:
        raise ValueError(f"Unsupported label {label!r}; expected {CLASSES}")
    expected_type = "linestrip" if label == "CRC" else "polygon"
    if shape.get("shape_type") != expected_type:
        raise ValueError(f"{label} requires {expected_type}, got {shape.get('shape_type')!r}")
    points = round_points(shape.get("points", []))
    minimum = 2 if label == "CRC" else 3
    if len(points) < minimum:
        raise ValueError(f"{label} requires at least {minimum} points")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if label == "CRC":
        draw.line(points, fill=255, width=1)
    else:
        draw.polygon(points, fill=255)
    return mask


def overlay_metadata(alpha: float = OVERLAY_ALPHA) -> dict[str, Any]:
    """Shared display-only styling; alpha is color opacity, not transparency."""
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("overlay alpha must be a finite number in 0..1")
    return {
        "class_colors_rgb": {label: list(color) for label, color in CLASS_COLORS.items()},
        "paint_order": list(OVERLAY_ORDER),
        "overlap_rule": "last listed class wins in RGB overlay only; all binary masks and instances preserved",
        "alpha": float(alpha),
        "blending_rule": "select the top class color, then blend once with original RGB; background unchanged",
    }


def render_overlay(image: Image.Image, masks: dict[str, Image.Image],
                   alpha: float = OVERLAY_ALPHA) -> Image.Image:
    """Blend class colors once with RGB; CRC > SPL > DLM, masks unchanged.

    Alpha 0 leaves the original visible, 1 paints opaque class colors. Masks
    must be source-size binary images: display opacity never changes GT or
    prediction pixels, and overlapping classes do not compound the opacity.
    """
    overlay_metadata(alpha)
    original = image.convert("RGB")
    overlay = original.copy()
    for label in OVERLAY_ORDER:
        mask = masks[label]
        if mask.mode != "L" or mask.size != original.size:
            raise ValueError(f"{label} overlay mask must be an L-mode image matching RGB dimensions")
        values = np.asarray(mask)
        if not np.all((values == 0) | (values == 255)):
            raise ValueError(f"{label} overlay mask must contain only binary values 0 and 255")
        overlay.paste(CLASS_COLORS[label], (0, 0), mask)
    return Image.blend(original, overlay, float(alpha))


def _save_png(image: Image.Image, root: Path, relative: str) -> None:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", compress_level=1)


def _tile_id(stem: str, x0: int, y0: int) -> str:
    return f"{stem}__x{x0:05d}_y{y0:05d}"


def _tile_crop(image: Image.Image, x0: int, y0: int, tile_size: int) -> Image.Image:
    # Pillow crop pads coordinates outside the original image with zero.
    return image.crop((x0, y0, x0 + tile_size, y0 + tile_size))


def _source_pairs(source_root: Path) -> list[tuple[Path, Path]]:
    image_root = source_root / "01_Dataset" / "images"
    label_root = source_root / "01_Dataset" / "labels"
    images: dict[str, Path] = {}
    for path in sorted(image_root.iterdir()):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}:
            if path.stem in images:
                raise ValueError(f"Duplicate image stem: {path.stem}")
            images[path.stem] = path
    labels = {path.stem: path for path in sorted(label_root.glob("*.json"))}
    if not images:
        raise ValueError(f"No source JPG images in {image_root}")
    if images.keys() != labels.keys():
        raise ValueError("Source JPG and JSON filename stems must match exactly")
    return [(images[stem], labels[stem]) for stem in sorted(images)]


def _build_dataset(source_root: Path, staging: Path, tile_size: int) -> dict[str, Any]:
    pairs = _source_pairs(source_root)
    source_files = sorted(path for path in source_root.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in source_root.rglob("*")):
        raise ValueError("Source release must not contain symbolic links")
    release_relative = Path("원본자료") / source_root.name
    copied_release = staging / release_relative
    source_hashes = {
        path.relative_to(source_root).as_posix(): sha256_file(path) for path in source_files
    }
    shutil.copytree(source_root, copied_release, copy_function=shutil.copyfile)
    release_files = []
    for relative, digest in source_hashes.items():
        if sha256_file(copied_release / relative) != digest:
            raise ValueError(f"Source changed while copying: {relative}")
        release_files.append({
            "source_relative_path": relative,
            "path": (release_relative / relative).as_posix(),
            "sha256": digest,
        })

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "tile_size": tile_size,
        "classes": list(CLASSES),
        "mask_values": {"background": 0, "foreground": 255},
        "coordinate_system": "original decoded image pixel grid, origin top-left, x right, y down",
        "rasterization": {
            "coordinate_rounding": "nearest integer; ties away from zero; once before rasterization",
            "CRC": "PIL.ImageDraw.line(fill=255, width=1) on original grid before cropping",
            "DLM": "PIL.ImageDraw.polygon(fill=255), independent binary mask",
            "SPL": "PIL.ImageDraw.polygon(fill=255), independent binary mask",
            "antialias": False, "resize": False, "dilation": False,
            "crc_width_meaning": "one-pixel annotation centerline; no physical opening width",
        },
        "padding": {
            "where": "right/bottom, strictly outside original source dimensions",
            "image_value": [0, 0, 0], "mask_value": 0,
            "valid_mask": "255 inside the original image, 0 outside; exclude 0 pixels from loss and metrics",
        },
        "training_policy": {
            "tile_selection": "training_eligible == true: at least one class has positive GT pixels",
            "query_selection": "use only training_classes: selected class must have positive GT pixels in the tile",
            "excluded": "fully background tiles and absent-class negative queries",
            "image_content": "keep the full 512-grid tile and its background; no foreground-only crop",
        },
        "overlay": {
            "source": "reviewed JSON GT only",
            **overlay_metadata(),
        },
        "source_release": {"name": source_root.name, "path": release_relative.as_posix(), "files": release_files},
        "sources": [], "tiles": [],
    }
    total_shapes: Counter[str] = Counter()
    years: Counter[str] = Counter()
    total_positive: Counter[str] = Counter()
    total_instance_tiles = 0
    for source_image, source_label in pairs:
        image_relative = source_image.relative_to(source_root).as_posix()
        label_relative = source_label.relative_to(source_root).as_posix()
        copied_image = copied_release / image_relative
        copied_label = copied_release / label_relative
        annotation_json = json.loads(copied_label.read_text(encoding="utf-8-sig"))
        with Image.open(copied_image) as opened:
            image = opened.convert("RGB")
        width, height = image.size
        if (annotation_json.get("imageWidth"), annotation_json.get("imageHeight")) != image.size:
            raise ValueError(f"JSON/image size mismatch: {source_image.name}")
        if annotation_json.get("imagePath") != source_image.name:
            raise ValueError(f"JSON imagePath must identify paired JPG basename: {source_label.name}")
        stem = source_image.stem
        year_match = re.match(r"DJI_(20\d{2})", stem)
        source_year = int(year_match.group(1)) if year_match else None
        years[str(source_year)] += 1
        class_masks = {label: Image.new("L", image.size, 0) for label in CLASSES}
        tile_lookup = {}
        for y0 in range(0, height, tile_size):
            for x0 in range(0, width, tile_size):
                tile_id = _tile_id(stem, x0, y0)
                tile = {
                    "id": tile_id, "source_id": stem, "source_year": source_year, "stem": stem,
                    "source_filename": source_image.name,
                    "x0": x0, "y0": y0,
                    "valid_width": min(tile_size, width - x0),
                    "valid_height": min(tile_size, height - y0),
                    "image_path": f"원본타일/{stem}/{tile_id}.png",
                    "mask_paths": {label: f"학습마스크/{label}/{stem}/{tile_id}.png" for label in CLASSES},
                    "valid_mask_path": f"학습마스크/VALID/{stem}/{tile_id}.png",
                    "overlay_path": f"라벨오버레이/{stem}/{tile_id}.png",
                    "damage_ids": [], "instances": [],
                }
                tile_lookup[(x0, y0)] = tile
        annotations = []
        class_count: Counter[str] = Counter()
        for shape_index, shape in enumerate(annotation_json.get("shapes", [])):
            instance_mask = rasterize_annotation(shape, image.size)
            label = shape["label"]
            class_count[label] += 1
            damage_id = f"{stem}__{label}_{class_count[label]:04d}"
            bounds = instance_mask.getbbox()
            if bounds is None:
                raise ValueError(f"Annotation has no pixels inside source: {damage_id}")
            class_masks[label].paste(255, (0, 0), instance_mask)
            annotation = {
                "damage_id": damage_id, "shape_index": shape_index,
                "class_index": class_count[label], "label": label,
                "shape_type": shape["shape_type"],
                "points": shape["points"],
                "rounded_points": [list(point) for point in round_points(shape["points"])],
                "original_shape": shape,
                "raster_bbox_xyxy": list(bounds), "tiles": [],
            }
            left, top, right, bottom = bounds
            for y0 in range((top // tile_size) * tile_size, bottom, tile_size):
                for x0 in range((left // tile_size) * tile_size, right, tile_size):
                    tile_instance = _tile_crop(instance_mask, x0, y0, tile_size)
                    local_bounds = tile_instance.getbbox()
                    if local_bounds is None:
                        continue
                    tile = tile_lookup[(x0, y0)]
                    relative = f"학습마스크/인스턴스/{stem}/{damage_id}__x{x0:05d}_y{y0:05d}.png"
                    _save_png(tile_instance, staging, relative)
                    mapping = {
                        "damage_id": damage_id, "label": label, "shape_index": shape_index,
                        "tile_id": tile["id"], "x0": x0, "y0": y0,
                        "local_bbox_xyxy": list(local_bounds),
                        "instance_mask_path": relative,
                        "positive_pixels": int(np.count_nonzero(np.asarray(tile_instance))),
                    }
                    tile["damage_ids"].append(damage_id)
                    tile["instances"].append(mapping)
                    annotation["tiles"].append(mapping)
                    total_instance_tiles += 1
            annotations.append(annotation)

        for (x0, y0), tile in tile_lookup.items():
            tile_image = _tile_crop(image, x0, y0, tile_size)
            tile_masks = {label: _tile_crop(mask, x0, y0, tile_size) for label, mask in class_masks.items()}
            valid = Image.new("L", (tile_size, tile_size), 0)
            valid.paste(255, (0, 0, tile["valid_width"], tile["valid_height"]))
            tile["positive_pixels"] = {
                label: int(np.count_nonzero(np.asarray(mask))) for label, mask in tile_masks.items()
            }
            total_positive.update(tile["positive_pixels"])
            tile["is_negative"] = not any(tile["positive_pixels"].values())
            tile["training_eligible"] = not tile["is_negative"]
            tile["training_classes"] = [label for label in CLASSES if tile["positive_pixels"][label] > 0]
            _save_png(tile_image, staging, tile["image_path"])
            _save_png(valid, staging, tile["valid_mask_path"])
            for label, mask in tile_masks.items():
                _save_png(mask, staging, tile["mask_paths"][label])
            _save_png(render_overlay(tile_image, tile_masks), staging, tile["overlay_path"])
            manifest["tiles"].append(tile)
        total_shapes.update(class_count)
        manifest["sources"].append({
            "id": stem, "stem": stem, "source_year": source_year,
            "source_filename": source_image.name, "label_filename": source_label.name,
            "width": width, "height": height,
            "image_path": (release_relative / image_relative).as_posix(),
            "label_path": (release_relative / label_relative).as_posix(),
            "image_sha256": source_hashes[image_relative], "label_sha256": source_hashes[label_relative],
            "tile_ids": [tile["id"] for tile in tile_lookup.values()],
            "annotation_counts": {label: class_count[label] for label in CLASSES},
            "annotations": annotations,
        })

    tiles = manifest["tiles"]
    manifest["summary"] = {
        "source_images": len(manifest["sources"]), "source_release_files": len(release_files),
        "source_year_counts": dict(sorted(years.items())),
        "tiles": len(tiles),
        "fully_valid_tiles": sum(tile["valid_width"] == tile_size and tile["valid_height"] == tile_size for tile in tiles),
        "padded_tiles": sum(tile["valid_width"] != tile_size or tile["valid_height"] != tile_size for tile in tiles),
        "negative_tiles": sum(tile["is_negative"] for tile in tiles),
        "positive_tiles": sum(not tile["is_negative"] for tile in tiles),
        "training_eligible_tiles": sum(tile["training_eligible"] for tile in tiles),
        "excluded_background_tiles": sum(not tile["training_eligible"] for tile in tiles),
        "training_pairs_by_class": {
            label: sum(tile["positive_pixels"][label] > 0 for tile in tiles) for label in CLASSES
        },
        "training_pairs": sum(len(tile["training_classes"]) for tile in tiles),
        "annotations": {label: total_shapes[label] for label in CLASSES},
        "positive_pixels": {label: total_positive[label] for label in CLASSES},
        "instance_tiles": total_instance_tiles,
    }
    # Written last inside staging; publication of the complete directory is atomic.
    (staging / "dataset.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def prepare_dataset(source_root: str | Path, output_root: str | Path, tile_size: int = 512) -> dict[str, Any]:
    """Build a complete portable dataset, refusing to overwrite any output path.

    The source release is only read. Work is staged beside ``output_root`` and
    the completed directory is renamed into place. All manifest paths are
    relative to the published dataset root, never to this machine.
    """
    if isinstance(tile_size, bool) or not isinstance(tile_size, int) or tile_size <= 0:
        raise ValueError("tile_size must be a positive integer")
    source_root = Path(source_root).expanduser().resolve(strict=True)
    output_root = Path(output_root).expanduser().absolute()
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing dataset: {output_root}")
    resolved_output = output_root.resolve()
    if resolved_output == source_root or source_root in resolved_output.parents:
        raise ValueError("Output must be outside the read-only source release")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_root.parent / f".{output_root.name}.prepare.lock"
    # Exclusive creation also prevents two prepare_dataset calls publishing together.
    with lock_path.open("x", encoding="utf-8"):
        pass
    staging: Path | None = None
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{output_root.name}.staging-", dir=output_root.parent))
        manifest = _build_dataset(source_root, staging, tile_size)
        if output_root.exists() or output_root.is_symlink():
            raise FileExistsError(f"Output appeared during preparation: {output_root}")
        staging.rename(output_root)
        staging = None
        return manifest
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock_path.unlink()
