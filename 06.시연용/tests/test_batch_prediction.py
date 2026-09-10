import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo512 import batch_prediction as batch
from demo512 import model as model_module
from demo512.data import CLASSES, CLASS_COLORS, OVERLAY_ALPHA, render_overlay
from demo512.training import sha256_file


def make_bundle(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    tiles = []
    for tile_id, color, positive in (("a_positive", (30, 40, 50), True),
                                      ("b_background", (60, 70, 80), False)):
        rgb = Image.new("RGB", (512, 512), (0, 0, 0))
        rgb.paste(color, (0, 0, 4, 4))
        rgb.save(root / f"{tile_id}.png")
        masks = {label: np.zeros((512, 512), dtype=np.uint8) for label in CLASSES}
        if positive:
            masks["CRC"][1, 1:3] = 255
            masks["SPL"][1, 1] = 255
        mask_paths = {}
        for label, mask in masks.items():
            relative = f"{tile_id}_{label}.png"
            Image.fromarray(mask).save(root / relative)
            mask_paths[label] = relative
        valid = Image.new("L", (512, 512), 0)
        valid.paste(255, (0, 0, 4, 4))
        valid_path = f"{tile_id}_valid.png"
        valid.save(root / valid_path)
        overlay_path = f"{tile_id}_GT.png"
        # Simulate the immutable historical training bundle, whose GT overlay
        # was saved fully opaque before display styling changed.
        render_overlay(rgb, {label: Image.fromarray(mask) for label, mask in masks.items()},
                       alpha=1.0).save(root / overlay_path)
        tiles.append({
            "id": tile_id, "source_id": "fixture", "x0": 0, "y0": 0,
            "valid_width": 4, "valid_height": 4,
            "image_path": f"{tile_id}.png", "mask_paths": mask_paths,
            "valid_mask_path": valid_path, "overlay_path": overlay_path,
            "positive_pixels": {label: int(np.count_nonzero(mask)) for label, mask in masks.items()},
            "training_eligible": positive,
            "training_classes": [label for label in CLASSES if masks[label].any()],
        })
    manifest = {"tile_size": 512, "classes": list(CLASSES), "tiles": list(reversed(tiles))}
    (root / "dataset.json").write_text(json.dumps(manifest), encoding="utf-8")
    checkpoint = tmp_path / "demo.pt"
    checkpoint.write_bytes(b"mock checkpoint; never loaded by torch")
    record = tmp_path / "학습기록.json"
    record.write_text(json.dumps({
        "dataset_manifest_sha256": sha256_file(root / "dataset.json"),
        "checkpoint": {"file": checkpoint.name, "sha256": sha256_file(checkpoint)},
        "status": "requested_training_complete", "readout": "semantic",
    }), encoding="utf-8")
    return root, record, tiles


def args_for(root, record, output, **kwargs):
    return argparse.Namespace(data=root, model_record=record, output=output, device="cpu", **kwargs)


def mock_model(monkeypatch, record):
    calls, builds = [], []
    checkpoint_hash = json.loads(record.read_text())["checkpoint"]["sha256"]

    def build(path, device, **kwargs):
        builds.append(path)
        assert device == "cpu"
        assert kwargs == {"checkpoint_kind": "demo", "expected_sha256": checkpoint_hash}
        return torch.nn.Linear(1, 1)

    def forward(model, tensor, label):
        assert not model.training
        assert not any(parameter.requires_grad for parameter in model.parameters())
        assert not torch.is_grad_enabled()
        assert tensor.shape == (1, 3, 512, 512)
        assert tensor.device.type == "cpu"
        assert tensor.min() >= 0 and tensor.max() <= 1
        calls.append(label)
        logits = torch.full((1, 1, 512, 512), -10.0)
        # These are outside source dimensions and must never enter masks/metrics.
        logits[0, 0, 10, 10] = 10.0
        if float(tensor[0, 0, 0, 0]) < 0.2:
            if label == "CRC":
                logits[0, 0, 1, 1] = 10.0
                logits[0, 0, 2, 1] = 10.0
            if label == "DLM":
                logits[0, 0, 1, 1] = 10.0
        return logits

    monkeypatch.setattr(model_module, "build_demo_model", build)
    monkeypatch.setattr(model_module, "forward_class_logits", forward)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    return calls, builds


def open_array(path):
    with Image.open(path) as image:
        return np.array(image)


def test_all_queries_precede_gt_reads_and_results_remain_independent(tmp_path, monkeypatch):
    root, record, tiles = make_bundle(tmp_path)
    original_bundle = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    calls, builds = mock_model(monkeypatch, record)
    output = tmp_path / "results"
    real_read_binary = batch.read_binary
    gt_reads = []

    def guarded_read(path):
        assert calls == list(CLASSES)
        for label in CLASSES:
            assert (output / f"모델예측마스크/{label}/a_positive.png").is_file()
        assert (output / "모델예측오버레이/a_positive.png").is_file()
        gt_reads.append(path)
        return real_read_binary(path)

    monkeypatch.setattr(batch, "read_binary", guarded_read)
    result = batch.run_batch_prediction(args_for(root, record, output))
    assert len(builds) == 1
    assert len(gt_reads) == 4
    assert calls == list(CLASSES)  # DLM has no GT but must still be predicted.
    assert result["status"] == "reproduction_check_complete"
    assert result["requested_tiles"] == result["completed_tiles"] == 1
    assert result["ground_truth_used_for_prediction"] is False
    assert result["check_scope"] == batch.CHECK_SCOPE
    assert result["official_accuracy_claim"] is False
    assert result["generalization_evaluation"] is False
    assert result["overlay"]["alpha"] == OVERLAY_ALPHA == 0.5
    tile = result["tiles"][0]
    assert tile["model_positive_pixels"] == {"CRC": 2, "DLM": 1, "SPL": 0}
    assert tile["ground_truth_positive_classes"] == ["CRC", "SPL"]
    for label, relative in tile["model_mask_paths"].items():
        mask = open_array(output / relative)
        assert mask.shape == (512, 512)
        assert set(np.unique(mask)).issubset({0, 255})
        assert not mask[4:, :].any() and not mask[:, 4:].any()
    # Independent overlapping class predictions survive; RGB uses CRC priority.
    assert open_array(output / tile["model_mask_paths"]["DLM"])[1, 1] == 255
    overlay = open_array(output / tile["model_overlay_path"])
    blended_crc = ((1 - OVERLAY_ALPHA) * np.array([30, 40, 50])
                   + OVERLAY_ALPHA * np.array(CLASS_COLORS["CRC"])).astype(np.uint8)
    np.testing.assert_array_equal(overlay[1, 1], blended_crc)
    np.testing.assert_array_equal(overlay[2, 1], blended_crc)
    # GT does not fill the model's false negative at (x=2,y=1).
    assert tuple(overlay[1, 2]) == (30, 40, 50)
    np.testing.assert_array_equal(open_array(output / tile["ground_truth_overlay_path"])[1, 2], blended_crc)
    for key in ("image_path", "model_overlay_path", "ground_truth_overlay_path"):
        relative = tile[key]
        assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
        with Image.open(output / relative) as image:
            assert image.size == (512, 512) and image.mode == "RGB"
    assert (output / tile["image_path"]).read_bytes() == (root / tiles[0]["image_path"]).read_bytes()
    assert (output / tile["ground_truth_overlay_path"]).read_bytes() != (root / tiles[0]["overlay_path"]).read_bytes()
    assert tuple(open_array(root / tiles[0]["overlay_path"])[1, 2]) == CLASS_COLORS["CRC"]
    for relative, content in original_bundle.items():
        assert (root / relative).read_bytes() == content
    assert str(tmp_path) not in (output / batch.MANIFEST_NAME).read_text()


def test_all_tiles_exact_counts_absent_class_false_positives_and_empty_overlay(tmp_path, monkeypatch):
    root, record, _ = make_bundle(tmp_path)
    calls, builds = mock_model(monkeypatch, record)
    output = tmp_path / "all_results"
    result = batch.run_batch_prediction(args_for(root, record, output, selection="all"))
    assert len(builds) == 1 and calls == list(CLASSES) * 2
    assert [tile["id"] for tile in result["tiles"]] == ["a_positive", "b_background"]
    metrics = json.loads((output / batch.METRICS_NAME).read_text())
    all_classes = metrics["all_queried_classes"]["by_class"]
    expected = {"CRC": (1, 1, 1, 29), "DLM": (0, 1, 0, 31), "SPL": (0, 0, 1, 31)}
    for label, counts in expected.items():
        assert tuple(all_classes[label][key] for key in batch.COUNT_KEYS) == counts
        assert all_classes[label]["valid_pixels"] == 32
        assert all_classes[label]["tile_class_pairs"] == 2
    assert all_classes["CRC"]["iou"] == pytest.approx(1 / 3)
    assert all_classes["CRC"]["f1"] == pytest.approx(0.5)
    assert all_classes["DLM"]["iou"] == all_classes["DLM"]["f1"] == 0
    assert all_classes["DLM"]["recall"] is None
    assert all_classes["SPL"]["precision"] is None
    assert metrics["all_queried_classes"]["micro"]["valid_pixels"] == 96
    positive = metrics["positive_ground_truth_class_pairs_only"]["by_class"]
    assert positive["DLM"]["tile_class_pairs"] == 0
    assert positive["DLM"]["fp"] == 0 and positive["DLM"]["iou"] is None
    assert positive["CRC"]["tile_class_pairs"] == positive["SPL"]["tile_class_pairs"] == 1
    negative = result["tiles"][1]
    assert negative["model_positive_pixels"] == dict.fromkeys(CLASSES, 0)
    np.testing.assert_array_equal(open_array(output / negative["model_overlay_path"]),
                                  open_array(output / negative["image_path"]))
    progress = [json.loads(line) for line in (output / batch.PROGRESS_NAME).read_text().splitlines()]
    assert [event["completed_tiles"] for event in progress] == [1, 2]


def test_smoke_limit_is_explicit_and_output_cannot_be_overwritten(tmp_path, monkeypatch):
    root, record, _ = make_bundle(tmp_path)
    calls, builds = mock_model(monkeypatch, record)
    output = tmp_path / "smoke"
    args = args_for(root, record, output, selection="all", max_tiles=1)
    result = batch.run_batch_prediction(args)
    assert result["status"] == "smoke_check_complete" and result["smoke_check"] is True
    assert result["selection_available_tiles"] == 2 and result["completed_tiles"] == 1
    before = (output / batch.MANIFEST_NAME).read_bytes()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        batch.run_batch_prediction(args)
    assert len(builds) == 1 and calls == list(CLASSES)
    assert (output / batch.MANIFEST_NAME).read_bytes() == before


@pytest.mark.parametrize("changed", ["dataset", "checkpoint"])
def test_provenance_mismatch_fails_before_model_load_or_output(tmp_path, monkeypatch, changed):
    root, record, _ = make_bundle(tmp_path)
    calls, builds = mock_model(monkeypatch, record)
    if changed == "dataset":
        path = root / "dataset.json"
        path.write_text(path.read_text() + "\n")
    else:
        (tmp_path / "demo.pt").write_bytes(b"changed checkpoint")
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="SHA-256"):
        batch.run_batch_prediction(args_for(root, record, output))
    assert not calls and not builds and not output.exists()


def test_failed_model_is_recorded_and_never_reads_labels(tmp_path, monkeypatch):
    root, record, _ = make_bundle(tmp_path)
    mock_model(monkeypatch, record)

    def failed_forward(*args):
        raise RuntimeError("synthetic prediction failure")

    def forbidden_gt(*args):
        pytest.fail("GT must not be read before successful model predictions")

    monkeypatch.setattr(model_module, "forward_class_logits", failed_forward)
    monkeypatch.setattr(batch, "read_binary", forbidden_gt)
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="synthetic prediction failure"):
        batch.run_batch_prediction(args_for(root, record, output))
    run = json.loads((output / batch.MANIFEST_NAME).read_text())
    assert run["status"] == "failed" and run["completed_tiles"] == 0
    assert run["failed_tile_id"] == "a_positive" and run["error_type"] == "RuntimeError"
    assert not (output / batch.METRICS_NAME).exists()


def test_modified_gt_is_rejected_after_prediction_without_changing_model_masks(tmp_path, monkeypatch):
    root, record, tiles = make_bundle(tmp_path)
    calls, _ = mock_model(monkeypatch, record)
    Image.new("L", (512, 512), 0).save(root / tiles[0]["mask_paths"]["CRC"])
    output = tmp_path / "invalid_gt"
    with pytest.raises(ValueError, match="GT pixel count differs"):
        batch.run_batch_prediction(args_for(root, record, output))
    assert calls == list(CLASSES)
    crc = open_array(output / "모델예측마스크/CRC/a_positive.png")
    assert np.count_nonzero(crc) == 2
    assert json.loads((output / batch.MANIFEST_NAME).read_text())["status"] == "failed"
