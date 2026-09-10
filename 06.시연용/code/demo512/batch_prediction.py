"""Predict every damage class, then check exact pixels on the training images.

GT metadata selects tiles when requested. The prediction function receives only
RGB pixels and source geometry; GT masks are opened only after all three model
masks have been thresholded and saved. GT never changes a model prediction.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image
import torch

from . import CLASSES, INPUT_SIZE
from .data import overlay_metadata, render_overlay
from .training import asset_path, read_binary, read_rgb, sha256_file, write_json


CHECK_SCOPE = "SAME_TRAINING_IMAGES_REPRODUCTION_CHECK"
MANIFEST_NAME = "배치예측정보.json"
METRICS_NAME = "재현점검.json"
PROGRESS_NAME = "배치예측진행.jsonl"
COUNT_KEYS = ("tp", "fp", "fn", "tn")


def _counts(prediction: np.ndarray, target: np.ndarray, valid: np.ndarray) -> dict:
    return {
        "tp": int(np.count_nonzero(prediction & target & valid)),
        "fp": int(np.count_nonzero(prediction & ~target & valid)),
        "fn": int(np.count_nonzero(~prediction & target & valid)),
        "tn": int(np.count_nonzero(~prediction & ~target & valid)),
    }


def _metrics(counts: dict) -> dict:
    tp, fp, fn, tn = (counts[key] for key in COUNT_KEYS)
    divide = lambda numerator, denominator: numerator / denominator if denominator else None
    return {
        **counts, "valid_pixels": tp + fp + fn + tn,
        "reference_positive_pixels": tp + fn, "predicted_positive_pixels": tp + fp,
        "precision": divide(tp, tp + fp), "recall": divide(tp, tp + fn),
        "iou": divide(tp, tp + fp + fn), "f1": divide(2 * tp, 2 * tp + fp + fn),
    }


def _new_totals() -> dict:
    return {label: {**dict.fromkeys(COUNT_KEYS, 0), "tile_class_pairs": 0} for label in CLASSES}


def _add_counts(totals: dict, label: str, counts: dict) -> None:
    for key in COUNT_KEYS:
        totals[label][key] += counts[key]
    totals[label]["tile_class_pairs"] += 1


def _summarize(totals: dict) -> dict:
    by_class = {label: _metrics(counts) for label, counts in totals.items()}
    micro = _metrics({key: sum(counts[key] for counts in totals.values())
                      for key in (*COUNT_KEYS, "tile_class_pairs")})
    macro = {}
    for key in ("iou", "f1"):
        defined = [value[key] for value in by_class.values() if value[key] is not None]
        macro[key] = sum(defined) / len(defined) if defined else None
        macro[f"{key}_defined_classes"] = len(defined)
    return {"by_class": by_class, "micro": micro, "macro": macro}


def _valid_geometry(tile: dict) -> np.ndarray:
    width, height = tile["valid_width"], tile["valid_height"]
    if any(isinstance(value, bool) or not isinstance(value, int)
           or not 1 <= value <= INPUT_SIZE for value in (width, height)):
        raise ValueError("valid width/height must be integers in 1..512")
    valid = np.zeros((INPUT_SIZE, INPUT_SIZE), dtype=bool)
    valid[:height, :width] = True
    return valid


def _predict_masks(model, rgb, valid, threshold, device, forward, use_bfloat16) -> dict:
    """No GT, tile metadata, annotations, or dataset paths enter this function."""
    tensor = torch.from_numpy(rgb.copy()).permute(2, 0, 1).float().div(255).unsqueeze(0).to(device)
    context = torch.autocast("cuda", dtype=torch.bfloat16) if use_bfloat16 else nullcontext()
    masks = {}
    with torch.no_grad(), context:
        for label in CLASSES:
            logits = forward(model, tensor, label)
            if tuple(logits.shape) != (1, 1, INPUT_SIZE, INPUT_SIZE):
                raise ValueError("model must return native [1,1,512,512] semantic logits")
            if not bool(torch.isfinite(logits).all()):
                raise ValueError("non-finite model logits")
            masks[label] = (logits.float().sigmoid()[0, 0].cpu().numpy() >= threshold) & valid
    return masks


def _save_model_outputs(destination: Path, tile_id: str, source: Path, rgb, masks) -> dict:
    image_path = f"원본타일/{tile_id}.png"
    overlay_path = f"모델예측오버레이/{tile_id}.png"
    mask_paths = {label: f"모델예측마스크/{label}/{tile_id}.png" for label in CLASSES}
    shutil.copyfile(source, destination / image_path)
    display_masks = {}
    for label in CLASSES:
        display_masks[label] = Image.fromarray(masks[label].astype(np.uint8) * 255)
        display_masks[label].save(destination / mask_paths[label])
    render_overlay(Image.fromarray(rgb), display_masks).save(destination / overlay_path)
    return {"image_path": image_path, "model_overlay_path": overlay_path,
            "model_mask_paths": mask_paths}


def _evaluate_saved_prediction(dataset_root, destination, tile, masks, valid, rgb):
    """Called only after every model mask and the model overlay are saved."""
    recorded_valid = read_binary(asset_path(dataset_root, tile["valid_mask_path"]))
    if not np.array_equal(recorded_valid, valid):
        raise ValueError(f"valid mask disagrees with source geometry: {tile['id']}")
    counts = {}
    positive_classes = []
    display_targets = {}
    for label in CLASSES:
        target = read_binary(asset_path(dataset_root, tile["mask_paths"][label]))
        if (target & ~valid).any():
            raise ValueError(f"GT pixels fall outside the source image: {tile['id']} / {label}")
        if int(target.sum()) != tile["positive_pixels"][label]:
            raise ValueError(f"GT pixel count differs from dataset manifest: {tile['id']} / {label}")
        counts[label] = _counts(masks[label], target, valid)
        display_targets[label] = Image.fromarray(target.astype(np.uint8) * 255)
        if target.any():
            positive_classes.append(label)
    gt_path = f"라벨오버레이/{tile['id']}.png"
    # Historical datasets can contain opaque overlays. Keep that dataset and
    # its recorded SHA untouched, and render this run's display from binary GT.
    render_overlay(Image.fromarray(rgb), display_targets).save(destination / gt_path)
    return counts, positive_classes, gt_path


def _validate_and_select(manifest, selection, max_tiles):
    if manifest.get("tile_size") != INPUT_SIZE or tuple(manifest.get("classes", ())) != CLASSES:
        raise ValueError("dataset must contain native 512px CRC/DLM/SPL tiles")
    if selection not in {"positive", "all"}:
        raise ValueError("selection must be 'positive' or 'all'")
    if max_tiles is not None and (isinstance(max_tiles, bool)
                                 or not isinstance(max_tiles, int) or max_tiles < 1):
        raise ValueError("max_tiles must be a positive integer")
    tiles = manifest["tiles"]
    seen = set()
    for tile in tiles:
        tile_id = tile["id"]
        if (not isinstance(tile_id, str) or not tile_id or tile_id in {".", ".."}
                or "/" in tile_id or "\\" in tile_id or tile_id in seen):
            raise ValueError("tile IDs must be unique portable filenames")
        seen.add(tile_id)
    selected = [tile for tile in tiles if selection == "all"
                or any(tile["positive_pixels"][label] > 0 for label in CLASSES)]
    selected.sort(key=lambda tile: tile["id"])
    available = len(selected)
    if max_tiles is not None:
        selected = selected[:max_tiles]
    if not selected:
        raise ValueError("selection contains no tiles")
    for tile in selected:
        _valid_geometry(tile)
    return selected, available


def run_batch_prediction(args) -> dict:
    """Load one recorded checkpoint and save/evaluate all three classes per tile.

    Required Namespace attributes: data, model_record, output. Optional:
    selection='positive', threshold=0.5, max_tiles=None, device='auto',
    progress_every=10. A max_tiles limit is explicitly marked as a smoke check.
    Existing output folders are refused, including folders from failed runs.
    """
    from .model import build_demo_model, forward_class_logits

    dataset_root = Path(args.data).expanduser().resolve(strict=True)
    manifest_path = dataset_root / "dataset.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selection = getattr(args, "selection", "positive")
    max_tiles = getattr(args, "max_tiles", None)
    tiles, available = _validate_and_select(manifest, selection, max_tiles)
    threshold = getattr(args, "threshold", 0.5)
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError("threshold must be finite and strictly between zero and one")
    progress_every = getattr(args, "progress_every", 10)
    if isinstance(progress_every, bool) or not isinstance(progress_every, int) or not 1 <= progress_every <= 25:
        raise ValueError("progress_every must be an integer in 1..25")
    record_path = Path(args.model_record).expanduser().resolve(strict=True)
    training = json.loads(record_path.read_text(encoding="utf-8"))
    dataset_hash = sha256_file(manifest_path)
    if training.get("dataset_manifest_sha256") != dataset_hash:
        raise ValueError("dataset manifest SHA-256 does not match the training record")
    saved = training["checkpoint"]
    checkpoint = asset_path(record_path.parent, saved["file"])
    if sha256_file(checkpoint) != saved["sha256"]:
        raise ValueError("checkpoint SHA-256 does not match the training record")
    device = getattr(args, "device", "auto")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device not in {"cuda", "cpu"} or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("device must be cpu or an available cuda device")
    use_bfloat16 = device == "cuda" and torch.cuda.is_bf16_supported()
    destination = Path(args.output).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing batch output: {destination}")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for folder in ("원본타일", "모델예측오버레이", "라벨오버레이",
                   *(f"모델예측마스크/{label}" for label in CLASSES)):
        (destination / folder).mkdir(parents=True)
    started = time.monotonic()
    run = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "initializing", "check_scope": CHECK_SCOPE,
        "generalization_evaluation": False, "official_accuracy_claim": False,
        "input_size": [INPUT_SIZE, INPUT_SIZE], "input_resized": False,
        "prediction_source": "actual_model_semantic_logits",
        "ground_truth_used_for_prediction": False,
        "ground_truth_metadata_used_for_tile_selection": selection == "positive",
        "ground_truth_read_after_all_tile_predictions_are_saved": True,
        "dataset_manifest_sha256": dataset_hash,
        "model_record_name": record_path.name, "model_record_sha256": sha256_file(record_path),
        "checkpoint_name": checkpoint.name, "checkpoint_sha256": saved["sha256"],
        "training_status": training.get("status"), "readout": training.get("readout"),
        "selection": selection, "dataset_tiles": len(manifest["tiles"]),
        "selection_available_tiles": available, "requested_tiles": len(tiles),
        "max_tiles": max_tiles, "smoke_check": max_tiles is not None,
        "completed_tiles": 0, "queried_classes_per_tile": list(CLASSES),
        "threshold": threshold, "threshold_rule": "sigmoid(logits) >= threshold",
        "device": device, "autocast_dtype": "bfloat16" if use_bfloat16 else None,
        "padding_excluded_from_masks_and_metrics": True,
        "independent_class_masks": True,
        "overlay": {
            **overlay_metadata(),
            "model_folder": "모델예측오버레이", "ground_truth_folder": "라벨오버레이",
            "ground_truth_source": "human_reviewed_dataset_labels",
            "ground_truth_rendering": "re-rendered from original RGB and binary GT masks; historical dataset overlay not copied",
        },
        "metrics_path": METRICS_NAME, "progress_path": PROGRESS_NAME, "tiles": [],
    }
    write_json(destination / MANIFEST_NAME, run)
    all_totals, positive_totals = _new_totals(), _new_totals()
    current_tile = None
    try:
        model = build_demo_model(checkpoint, device, checkpoint_kind="demo", expected_sha256=saved["sha256"])
        model.eval()
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        run["status"] = "predicting"
        write_json(destination / MANIFEST_NAME, run)
        with (destination / PROGRESS_NAME).open("x", encoding="utf-8") as progress:
            for index, tile in enumerate(tiles, 1):
                current_tile = tile["id"]
                source = asset_path(dataset_root, tile["image_path"])
                rgb, valid = read_rgb(source), _valid_geometry(tile)
                masks = _predict_masks(model, rgb, valid, threshold, device, forward_class_logits, use_bfloat16)
                paths = _save_model_outputs(destination, tile["id"], source, rgb, masks)
                # Labels are opened for the first time after predictions exist on disk.
                counts, positive_classes, gt_path = _evaluate_saved_prediction(
                    dataset_root, destination, tile, masks, valid, rgb)
                for label in CLASSES:
                    _add_counts(all_totals, label, counts[label])
                    if label in positive_classes:
                        _add_counts(positive_totals, label, counts[label])
                run["tiles"].append({
                    "id": tile["id"], "source_id": tile.get("source_id"),
                    "damage_ids": list(tile.get("damage_ids", [])),
                    "x0": tile.get("x0"), "y0": tile.get("y0"),
                    "valid_width": tile["valid_width"], "valid_height": tile["valid_height"],
                    **paths, "ground_truth_overlay_path": gt_path,
                    "model_positive_pixels": {label: int(masks[label].sum()) for label in CLASSES},
                    "ground_truth_positive_classes": positive_classes,
                    "metrics_by_class": {label: _metrics(counts[label]) for label in CLASSES},
                })
                run["completed_tiles"] = index
                if index == 1 or index % progress_every == 0 or index == len(tiles):
                    elapsed = time.monotonic() - started
                    event = {"completed_tiles": index, "requested_tiles": len(tiles),
                             "tile_id": tile["id"], "elapsed_seconds": elapsed,
                             "estimated_remaining_seconds": elapsed / index * (len(tiles) - index)}
                    progress.write(json.dumps(event, ensure_ascii=False) + "\n")
                    progress.flush()
                    run["elapsed_seconds"] = elapsed
                    write_json(destination / MANIFEST_NAME, run)
                    print(json.dumps(event, ensure_ascii=False), flush=True)
        if sha256_file(manifest_path) != dataset_hash or sha256_file(record_path) != run["model_record_sha256"]:
            raise ValueError("dataset manifest or model record changed during prediction")
        metrics = {
            "check_scope": CHECK_SCOPE, "generalization_evaluation": False,
            "official_accuracy_claim": False, "selection": selection,
            "smoke_check": max_tiles is not None, "evaluated_tiles": len(tiles),
            "threshold": threshold, "checkpoint_sha256": saved["sha256"],
            "dataset_manifest_sha256": dataset_hash,
            "pixel_matching": "exact same-position valid pixels; no tolerance or morphology",
            "zero_denominator": "null (undefined); macro mean excludes undefined classes",
            "class_overlap": "each class evaluated independently, including overlapping pixels",
            "all_queried_classes": _summarize(all_totals),
            "positive_ground_truth_class_pairs_only": _summarize(positive_totals),
            "positive_subset_warning": "excludes absent-class queries; use all_queried_classes to include their false positives",
        }
        write_json(destination / METRICS_NAME, metrics)
        run.update(status="smoke_check_complete" if max_tiles is not None else "reproduction_check_complete",
                   elapsed_seconds=time.monotonic() - started)
        write_json(destination / MANIFEST_NAME, run)
        return run
    except BaseException as exc:
        run.update(status="failed", error_type=type(exc).__name__, error=str(exc),
                   failed_tile_id=current_tile, elapsed_seconds=time.monotonic() - started)
        write_json(destination / MANIFEST_NAME, run)
        raise


def add_batch_prediction_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data", required=True, help="512 원본 타일과 라벨이 포함된 시연 데이터 폴더")
    parser.add_argument("--model-record", required=True, help="저장 체크포인트가 기록된 학습기록.json")
    parser.add_argument("--output", required=True, help="새 배치 결과 폴더; 기존 폴더 사용 불가")
    parser.add_argument("--selection", choices=["positive", "all"], default="positive",
                        help="positive: 손상 있는 타일; all: 배경 타일 포함. 각 타일의 세 클래스 모두 예측")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--max-tiles", type=int, help="소량 동작 점검용 타일 제한; 정식 전체 결과로 표시하지 않음")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--progress-every", type=int, default=10, help="진행 기록 간격 (1~25 타일)")
