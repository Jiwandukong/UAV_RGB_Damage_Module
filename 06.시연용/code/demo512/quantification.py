"""GT-only demo deliverables using the existing OBJ ray/GSD report contract.

No checkpoint is loaded. Original annotations stay independent, including
overlapping shapes and shapes crossing tile boundaries. CSV columns are reused
verbatim; provenance, review flags and label-ID mappings belong in JSON only.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "03_Processing" / "src"))

from uav_rgb.asset_contract import load_mesh_asset_contract, verify_mesh_file, verify_loaded_mesh_geometry
from uav_rgb.camera_pose import read_dji_xmp
from uav_rgb.mesh_ray import MeshSurfaceIndex, build_mesh_ray_context_with_surface
from .report_contract import PRIMARY_COLUMNS, DAMAGE_NAMES_KO, write_csv, write_workbook, json_ready

from .data import CLASSES, OVERLAY_ALPHA, overlay_metadata, render_overlay, sha256_file
from .quant_geometry import quantify_source


REQUIRED_XMP = ("GpsLatitude", "GpsLongitude", "AbsoluteAltitude", "GimbalYawDegree",
                "GimbalPitchDegree", "GimbalRollDegree", "CalibratedFocalLength",
                "CalibratedOpticalCenterX", "CalibratedOpticalCenterY")
GSD_REVIEW_RATIO = 10.0


def _asset(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("input assets must remain inside the data bundle")
    return path


def _dump(path: Path, value) -> None:
    path.write_text(json.dumps(json_ready(value), ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def _check_source(root: Path, source: dict) -> Path:
    image = _asset(root, source["image_path"])
    labels = _asset(root, source["label_path"])
    if sha256_file(image) != source["image_sha256"] or sha256_file(labels) != source["label_sha256"]:
        raise ValueError(f"source image or labels changed: {source['id']}")
    with Image.open(image) as opened:
        if opened.size != (source["width"], source["height"]):
            raise ValueError("source dimensions differ from the dataset manifest")
    shapes = json.loads(labels.read_text(encoding="utf-8-sig"))["shapes"]
    annotations = sorted(source["annotations"], key=lambda ann: ann["shape_index"])
    if len(shapes) != len(annotations):
        raise ValueError("every original annotation must have exactly one exported row")
    for index, annotation in enumerate(annotations):
        if annotation["shape_index"] != index or annotation["original_shape"] != shapes[index]:
            raise ValueError("annotation differs from the preserved original JSON")
    xmp = read_dji_xmp(image)
    for name in REQUIRED_XMP:
        if name not in xmp or not math.isfinite(float(xmp[name])):
            raise ValueError(f"missing or non-finite DJI metadata: {image.name}: {name}")
    if float(xmp["CalibratedFocalLength"]) <= 0:
        raise ValueError("camera focal length must be positive")
    return image


def review_measurement(spatial: dict, focal_px: float) -> dict:
    """Conservative display gate, NOT a new GSD estimate or accuracy claim.

    For the user's roughly frontal imagery assumption, a local scale over 10x
    camera-to-hit distance / focal length needs manual review. Raw legacy
    measurements are preserved even when omitted from the public CSV.
    """
    reasons = []
    if not spatial.get("xyz_valid"):
        reasons.append(spatial.get("xyz_miss_reason") or "representative_ray_no_hit")
    if not spatial.get("measurement_valid"):
        reasons.append(spatial.get("measurement_miss_reason") or "local_gsd_unavailable")
    distance = spatial.get("mesh_ray_t_m")
    reference = float(distance) / float(focal_px) if distance is not None and distance > 0 else None
    scales = [spatial.get("gsd_length_m_per_px"), spatial.get("gsd_width_m_per_px")]
    scale = max((float(value) for value in scales if value is not None), default=None)
    ratio = scale / reference if reference and scale is not None else None
    if ratio is not None and (not math.isfinite(ratio) or ratio > GSD_REVIEW_RATIO):
        reasons.append("local_gsd_exceeds_10x_frontal_reference_manual_review")
    return {"physical_values_exported": not reasons,
            "reasons": reasons, "frontal_reference_m_per_px": reference,
            "max_directional_gsd_to_frontal_ratio": ratio,
            "review_ratio_threshold": GSD_REVIEW_RATIO}


def build_row(source: dict, annotation: dict, spatial: dict, damage_id: str,
              tiles: dict, focal_px: float) -> tuple[dict, dict]:
    links = list(annotation["tiles"])
    if not links or len({link["tile_id"] for link in links}) != len(links):
        raise ValueError("annotation tile references must be nonempty and unique")
    # The first display tile contains the exact representative ray's source pixel.
    px, py = spatial.get("image_pixel_x"), spatial.get("image_pixel_y")
    def order(link):
        tile = tiles[link["tile_id"]]
        match = px is not None and py is not None and (
            tile["x0"] <= px < tile["x0"] + tile["valid_width"]
            and tile["y0"] <= py < tile["y0"] + tile["valid_height"])
        return (not match, tile["y0"], tile["x0"])
    links.sort(key=order)
    for link in links:
        tile = tiles[link["tile_id"]]
        if annotation["damage_id"] not in tile["damage_ids"] or tile["source_id"] != source["id"]:
            raise ValueError("annotation-to-tile identity mismatch")
    original_paths = [f"512원본타일/{link['tile_id']}.png" for link in links]
    overlay_paths = [f"512라벨오버레이/{link['tile_id']}.png" for link in links]
    review = review_measurement(spatial, focal_px)
    row = dict.fromkeys(PRIMARY_COLUMNS)
    row.update(image=source["source_filename"], damage_id=damage_id,
               damage_type=annotation["label"], damage_name_ko=DAMAGE_NAMES_KO[annotation["label"]],
               pixel_nodes_json=spatial.get("nodes_image_xy_json"),
               world_center_x_m=spatial.get("world_x_m") if spatial.get("xyz_valid") else None,
               world_center_y_m=spatial.get("world_y_m") if spatial.get("xyz_valid") else None,
               world_center_z_m=spatial.get("world_z_m") if spatial.get("xyz_valid") else None,
               length_px=spatial.get("length_px"), width_px=spatial.get("width_px"),
               source_image_path=f"원본사진/{source['source_filename']}",
               tile_original_paths_json=json.dumps(original_paths, ensure_ascii=False, separators=(",", ":")),
               tile_overlay_paths_json=json.dumps(overlay_paths, ensure_ascii=False, separators=(",", ":")))
    if review["physical_values_exported"]:
        row.update({key: spatial.get(key) for key in ("length_m", "width_m", "area_m2")})
    mapping = {"damage_id": damage_id, "source_annotation_id": annotation["damage_id"],
               "image": source["source_filename"], "shape_index": annotation["shape_index"],
               "label": annotation["label"], "representative_source_pixel_xy": [px, py],
               "tile_ids": [link["tile_id"] for link in links],
               "review": review, "raw_legacy_mapping_and_measurement": spatial}
    return row, mapping


def _save_tiles(root: Path, destination: Path, tiles: list[dict]) -> list[dict]:
    mappings = []
    for index, tile in enumerate(tiles, 1):
        source_path = _asset(root, tile["image_path"])
        with Image.open(source_path) as opened:
            if opened.size != (512, 512) or opened.mode != "RGB":
                raise ValueError("display source tile must be untouched 512x512 RGB")
            original = opened.copy()
        masks = {}
        for label in CLASSES:
            with Image.open(_asset(root, tile["mask_paths"][label])) as opened:
                masks[label] = opened.copy()
            values = np.asarray(masks[label])
            if int(np.count_nonzero(values)) != tile["positive_pixels"][label]:
                raise ValueError("GT tile mask count differs from dataset")
            if values[tile["valid_height"]:, :].any() or values[:, tile["valid_width"]:].any():
                raise ValueError("GT pixels outside the valid photo area")
        image_path = f"512원본타일/{tile['id']}.png"
        overlay_path = f"512라벨오버레이/{tile['id']}.png"
        shutil.copyfile(source_path, destination / image_path)
        render_overlay(original, masks, alpha=OVERLAY_ALPHA).save(destination / overlay_path)
        mappings.append({"tile_id": tile["id"], "source_id": tile["source_id"],
                         "x0": tile["x0"], "y0": tile["y0"],
                         "valid_width": tile["valid_width"], "valid_height": tile["valid_height"],
                         "source_annotation_ids": tile["damage_ids"],
                         "image_path": image_path, "overlay_path": overlay_path,
                         "original_sha256": sha256_file(destination / image_path),
                         "overlay_sha256": sha256_file(destination / overlay_path)})
        if index % 100 == 0 or index == len(tiles):
            print(f"시연 이미지 저장: {index}/{len(tiles)} 타일", flush=True)
    return mappings


def _readme(summary: dict) -> str:
    return f"""# 대청댐 시연용 산출물

검수된 손상 라벨을 기준으로 만든 자료입니다. **모델의 자동 탐지 결과나 실제 측량 결과가 아닙니다.**

## 바로 사용할 파일

- `damage_results.csv`: UTF-8 BOM CSV, 손상 라벨 하나당 한 행.
- `damage_results.xlsx`: 같은 내용의 Excel (`Damage_Details` 시트).
- `원본사진/`: 촬영 정보까지 보존한 원본 JPG.
- `512원본타일/`, `512라벨오버레이/`: 같은 파일명끼리 대응하는 512×512 이미지. 확대·축소 없음. 오버레이 색상 불투명도50%.
- `연결정보.json`: CSV 손상 ID와 기존 라벨 ID, 타일 시작 위치를 연결하는 기록.
- `정량계산기록.json`: 사진별 촬영 정보, Ray/GSD 계산 근거, 계산 실패·검토 사유.

이번 결과: 원본{summary['images']}장, 라벨{summary['rows']}행, 손상 타일{summary['tiles']}개.
좌표 계산 성공{summary['mapped_rows']}행, 정량값 표출{summary['physical_values_exported']}행,
정량값 보류{summary['physical_values_withheld']}행입니다. **빈칸은0이 아닙니다.**

## 표출과 연결에 사용하는 열

| 열 | 의미 |
|---|---|
| `image` | 잘리기 전 원본 JPG 파일명 |
| `damage_id` | 이번 산출물 내 손상 ID (`D000001` 형식) |
| `damage_type` | CRC=Crack(균열), DLM=Delamination(박리), SPL=Spalling(박락) |
| `damage_name_ko` | 손상 종류의 한글 이름 |
| `pixel_nodes_json` | 원본 사진 좌표의 외곽선 표본 `[[x,y],...]`. 타일 좌표가 아님 |
| `world_center_x_m`, `world_center_y_m`, `world_center_z_m` | 3D 표시점. X/Y는EPSG:5186, Z는기존OBJ 고도, 단위m |
| `source_image_path` | 원본 JPG 상대경로 |
| `tile_original_paths_json` | 해당 손상이 있는 원본 타일 경로의 JSON 배열 |
| `tile_overlay_paths_json` | 위 배열과 같은 순서의 라벨 오버레이 경로 배열 |

**모든 경로의 기준은 이 README와 CSV가 있는 폴더입니다.** 이미지까지 이 폴더를 통째로 전달하면 됩니다.
타일 배열의 첫 번째 항목은 대표점에 대응하는 기본 표출 타일입니다. 같은 손상이 여러 타일에 걸쳐도 CSV 행과 정량값을 중복 생성하지 않습니다.
원본 픽셀 좌표를 타일 좌표로 바꿀 때는 `연결정보.json`에 기록된 `x0`, `y0`를 뺍니다.
좌표가 빈 행에는 임의의3D 마커를 만들지 말고 이미지 목록에서 확인하십시오.

## 정량값에 사용하는 열

| 열 | 의미 |
|---|---|
| `length_px`, `length_m` | CRC 라벨을 둘러싼 최소면적 회전사각형의 긴 변. 각각px와m |
| `width_px`, `width_m` | 같은 사각형의 짧은 변. 각각px와m |
| `area_m2` | DLM/SPL 라벨 마스크의 근사 표면 면적, m² |

CRC의 `area_m2`와 DLM/SPL의 길이·폭은 기존 산출물 규칙에 따라 빈칸입니다.
**CRC 폭은 실제 균열의 벌어진 폭이 아닙니다.** 1픽셀 중심선 라벨만 있어 실제 개구폭을 알 수 없습니다.
굽은 선의 회전사각형 폭은1픽셀보다 클 수 있고, 길이도 선을 따라 잰 전체 경로 길이가 아닙니다.

## 계산 방법과 한계

기존 `dam - Cloud.obj`와 각 원본 JPG의 촬영 위치·방향·초점 정보를 사용했습니다. 다른 비행의MRK나 새GLB를 사용하지 않았습니다.
기존 방식대로 손상 주변4개 픽셀 위치의 Ray와OBJ 교점을 이용해 방향별GSD를 구합니다.
CRC 사각형 길이·폭에 해당 방향GSD를 곱하고, DLM/SPL 픽셀 수에는 국부 픽셀 표면 면적을 곱합니다.

- Ray가OBJ와 만나지 않거나GSD를 계산할 수 없으면 관련 값을 빈칸으로 둡니다.
- 정면 촬영을 가정한 거리/초점 기준보다 국부GSD가10배 넘으면 검토 대상으로 보고 물리 정량값을 보류했습니다. 이는 메시 경계의 불연속을 걸러내는 경험적 검토 기준이지 정확도 보증이 아닙니다.
- 보류된 항목도 행·라벨·이미지 연결은 유지합니다. 기존 수식의 원계산값과 사유는 `정량계산기록.json`에 따로 보존합니다. 다른 손상의GSD나 임의 좌표로 채우지 않습니다.
- GPS고도와OBJ고도의 수직 기준 일치 여부, 렌즈 왜곡은 검증·보정하지 않았습니다. 모든 정량값은 시연용 근사치입니다.
- 서로 겹친 라벨이나 다른 사진의 같은 물리 손상을 합치지 않았습니다. 전체 행의 합계를 댐 전체 손상 총량으로 해석하지 마십시오.

기존13개 산출물 열과 이미 승인된3개 이미지 연결 열, 총16개를 유지했습니다. 품질·GSD·날짜 등 새로운CSV 열이나Excel 시트는 추가하지 않았습니다.
"""


def export_demo(data: str | Path, output: str | Path, mesh: str | Path,
                asset_manifest: str | Path | None = None, *,
                ray_backend: str = "auto", warp_device: str = "cpu") -> dict:
    started = time.monotonic()
    root = Path(data).resolve(strict=True)
    requested = Path(output).expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise FileExistsError(f"refusing to overwrite an existing deliverable: {requested}")
    destination = requested.resolve()
    if destination.is_relative_to(root):
        raise ValueError("deliverables must not be placed inside the immutable training dataset")
    dataset_path = root / "dataset.json"
    dataset_hash = sha256_file(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if dataset.get("tile_size") != 512 or tuple(dataset.get("classes", ())) != CLASSES:
        raise ValueError("expected the preserved native512 CRC/DLM/SPL dataset")
    sources = sorted(dataset["sources"], key=lambda source: source["id"])
    tiles = {tile["id"]: tile for tile in dataset["tiles"]}
    if len(tiles) != len(dataset["tiles"]):
        raise ValueError("tile IDs must be unique")
    annotation_ids = [ann["damage_id"] for source in sources for ann in source["annotations"]]
    if not annotation_ids or len(set(annotation_ids)) != len(annotation_ids):
        raise ValueError("source annotation IDs must be unique and nonempty")
    source_paths = {source["id"]: _check_source(root, source) for source in sources}
    manifest_path = Path(asset_manifest) if asset_manifest else PROJECT_ROOT / "01_RawData/manifests/assets.yaml"
    contract = load_mesh_asset_contract(manifest_path)
    mesh_path = Path(mesh).resolve(strict=True)
    print("기존 OBJ의 파일 크기·SHA256 확인", flush=True)
    mesh_verification = verify_mesh_file(mesh_path, contract)
    surface = MeshSurfaceIndex(mesh_path, ray_backend=ray_backend, warp_device=warp_device)
    geometry_verification = verify_loaded_mesh_geometry(
        vertex_count=surface.vertex_count, face_count=surface.face_count,
        bounds=surface.bounds, contract=contract)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".demo-quantification-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        for folder in ("원본사진", "512원본타일", "512라벨오버레이"):
            (staging / folder).mkdir()
        rows, calculations, image_records = [], [], []
        for number, source in enumerate(sources, 1):
            image = source_paths[source["id"]]
            print(f"라벨 정량 계산: {number}/{len(sources)} {image.name}", flush=True)
            context = build_mesh_ray_context_with_surface(
                image, surface, mrk_path=None, representative_mode="centroid",
                node_sample_count=256, ray_batch_size=256)
            results = quantify_source(root, source, context)
            for result in results:
                row, calculation = build_row(source, result["annotation"], result["spatial"],
                                             f"D{len(rows) + 1:06d}", tiles,
                                             context.intrinsics.focal_length_px)
                calculation["label_area_px"] = result["base"]["area_px"]
                rows.append(row)
                calculations.append(calculation)
            shutil.copyfile(image, staging / "원본사진" / image.name)
            if sha256_file(staging / "원본사진" / image.name) != source["image_sha256"]:
                raise ValueError("source changed while copying")
            image_records.append({"image": image.name, "image_sha256": source["image_sha256"],
                                  "label_sha256": source["label_sha256"],
                                  "annotation_count": len(results), "mapping": context.to_dict()})
        if len(rows) != len(annotation_ids):
            raise ValueError("one-row-per-original-annotation contract was violated")
        used_tiles = {tile_id for calculation in calculations for tile_id in calculation["tile_ids"]}
        tile_records = _save_tiles(root, staging, [tiles[tile_id] for tile_id in sorted(used_tiles)])
        for row in rows:
            for key in ("tile_original_paths_json", "tile_overlay_paths_json"):
                for relative in json.loads(row[key]):
                    if not (staging / relative).is_file():
                        raise ValueError("missing linked output image")
        summary = {"images": len(sources), "rows": len(rows), "tiles": len(used_tiles),
                   "class_rows": dict(Counter(row["damage_type"] for row in rows)),
                   "mapped_rows": sum(row["world_center_x_m"] is not None for row in rows),
                   "physical_values_exported": sum(item["review"]["physical_values_exported"] for item in calculations),
                   "physical_values_withheld": sum(not item["review"]["physical_values_exported"] for item in calculations),
                   "review_reasons": dict(Counter(reason for item in calculations for reason in item["review"]["reasons"]))}
        write_csv(staging / "damage_results.csv", rows, PRIMARY_COLUMNS)
        write_workbook(staging / "damage_results.xlsx", rows=rows)
        connections = {"path_base": "this_output_folder", "tile_size": 512,
                       "columns": list(PRIMARY_COLUMNS), "overlay": overlay_metadata(),
                       "tiles": tile_records,
                       "damages": [{key: value for key, value in item.items()
                                    if key not in {"review", "raw_legacy_mapping_and_measurement"}}
                                   for item in calculations]}
        _dump(staging / "연결정보.json", connections)
        record = {"created_utc": datetime.now(timezone.utc).isoformat(),
                  "result_source": "human_reviewed_labels_not_model_predictions",
                  "model_loaded": False, "source_resized": False,
                  "dataset_manifest_sha256": dataset_hash, "summary": summary,
                  "mesh": {"contract": contract.to_dict(), "file_verification": mesh_verification,
                           "geometry_verification": geometry_verification,
                           "ray_backend": surface.ray_backend, "warp_device": warp_device},
                  "columns": list(PRIMARY_COLUMNS), "crc_width_is_physical_aperture": False,
                  "approximate": True, "review_ratio_threshold": GSD_REVIEW_RATIO,
                  "images": image_records, "damages": calculations,
                  "elapsed_seconds": time.monotonic() - started}
        _dump(staging / "정량계산기록.json", record)
        (staging / "README.md").write_text(_readme(summary), encoding="utf-8")
        if sha256_file(dataset_path) != dataset_hash:
            raise ValueError("immutable dataset manifest changed during export")
        staging.rename(destination)
    return {"output": str(destination), **summary, "elapsed_seconds": time.monotonic() - started}
