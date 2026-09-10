"""Analytic CPU geometry tests; no checkpoint or delivered dam OBJ is loaded."""

import copy
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT / "code"))
sys.path.insert(0, str(DEMO_ROOT.parent / "03_Processing" / "src"))

from demo512.quant_geometry import quantify_source
from uav_rgb.camera_pose import CameraIntrinsics, CameraPose
from uav_rgb.mesh_ray import MeshRayGeo3DContext, empty_mesh_hit


class AnalyticPlane:
    """Horizontal z=0 plane and real camera rays give 10m/1000px=0.01m/px."""

    ray_backend = "analytic_test_plane"

    def __init__(self, miss=False):
        self.miss = miss

    def intersect_rays(self, origins, directions):
        results = []
        for origin, direction in zip(origins, directions):
            if self.miss or direction[2] >= 0:
                results.append(empty_mesh_hit("test_no_hit", None, None))
                continue
            distance = -origin[2] / direction[2]
            point = origin + distance * direction
            results.append({
                "world_x_m": float(point[0]), "world_y_m": float(point[1]),
                "world_z_m": float(point[2]), "mesh_ray_t_m": float(distance),
                "mesh_face_index": 0, "mesh_ray_hit": True, "xyz_valid": True,
            })
        return results


def make_context(width, height, miss=False):
    return MeshRayGeo3DContext(
        intrinsics=CameraIntrinsics(width, height, 1000.0, width / 2, height / 2),
        pose=CameraPose("source.png", (243000.0, 431000.0, 10.0), 0.0, -90.0, 0.0, "test", "test"),
        surface=AnalyticPlane(miss),
        node_sample_count=256,
    )


def make_source(root, masks):
    """Create independent instance PNGs in exactly the prepared-bundle format."""
    root.mkdir(exist_ok=True)
    height, width = masks[0][1].shape
    Image.new("RGB", (width, height)).save(root / "source.png")
    source = {"id": "source", "width": width, "height": height, "image_path": "source.png", "annotations": []}
    for index, (label, mask) in enumerate(masks):
        ys, xs = np.nonzero(mask)
        ann = {
            "damage_id": f"source__{label}_{index:04d}", "label": label,
            "shape_index": index,
            "raster_bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            "tiles": [],
        }
        for y0 in range(0, height, 512):
            for x0 in range(0, width, 512):
                tile = np.zeros((512, 512), dtype=np.uint8)
                crop = mask[y0:y0 + 512, x0:x0 + 512]
                tile[:crop.shape[0], :crop.shape[1]] = crop.astype(np.uint8) * 255
                image = Image.fromarray(tile)
                bounds = image.getbbox()
                if bounds is None:
                    continue
                path = f"{index}_{x0}_{y0}.png"
                image.save(root / path)
                ann["tiles"].append({
                    "damage_id": ann["damage_id"], "shape_index": index, "label": label,
                    "tile_id": f"source__x{x0}_y{y0}", "x0": x0, "y0": y0,
                    "local_bbox_xyxy": list(bounds), "positive_pixels": int(np.count_nonzero(tile)),
                    "instance_mask_path": path,
                })
        source["annotations"].append(ann)
    return source


def test_boundary_reassembly_original_coordinates_and_known_planar_area(tmp_path):
    mask = np.zeros((520, 1030), dtype=bool)
    mask[505:518, 508:519] = True  # Four native tiles, including padded lower tiles.
    source = make_source(tmp_path, [("DLM", mask)])
    results = quantify_source(tmp_path, source, make_context(1030, 520))
    assert len(results) == 1
    base, spatial = results[0]["base"], results[0]["spatial"]
    assert len(source["annotations"][0]["tiles"]) == 4
    assert base["area_px"] == 143
    assert base["centroid_x_px"] == 513.0
    assert base["centroid_y_px"] == 511.0
    assert base["bbox_xmin_px"] == 508 and base["bbox_ymin_px"] == 505
    assert spatial["measurement_valid"] is True
    assert spatial["gsd_length_m_per_px"] == pytest.approx(0.01)
    assert spatial["gsd_width_m_per_px"] == pytest.approx(0.01)
    assert spatial["gsd_area_m2_per_px"] == pytest.approx(0.0001)
    assert spatial["area_m2"] == pytest.approx(0.0143)
    assert spatial["length_m"] is None and spatial["width_m"] is None
    nodes = np.asarray(json.loads(spatial["nodes_image_xy_json"]))
    assert len(nodes) <= 256
    assert np.all(nodes[:, 0] >= 508) and np.all(nodes[:, 1] >= 505)


def test_overlapping_and_disconnected_labels_remain_separate_and_buffers_reused(tmp_path, monkeypatch):
    first = np.zeros((48, 64), dtype=bool)
    first[10:15, 8:13] = True
    first[20:23, 32:35] = True  # A disconnected part remains in this annotation.
    second = np.zeros_like(first)
    second[12:18, 10:16] = True  # Same-class overlap is not unioned or deduplicated.
    source = make_source(tmp_path, [("DLM", first), ("DLM", second), ("SPL", second)])
    source["annotations"].reverse()
    context = make_context(64, 48)
    original_map = context.image_region_to_world3d
    buffers = []
    actual_masks = []

    def spy(base, pred_mask, *, instance_label_maps):
        label_map = instance_label_maps[base["class_id"]]
        assert pred_mask.dtype == np.uint8 and label_map.dtype == np.uint32
        assert base["instance_local_id"] == 1
        assert np.array_equal(pred_mask != 0, label_map == 1)
        assert set(np.unique(pred_mask)) == {0, base["class_id"]}
        buffers.append((pred_mask, label_map))
        actual_masks.append(label_map.astype(bool))
        return original_map(base, pred_mask=pred_mask, instance_label_maps=instance_label_maps)

    monkeypatch.setattr(context, "image_region_to_world3d", spy)
    result = quantify_source(tmp_path, source, context)
    assert [row["annotation"]["shape_index"] for row in result] == [0, 1, 2]
    assert [row["base"]["area_px"] for row in result] == [34, 36, 36]
    for measured, expected in zip(actual_masks, (first, second, second)):
        assert np.array_equal(measured, expected)
    assert len({id(pair[0]) for pair in buffers}) == 1
    assert len({id(pair[1]) for pair in buffers}) == 1
    assert not buffers[0][0].any() and not buffers[0][1].any()


def test_crc_bent_one_pixel_line_retains_minimum_rectangle_not_aperture(tmp_path):
    mask = np.zeros((64, 64), dtype=bool)
    mask[10, 10:31] = True
    mask[10:26, 30] = True
    source = make_source(tmp_path, [("CRC", mask)])
    result = quantify_source(tmp_path, source, make_context(64, 64))[0]
    base, spatial = result["base"], result["spatial"]
    assert base["area_px"] == 36
    assert base["width_px"] > 1.0  # Preserve existing width semantics, not a forced 1px aperture.
    assert base["length_px"] != 35.0  # Not the 20+15-pixel polyline arc length.
    assert spatial["length_m"] == pytest.approx(base["length_px"] * 0.01, abs=1e-7)
    assert spatial["width_m"] == pytest.approx(base["width_px"] * 0.01, abs=1e-7)
    assert spatial["area_m2"] is None


def test_no_hit_keeps_pixel_contours_without_inventing_quantities_or_world_points(tmp_path):
    mask = np.zeros((64, 64), dtype=bool)
    mask[12:25, 20:31] = True
    source = make_source(tmp_path, [("SPL", mask)])
    spatial = quantify_source(tmp_path, source, make_context(64, 64, miss=True))[0]["spatial"]
    assert spatial["xyz_valid"] is False and spatial["measurement_valid"] is False
    for key in ("world_x_m", "world_y_m", "world_z_m", "length_m", "width_m", "area_m2",
                "gsd_length_m_per_px", "gsd_width_m_per_px", "gsd_area_m2_per_px"):
        assert spatial[key] is None
    nodes = json.loads(spatial["nodes_image_xy_json"])
    assert 0 < len(nodes) <= 256
    assert all(20 <= x <= 30 and 12 <= y <= 24 for x, y in nodes)
    assert json.loads(spatial["nodes_world_xyz_json"]) == [[None, None, None] for _ in nodes]
    assert spatial["nodes_geo3d_source"] == "pixel_contour_only_no_world_fallback"


@pytest.mark.parametrize("corruption", ["count", "bounds", "duplicate", "binary", "padding", "source_size", "context_size", "path_escape"])
def test_corrupt_instance_geometry_is_rejected(tmp_path, corruption):
    mask = np.zeros((520, 520), dtype=bool)
    mask[514:518, 514:518] = True
    source = make_source(tmp_path / "bundle", [("SPL", mask)])
    root = tmp_path / "bundle"
    context = make_context(520, 520)
    ann = source["annotations"][0]
    mapping = ann["tiles"][0]
    if corruption == "count":
        mapping["positive_pixels"] += 1
    elif corruption == "bounds":
        ann["raster_bbox_xyxy"][0] -= 1
    elif corruption == "duplicate":
        ann["tiles"].append(copy.deepcopy(mapping))
    elif corruption in {"binary", "padding"}:
        path = root / mapping["instance_mask_path"]
        with Image.open(path) as image:
            pixels = np.array(image)
        pixels[2, 2] = 7 if corruption == "binary" else 255
        if corruption == "padding":
            pixels[10, 10] = 255
            mapping["positive_pixels"] += 1
            mapping["local_bbox_xyxy"] = [2, 2, 11, 11]
        Image.fromarray(pixels).save(path)
    elif corruption == "source_size":
        Image.new("RGB", (519, 520)).save(root / "source.png")
    elif corruption == "context_size":
        context = make_context(512, 512)
    elif corruption == "path_escape":
        Image.new("L", (512, 512)).save(tmp_path / "outside.png")
        mapping["instance_mask_path"] = "../outside.png"
    with pytest.raises(ValueError):
        quantify_source(root, source, context)
