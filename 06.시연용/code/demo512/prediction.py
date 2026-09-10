"""Actual model predictions on 512px RGB tiles; no labels accepted or read."""
from __future__ import annotations

import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import torch

from . import CLASSES
from .data import overlay_metadata, render_overlay
from .training import read_rgb, write_json


def run_prediction(args):
    from .model import build_demo_model, forward_class_logits

    source = Path(args.image).resolve(strict=True)
    rgb = read_rgb(source)
    run_path = Path(args.model_record).resolve(strict=True)
    training = json.loads(run_path.read_text(encoding="utf-8"))
    saved = training["checkpoint"]
    checkpoint = (run_path.parent / saved["file"]).resolve(strict=True)
    if not checkpoint.is_relative_to(run_path.parent):
        raise ValueError("model checkpoint must remain inside its recorded folder")
    if not 0 < args.threshold < 1:
        raise ValueError("threshold must be strictly between zero and one")
    if not 1 <= args.valid_width <= 512 or not 1 <= args.valid_height <= 512:
        raise ValueError("valid width/height must be in 1..512")
    destination = Path(args.output).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    started = time.monotonic()
    model = build_demo_model(checkpoint, device, checkpoint_kind="demo", expected_sha256=saved["sha256"])
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    tensor = torch.from_numpy(rgb.copy()).permute(2, 0, 1).float().div(255).unsqueeze(0).to(device)
    files, pixels, masks = {}, {}, {}
    with torch.no_grad():
        for class_name in CLASSES:
            logits = forward_class_logits(model, tensor, class_name)
            mask = logits.sigmoid()[0, 0].cpu().numpy() >= args.threshold
            mask[args.valid_height:, :] = False
            mask[:, args.valid_width:] = False
            name = f"{class_name}_모델예측.png"
            Image.fromarray(mask.astype(np.uint8) * 255).save(destination / name)
            files[class_name] = name
            pixels[class_name] = int(mask.sum())
            masks[class_name] = mask
    original = Image.fromarray(rgb)
    overlay = render_overlay(original, {
        label: Image.fromarray(mask.astype(np.uint8) * 255) for label, mask in masks.items()
    })
    original.save(destination / "입력타일.png")
    overlay.save(destination / "모델예측_오버레이.png")
    result = {"source_image": source.name, "input_size": [512, 512], "input_resized": False,
              "result_source": "model_prediction", "ground_truth_used_for_prediction": False,
              "checkpoint_sha256": saved["sha256"], "training_status": training["status"],
              "demo_quality_validated": training.get("demo_quality_validated", False),
              "readout": training["readout"], "threshold": args.threshold, "device": device,
              "valid_width": args.valid_width, "valid_height": args.valid_height,
              "masks": files, "positive_pixels": pixels,
              "overlay_style": overlay_metadata(),
              "overlay": "모델예측_오버레이.png", "elapsed_seconds": time.monotonic() - started}
    write_json(destination / "예측정보.json", result)
    return result
