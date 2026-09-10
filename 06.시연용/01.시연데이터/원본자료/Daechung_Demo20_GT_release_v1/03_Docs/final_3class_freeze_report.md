# Daechung demo20 최종 3-class GT freeze audit

DEMO20_FINAL_3CLASS_FREEZE_AUDIT = PASS

작성 시각: 2026-09-09T10:44:53.346619+00:00 (UTC)

FINAL source: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1`

dataset_role = Reviewed Daechung demo20 3-class GT

현재 FINAL JSON은 사람 검수가 완료된 authoritative annotation이다. 이 audit는 annotation을 수정하지 않고 파일 pairing, 이미지 decode, geometry, CRC 동결 기준 및 source integrity를 검증했다. 후보 JSON은 비교용 reference로만 읽었다.

## 전체 결과

```text
DEMO20_FINAL_3CLASS_FREEZE_AUDIT = PASS
final_root = /data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1
jpg_count = 20
json_count = 20
pairing = 20/20
imagePath_pairing = 20/20
json_parse_pass = 20/20
decode_pass = 20/20
resolution_5280x3956 = 20/20
rgb_images = 20/20
duplicate_basename = 0
duplicate_image_sha256_pairs = 0
total_shapes = 629
total_crc = 312
total_dlm = 86
total_spl = 231
total_delete_roi = 0
total_other_labels = 0
CRC_COUNT_UNCHANGED = PASS
CRC_GEOMETRY_UNCHANGED = PASS
crc_linestrip_valid = 312/312
dlm_polygon_valid = 86/86
spl_polygon_valid = 231/231
NaN = 0
inf = 0
invalid_coordinate = 0
out_of_bounds = 0
degenerate_crc = 0
degenerate_polygon = 0
invalid_polygon = 0
canvas_edge_coordinates = 0
total_candidate_dlm = 127
total_final_dlm = 86
dlm_manual_delta = -41
total_candidate_spl = 522
total_final_spl = 231
spl_manual_delta = -291
images_with_dlm_manual_changes = 8
images_with_spl_manual_changes = 12
images_with_dlm_count_changes = 8
images_with_spl_count_changes = 12
final_files_unchanged = PASS
source_files_unchanged = PASS
protected_files = 196
FINAL_3CLASS_GT_FROZEN = YES
annotation_modified = NO
inference_run = NO
checkpoint_loaded = NO
training = NO
min100_reapplied = NO
rdp_reapplied = NO
delete_roi_applied = NO
```

CRC hash match = 20/20. 원본 input JPG와 FINAL JPG의 SHA256도 20/20 일치한다.

## 클래스와 생성 이력

| Class | Labelme shape_type | 최종 개수 |
|---|---|---:|
| CRC | linestrip | 312 |
| DLM | polygon | 86 |
| SPL | polygon | 231 |

CRC: DamSegment NEW Stage A → mask threshold 0.60 → skeleton → min_path_length 100 px → RDP epsilon 0.5 → DELETE_ROI Pass 1 → DELETE_ROI Pass 2 → human final review.

DLM/SPL: Stage C → DLM/SPL candidate polygon → human final review.

- min100은 crack width 기준이 아니라 skeleton centerline path length filter이다.
- SAM mask thickness는 physical crack width가 아니다.
- physical CRC 약 1 mm 기준을 적용하려면 향후 image별 standoff/GSD가 필요하다.
- 현재 데이터는 사람이 시각 검수한 최종 GT이다. 이 audit의 기술 검증은 annotation의 의미적 정확도를 별도로 재판정한 결과는 아니다.
- 이 단계에서 inference, checkpoint load, training, DELETE_ROI 실행, min100/RDP 재적용을 수행하지 않았다.

## 검증 방법

### Pairing, 이미지 및 JSON

JPG/JPEG와 JSON을 확장자별로 집계하고 각 그룹 안에서 casefold basename 중복을 검사했다. 각 JSON과 JPG는 고유 basename으로 대응하며, JSON imagePath는 대응 JPG filename과 정확히 일치하고 FINAL 폴더에서 존재한다. FINAL에는 정확히 40개 일반 파일만 있으며 이미지 SHA256 duplicate pair는 0이다.

Pillow로 JPEG main image의 frame 0을 끝까지 decode했다. embedded thumbnail을 치수 기준으로 사용하거나 EXIF에 따라 원본을 변환하지 않았다. 20/20 모두 width 5280, height 3956, mode RGB, channels 3이다. JSON imageWidth/imageHeight도 실제 main image와 일치한다. version, flags, imageData 및 shapes/points 구조를 검사했다.

### CRC freeze canonical serialization

기존 baseline: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/crc_geometry_hash_before_stagec.csv`

재사용 verifier: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/crc_geometry_lock.py`

기존 specification에 기록된 baseline CSV SHA256 및 verifier script SHA256을 먼저 검증하고, 동일 crc_fingerprint 함수를 source 변경 없이 실행했다. Canonical schema는 `daechung-crc-full-shape-ordered-json-v1`이다.

CRC shape만 원래 shapes list의 상대 순서대로 선택하고 각 shape dictionary 전체를 포함한다. `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)`의 UTF-8 bytes를 SHA256으로 계산한다. label, shape_type, points, group_id, flags뿐 아니라 description, mask 등 존재하는 모든 shape 필드를 포함한다. point 순서, shape 순서, int/float 표현 및 missing/null 구분도 유지한다. CRC count와 hash 모두 image별 baseline과 일치해야 PASS이다.

### Geometry strict validation

검사 환경: Pillow 11.1.0, Shapely 2.1.1, GEOS 3.13.1.

CRC는 linestrip, points ≥ 2, 모든 coordinate가 유한한 숫자, 전체 길이 > 1e-9 px여야 한다. DLM/SPL은 polygon, points ≥ 3, 서로 다른 vertex ≥ 3, 면적 > 1e-12 px², GEOS is_valid여야 한다. 자기 교차 등 invalid polygon은 FAIL로 처리하며 geometry repair는 수행하지 않았다. NaN/inf와 잘못된 xy pair를 별도 집계했다.

좌표 범위는 연속 이미지 canvas [0, width] × [0, height], 허용 오차 1e-6 px로 검사했다. 픽셀 중심 최대 좌표인 width−1/height−1을 넘되 canvas 안에 있는 edge coordinate도 별도 기록했으며 실제 0개였다. 따라서 이번 데이터의 모든 좌표는 통상적인 픽셀 범위 안에도 존재한다.

## Stage C candidate 대비 사람 검수 변화

Reference: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json`

| Class | Candidate | Final | Final − candidate | Geometry 변경 이미지 | Count 변경 이미지 |
|---|---:|---:|---:|---:|---:|
| DLM | 127 | 86 | -41 | 8 | 8 |
| SPL | 522 | 231 | -291 | 12 | 12 |

이 delta는 최종 polygon 개수의 순변화이며 삭제 작업 횟수나 삭제 면적을 뜻하지 않는다. 사람이 삭제, 경계 수정 또는 신규 polygon 추가를 할 수 있으므로 delta 자체를 FAIL 조건으로 사용하지 않았다.

DLM/SPL geometry 비교는 label, shape_type, points를 polygon별 canonical serialization한 뒤 정렬된 multiset SHA256으로 계산했다. polygon들의 shapes list 순서와 int/float 표기 차이는 무시하고 각 polygon 내부 vertex 순서와 중복 개수는 유지한다. cyclic vertex rotation/reversal은 정규화하지 않으므로 동일 영역을 다른 vertex 순서로 표현한 경우도 변경으로 집계될 수 있다. 이 비교에는 non-geometry metadata를 포함하지 않았다. CRC 비교에는 이 방식을 사용하지 않고 위의 기존 strict 방식만 사용했다.

| Image JSON | CRC | DLM candidate | DLM final | Δ DLM | DLM geometry 변경 | SPL candidate | SPL final | Δ SPL | SPL geometry 변경 | CRC hash | Annotation |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|---|
| DJI_20250702150745_0300_V.json | 56 | 13 | 9 | -4 | YES | 23 | 22 | -1 | YES | PASS | PASS |
| DJI_20250702151015_0500_V.json | 29 | 7 | 7 | 0 | NO | 41 | 40 | -1 | YES | PASS | PASS |
| DJI_20250702160538_0800_V.json | 31 | 7 | 7 | 0 | NO | 14 | 13 | -1 | YES | PASS | PASS |
| DJI_20250702160658_0900_V.json | 13 | 7 | 7 | 0 | NO | 7 | 7 | 0 | NO | PASS | PASS |
| DJI_20250702162237_0020_V.json | 0 | 0 | 0 | 0 | NO | 5 | 2 | -3 | YES | PASS | PASS |
| DJI_20250702162257_0040_V.json | 5 | 0 | 0 | 0 | NO | 145 | 4 | -141 | YES | PASS | PASS |
| DJI_20250702164518_0050_V.json | 13 | 9 | 1 | -8 | YES | 7 | 1 | -6 | YES | PASS | PASS |
| DJI_20250702165251_0480_V.json | 16 | 1 | 1 | 0 | NO | 0 | 0 | 0 | NO | PASS | PASS |
| DJI_20260826093331_0020_V.json | 16 | 3 | 3 | 0 | NO | 3 | 7 | 4 | YES | PASS | PASS |
| DJI_20260826094118_0100_V.json | 6 | 16 | 7 | -9 | YES | 26 | 26 | 0 | NO | PASS | PASS |
| DJI_20260826094549_0300_V.json | 21 | 8 | 5 | -3 | YES | 19 | 19 | 0 | NO | PASS | PASS |
| DJI_20260826094700_0360_V.json | 22 | 20 | 15 | -5 | YES | 22 | 22 | 0 | NO | PASS | PASS |
| DJI_20260826102236_0200_V.json | 4 | 17 | 10 | -7 | YES | 22 | 22 | 0 | NO | PASS | PASS |
| DJI_20260826102412_0300_V.json | 3 | 3 | 1 | -2 | YES | 21 | 1 | -20 | YES | PASS | PASS |
| DJI_20260826112900_0100_V.json | 13 | 0 | 0 | 0 | NO | 2 | 2 | 0 | NO | PASS | PASS |
| DJI_20260826114456_1000_V.json | 7 | 0 | 0 | 0 | NO | 5 | 4 | -1 | YES | PASS | PASS |
| DJI_20260826120100_0500_V.json | 10 | 2 | 2 | 0 | NO | 7 | 7 | 0 | NO | PASS | PASS |
| DJI_20260826120256_0600_V.json | 35 | 0 | 0 | 0 | NO | 31 | 8 | -23 | YES | PASS | PASS |
| DJI_20260826124557_0200_V.json | 8 | 6 | 3 | -3 | YES | 32 | 7 | -25 | YES | PASS | PASS |
| DJI_20260826125854_0900_V.json | 4 | 8 | 8 | 0 | NO | 90 | 17 | -73 | YES | PASS | PASS |

## PASS 조건 확인

| Check | Result |
|---|---|
| crc_baseline_file_sha_match | PASS |
| crc_verifier_source_sha_match | PASS |
| crc_baseline_20_rows_312_crc | PASS |
| final_has_exactly_40_regular_files | PASS |
| images_20 | PASS |
| json_20 | PASS |
| duplicate_basename_zero | PASS |
| duplicate_image_sha_pairs_zero | PASS |
| final_json_names_match_crc_baseline | PASS |
| pairing_20_of_20 | PASS |
| json_parse_20_of_20 | PASS |
| decode_20_of_20 | PASS |
| resolution_20_of_20 | PASS |
| rgb_20_of_20 | PASS |
| crc_total_312 | PASS |
| crc_count_unchanged | PASS |
| crc_geometry_unchanged | PASS |
| crc_linestrips_all_valid | PASS |
| dlm_polygons_all_valid | PASS |
| spl_polygons_all_valid | PASS |
| forbidden_labels_zero | PASS |
| annotations_all_pass | PASS |
| candidate_dlm_127 | PASS |
| candidate_spl_522 | PASS |
| final_files_unchanged | PASS |
| source_files_unchanged | PASS |

문제 목록: 없음.

## Source integrity

보호 파일 196개를 audit 시작 전과 종료 시점에 SHA256 및 metadata로 재검증했다. FINAL의 JPG 20개와 JSON 20개를 포함한다. 파일 inventory의 추가/삭제도 검사했다.

모든 파일의 size, mtime_ns, ctime_ns, atime_ns, inode, device, mode, uid, gid, nlink를 비교했다. 원본 읽기에 O_NOATIME을 사용했다. checkpoint는 SHA256 계산만 수행했으며 load하지 않았다. SHA256, size 및 mtime은 아래에 기록하고 manifest에도 FINAL 파일별 before/after size/mtime을 기록했다.

| Protected scope | Files | Inventory unchanged |
|---|---:|---|
| final: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1` | 40 | PASS |
| original_crc_final: `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1` | 40 | PASS |
| crc_freeze_reference: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference` | 7 | PASS |
| candidate: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json` | 40 | PASS |
| original_images: `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images` | 20 | PASS |
| stagec_input_copy: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy` | 40 | PASS |
| original_crc_freeze_audit: `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/freeze_audit_v1` | 3 | PASS |

위 directory scope 외 wrapper, persistent launcher, run-local launcher, 기존 Stage C pilot source, Stage C checkpoint 및 NEW Stage A checkpoint도 파일 단위로 보호했다.

아래 SHA256은 before 값이다. 각 행의 PASS는 after SHA256이 동일하고 위 metadata 모두 변하지 않았음을 뜻한다. mtime은 Unix epoch 기준 nanoseconds이다.

| Protected file | SHA256 before (= after on PASS) | Bytes before / after | mtime_ns before / after | All integrity checks |
|---|---|---:|---|---|
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788949929700041852 / 1788949929700041852 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702150745_0300_V.json` | `1d9952cc4b7b9253bd08cfac51f6ef6589ecbae820f82b44b051c4576c1e3cc8` | 1220459 / 1220459 | 1788950023944099034 / 1788950023944099034 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788949929707041931 / 1788949929707041931 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702151015_0500_V.json` | `e762cebeb3239765a0bcb197ad5ffb07cf29390e94d39d18552f36e88730151d` | 1680533 / 1680533 | 1788950023992099567 / 1788950023992099567 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788949929713041999 / 1788949929713041999 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160538_0800_V.json` | `f5664eba851dca51a01ceef86c8cfc6430f0c6bd1bb7a5cca6b31dd99eb7d89c` | 721087 / 721087 | 1788950024014099812 / 1788950024014099812 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788949929720042079 / 1788949929720042079 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160658_0900_V.json` | `9995a2fddde4c2e79069b1fd697f78d331d6f9842c532d306d80195db02830ff` | 551039 / 551039 | 1788950024033695900 / 1788950024033695900 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788949929726042147 / 1788949929726042147 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162237_0020_V.json` | `41ab3c8003d82824f3eb399e03a182f7b17edb02855870e5fe6b0516a3c4305f` | 99540 / 99540 | 1788950024039100090 / 1788950024039100090 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788949929732042214 / 1788949929732042214 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162257_0040_V.json` | `3840354dadaa2f9f48a831f63dde86bd0ac9485b55e4350912c08ba8d5188ed0` | 1672007 / 1672007 | 1788950024097214910 / 1788950024097214910 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788949929739042294 / 1788949929739042294 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702164518_0050_V.json` | `b3c7c4e6312853ffc8be033391127aed9e35fb52f85b91a36476f073559d6b89` | 415601 / 415601 | 1788950024110100878 / 1788950024110100878 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788949929746042373 / 1788949929746042373 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702165251_0480_V.json` | `70fa04acce6980905b6312298e143545e08a9f8af4e03bc0f5892afb689cd195` | 44361 / 44361 | 1788950024114100923 / 1788950024114100923 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788949929751042430 / 1788949929751042430 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826093331_0020_V.json` | `64156f8e84f326956c71737cf0217c042deed7ac086ec960037716e7bfb87ff4` | 189268 / 189268 | 1788950024121101001 / 1788950024121101001 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788949929755042475 / 1788949929755042475 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094118_0100_V.json` | `0603e00643b371e6527f8a4c2e7c8ec81f205a98943bb4fd31b310b46a9af2d2` | 1284912 / 1284912 | 1788950024157101401 / 1788950024157101401 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788949929760042532 / 1788949929760042532 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094549_0300_V.json` | `3214c30dc493aba1afc6fbdc393c084ddabefdd32e454c427ea21c0f90ea2536` | 1303574 / 1303574 | 1788950024193101801 / 1788950024193101801 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788949929765042589 / 1788949929765042589 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094700_0360_V.json` | `c8e548ef8d19e0d6f05accd14fcb682689e2ee742b29d106af7d8a1e89c85711` | 2339022 / 2339022 | 1788950024252102457 / 1788950024252102457 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788949929770042645 / 1788949929770042645 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102236_0200_V.json` | `788cefe6db7fd928e4c6f0a096eae05fc33626e4ac890ebd0bd0b7a67cc4e4f0` | 1577465 / 1577465 | 1788950024294102924 / 1788950024294102924 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788949929776042713 / 1788949929776042713 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102412_0300_V.json` | `f660348b0082a5f8544373d939b0c1dc7ca2a902683b3e515b013baf30b9de0a` | 13748 / 13748 | 1788950024298102969 / 1788950024298102969 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788949929781042769 / 1788949929781042769 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826112900_0100_V.json` | `61d4794eaea7c71cd4ea309f1e830c4a4b7eaf776399ee12c0f8bc03743e7ae8` | 100361 / 100361 | 1788950024303391364 / 1788950024303391364 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788949929787159870 / 1788949929787159870 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826114456_1000_V.json` | `70f3fdb63cb7b2078dec1ab64cc2f02d74885be5c69e9301747bf07d282e4e4c` | 163716 / 163716 | 1788950024309103091 / 1788950024309103091 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788949929794042917 / 1788949929794042917 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120100_0500_V.json` | `ff5f023e6d2f2c998006b3798fcf6e3a1d88afef99d138ac85d7041d23c3157f` | 465130 / 465130 | 1788950024325103268 / 1788950024325103268 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788949929799042974 / 1788949929799042974 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120256_0600_V.json` | `9cf2ffb3ce85eb72d58148d04cf25e69e28a06b3d37ca7f5b8e3089315d5b127` | 1035077 / 1035077 | 1788950024352103569 / 1788950024352103569 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788949929807043064 / 1788949929807043064 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826124557_0200_V.json` | `9d64bfb7104858660808970498578867df086990828aaeb7c161137489910af2` | 1499101 / 1499101 | 1788950023863591673 / 1788950023863591673 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788949929814043143 / 1788949929814043143 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826125854_0900_V.json` | `5d98a0a97035bb1c91e6d46c17c96b8cbda304acae4fe664d8d174ab31f6fdad` | 1884679 / 1884679 | 1788950023911098667 / 1788950023911098667 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788927862494967219 / 1788927862494967219 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788927863407957641 / 1788927863407957641 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788927864208968357 / 1788927864208968357 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788927865087940092 / 1788927865087940092 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788927865909697425 / 1788927865909697425 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788927866694923403 / 1788927866694923403 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788927867419915902 / 1788927867419915902 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788927868159908263 / 1788927868159908263 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788927868692902775 / 1788927868692902775 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788927869183897725 / 1788927869183897725 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788927869773891670 / 1788927869773891670 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788927870441884832 / 1788927870441884832 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788927871135216281 / 1788927871135216281 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788927856826027337 / 1788927856826027337 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788927857426020921 / 1788927857426020921 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788927858097013758 / 1788927858097013758 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788927858792006359 / 1788927858792006359 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788927859483999010 / 1788927859483999010 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788927860495328894 / 1788927860495328894 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/01_input_images/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788927861507977605 / 1788927861507977605 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788941944490345928 / 1788941944490345928 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702150745_0300_V.json` | `6d3fbff1cf820c395a4670a998602f7638e6910393dbd0da88bf09d1f9139317` | 145236 / 145236 | 1788942012223805734 / 1788942012223805734 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788941944497345976 / 1788941944497345976 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702151015_0500_V.json` | `9e5bcae9f813505ffd07c84582f45f0867d322e4447facad4833ec282f3825ef` | 80679 / 80679 | 1788942012226805755 / 1788942012226805755 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788941944503346016 / 1788941944503346016 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702160538_0800_V.json` | `55ff3b43ad1ede45bb46fd6a912933c3a5a2a3fa7d44461468db515d0965b609` | 75020 / 75020 | 1788942012230805782 / 1788942012230805782 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788941944509346058 / 1788941944509346058 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702160658_0900_V.json` | `34f418820d2e8610de2215614a51977fb1e2e2440bf2b9978f9e179b2e6c8486` | 27496 / 27496 | 1788942012233974923 / 1788942012233974923 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788941944517346112 / 1788941944517346112 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702162237_0020_V.json` | `d857ff196164d4b94c073b5c14b1b02fe17dd3cb49b130f6fa2da5aeb24b2cdc` | 170 / 170 | 1788942012235805816 / 1788942012235805816 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788941944524471137 / 1788941944524471137 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702162257_0040_V.json` | `7a0d4af1eecfcd751c1c083688c420f7d5200638bfc827ce7a42f5166de6f95e` | 11881 / 11881 | 1788942012238805836 / 1788942012238805836 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788941944530372591 / 1788941944530372591 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702164518_0050_V.json` | `97089538241d2c1fe2fe1f80d756cdff39e308442fcc5ac0bd59e857962ccd6e` | 42440 / 42440 | 1788942012240805849 / 1788942012240805849 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788941944537346248 / 1788941944537346248 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20250702165251_0480_V.json` | `3342bc5e7fc288e7eafe1a2b2c9aad4ab5c75915d7d7d715f28ed997578f2eb5` | 34793 / 34793 | 1788942012243805869 / 1788942012243805869 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788941944541346275 / 1788941944541346275 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826093331_0020_V.json` | `c1c2725bf51873662a93abed95ae9f8cf5fc032e2e51dde1426453fc49eda713` | 37227 / 37227 | 1788942012246805890 / 1788942012246805890 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788941944546346309 / 1788941944546346309 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094118_0100_V.json` | `74605c4f35e54e42fa8b9e54c82125dea9c439ece1437f943641a19c0dc2752d` | 16588 / 16588 | 1788942012249805910 / 1788942012249805910 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788941944551346343 / 1788941944551346343 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094549_0300_V.json` | `91885d9bcbab690a51087a5b8ee19bd9617e47ede47d7ed10421065fbb115a1b` | 74606 / 74606 | 1788942012253805938 / 1788942012253805938 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788941944556346377 / 1788941944556346377 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826094700_0360_V.json` | `180ae77132b0224cc27cfd15d5bded398b702d11c2dedc97a497b9f6ded7f3ba` | 62904 / 62904 | 1788942012256805958 / 1788942012256805958 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788941944561346411 / 1788941944561346411 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826102236_0200_V.json` | `0e53d4d84357ef035f7bcf0b8fb61734ad0b668a91bc87919d9d4f928eda51c4` | 22892 / 22892 | 1788942012258805971 / 1788942012258805971 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788941944567346451 / 1788941944567346451 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826102412_0300_V.json` | `68b439c0b86134342a08db446126fcf6c2a306d7c9affbff9aabed1defb5ec33` | 7637 / 7637 | 1788942012261805991 / 1788942012261805991 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788941944573820158 / 1788941944573820158 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826112900_0100_V.json` | `a04275d63e1985d13888c4d2795ea1582b0c3314948f9bc52218d36ff0236969` | 30346 / 30346 | 1788942012263806005 / 1788942012263806005 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788941944580319292 / 1788941944580319292 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826114456_1000_V.json` | `411ce17ea607340dda11a1dfa1d46103aaa1d13da74370083dad0f113d760254` | 22128 / 22128 | 1788942012266806026 / 1788942012266806026 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788941944586346580 / 1788941944586346580 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826120100_0500_V.json` | `3eae4e4f2bdb2c24acbdd7080dd64447a9a6b6cf2adfb29d967f942e3c3549c6` | 27155 / 27155 | 1788942012269806046 / 1788942012269806046 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788941944592346622 / 1788941944592346622 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826120256_0600_V.json` | `a001016e2a3570c51d23960f4beb3b44710b6cf3419bf164d208f5667e97a298` | 70719 / 70719 | 1788942012273806073 / 1788942012273806073 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788941944600346676 / 1788941944600346676 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826124557_0200_V.json` | `7bacb6159346bb71a842f45be6e2b068b88d0e3a984080fdc0e35f6e8b0f750d` | 27110 / 27110 | 1788942012214805673 / 1788942012214805673 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788941944608346730 / 1788941944608346730 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/final_v1/DJI_20260826125854_0900_V.json` | `5d841ea625b6b82997489a81414260b23875a27d9aab8645ce13e36858623654` | 12684 / 12684 | 1788942012217805694 / 1788942012217805694 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/freeze_audit_v1/final_crc_freeze_report.md` | `3f943b49af3fe98c4c58acd11433ac3e010a24b914f1ab06b65eac7d7dfb5aa0` | 31847 / 31847 | 1788942629149081552 / 1788942629149081552 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/freeze_audit_v1/final_crc_manifest.csv` | `1f516fffbc0f9e2394adbede92cb8f125e4f5719cd45f5e5a247a2feb17ce4a6` | 12195 / 12195 | 1788942629148814737 / 1788942629148814737 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/crc_demo20_min100_v1/06_reviewed_crc/freeze_audit_v1/final_crc_sha256.txt` | `09c5c7e59ea2941239977c7df495334395e7b0434968e0f2dbc9ebb5adb8aba6` | 3860 / 3860 | 1788942629148963813 / 1788942629148963813 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/CRC_PROTECTION_RULES.md` | `d3332b7fb1f818dbdf5a731677dada775b6414157235e773cc56f3fd96eb63e2` | 2168 / 2168 | 1788943259529916804 / 1788943259529916804 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/crc_geometry_canonicalization.json` | `a6ed77fd2a8b9b30fa3275694fa739a6e0646a721e43574b7658cabc7da1c4d0` | 1251 / 1251 | 1788943259529807289 / 1788943259529807289 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/crc_geometry_hash_before_stagec.csv` | `ce531bb0ff47907f5d2a9f4292c8324e4adaf9ccdc320a7f3a9f144bee4de4f6` | 2032 / 2032 | 1788943259485556804 / 1788943259485556804 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/crc_geometry_lock.py` | `ee719f879f6b0aad84191b726ac9c9d1f5c9a93ae6af1cd91dcefa0b6019b77b` | 3937 / 3937 | 1788943259485683785 / 1788943259485683785 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/final_crc_freeze_report.md` | `3f943b49af3fe98c4c58acd11433ac3e010a24b914f1ab06b65eac7d7dfb5aa0` | 31847 / 31847 | 1788943256974329170 / 1788943256974329170 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/final_crc_manifest.csv` | `1f516fffbc0f9e2394adbede92cb8f125e4f5719cd45f5e5a247a2feb17ce4a6` | 12195 / 12195 | 1788943256974148587 / 1788943256974148587 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/00_crc_freeze_reference/final_crc_sha256.txt` | `09c5c7e59ea2941239977c7df495334395e7b0434968e0f2dbc9ebb5adb8aba6` | 3860 / 3860 | 1788943256974233665 / 1788943256974233665 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788943256549172481 / 1788943256549172481 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702150745_0300_V.json` | `6d3fbff1cf820c395a4670a998602f7638e6910393dbd0da88bf09d1f9139317` | 145236 / 145236 | 1788943256564979373 / 1788943256564979373 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788943256573939250 / 1788943256573939250 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702151015_0500_V.json` | `9e5bcae9f813505ffd07c84582f45f0867d322e4447facad4833ec282f3825ef` | 80679 / 80679 | 1788943256590348402 / 1788943256590348402 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788943256597929246 / 1788943256597929246 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702160538_0800_V.json` | `55ff3b43ad1ede45bb46fd6a912933c3a5a2a3fa7d44461468db515d0965b609` | 75020 / 75020 | 1788943256612108528 / 1788943256612108528 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788943256621159553 / 1788943256621159553 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702160658_0900_V.json` | `34f418820d2e8610de2215614a51977fb1e2e2440bf2b9978f9e179b2e6c8486` | 27496 / 27496 | 1788943256637752813 / 1788943256637752813 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788943256645321068 / 1788943256645321068 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702162237_0020_V.json` | `d857ff196164d4b94c073b5c14b1b02fe17dd3cb49b130f6fa2da5aeb24b2cdc` | 170 / 170 | 1788943256659932133 / 1788943256659932133 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788943256668180725 / 1788943256668180725 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702162257_0040_V.json` | `7a0d4af1eecfcd751c1c083688c420f7d5200638bfc827ce7a42f5166de6f95e` | 11881 / 11881 | 1788943256683677699 / 1788943256683677699 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788943256691580799 / 1788943256691580799 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702164518_0050_V.json` | `97089538241d2c1fe2fe1f80d756cdff39e308442fcc5ac0bd59e857962ccd6e` | 42440 / 42440 | 1788943256706420760 / 1788943256706420760 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788943256714975064 / 1788943256714975064 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20250702165251_0480_V.json` | `3342bc5e7fc288e7eafe1a2b2c9aad4ab5c75915d7d7d715f28ed997578f2eb5` | 34793 / 34793 | 1788943256731093677 / 1788943256731093677 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788943256737158750 / 1788943256737158750 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826093331_0020_V.json` | `c1c2725bf51873662a93abed95ae9f8cf5fc032e2e51dde1426453fc49eda713` | 37227 / 37227 | 1788943256748628940 / 1788943256748628940 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788943256754237434 / 1788943256754237434 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094118_0100_V.json` | `74605c4f35e54e42fa8b9e54c82125dea9c439ece1437f943641a19c0dc2752d` | 16588 / 16588 | 1788943256764848005 / 1788943256764848005 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788943256770464200 / 1788943256770464200 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094549_0300_V.json` | `91885d9bcbab690a51087a5b8ee19bd9617e47ede47d7ed10421065fbb115a1b` | 74606 / 74606 | 1788943256781195013 / 1788943256781195013 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788943256787565127 / 1788943256787565127 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826094700_0360_V.json` | `180ae77132b0224cc27cfd15d5bded398b702d11c2dedc97a497b9f6ded7f3ba` | 62904 / 62904 | 1788943256799491816 / 1788943256799491816 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788943256805770012 / 1788943256805770012 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826102236_0200_V.json` | `0e53d4d84357ef035f7bcf0b8fb61734ad0b668a91bc87919d9d4f928eda51c4` | 22892 / 22892 | 1788943256817172061 / 1788943256817172061 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788943256824621013 / 1788943256824621013 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826102412_0300_V.json` | `68b439c0b86134342a08db446126fcf6c2a306d7c9affbff9aabed1defb5ec33` | 7637 / 7637 | 1788943256837292428 / 1788943256837292428 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788943256843703964 / 1788943256843703964 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826112900_0100_V.json` | `a04275d63e1985d13888c4d2795ea1582b0c3314948f9bc52218d36ff0236969` | 30346 / 30346 | 1788943256856067173 / 1788943256856067173 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788943256863296446 / 1788943256863296446 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826114456_1000_V.json` | `411ce17ea607340dda11a1dfa1d46103aaa1d13da74370083dad0f113d760254` | 22128 / 22128 | 1788943256877267133 / 1788943256877267133 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788943256884920757 / 1788943256884920757 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826120100_0500_V.json` | `3eae4e4f2bdb2c24acbdd7080dd64447a9a6b6cf2adfb29d967f942e3c3549c6` | 27155 / 27155 | 1788943256899930394 / 1788943256899930394 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788943256907097312 / 1788943256907097312 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826120256_0600_V.json` | `a001016e2a3570c51d23960f4beb3b44710b6cf3419bf164d208f5667e97a298` | 70719 / 70719 | 1788943256920667555 / 1788943256920667555 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788943256930944051 / 1788943256930944051 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826124557_0200_V.json` | `7bacb6159346bb71a842f45be6e2b068b88d0e3a984080fdc0e35f6e8b0f750d` | 27110 / 27110 | 1788943256949154985 / 1788943256949154985 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788943256957572433 / 1788943256957572433 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/01_input_copy/DJI_20260826125854_0900_V.json` | `5d841ea625b6b82997489a81414260b23875a27d9aab8645ce13e36858623654` | 12684 / 12684 | 1788943256973904188 / 1788943256973904188 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/02_inference/run_full20_from_frozen_wrapper.py` | `6ae756241b8ecd25bcb7c0c60c35870282456bf5588311be6b6d9ad3c3e3b356` | 10832 / 10832 | 1788946692292089224 / 1788946692292089224 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788946735320677006 / 1788946735320677006 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702150745_0300_V.json` | `15a357104c243f2951c39ce346e34316f6a3e58c0a100faf0627c1c8cc91d66a` | 1207765 / 1207765 | 1788946735330755585 / 1788946735330755585 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788946749972085653 / 1788946749972085653 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702151015_0500_V.json` | `98b4262ca0158987eb0954680d633f12dd1b05d1a03398655602a1bcad9f716b` | 1409171 / 1409171 | 1788946749979019672 / 1788946749979019672 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788946765647454334 / 1788946765647454334 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702160538_0800_V.json` | `f95670e8e0e40c0dfd306d0877c657ac978fed9de0c05fe7d121d082ff36e729` | 784895 / 784895 | 1788946765653506294 / 1788946765653506294 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788946778659313230 / 1788946778659313230 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702160658_0900_V.json` | `9995a2fddde4c2e79069b1fd697f78d331d6f9842c532d306d80195db02830ff` | 551039 / 551039 | 1788946778666532128 / 1788946778666532128 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788946791127742795 / 1788946791127742795 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702162237_0020_V.json` | `c7c13ebdd3ca78ef80f9446462d977ba4319fc6300cf8ab3c4221b7b77eb8fd6` | 83435 / 83435 | 1788946791136341052 / 1788946791136341052 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788946806768636418 / 1788946806768636418 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702162257_0040_V.json` | `fff2ed567b22ebfbb15967ca0d2a8913bf16ad43f759843328b87a67b6cd4303` | 1693353 / 1693353 | 1788946806775107028 / 1788946806775107028 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788946821054814340 / 1788946821054814340 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702164518_0050_V.json` | `c0dd12a31e12ba47c97112aca02abc0c2eb72e29b25e7fb9b0d2053b1a88b58c` | 684238 / 684238 | 1788946821063404804 / 1788946821063404804 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788946836380406826 / 1788946836380406826 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20250702165251_0480_V.json` | `70fa04acce6980905b6312298e143545e08a9f8af4e03bc0f5892afb689cd195` | 44361 / 44361 | 1788946836391477807 / 1788946836391477807 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788946850809972297 / 1788946850809972297 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826093331_0020_V.json` | `86f77df4d9e82ced63fbbf333dc90dabb4fdf71019c8b9d7a7605e3e2037c654` | 151350 / 151350 | 1788946850816478941 / 1788946850816478941 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788946866744048746 / 1788946866744048746 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094118_0100_V.json` | `30f204b8c6a1f502270422bf669236b5230cb886d5de9eb54ba38545ad2995ef` | 1137706 / 1137706 | 1788946866750334928 / 1788946866750334928 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788946880585598456 / 1788946880585598456 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094549_0300_V.json` | `3a1e1984eb30a6c1cb01fa697e8b0eb8bbcb47494f57b3d514a266398b82edda` | 1072204 / 1072204 | 1788946880591980261 / 1788946880591980261 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788946896738536952 / 1788946896738536952 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826094700_0360_V.json` | `5b5c737c7659786b5f5556d5d0eefc20c44a270e1cfbd6cf3fc24c2214a3a12b` | 1881124 / 1881124 | 1788946896745603860 / 1788946896745603860 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788946911205861606 / 1788946911205861606 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826102236_0200_V.json` | `22c7a04d794acce91ceb4cba3ffbda0cf0134a37bbb47f79bef67ce6ca5060b5` | 1272983 / 1272983 | 1788946911214181513 / 1788946911214181513 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788946924874682728 / 1788946924874682728 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826102412_0300_V.json` | `d17024b615cb4f9ed80cc637258eddde02d5cc5a776a18353fa1bad2fede9e07` | 806614 / 806614 | 1788946924882615319 / 1788946924882615319 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788946938847162558 / 1788946938847162558 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826112900_0100_V.json` | `61d4794eaea7c71cd4ea309f1e830c4a4b7eaf776399ee12c0f8bc03743e7ae8` | 100361 / 100361 | 1788946938853116708 / 1788946938853116708 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788946951398298160 / 1788946951398298160 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826114456_1000_V.json` | `5179dd007574620088b2fe92c0e439872102228d63f3cf29c84cefb76fab38e6` | 137860 / 137860 | 1788946951406830414 / 1788946951406830414 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788946966738276088 / 1788946966738276088 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826120100_0500_V.json` | `ff5f023e6d2f2c998006b3798fcf6e3a1d88afef99d138ac85d7041d23c3157f` | 465130 / 465130 | 1788946966747476239 / 1788946966747476239 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788946980740104258 / 1788946980740104258 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826120256_0600_V.json` | `b208d5efc3d4f068b390735cfbca475e75acdd85abcc580e688fff5e16213543` | 1054071 / 1054071 | 1788946980746505621 / 1788946980746505621 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788946994603731314 / 1788946994603731314 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826124557_0200_V.json` | `64a1ba3e0bbbb9d59f83cd61caea0aeb56e072f779d1410cf8739a7ad61a05cf` | 1304262 / 1304262 | 1788946994617154766 / 1788946994617154766 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788947011171716639 / 1788947011171716639 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/full20_run_v1/04_candidate_json/DJI_20260826125854_0900_V.json` | `2784129815df8cb4b4fca59b4f9445d2410f12ec0d05b0bce151dc13eec64f1f` | 1679601 / 1679601 | 1788947011182386162 / 1788947011182386162 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/run_demo20_stagec_crc_preserve_v1.py` | `510599b9614fa7f688dbb69fe3c0fb7967b43c9a39b0677cecf9e490990acd8d` | 25442 / 25442 | 1788943919972713068 / 1788943919972713068 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/run_full20_from_frozen_wrapper_v1.py` | `6ae756241b8ecd25bcb7c0c60c35870282456bf5588311be6b6d9ad3c3e3b356` | 10832 / 10832 | 1788946608622835517 / 1788946608622835517 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/new_stage_a_damsegment_v1/stage_a_native640_raw2q_7331_v1/training_outputs/train7331_v1/checkpoints/checkpoint_final.pt` | `b602b2363d4776015074a69513f61ca0ea20cc138c8943537100762c8107621d` | 10081320598 / 10081320598 | 1786980741851226104 / 1786980741851226104 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/stage_c_dlm_spl_semiauto_pilot5_v1/run_stage_c_dlm_spl_semiauto_pilot5_v1.py` | `b01d91bc3291650c644270cacaad9b09834d09b1d18fb0cd16bfc57ebc7a7ab2` | 32936 / 32936 | 1788154744611996457 / 1788154744611996457 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/stage_c_t1b_new100_full_ft_7px_s512_v1/training_outputs/checkpoints/checkpoint.pt` | `eb0d6ed66df362d034b0d4bb05ff3e8069da212084c526e8e1c25ac2bc8dc987` | 10081246604 / 10081246604 | 1786739182685744096 / 1786739182685744096 | PASS |

## Audit artifacts

- [final_3class_manifest.csv](final_3class_manifest.csv): 20개 pair의 SHA256, geometry/CRC 검사, candidate 비교, size/mtime before/after.
- [final_3class_sha256.txt](final_3class_sha256.txt): FINAL의 JPG/JSON 40개 SHA256. 각 filename은 FINAL_ROOT 기준 상대 경로이다.
- final_3class_freeze_report.md: 이 보고서.

Freeze는 검증된 데이터 상태와 해시를 별도 audit root에 기록한 것이다. FINAL_ROOT에 파일을 추가하거나 annotation, 파일명, 위치, 권한을 변경하지 않았다.

FINAL_3CLASS_GT_FROZEN = YES
