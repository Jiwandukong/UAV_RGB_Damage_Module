# UAV RGB Damage Module

드론으로 촬영한 콘크리트 댐 RGB 사진에서 손상을 찾고, 사진 위 위치와 댐 3D 모델 위 위치를 계산한 뒤 길이·폭·면적을 CSV와 Excel로 정리하는 프로젝트입니다.

처리 결과는 다음 순서로 만들어집니다.

```text
드론 원본 사진
  → SAM3 손상 탐지
  → 사진 위 손상 경계 추출
  → 카메라에서 3D 댐 모델로 가상의 직선(Ray)을 보내 손상 좌표 계산
  → 3D 모델에서 사진 한 픽셀(pixel)의 실제 크기(GSD)를 근사 계산
  → 손상 길이·폭·면적 환산
  → CSV 및 Excel 저장
```

원본 사진은 크기를 바꾸지 않습니다. 5280×3956 사진의 오른쪽과 아래쪽만 임시로 채운 뒤 512×512 조각으로 탐지하고, 결과를 다시 원본 사진 좌표에 맞춥니다.

3D 좌표 계산에는 EPSG:5186 X/Y와 Z-up 고도 좌표를 사용하는 `dam - Cloud.obj`가 필요합니다. 절대좌표가 없는 `DaecheongDam_v0829_grid.glb`는 사용하지 않습니다.

## 손상 라벨

| 라벨 | 영문 | 한글 | 의미 | 이 프로젝트의 정량값 |
|---|---|---|---|---|
| `CRC` | Crack | 균열 | 콘크리트 표면에 생긴 갈라짐 | 길이와 폭 |
| `DLM` | Delamination | 박리 | 표면 또는 피복층이 들뜨거나 분리된 영역 | 면적 |
| `SPL` | Spalling | 박락 | 콘크리트 일부가 떨어져 나간 영역 | 면적 |

라벨과 손상 범위는 SAM3가 예측한 결과이며, 전문가의 현장 진단을 대신하지 않습니다.

## 최종 산출물

실행이 끝나면 `04_Output/runs/<실행시각>/tables/`에 다음 파일이 생성됩니다.

- `damage_results.csv`: 다른 프로그램에서 읽기 쉬운 CSV
- `damage_results.xlsx`: 사람이 확인하기 쉬운 Excel. `Damage_Details` 시트 하나만 포함합니다.

한 행은 사진 한 장에서 서로 이어진 손상 영역 한 개를 뜻합니다. 같은 실제 손상이 여러 사진에 보이면 여러 행으로 기록될 수 있으며, 현재 버전은 사진 간 중복을 자동으로 합치지 않습니다.

### 산출물 13개 열

| 구분 | 열 이름 | 내용과 용도 |
|---|---|---|
| 기본 정보 | `image` | 손상이 탐지된 원본 사진 파일명 |
| 기본 정보 | `damage_id` | 한 번의 전체 실행에서 손상마다 순서대로 부여한 ID |
| 기본 정보 | `damage_type` | 손상 코드: `CRC`, `DLM`, `SPL` |
| 기본 정보 | `damage_name_ko` | 손상 한글명: 균열, 박리, 박락 |
| 영상 표출용 | `pixel_nodes_json` | 원본 사진 위 손상 외곽선의 대표점 목록. `[[x, y], ...]` 형식이며 사진의 왼쪽 위가 `(0, 0)`입니다. x는 오른쪽, y는 아래쪽으로 커집니다. |
| 3D 표출용 | `world_center_x_m` | 손상 영역 중심에 가장 가까운 손상 pixel에서 보낸 Ray가 3D 모델과 만나는 EPSG:5186 X 좌표(m) |
| 3D 표출용 | `world_center_y_m` | 같은 교차점의 EPSG:5186 Y 좌표(m) |
| 3D 표출용 | `world_center_z_m` | 같은 교차점의 Z-up 높이(m) |
| 정량 정보 | `length_px` | `CRC` 영역을 가장 작게 감싸는 기울어진 사각형의 긴 변(pixel) |
| 정량 정보 | `length_m` | `length_px`를 손상 위치의 GSD로 환산한 근사 길이(m) |
| 정량 정보 | `width_px` | `CRC` 영역을 가장 작게 감싸는 기울어진 사각형의 짧은 변(pixel) |
| 정량 정보 | `width_m` | `width_px`를 손상 위치의 GSD로 환산한 근사 폭(m) |
| 정량 정보 | `area_m2` | `DLM` 또는 `SPL`로 탐지된 pixel 수를 손상 위치의 GSD로 환산한 근사 면적(m²) |

`pixel_nodes_json`은 화면에 손상 외곽선을 그리기 위한 대표점이며 탐지 영역의 모든 pixel을 담은 데이터는 아닙니다. 3D 화면에는 `world_center_x_m`, `world_center_y_m`, `world_center_z_m`을 손상 표시점 위치로 사용할 수 있습니다.

빈칸은 0을 뜻하지 않습니다.

- `CRC` 행의 `area_m2`는 사용하지 않으므로 비어 있습니다.
- `DLM`, `SPL` 행의 길이·폭 4개 열은 사용하지 않으므로 비어 있습니다.
- Ray가 3D 모델에 닿지 않으면 3D 좌표가 비어 있을 수 있습니다.
- 손상 위치의 GSD를 계산하지 못하면 해당 m 또는 m² 값이 비어 있을 수 있습니다.

`CRC`의 길이는 굽은 균열을 따라 측정한 중심선 길이가 아니라, 탐지 영역을 가장 작게 감싸는 기울어진 사각형의 긴 변입니다. `length_m`, `width_m`, `area_m2`는 정밀 측량값이 아닌 근사값으로 사용해야 합니다.

샘플 사진 7장을 실행한 결과는 다음 파일에서 바로 확인할 수 있습니다.

- [산출물 설명](04_Output/examples/left03_aug512_full_20260903/README.md)
- [CSV 예시](04_Output/examples/left03_aug512_full_20260903/damage_results.csv)
- [Excel 예시](04_Output/examples/left03_aug512_full_20260903/damage_results.xlsx)

예시에는 총 718개 손상 관측이 있으며 `CRC` 110개, `DLM` 338개, `SPL` 270개입니다.

## 폴더 구조

```text
UAV_RGB/
├── 01_RawData/
│   ├── missions/             # 공개 샘플 원본 사진과 비행 위치·자세 자료
│   ├── geometry/             # 3D OBJ를 둘 위치와 파일 정보
│   └── manifests/            # 입력 파일 크기와 SHA-256
├── 02_Model/
│   └── sam3_aug512/          # 모델 설명, 체크포인트 검증·배포 정보
├── 03_Processing/
│   ├── configs/              # 탐지 설정
│   ├── scripts/              # 다운로드·검증·전체 실행 명령
│   ├── src/                  # 처리 코드
│   └── tests/                # 자동 테스트
├── 04_Output/
│   ├── examples/             # Git에 포함한 최종 산출물 예시
│   └── runs/                 # 새 실행 결과가 저장되는 위치
└── 05_Docs/                  # 좌표, GSD, 산출물 상세 문서
```

## 설치

Python 3.11 이상, CUDA를 사용할 수 있는 NVIDIA GPU, CUDA 지원 PyTorch가 필요합니다. 현재 확인한 SAM3 코드는 모델을 만드는 과정에서 CUDA가 필요하므로 CPU 전용 환경은 지원하지 않습니다.

저장소를 받은 뒤 공식 SAM3를 별도 설치합니다. 이 프로젝트에서 호환성을 확인한 SAM3 commit은 아래와 같습니다.

```bash
git clone https://github.com/Jiwandukong/UAV_RGB_Damage_Module.git UAV_RGB
cd UAV_RGB

git clone https://github.com/facebookresearch/sam3.git ../sam3
git -C ../sam3 checkout 46957e47805eaa273f4aa7bbbd25a88bca9108ce

python -m pip install -e ../sam3
python -m pip install -e ".[mesh-gpu]"
```

## SAM3 체크포인트 받기

학습된 `checkpoint_final.pt`는 10,081,318,934 bytes이므로 일반 Git 파일로 포함하지 않습니다. GitHub Release의 6개 분할 파일을 다음 명령이 내려받고, SHA-256을 확인한 뒤 하나의 파일로 복원하도록 구성했습니다.

```bash
python 03_Processing/scripts/download_checkpoint.py
python 03_Processing/scripts/verify_checkpoint.py --strict-load
```

복원된 파일 위치:

```text
02_Model/sam3_aug512/checkpoints/checkpoint_final.pt
```

체크포인트 SHA-256:

```text
a2749dba62207575afac9ed42f923d7cdfd7e2d2f0ffb2210a103e91657d985d
```

GitHub Release 다운로드 또는 분할 파일 복원이 작동하지 않으면 저장소 관리자에게 요청해 원본 약 10GB `checkpoint_final.pt`를 직접 전달받은 뒤 위 경로에 두십시오.

## 3D OBJ 준비

좌표 계산에 필요한 OBJ도 Git 저장소에는 포함하지 않습니다. 아래 파일과 일치하는 원본을 별도로 준비해 지정된 경로에 두십시오.

- 원본 파일명: `dam - Cloud.obj`
- 크기: 184,020,785 bytes
- 좌표 기준: EPSG:5186 X/Y, metre, Z-up
- SHA-256: `a7566c8d8f70de91db18c70ae5f404b0f7885e679a1027fd3e1936afd2d1e470`

```bash
cp "/path/to/dam - Cloud.obj" 01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
python 03_Processing/scripts/verify_assets.py
```

OBJ 파일 자체에는 CRS 태그가 없으므로 위 좌표 기준 정보를 파일과 함께 관리해야 합니다.

## 실행

기본 입력은 저장소에 포함된 `DJI_202507021616_left03`의 원본 사진 7장입니다.

```bash
python 03_Processing/scripts/run_pipeline.py --profile
```

다른 사진과 위치 자료를 사용하려면 `--images`, `--mrk`, `--mesh`, `--output-dir` 인수를 지정하십시오. 전체 인수는 다음 명령으로 확인할 수 있습니다.

```bash
python 03_Processing/scripts/run_pipeline.py --help
```

## 결과를 해석할 때 주의할 점

- SAM3 학습용 512×512는 입력 사진 전체 크기가 아니라 잘라서 처리하는 한 조각의 크기입니다.
- 사진 전체에 고정 GSD 하나를 적용하지 않고, 각 손상 주변의 Ray와 3D 모델 교차점을 이용해 방향별 GSD를 근사합니다.
- 카메라 렌즈 왜곡 보정과 MRK 고도/OBJ 높이 기준의 일치 여부는 아직 검증하지 않았습니다.
- `CRC`, `DLM`, `SPL`은 서로 독립적으로 탐지하므로 같은 pixel에 둘 이상의 라벨이 겹칠 수 있습니다.
- 여러 사진의 결과를 단순 합산하면 같은 실제 손상을 중복 계산할 수 있습니다.
- 이 결과는 연구 및 검토용이며 구조물 안전 판정이나 정밀 측량을 대신하지 않습니다.

계산 방식은 [좌표와 GSD](05_Docs/COORDINATES_AND_GSD.md), 파일 형식은 [산출물 명세](05_Docs/OUTPUT_SPECIFICATION.md)에서 자세히 설명합니다.

## License

프로젝트 코드는 [MIT License](LICENSE)를 따릅니다. SAM3와 체크포인트는 별도 [SAM License](02_Model/sam3_aug512/third_party/SAM_LICENSE)를 따릅니다. 공개 샘플 데이터와 외부 자산의 권리는 코드 License와 별도로 확인해야 합니다.
