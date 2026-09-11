"""Quantify reviewed demo annotations using the unchanged production mapper.

Every original LabelMe shape remains one observation, including disconnected
raster pieces, overlaps and shapes crossing 512-pixel tile boundaries. Geometry
is measured in the original photo grid, never in a resized image. CRC length
and width retain the production minimum-area-rectangle definition: a one-pixel
training centerline does *not* establish a physical crack opening width.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .geometry.mesh_ray import MeshRayGeo3DContext, extract_contour_nodes
from .geometry.surface_metrics import measure_oriented_pixel_geometry


CLASS_IDS = {"CRC": 1, "DLM": 2, "SPL": 3}
TILE_SIZE = 512


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _bbox(value: Any, name: str, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{name} must contain x0, y0, x1, y1")
    x0, y0, x1, y1 = (_integer(item, name) for item in value)
    if not (x0 < x1 <= width and y0 < y1 <= height):
        raise ValueError(f"{name} must be a nonempty bbox inside {width} x {height}")
    return x0, y0, x1, y1


def _bundle_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Dataset paths must be nonempty relative paths")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Dataset file must remain inside its bundle: {relative}")
    return path


def _reassemble_annotation(
    root: Path, annotation: dict[str, Any], width: int, height: int,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Return the exact tight mask assembled from independent instance PNGs."""
    bounds = _bbox(annotation["raster_bbox_xyxy"], "raster_bbox_xyxy", width, height)
    left, top, right, bottom = bounds
    assembled = np.zeros((bottom - top, right - left), dtype=bool)
    mappings = annotation.get("tiles")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError(f"Annotation has no instance tile masks: {annotation.get('damage_id')}")
    seen_origins: set[tuple[int, int]] = set()
    pixel_sum = 0
    for mapping in mappings:
        for key in ("damage_id", "label", "shape_index"):
            if mapping.get(key) != annotation[key]:
                raise ValueError(f"Instance tile {key} does not match its annotation")
        x0 = _integer(mapping["x0"], "tile x0")
        y0 = _integer(mapping["y0"], "tile y0")
        if x0 >= width or y0 >= height or x0 % TILE_SIZE or y0 % TILE_SIZE:
            raise ValueError("Instance tiles must lie on the original 512-pixel grid")
        if (x0, y0) in seen_origins:
            raise ValueError("Duplicate instance tile origin in one annotation")
        seen_origins.add((x0, y0))
        local_bounds = _bbox(mapping["local_bbox_xyxy"], "local_bbox_xyxy", TILE_SIZE, TILE_SIZE)
        path = _bundle_path(root, mapping["instance_mask_path"])
        with Image.open(path) as opened:
            if opened.mode != "L" or opened.size != (TILE_SIZE, TILE_SIZE):
                raise ValueError(f"Instance mask must be 512 x 512, L mode: {path}")
            mask = np.asarray(opened)
            if not np.all((mask == 0) | (mask == 255)):
                raise ValueError(f"Instance mask must be binary 0/255: {path}")
            actual_bounds = opened.getbbox()
        count = int(np.count_nonzero(mask))
        if count != _integer(mapping["positive_pixels"], "positive_pixels", 1):
            raise ValueError(f"Instance tile positive_pixels mismatch: {path}")
        if actual_bounds != local_bounds:
            raise ValueError(f"Instance tile local bbox mismatch: {path}")
        lx0, ly0, lx1, ly1 = local_bounds
        gx0, gy0, gx1, gy1 = x0 + lx0, y0 + ly0, x0 + lx1, y0 + ly1
        if not (left <= gx0 < gx1 <= right and top <= gy0 < gy1 <= bottom):
            raise ValueError(f"Instance pixels exceed annotation/source bounds: {path}")
        # Bounds above also forbid any nonzero padded pixels outside the JPG.
        assembled[gy0 - top:gy1 - top, gx0 - left:gx1 - left] = (
            mask[ly0:ly1, lx0:lx1] == 255
        )
        pixel_sum += count
    if int(np.count_nonzero(assembled)) != pixel_sum:
        raise ValueError("Reassembled annotation pixel count differs from its instance tiles")
    if not (assembled[0].any() and assembled[-1].any()
            and assembled[:, 0].any() and assembled[:, -1].any()):
        raise ValueError("raster_bbox_xyxy is not the exact tight annotation bbox")
    return assembled, bounds


def quantify_source(
    dataset_root: Path, source: dict[str, Any], context: MeshRayGeo3DContext,
) -> list[dict[str, Any]]:
    """Return ``annotation/base/spatial`` records in original shape order.

    Only two full-photo buffers are allocated, once per source. Each original
    annotation is placed into them independently, mapped through the public
    production API, and cleared before the next shape. Missing mesh hits stay
    missing; a pixel-contour fallback supplies display geometry only, never
    fabricated world coordinates or physical measurements.
    """
    root = Path(dataset_root).resolve(strict=True)
    width = _integer(source["width"], "source width", 1)
    height = _integer(source["height"], "source height", 1)
    if (context.intrinsics.width, context.intrinsics.height) != (width, height):
        raise ValueError("Camera intrinsics dimensions do not match the original source image")
    with Image.open(_bundle_path(root, source["image_path"])) as image:
        if image.size != (width, height):
            raise ValueError("Manifest source dimensions do not match the original image")
    annotations = source.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError("source annotations must be a list")
    seen_shapes: set[int] = set()
    seen_damage_ids: set[str] = set()
    for annotation in annotations:
        shape_index = _integer(annotation["shape_index"], "shape_index")
        damage_id = annotation["damage_id"]
        if not isinstance(damage_id, str) or not damage_id:
            raise ValueError("Every annotation needs a nonempty damage_id")
        if shape_index in seen_shapes or damage_id in seen_damage_ids:
            raise ValueError("Duplicate source shape_index or damage_id")
        if annotation.get("label") not in CLASS_IDS:
            raise ValueError(f"Unsupported annotation label: {annotation.get('label')}")
        seen_shapes.add(shape_index)
        seen_damage_ids.add(damage_id)

    segmentation = np.zeros((height, width), dtype=np.uint8)
    instance_labels = np.zeros((height, width), dtype=np.uint32)
    results: list[dict[str, Any]] = []
    for annotation in sorted(annotations, key=lambda item: item["shape_index"]):
        submask, (x0, y0, x1, y1) = _reassemble_annotation(root, annotation, width, height)
        ys, xs = np.nonzero(submask)
        class_id = CLASS_IDS[annotation["label"]]
        geometry = measure_oriented_pixel_geometry(submask, offset_x=x0, offset_y=y0)
        assert geometry is not None  # Empty masks were rejected during assembly.
        is_crack = class_id == 1
        base = {
            "instance_id": annotation["shape_index"] + 1,
            "instance_local_id": 1,
            "class_id": class_id,
            "class_name": annotation["label"],
            "centroid_x_px": round(float(xs.mean()) + x0, 4),
            "centroid_y_px": round(float(ys.mean()) + y0, 4),
            "bbox_xmin_px": x0, "bbox_ymin_px": y0,
            "bbox_xmax_px": x1, "bbox_ymax_px": y1,
            "bbox_w_px": x1 - x0, "bbox_h_px": y1 - y0,
            "area_px": int(len(xs)),
            "length_px": round(float(geometry.length_px), 6) if is_crack else None,
            "width_px": round(float(geometry.width_px), 6) if is_crack else None,
            "measurement_angle_deg": round(float(geometry.angle_deg), 6) if is_crack else None,
        }
        segmentation[y0:y1, x0:x1] = submask.astype(np.uint8) * class_id
        instance_labels[y0:y1, x0:x1] = submask
        try:
            spatial = context.image_region_to_world3d(
                base, pred_mask=segmentation,
                instance_label_maps={class_id: instance_labels},
            )
        finally:
            segmentation[y0:y1, x0:x1] = 0
            instance_labels[y0:y1, x0:x1] = 0
        if not spatial.get("nodes_image_xy_json") or spatial["nodes_image_xy_json"] == "[]":
            nodes = extract_contour_nodes(submask, offset_x=x0, offset_y=y0, max_count=256)
            spatial.update({
                "nodes_image_xy_json": json.dumps(
                    [[round(float(x), 4), round(float(y), 4)] for x, y in nodes],
                    separators=(",", ":"),
                ),
                "nodes_world_xyz_json": json.dumps([[None, None, None] for _ in nodes], separators=(",", ":")),
                "node_count": int(len(nodes)),
                "node_xyz_valid_count": 0,
                "node_xyz_hit_ratio": 0.0,
                "nodes_geo3d_source": "pixel_contour_only_no_world_fallback",
                "nodes_miss_reason": "native_mapper_did_not_return_contour_world_coordinates",
            })
        results.append({"annotation": annotation, "base": base, "spatial": spatial})
    return results
