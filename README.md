# UAV RGB Damage Module

드론 RGB 사진을 입력하면 콘크리트 손상 결과를 생성하는 실행용 저장소입니다.

표출 시스템에서 사용하는 핵심 결과는 다음과 같습니다.

- 원본 사진 위에 표시할 손상 외곽선 좌표
- 3D 댐 모델 위에 표시할 손상 대표 좌표
- 균열 길이·폭과 박리·박락 면적
- 전체 결과를 정리한 CSV와 Excel
- 손상 영역 영상(mask)과 원본 사진에 손상을 겹친 영상(overlay)

## 폴더 구성

```text
UAV_RGB/
├── 01_RawData/       # 입력 사진, 비행정보, 3D 모델
├── 02_Model/         # 모델 다운로드 및 검증 파일
├── 03_Processing/    # 실행 코드와 설정
├── 04_Output/        # 실행 결과와 공개 예시
└── 05_Docs/          # 상세 문서
```

주요 입력과 결과 위치는 다음과 같습니다.

```text
01_RawData/
├── missions/DJI_202507021616_left03/
│   ├── images/       # 샘플 원본 사진 7장
│   └── navigation/   # 사진의 위치·자세 정보
└── geometry/
    └── daecheong_dam_epsg5186_zup.obj

02_Model/sam3_aug512/checkpoints/
└── checkpoint_final.pt

04_Output/
├── runs/             # 새로 실행한 전체 결과
└── examples/         # GitHub에 포함된 결과 예시
```

## 실행 환경 준비

Python 3.11 이상, CUDA를 사용할 수 있는 NVIDIA GPU, CUDA 지원 PyTorch가 필요합니다.

```bash
git clone https://github.com/Jiwandukong/UAV_RGB_Damage_Module.git UAV_RGB
cd UAV_RGB

git clone https://github.com/facebookresearch/sam3.git ../sam3
git -C ../sam3 checkout 46957e47805eaa273f4aa7bbbd25a88bca9108ce

python -m pip install -e ../sam3
python -m pip install -e ".[mesh-gpu]"
```

## 모델 받기

모델은 Git 저장소에 직접 포함하지 않고 [GitHub Release](https://github.com/Jiwandukong/UAV_RGB_Damage_Module/releases/tag/sam3-aug512-v1)에서 제공합니다.

다음 명령을 실행하면 Release의 모델 조각 6개를 내려받아 `checkpoint_final.pt`로 복원하고 파일을 검증합니다.

```bash
python 03_Processing/scripts/download_checkpoint.py
python 03_Processing/scripts/verify_checkpoint.py --strict-load
```

복원 위치:

```text
02_Model/sam3_aug512/checkpoints/checkpoint_final.pt
```

- 파일 크기: 10,081,318,934 bytes
- SHA-256: `a2749dba62207575afac9ed42f923d7cdfd7e2d2f0ffb2210a103e91657d985d`

Release 다운로드 또는 복원이 작동하지 않으면 저장소 관리자에게 요청해 원본 약 10GB `checkpoint_final.pt`를 직접 전달받은 뒤 위 경로에 두십시오.

## 3D 모델 준비

3D 표출 좌표를 생성하려면 다음 OBJ 파일이 필요합니다. OBJ는 Git 저장소에 포함되지 않으므로 별도로 준비합니다.

```text
원본 파일명: dam - Cloud.obj
저장 위치: 01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
좌표 기준: EPSG:5186 X/Y, metre, Z-up
파일 크기: 184,020,785 bytes
SHA-256: a7566c8d8f70de91db18c70ae5f404b0f7885e679a1027fd3e1936afd2d1e470
```

```bash
cp "/path/to/dam - Cloud.obj" 01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
python 03_Processing/scripts/verify_assets.py
```

## 실행

별도 인수 없이 실행하면 저장소에 포함된 샘플 사진 7장을 처리합니다.

```bash
python 03_Processing/scripts/run_pipeline.py
```

결과는 실행할 때마다 새로운 폴더에 저장됩니다.

```text
04_Output/runs/left03_aug512_<실행시각>/
```

다른 입력을 사용할 때 지정할 수 있는 경로는 다음 명령으로 확인합니다.

```bash
python 03_Processing/scripts/run_pipeline.py --help
```

## 결과 폴더

```text
04_Output/runs/<실행 폴더>/
├── masks/<사진명>/
│   ├── CRC.png
│   ├── DLM.png
│   ├── SPL.png
│   ├── multilabel_rgb.png
│   └── preview.png
├── overlays/
│   └── <사진명>_overlay.png
├── tables/
│   ├── damage_results.csv
│   ├── damage_results.xlsx
│   └── per_image/<사진명>_damage_details.csv
└── metadata/
    ├── run_metadata.json
    └── per_image/<사진명>_metadata.json
```

| 결과 | 용도 |
|---|---|
| `masks/<사진명>/CRC.png` | 균열 영역을 흰색, 나머지를 검정으로 저장한 영상 |
| `masks/<사진명>/DLM.png` | 박리 영역을 흰색, 나머지를 검정으로 저장한 영상 |
| `masks/<사진명>/SPL.png` | 박락 영역을 흰색, 나머지를 검정으로 저장한 영상 |
| `masks/<사진명>/multilabel_rgb.png` | R=균열, G=박리, B=박락으로 저장한 영상. 채널은 독립적이므로 한 pixel에 여러 손상이 겹칠 수 있음 |
| `masks/<사진명>/preview.png` | 균열은 빨강, 박리는 노랑, 박락은 파랑으로 표시한 미리보기 |
| `overlays/<사진명>_overlay.png` | 원본 사진 위에 같은 라벨 색상 기준으로 손상을 반투명하게 표시한 영상 |
| `tables/damage_results.csv` | 전체 사진의 손상 결과를 합친 CSV |
| `tables/damage_results.xlsx` | 전체 사진의 손상 결과를 합친 최종 Excel |
| `tables/per_image/*.csv` | 사진별 손상 결과 CSV |
| `metadata/*.json` | 실행과 입력 파일을 확인하기 위한 기록. 일반 표출 연계에는 필수가 아님 |

표출 연계의 기본 산출물은 `damage_results.csv` 또는 `damage_results.xlsx`입니다. Excel에는 `Damage_Details` 시트 하나만 있으며 CSV와 같은 13개 열을 사용합니다.

mask, 미리보기, overlay는 입력 사진과 같은 pixel 크기로 저장됩니다.

## 손상 라벨

| 라벨 | 영문 | 한글 | 제공되는 정량값 |
|---|---|---|---|
| `CRC` | Crack | 균열 | 길이, 폭 |
| `DLM` | Delamination | 박리 | 면적 |
| `SPL` | Spalling | 박락 | 면적 |

## CSV와 Excel 열

| 구분 | 열 이름 | 표출 시스템에서의 의미 |
|---|---|---|
| 기본 정보 | `image` | 원본 사진 파일명 |
| 기본 정보 | `damage_id` | 한 번의 실행에서 손상마다 부여한 고유 ID |
| 기본 정보 | `damage_type` | 손상 코드: `CRC`, `DLM`, `SPL` |
| 기본 정보 | `damage_name_ko` | 손상 한글명: 균열, 박리, 박락 |
| 2D 표출 | `pixel_nodes_json` | 원본 사진 위 손상 외곽선을 표출하기 위해 간추린 대표 좌표 `[[x, y], ...]` |
| 3D 표출 | `world_center_x_m` | 손상 대표점의 EPSG:5186 X 좌표(m) |
| 3D 표출 | `world_center_y_m` | 손상 대표점의 EPSG:5186 Y 좌표(m) |
| 3D 표출 | `world_center_z_m` | 손상 대표점의 OBJ Z-up 좌표(m) |
| 정량값 | `length_px` | 균열 길이(pixel) |
| 정량값 | `length_m` | 균열 길이(m) |
| 정량값 | `width_px` | 균열 폭(pixel) |
| 정량값 | `width_m` | 균열 폭(m) |
| 정량값 | `area_m2` | 박리 또는 박락 면적(m²) |

### 표출 시 적용 기준

- 2D 사진 표출에는 `image`와 `pixel_nodes_json`을 사용합니다.
- `pixel_nodes_json`은 손상 영역의 모든 pixel이나 완전한 mask가 아니라 표출용 외곽선 대표점입니다.
- `pixel_nodes_json`의 원점 `(0, 0)`은 원본 사진의 왼쪽 위입니다. x는 오른쪽, y는 아래쪽으로 증가합니다.
- 3D 모델 표출에는 `world_center_x_m`, `world_center_y_m`, `world_center_z_m`을 한 개의 손상 표시점으로 사용합니다.
- 길이·폭·면적 표출에는 손상 종류에 맞는 정량 열을 사용합니다.
- `CRC` 행의 `area_m2`는 사용하지 않으므로 비어 있습니다.
- `DLM`, `SPL` 행의 길이·폭 열은 사용하지 않으므로 비어 있습니다.
- 빈칸은 0이 아니라 해당 값이 적용되지 않거나 생성되지 않았다는 의미입니다.
- 한 행은 사진 한 장에서 확인된 손상 한 건입니다. 같은 손상이 여러 사진에 나타나면 여러 행으로 기록될 수 있습니다.
- m와 m² 단위 정량값은 근사값이므로 정밀 측량값으로 사용하지 않습니다.

## 산출물 예시

샘플 사진 7장의 결과에는 총 718개 손상 행이 있습니다.

- `CRC`: 110개
- `DLM`: 338개
- `SPL`: 270개

파일은 다음 위치에서 바로 확인할 수 있습니다.

- [CSV 예시](04_Output/examples/left03_aug512_full_20260903/damage_results.csv)
- [Excel 예시](04_Output/examples/left03_aug512_full_20260903/damage_results.xlsx)
- [예시 파일 설명](04_Output/examples/left03_aug512_full_20260903/README.md)

## License

프로젝트 코드는 [MIT License](LICENSE)를 따릅니다. 모델은 별도 [SAM License](02_Model/sam3_aug512/third_party/SAM_LICENSE)를 따릅니다.
