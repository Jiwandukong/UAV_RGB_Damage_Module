import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo512.data import CLASSES, render_overlay, sha256_file
from demo512.overlay_refresh import refresh_batch_overlays


def bundle(tmp_path):
    data, output = tmp_path / "data", tmp_path / "output"
    data.mkdir()
    output.mkdir()
    rgb = Image.new("RGB", (512, 512), (70, 80, 90))
    rgb.save(data / "original.png")
    rgb.save(output / "original.png")
    Image.new("L", (512, 512), 255).save(data / "valid.png")
    masks = {label: Image.new("L", (512, 512), 0) for label in CLASSES}
    for mask in masks.values():
        mask.putpixel((10, 10), 255)
    for label, mask in masks.items():
        mask.save(data / f"{label}.png")
        mask.save(output / f"{label}.png")
    render_overlay(rgb, masks, alpha=1).save(data / "old_overlay.png")
    dataset = {"tiles": [{"id": "tile", "image_path": "original.png",
                          "valid_mask_path": "valid.png", "overlay_path": "old_overlay.png",
                          "mask_paths": {label: f"{label}.png" for label in CLASSES}}]}
    (data / "dataset.json").write_text(json.dumps(dataset), encoding="utf-8")
    tile = {"id": "tile", "image_path": "original.png",
            "model_mask_paths": {label: f"{label}.png" for label in CLASSES},
            "model_overlay_path": "모델예측오버레이/tile.png",
            "ground_truth_overlay_path": "라벨오버레이/tile.png"}
    for key in ("model_overlay_path", "ground_truth_overlay_path"):
        target = output / tile[key]
        target.parent.mkdir()
        render_overlay(rgb, masks, alpha=1).save(target)
    manifest = {"dataset_manifest_sha256": sha256_file(data / "dataset.json"),
                "checkpoint_sha256": "checkpoint-is-never-opened",
                "status": "reproduction_check_complete", "completed_tiles": 1,
                "overlay": {"alpha": 1}, "tiles": [tile]}
    (output / "배치예측정보.json").write_text(json.dumps(manifest), encoding="utf-8")
    (output / "재현점검.json").write_text('{"original_metrics": true}', encoding="utf-8")
    return data, output


def test_refresh_changes_only_previews_and_style_and_is_idempotent(tmp_path):
    data, output = bundle(tmp_path)
    preserved = list(data.rglob("*")) + [output / "original.png", output / "재현점검.json"]
    preserved += [output / f"{label}.png" for label in CLASSES]
    hashes = {path: sha256_file(path) for path in preserved if path.is_file()}
    report = refresh_batch_overlays(data, output, 0.5)
    assert report["overlay_images_updated"] == 2
    assert report["model_inference_rerun"] is False
    overlays = [output / f"{folder}/tile.png" for folder in ("라벨오버레이", "모델예측오버레이")]
    for path in overlays:
        with Image.open(path) as image:
            assert image.size == (512, 512)
            assert image.getpixel((10, 10)) == (35, 167, 45)
            assert image.getpixel((11, 10)) == (70, 80, 90)
    assert {path: sha256_file(path) for path in hashes} == hashes
    first = [path.read_bytes() for path in overlays]
    refresh_batch_overlays(data, output, 0.5)
    assert [path.read_bytes() for path in overlays] == first
    assert json.loads((output / "배치예측정보.json").read_text())["overlay"]["alpha"] == 0.5


@pytest.mark.parametrize("alpha", [-0.1, 1.1, float("nan"), float("inf"), True])
def test_bad_alpha_writes_nothing(tmp_path, alpha):
    data, output = bundle(tmp_path)
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="alpha"):
        refresh_batch_overlays(data, output, alpha)
    assert {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} == before


def test_bad_mask_leaves_all_existing_previews_unchanged(tmp_path):
    data, output = bundle(tmp_path)
    Image.new("L", (512, 512), 127).save(output / "CRC.png")
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="binary"):
        refresh_batch_overlays(data, output)
    assert {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} == before


def test_training_manifest_mismatch_refused(tmp_path):
    data, output = bundle(tmp_path)
    with (data / "dataset.json").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="does not match"):
        refresh_batch_overlays(data, output)


def test_cannot_replace_an_original_image_via_overlay_path(tmp_path):
    data, output = bundle(tmp_path)
    path = output / "배치예측정보.json"
    manifest = json.loads(path.read_text())
    manifest["tiles"][0]["model_overlay_path"] = "original.png"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    original = (output / "original.png").read_bytes()
    with pytest.raises(ValueError, match="only the recorded"):
        refresh_batch_overlays(data, output)
    assert (output / "original.png").read_bytes() == original
