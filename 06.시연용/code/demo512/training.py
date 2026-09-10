"""Native-512 supervised fine-tuning, separate from label-based deliverables.

Uses SAM3's existing text-conditioned semantic segmentation head, not the
legacy score-filtered instance union. No input/target resizing or GT lookup
is used by the model. The backbone stays frozen in this initial fine-tuning
recipe; only the encoder and pixel/semantic head are optimized.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

from . import CLASSES, CRACK_LINE_WIDTH, INPUT_SIZE


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_checkpoint(model, destination: Path, name: str, run: dict) -> dict:
    """Publish a complete, self-contained checkpoint, never a partial final file."""
    path = destination / name
    temporary = destination / (name + ".incomplete")
    if path.exists() or temporary.exists():
        raise FileExistsError(f"checkpoint already exists: {path}")
    payload = {"model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
               "demo512": run}
    with temporary.open("xb") as stream:
        torch.save(payload, stream)
    temporary.rename(path)
    return {"file": name, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def asset_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("dataset path must stay inside its bundle")
    return path


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != (INPUT_SIZE, INPUT_SIZE) or image.mode != "RGB":
            raise ValueError(f"expected untouched 512x512 RGB tile: {path}")
        return np.array(image, dtype=np.uint8)


def read_binary(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != (INPUT_SIZE, INPUT_SIZE) or image.mode != "L":
            raise ValueError(f"expected 512x512 single-channel mask: {path}")
        mask = np.array(image, dtype=np.uint8)
    if not np.isin(mask, [0, 255]).all():
        raise ValueError(f"mask must contain only 0 or 255: {path}")
    return mask > 0


def load_training_sample(root: Path, tile: dict, class_name: str):
    rgb = read_rgb(asset_path(root, tile["image_path"]))
    target = read_binary(asset_path(root, tile["mask_paths"][class_name]))
    valid = read_binary(asset_path(root, tile["valid_mask_path"]))
    if (target & ~valid).any() or not valid.any():
        raise ValueError("mask labels must remain inside real source pixels")
    if not target.any():
        raise ValueError("only damage-positive tile/class pairs may be trained")
    return (
        torch.from_numpy(rgb.copy()).permute(2, 0, 1).float().div(255).unsqueeze(0),
        torch.from_numpy(target.copy()).float().unsqueeze(0).unsqueeze(0),
        torch.from_numpy(valid.copy()).float().unsqueeze(0).unsqueeze(0),
    )


def masked_segmentation_loss(logits, target, valid):
    """Full-resolution BCE+Dice; real one-pixel labels are never downsampled.

    Positive/negative BCE terms have equal weight when both exist. This avoids
    suppressing thin CRC masks because their background greatly outnumbers them.
    Padded pixels are excluded from every term.
    """
    if logits.shape != target.shape or target.shape != valid.shape:
        raise ValueError("logits, labels and valid mask must have identical shapes")
    if tuple(logits.shape[-2:]) != (INPUT_SIZE, INPUT_SIZE):
        raise ValueError("training loss requires 512x512 logits and labels")
    if not torch.isfinite(logits).all():
        raise ValueError("non-finite model logits")
    keep = valid.bool()
    if not keep.any():
        raise ValueError("sample has no valid pixels")
    pos, neg = keep & target.bool(), keep & ~target.bool()
    pixel_loss = F.binary_cross_entropy_with_logits(logits.float(), target.float(), reduction="none")
    terms = [pixel_loss[selection].mean() for selection in (pos, neg) if selection.any()]
    bce = torch.stack(terms).mean()
    probability = logits.float().sigmoid()[keep]
    labels = target.float()[keep]
    dice = 1.0 - (2 * (probability * labels).sum() + 1.0) / (probability.sum() + labels.sum() + 1.0)
    return bce + dice


def training_parameters(model):
    # The decoder instance head is not supervised by this semantic-mask recipe.
    # Do not mark unrelated parameters trainable or imply full-model training.
    selected = []
    for name, parameter in model.named_parameters():
        trainable = name.startswith("transformer.encoder.") or (
            name.startswith("segmentation_head.") and not any(
                token in name for token in ("instance_seg_head", "mask_predictor", "presence_head")
            )
        )
        # The three-level FPN has two skip fusions. Upstream constructs an
        # extra final decoder stage that is not executed by this readout.
        if name.startswith(("segmentation_head.pixel_decoder.conv_layers.2.",
                            "segmentation_head.pixel_decoder.norms.2.")):
            trainable = False
        parameter.requires_grad_(trainable)
        if trainable:
            selected.append((name, parameter))
    if not selected:
        raise ValueError("SAM3 encoder/semantic parameters not found")
    # eval disables optional instance matching/dropout, not autograd.
    model.eval()
    return selected


def build_schedule(tiles: list[dict], seed: int, epoch: int):
    """Only damage-positive tiles AND present classes; no negative queries."""
    schedule = [(index, class_name) for index, tile in enumerate(tiles)
                for class_name in CLASSES if tile["positive_pixels"][class_name] > 0]
    if not schedule:
        raise ValueError("dataset has no damage-positive tile/class pairs")
    random.Random(seed + epoch).shuffle(schedule)
    return schedule


def run_training(args) -> dict:
    from .model import build_demo_model, forward_class_logits

    dataset_root = Path(args.data).resolve()
    manifest_path = dataset_root / "dataset.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("tile_size", 0)) != INPUT_SIZE:
        raise ValueError("only native 512 datasets are supported")
    rasterization = manifest.get("rasterization", {})
    if "width=1" not in rasterization.get("CRC", "") or any(
        rasterization.get(option) is not False for option in ("resize", "dilation", "antialias")
    ):
        raise ValueError("dataset must use unresized, undilated one-pixel CRC labels")
    tiles = manifest["tiles"]
    if not tiles or args.epochs < 1 or (args.max_steps is not None and args.max_steps < 1):
        raise ValueError("nonempty dataset and positive epochs/max-steps are required")
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError("learning rate must be positive and finite")
    save_every = getattr(args, "save_every", 5)
    if save_every < 1:
        raise ValueError("save-every must be a positive epoch count")
    if args.device != "cuda" or not torch.cuda.is_available():
        raise ValueError("this training recipe requires an available CUDA GPU")
    destination = Path(args.output).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    checkpoint = Path(args.checkpoint).resolve()
    started = time.monotonic()
    run = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "initializing", "input_size": [512, 512],
        "input_resized": False, "crc_training_line_width_px": CRACK_LINE_WIDTH,
        "readout": "sam3_existing_text_conditioned_semantic_head",
        "target_source": "human_reviewed_labelme_gt",
        "base_checkpoint_name": checkpoint.name,
        "dataset_manifest_sha256": sha256_file(manifest_path),
        "seed": args.seed, "epochs_requested": args.epochs,
        "learning_rate": args.learning_rate, "batch_size": 1,
        "schedule": "only damage-positive tile/class pairs, once per epoch; no negative queries",
        "training_pairs_per_epoch": len(build_schedule(tiles, args.seed, 0)),
        "training_tiles": sum(any(t["positive_pixels"][c] > 0 for c in CLASSES) for t in tiles),
        "background_only_tiles_excluded": sum(not any(t["positive_pixels"][c] > 0 for c in CLASSES) for t in tiles),
        "loss": "valid-pixel class-balanced BCE + soft Dice at 512x512",
        "max_steps": args.max_steps,
        "same_image_check_is_generalization_evaluation": False,
        "crc_training_width_is_physical_width": False,
        "save_every_epochs": save_every,
        "epoch_summaries": [], "intermediate_checkpoints": [],
        "backbone_frozen": True,
    }
    write_json(destination / "학습기록.json", run)
    try:
        model = build_demo_model(checkpoint, args.device, training=False)
        def verify_backbone_input(module, inputs):
            shape = list(inputs[0].shape)
            if shape[1:] != [3, 512, 512]:
                raise RuntimeError(f"actual patch encoder input is not native512: {shape}")
            run["observed_patch_encoder_input_shape"] = shape
        model.backbone.vision_backbone.trunk.patch_embed.proj.register_forward_pre_hook(verify_backbone_input)
        selected = training_parameters(model)
        run["trainable_parameters"] = sum(parameter.numel() for _, parameter in selected)
        run["trainable_parameter_names"] = [name for name, _ in selected]
        run["model_geometry"] = getattr(model, "demo512_metadata", {})
        run["status"] = "training"
        write_json(destination / "학습기록.json", run)
        optimizer = torch.optim.AdamW([p for _, p in selected], lr=args.learning_rate, weight_decay=0.01)
        step, completed_epochs, final_loss = 0, 0, None
        torch.cuda.reset_peak_memory_stats()
        use_bfloat16 = torch.cuda.is_bf16_supported()
        amp_context = lambda: torch.autocast("cuda", dtype=torch.bfloat16) if use_bfloat16 else nullcontext()
        with (destination / "학습진행.jsonl").open("x", encoding="utf-8") as log:
            for epoch in range(args.epochs):
                schedule = build_schedule(tiles, args.seed, epoch)
                processed = 0
                epoch_start = time.monotonic()
                class_losses = {name: [] for name in CLASSES}
                for index, class_name in schedule:
                    tile = tiles[index]
                    image, target, valid = [t.to(args.device) for t in load_training_sample(dataset_root, tile, class_name)]
                    optimizer.zero_grad(set_to_none=True)
                    with amp_context():
                        logits = forward_class_logits(model, image, class_name)
                        loss = masked_segmentation_loss(logits, target, valid)
                    loss.backward()
                    if step == 0:
                        run["parameters_with_first_step_gradients"] = sum(p.numel() for _, p in selected if p.grad is not None)
                        run["selected_parameters_without_first_step_gradient"] = [name for name, p in selected if p.grad is None]
                    norm = torch.nn.utils.clip_grad_norm_([p for _, p in selected], 1.0, error_if_nonfinite=True)
                    optimizer.step()
                    step += 1
                    processed += 1
                    final_loss = float(loss.detach())
                    class_losses[class_name].append(final_loss)
                    record = {"step": step, "epoch": epoch + 1, "tile_id": tile["id"], "class": class_name,
                              "loss": final_loss, "grad_norm": float(norm), "input_shape": list(image.shape),
                              "target_shape": list(target.shape), "elapsed_seconds": time.monotonic() - started}
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    log.flush()
                    if step == 1 or step % 10 == 0 or args.max_steps == step:
                        print(json.dumps(record, ensure_ascii=False), flush=True)
                    if step == 1 or step % 100 == 0:
                        run.update(completed_steps=step, completed_epochs=completed_epochs,
                                   last_loss=final_loss, elapsed_seconds=time.monotonic() - started)
                        write_json(destination / "학습기록.json", run)
                    if args.max_steps is not None and step >= args.max_steps:
                        break
                if processed == len(schedule):
                    completed_epochs += 1
                epoch_info = {"epoch": epoch + 1, "complete": processed == len(schedule),
                              "steps": processed, "elapsed_seconds": time.monotonic() - epoch_start,
                              "mean_loss": sum(sum(values) for values in class_losses.values()) / processed,
                              "class_mean_loss": {name: sum(values) / len(values) if values else None
                                                  for name, values in class_losses.items()}}
                run["epoch_summaries"].append(epoch_info)
                run.update(completed_steps=step, completed_epochs=completed_epochs,
                           last_loss=final_loss, elapsed_seconds=time.monotonic() - started)
                if completed_epochs and completed_epochs % save_every == 0 and completed_epochs < args.epochs:
                    saved = save_checkpoint(model, destination, f"sam3_demo512_{completed_epochs:03d}회.pt", run)
                    run["intermediate_checkpoints"].append({"epoch": completed_epochs, **saved})
                write_json(destination / "학습기록.json", run)
                print(json.dumps({"epoch_summary": epoch_info}, ensure_ascii=False), flush=True)
                if args.max_steps is not None and step >= args.max_steps:
                    break
        limited = completed_epochs < args.epochs
        run.update(status="step_limited_check_complete" if limited else "requested_training_complete",
                   completed_steps=step, completed_epochs=completed_epochs, last_loss=final_loss,
                   elapsed_seconds=time.monotonic() - started,
                   peak_allocated_gpu_bytes=torch.cuda.max_memory_allocated(),
                   demo_quality_validated=False)
        name = "sam3_demo512_점검용.pt" if limited else "sam3_demo512_학습완료.pt"
        run["checkpoint"] = save_checkpoint(model, destination, name, run)
        run["elapsed_seconds"] = time.monotonic() - started
        write_json(destination / "학습기록.json", run)
        return run
    except BaseException as exc:
        run.update(status="failed", error_type=type(exc).__name__, error=str(exc),
                   elapsed_seconds=time.monotonic() - started)
        write_json(destination / "학습기록.json", run)
        raise


def add_training_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--data", required=True, help="데이터 준비로 생성된 폴더")
    parser.add_argument("--checkpoint", required=True, help="보존할 기존 SAM3 체크포인트")
    parser.add_argument("--output", required=True, help="새 학습 결과 폴더; 기존 폴더 사용 불가")
    parser.add_argument("--epochs", required=True, type=int, help="전체 데이터 반복 횟수")
    parser.add_argument("--max-steps", type=int, help="소량 학습 점검용 단계 제한; 최종 모델로 표시하지 않음")
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--device", choices=["cuda"], default="cuda")
    parser.add_argument("--save-every", type=int, default=5, help="몇 회 반복마다 중간 모델을 보존할지 지정")
