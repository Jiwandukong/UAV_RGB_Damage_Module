import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo512 import model as model_module
from demo512.prediction import run_prediction
from demo512.data import CLASS_COLORS, OVERLAY_ALPHA, OVERLAY_ORDER


def test_prediction_uses_only_rgb_and_model_and_excludes_padding(tmp_path, monkeypatch):
    image = tmp_path / "tile.png"
    Image.new("RGB", (512, 512), (70, 80, 90)).save(image)
    # No GT JSON, masks or dataset folder exists in this isolated fixture.
    checkpoint = tmp_path / "demo.pt"
    checkpoint.write_bytes(b"dummy checkpoint; builder mocked")
    record = tmp_path / "학습기록.json"
    record.write_text(json.dumps({"checkpoint": {"file": "demo.pt", "sha256": "mock-hash"},
                                  "status": "step_limited_check_complete", "readout": "semantic"}))
    calls = []

    def build(path, device, **kwargs):
        assert kwargs == {"checkpoint_kind": "demo", "expected_sha256": "mock-hash"}
        return torch.nn.Linear(1, 1)

    def forward(model, tensor, class_name):
        assert tensor.shape == (1, 3, 512, 512)
        assert 0 <= tensor.min() <= tensor.max() <= 1
        calls.append(class_name)
        return torch.full((1, 1, 512, 512), 10.0)

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(model_module, "build_demo_model", build)
    monkeypatch.setattr(model_module, "forward_class_logits", forward)
    destination = tmp_path / "prediction"
    result = run_prediction(argparse.Namespace(image=str(image), model_record=str(record), output=str(destination),
                                             threshold=0.5, valid_width=160, valid_height=372))
    assert calls == ["CRC", "DLM", "SPL"]
    assert result["ground_truth_used_for_prediction"] is False
    assert result["overlay_style"]["alpha"] == OVERLAY_ALPHA == 0.5
    assert result["positive_pixels"] == {c: 160 * 372 for c in calls}
    with Image.open(destination / "CRC_모델예측.png") as png:
        mask = np.array(png)
    assert not mask[372:, :].any() and not mask[:, 160:].any()
    with Image.open(destination / "모델예측_오버레이.png") as png:
        overlay = np.array(png)
    expected = ((1 - OVERLAY_ALPHA) * np.array([70, 80, 90])
                + OVERLAY_ALPHA * np.array(CLASS_COLORS[OVERLAY_ORDER[-1]])).astype(np.uint8)
    np.testing.assert_array_equal(overlay[10, 10], expected)
    assert tuple(overlay[511, 511]) == (70, 80, 90)
