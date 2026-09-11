# 댐 3D 모델 받기

손상 위치와 정량값 계산에 사용하는 **기존 `dam - Cloud.obj`**입니다. 새 GLB 모델로 바꾸지 않았습니다.

`06.시연용/`에서 실행합니다. Python 표준 라이브러리만 필요하며, 다운로드 후 크기와 SHA256을 검사합니다.

```bash
python code/3D모델받기.py
```

저장 위치와 파일 크기입니다.

```text
02.시연모델/댐3D모델/daecheong_dam_epsg5186_zup.obj
184,020,785 bytes (약 184MB)
```

[대청댐 OBJ Release](https://github.com/Jiwandukong/UAV_RGB_Damage_Module/releases/tag/daecheong-dam-geometry-v1)에서 직접 받거나 관리자에게 전달받아 같은 위치에 넣어도 됩니다.

- 파일 SHA256: `a7566c8d8f70de91db18c70ae5f404b0f7885e679a1027fd3e1936afd2d1e470`
- 좌표 기준: X/Y는 EPSG:5186, 단위 m, Z-up. OBJ 자체에 좌표계 태그가 들어 있는 것은 아닙니다.
- 같은 폴더의 [assets.yaml](assets.yaml)이 이 파일의 좌표 기준과 검증 정보를 제공합니다. 모델과 함께 유지하십시오.

다음 단계: [원본 사진 추론](../../code/플랫폼추론.md).
