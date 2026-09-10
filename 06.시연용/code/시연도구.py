#!/usr/bin/env python3
"""Prepare immutable Demo20 tiles or fine-tune the separate native512 model."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="시연용 데이터 준비 및 실제 512×512 SAM3 추가 학습")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="원본/라벨에서512타일과1픽셀균열마스크준비")
    prepare.add_argument("--source", required=True, help="Daechung_Demo20_GT_release_v1 폴더")
    prepare.add_argument("--output", required=True, help="새 데이터 폴더; 기존 폴더 덮어쓰기 금지")
    train = commands.add_parser("train", help="손상이 있는 타일만 실제512입력으로학습")
    from demo512.training import add_training_arguments, run_training
    add_training_arguments(train)
    predict = commands.add_parser("predict", help="학습한 모델로512타일한장실제예측; 라벨불사용")
    predict.add_argument("--image", required=True, help="512×512 RGB 타일 PNG")
    predict.add_argument("--model-record", required=True, help="학습 결과의 학습기록.json")
    predict.add_argument("--output", required=True, help="새 예측 결과 폴더")
    predict.add_argument("--threshold", type=float, default=0.5)
    predict.add_argument("--valid-width", type=int, default=512, help="가장자리 타일의 실제 사진 폭; dataset.json valid_width")
    predict.add_argument("--valid-height", type=int, default=512, help="가장자리 타일의 실제 사진 높이; dataset.json valid_height")
    batch = commands.add_parser("predict-batch", help="손상타일 전체의 모델예측·라벨오버레이를 따로 저장하고 비교")
    from demo512.batch_prediction import add_batch_prediction_arguments
    add_batch_prediction_arguments(batch)
    refresh = commands.add_parser("refresh-overlays", help="재학습·재추론 없이 저장된 배치 오버레이의 투명도만 변경")
    refresh.add_argument("--data", required=True, help="기존 01.시연데이터 폴더; 변경하지 않음")
    refresh.add_argument("--results", required=True, help="이미 완료된 배치 결과 폴더; 오버레이만 다시 저장")
    refresh.add_argument("--alpha", type=float, default=0.5, help="색상 불투명도: 0=원본, 0.5=반투명, 1=진한 단색")
    quantify = commands.add_parser("quantify", help="검수 라벨+기존OBJ로 시연용CSV·Excel·512표출이미지 생성; 모델추론 없음")
    quantify.add_argument("--data", required=True, help="보존된 01.시연데이터 폴더")
    quantify.add_argument("--output", required=True, help="새 시연 산출물 폴더; 기존 폴더 덮어쓰기 금지")
    quantify.add_argument("--mesh", required=True, help="기존 dam - Cloud.obj; 새 GLB 사용 불가")
    quantify.add_argument("--asset-manifest", help="기존 OBJ의 SHA256·좌표계 기록; 생략 시 프로젝트 기본값")
    quantify.add_argument("--ray-backend", choices=["auto", "warp", "trimesh"], default="auto")
    quantify.add_argument("--warp-device", default="cpu", help="Ray 계산 장치; 기본CPU, 학습용GPU 불필요")
    args = parser.parse_args()
    if args.command == "prepare":
        from demo512.data import prepare_dataset
        result = prepare_dataset(args.source, args.output, tile_size=512)
        print(json.dumps(result.get("summary", {}), ensure_ascii=False, indent=2))
    elif args.command == "train":
        result = run_training(args)
        print(json.dumps({key: result.get(key) for key in (
            "status", "completed_steps", "completed_epochs", "checkpoint", "demo_quality_validated"
        )}, ensure_ascii=False, indent=2))
    elif args.command == "predict":
        from demo512.prediction import run_prediction
        print(json.dumps(run_prediction(args), ensure_ascii=False, indent=2))
    elif args.command == "refresh-overlays":
        from demo512.overlay_refresh import refresh_batch_overlays
        print(json.dumps(refresh_batch_overlays(args.data, args.results, args.alpha),
                         ensure_ascii=False, indent=2))
    elif args.command == "quantify":
        from demo512.quantification import export_demo
        result = export_demo(args.data, args.output, args.mesh, args.asset_manifest,
                             ray_backend=args.ray_backend, warp_device=args.warp_device)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        from demo512.batch_prediction import run_batch_prediction
        result = run_batch_prediction(args)
        print(json.dumps({key: result.get(key) for key in ("status", "completed_tiles", "metrics_path")},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
