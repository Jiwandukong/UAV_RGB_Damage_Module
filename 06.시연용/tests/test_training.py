from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo512.training import (build_schedule, masked_segmentation_loss, read_rgb,
                             load_training_sample, training_parameters, save_checkpoint, sha256_file)


def test_only_damage_positive_tile_class_pairs():
    tiles = [
        {"positive_pixels": {"CRC": 3, "DLM": 0, "SPL": 0}},
        {"positive_pixels": {"CRC": 0, "DLM": 0, "SPL": 0}},
        {"positive_pixels": {"CRC": 0, "DLM": 20, "SPL": 10}},
    ]
    schedule = build_schedule(tiles, 123, 0)
    assert set(schedule) == {(0, "CRC"), (2, "DLM"), (2, "SPL")}
    assert schedule == build_schedule(tiles, 123, 0)


def test_no_positive_training_data_is_an_error():
    with pytest.raises(ValueError, match="no damage-positive"):
        build_schedule([{"positive_pixels": {"CRC": 0, "DLM": 0, "SPL": 0}}], 0, 0)


def test_loss_keeps_one_pixel_crack_and_ignores_padding():
    logits = torch.zeros((1, 1, 512, 512), requires_grad=True)
    labels = torch.zeros_like(logits)
    labels[:, :, 10, 2:100] = 1
    valid = torch.zeros_like(logits)
    valid[:, :, :400, :300] = 1
    loss = masked_segmentation_loss(logits, labels, valid)
    loss.backward()
    assert torch.isfinite(loss)
    assert torch.all(logits.grad[:, :, 10, 2:100] < 0)
    assert torch.count_nonzero(logits.grad[:, :, 400:, :]) == 0
    assert torch.count_nonzero(logits.grad[:, :, :, 300:]) == 0
    assert int(labels.sum()) == 98


def test_loss_rejects_non512_input():
    value = torch.zeros((1, 1, 1008, 1008))
    with pytest.raises(ValueError, match="512x512"):
        masked_segmentation_loss(value, value, torch.ones_like(value))


def test_read_rgb_refuses_resize(tmp_path):
    path = tmp_path / "tile.png"
    Image.new("RGB", (1008, 1008)).save(path)
    with pytest.raises(ValueError, match="512x512"):
        read_rgb(path)


def test_sample_preserves_pixels_and_excludes_negative_target(tmp_path):
    rgb = np.zeros((512, 512, 3), dtype=np.uint8)
    rgb[511, 511] = [127, 255, 64]
    Image.fromarray(rgb).save(tmp_path / "tile.png")
    mask = np.zeros((512, 512), dtype=np.uint8)
    mask[511, 511] = 255
    Image.fromarray(mask).save(tmp_path / "mask.png")
    Image.new("L", (512, 512), 255).save(tmp_path / "valid.png")
    tile = {"image_path": "tile.png", "mask_paths": {"CRC": "mask.png"}, "valid_mask_path": "valid.png"}
    x, y, valid = load_training_sample(tmp_path, tile, "CRC")
    assert x.shape == (1, 3, 512, 512)
    assert torch.allclose(x[0, :, 511, 511], torch.tensor([127, 255, 64]) / 255)
    assert y.sum().item() == 1
    Image.new("L", (512, 512)).save(tmp_path / "mask.png")
    with pytest.raises(ValueError, match="damage-positive"):
        load_training_sample(tmp_path, tile, "CRC")


def test_training_groups_exclude_backbone_instance_and_unused_stage():
    class TinyModel:
        def __init__(self):
            self.values = {name: torch.nn.Parameter(torch.zeros(1)) for name in (
                "backbone.vision.weight", "transformer.encoder.weight",
                "segmentation_head.semantic_seg_head.weight",
                "segmentation_head.instance_seg_head.weight",
                "segmentation_head.pixel_decoder.conv_layers.0.weight",
                "segmentation_head.pixel_decoder.conv_layers.2.weight",
                "segmentation_head.pixel_decoder.norms.2.weight")}
        def named_parameters(self):
            return self.values.items()
        def eval(self):
            return self
    model = TinyModel()
    selected = training_parameters(model)
    assert {name for name, _ in selected} == {
        "transformer.encoder.weight", "segmentation_head.semantic_seg_head.weight",
        "segmentation_head.pixel_decoder.conv_layers.0.weight"}
    assert not model.values["backbone.vision.weight"].requires_grad


def test_checkpoint_published_complete_and_never_overwritten(tmp_path):
    model = torch.nn.Linear(2, 1)
    info = save_checkpoint(model, tmp_path, "new.pt", {"completed_epochs": 5})
    saved = tmp_path / info["file"]
    assert not (tmp_path / "new.pt.incomplete").exists()
    assert info["sha256"] == sha256_file(saved)
    payload = torch.load(saved, map_location="cpu", weights_only=True, mmap=True)
    assert payload["demo512"]["completed_epochs"] == 5
    assert torch.equal(payload["model"]["weight"], model.weight)
    with pytest.raises(FileExistsError):
        save_checkpoint(model, tmp_path, "new.pt", {})
