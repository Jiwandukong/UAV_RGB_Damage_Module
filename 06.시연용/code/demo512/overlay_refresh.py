"""Redraw saved batch previews only; never run or modify the model or masks."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image

from .data import CLASSES, OVERLAY_ALPHA, overlay_metadata, render_overlay, sha256_file


def _asset(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("asset paths must be relative and stay inside their bundle")
    return path


def _image(path: Path, mode: str) -> Image.Image:
    with Image.open(path) as image:
        if image.size != (512, 512) or image.mode != mode:
            raise ValueError(f"expected 512x512 {mode}: {path}")
        result = image.copy()
    if mode == "L" and not np.isin(np.asarray(result), [0, 255]).all():
        raise ValueError(f"mask is not binary: {path}")
    return result


def refresh_batch_overlays(data: str | Path, results: str | Path,
                           alpha: float = OVERLAY_ALPHA) -> dict:
    """Stage all images before replacing the two display folders in-place.

    dataset.json is an immutable training snapshot: its old overlay style stays
    intact. Only the separate batch display copies and their style record change.
    Repeating this operation always starts from the original RGB, not a blended
    preview. Thus applying the same alpha twice does not accumulate opacity.
    """
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("alpha must be finite and in 0..1 (0=original, 1=solid)")
    root, destination = Path(data).resolve(strict=True), Path(results).resolve(strict=True)
    dataset_path = root / "dataset.json"
    manifest_path = destination / "배치예측정보.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_hash = sha256_file(dataset_path)
    if dataset_hash != manifest["dataset_manifest_sha256"]:
        raise ValueError("dataset manifest does not match the saved predictions")
    if manifest["status"] not in {"reproduction_check_complete", "smoke_check_complete"}:
        raise ValueError("only completed batch results may be refreshed")
    if len(manifest["tiles"]) != manifest["completed_tiles"] or not manifest["tiles"]:
        raise ValueError("saved tile list is incomplete")
    lookup = {tile["id"]: tile for tile in dataset["tiles"]}
    protected_hashes = {dataset_path: dataset_hash,
                        manifest_path: sha256_file(manifest_path)}
    for name in ("재현점검.json", "배치예측진행.jsonl"):
        path = destination / name
        if path.exists():
            protected_hashes[path] = sha256_file(path)
    old_style = dict(manifest["overlay"])
    planned = []
    targets = set()
    # Validate and render every tile before changing any existing preview.
    with tempfile.TemporaryDirectory(prefix=".overlay-refresh-", dir=destination) as temporary:
        staging = Path(temporary)
        for index, tile in enumerate(manifest["tiles"]):
            source_tile = lookup[tile["id"]]
            original = _asset(destination, tile["image_path"])
            original_hash = sha256_file(original)
            if original_hash != sha256_file(_asset(root, source_tile["image_path"])):
                raise ValueError(f"original tile differs from training data: {tile['id']}")
            protected_hashes[original] = original_hash
            rgb = _image(original, "RGB")
            valid_path = _asset(root, source_tile["valid_mask_path"])
            protected_hashes[valid_path] = sha256_file(valid_path)
            valid = np.asarray(_image(valid_path, "L")) > 0
            for key, mask_root, mask_paths, folder in (
                ("model_overlay_path", destination, tile["model_mask_paths"], "모델예측오버레이"),
                ("ground_truth_overlay_path", root, source_tile["mask_paths"], "라벨오버레이"),
            ):
                relative = tile[key]
                if relative != f"{folder}/{tile['id']}.png":
                    raise ValueError("only the recorded batch overlay PNGs may be replaced")
                target = _asset(destination, relative)
                if target != destination / relative:
                    raise ValueError("overlay replacement must not follow symbolic links")
                if target in targets:
                    raise ValueError("duplicate overlay target")
                targets.add(target)
                masks = {}
                for label in CLASSES:
                    mask_path = _asset(mask_root, mask_paths[label])
                    protected_hashes[mask_path] = sha256_file(mask_path)
                    masks[label] = _image(mask_path, "L")
                    if (np.asarray(masks[label])[~valid] > 0).any():
                        raise ValueError("damage mask includes pixels outside the original photo")
                staged = staging / relative
                staged.parent.mkdir(parents=True, exist_ok=True)
                render_overlay(rgb, masks, alpha=alpha).save(staged)
                planned.append((staged, target))
            if (index + 1) % 100 == 0:
                print(f"오버레이 준비: {index + 1}/{len(manifest['tiles'])} 타일", flush=True)
        for path, digest in protected_hashes.items():
            if sha256_file(path) != digest:
                raise ValueError(f"source changed during overlay refresh: {path.name}")
        manifest["overlay"].update(overlay_metadata(alpha))
        manifest["overlay"]["ground_truth_rendered_from"] = "unchanged dataset class masks and original RGB"
        report = {
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "display_only": True, "model_inference_rerun": False,
            "dataset_manifest_sha256": dataset_hash,
            "checkpoint_sha256": manifest["checkpoint_sha256"],
            "previous_overlay_style": old_style, "alpha": alpha,
            "tiles": len(manifest["tiles"]), "overlay_images_updated": len(planned),
            "originals_and_masks_unchanged": True, "metrics_unchanged": True,
            "historical_training_dataset_unchanged": True,
        }
        for name, value in ((manifest_path.name, manifest), ("오버레이변경기록.json", report)):
            (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        for staged, target in planned:
            staged.replace(target)
        (staging / manifest_path.name).replace(manifest_path)
        (staging / "오버레이변경기록.json").replace(destination / "오버레이변경기록.json")
    return report
