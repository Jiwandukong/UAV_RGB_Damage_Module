# 대청댐 손상 시연

원본 사진 20장의 손상 라벨로 만든 **CSV·Excel과 512×512 이미지**입니다. 시연 결과는 라벨 기준이며, 실제 모델 예측은 별도로 제공합니다.

## 데이터와 결과는 어디에 있나요?

아래 경로는 모두 `06.시연용/` 기준입니다.

| 필요한 자료 | 위치 |
|---|---|
| Raw 데이터 — 원본 JPG 20장 | [01.시연데이터/원본자료/Daechung_Demo20_GT_release_v1/01_Dataset/images/](01.시연데이터/원본자료/Daechung_Demo20_GT_release_v1/01_Dataset/images/) |
| Raw 데이터 — 손상 라벨 JSON 20개 | [01.시연데이터/원본자료/Daechung_Demo20_GT_release_v1/01_Dataset/labels/](01.시연데이터/원본자료/Daechung_Demo20_GT_release_v1/01_Dataset/labels/) |
| 처리된 이미지 — 512×512 타일 489장 | [04.시연산출물/512원본타일/](04.시연산출물/512원본타일/) |
| 시연용 오버레이 — 라벨을 표시한 489장 | [04.시연산출물/512라벨오버레이/](04.시연산출물/512라벨오버레이/) |
| 실제 모델 예측 오버레이 489장 | [03.모델예측/20회학습_손상타일489개_오버레이/모델예측오버레이/](03.모델예측/20회학습_손상타일489개_오버레이/모델예측오버레이/) |
| CSV 결과 — 손상 629건 | [04.시연산출물/damage_results.csv](04.시연산출물/damage_results.csv) |
| Excel 결과 — CSV와 같은 내용 | [04.시연산출물/damage_results.xlsx](04.시연산출물/damage_results.xlsx) |

오버레이 색상은 **CRC = Crack(균열, 초록), DLM = Delamination(박리, 파랑), SPL = Spalling(박락, 노랑)**입니다. 원본이 보이도록 색상을 50%로 겹쳤습니다.

## 만들어진 결과를 플랫폼에 연결하기

`04.시연산출물/`을 이미지와 함께 사용하면 됩니다. **이미 저장된 결과를 표시하는 데는 코드 실행·모델·GPU가 필요하지 않습니다.**

1. CSV의 `world_center_x_m`, `world_center_y_m`, `world_center_z_m`으로 3D 손상점을 표시합니다. X/Y는 EPSG:5186, 단위는 m입니다. 좌표가 빈 행은 3D 표시에서 제외합니다.
2. 손상점을 클릭하면 해당 행의 `tile_original_paths_json`과 `tile_overlay_paths_json`을 JSON 배열로 읽습니다.
3. 두 배열의 같은 순번끼리 원본·오버레이를 연결합니다. 첫 번째 이미지를 기본 화면으로 사용합니다.

이미지 경로는 **CSV가 있는 `04.시연산출물/` 기준 상대경로**입니다. 잘리기 전 사진은 `source_image_path`에 있습니다.

길이·폭·면적과 표출용 컬럼의 뜻은 [CSV 컬럼 설명](04.시연산출물/README.md)을 참고하십시오. 빈칸은 0이 아니라 해당 없음 또는 계산 보류입니다.

## 원본부터 CSV와 오버레이를 다시 만들기

이 과정은 라벨로 시연 결과를 다시 만듭니다. **SAM3 모델이나 GPU는 필요하지 않습니다.** Python 3.11 환경에서 실행하십시오.

### 1. 설치와 3D 모델 준비

저장소 최상위 폴더(`pyproject.toml`이 있는 곳)에서 실행합니다.

```bash
python -m pip install -e . "warp-lang>=1.8"
```

[3D 모델 Release](https://github.com/Jiwandukong/UAV_RGB_Damage_Module/releases/tag/daecheong-dam-geometry-v1)에서 `daecheong_dam_epsg5186_zup.obj`를 받아 `01_RawData/geometry/`에 놓으십시오. 이미 있으면 다시 받을 필요가 없습니다.

### 2. Raw 데이터를 512×512로 자르기

```bash
cd '06.시연용'
python code/시연도구.py prepare \
  --source 01.시연데이터/원본자료/Daechung_Demo20_GT_release_v1 \
  --output 01.시연데이터/새_512데이터
```

리사이즈 없이 자릅니다. **학습·재계산용 처리 데이터**는 `01.시연데이터/새_512데이터/`에 생성됩니다. 그 안의 `원본타일/`은 이미지, `학습마스크/`는 손상 영역, `라벨오버레이/`는 확인용 이미지, `dataset.json`은 이들을 연결하는 목록입니다. 이 중간 데이터는 Git에 포함하지 않습니다.

### 3. CSV·Excel·표출 이미지 생성

```bash
python code/시연도구.py quantify \
  --data 01.시연데이터/새_512데이터 \
  --output 04.시연산출물_재생성 \
  --mesh ../01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
```

결과는 **`04.시연산출물_재생성/`**에 저장됩니다. CSV는 `damage_results.csv`, Excel은 `damage_results.xlsx`, 표출 이미지는 `512원본타일/`과 `512라벨오버레이/`에 있습니다.

두 명령 모두 기존 출력 폴더를 덮어쓰지 않습니다. 다시 실행할 때는 `--output`에 새 폴더명을 사용하고, `quantify --data`에는 앞서 만든 처리 데이터 폴더를 지정하십시오.

## SAM3 모델을 직접 실행하려면

시연용 모델 `sam3_demo512_학습완료.pt`는 약 3.37GB이며 Git에 포함되지 않습니다. **시연 모델 Release는 아직 없으므로 관리자에게 파일을 전달받아야 합니다.** [모델 저장 위치](02.시연모델/README.md)와 [모델 실행 명령](code/실행안내.md#4-실제-모델로512타일-한-장-예측)을 참고하십시오.

사진·라벨·모델의 이용 조건: [자료 출처와 이용 안내](권리_및_자료출처.md).
