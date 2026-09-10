#!/usr/bin/env python3
"""시연용 모델의 Release 조각을 내려받고 검증하여 합칩니다."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DEMO_ROOT.parent
DEFAULT_MANIFEST = DEMO_ROOT / "02.시연모델/release/release_manifest.json"
DEFAULT_OUTPUT = (
    DEMO_ROOT
    / "02.시연모델/손상타일489개_512입력_20회학습/sam3_demo512_학습완료.pt"
)
DOWNLOADER = PROJECT_ROOT / "03_Processing/scripts/download_checkpoint.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="시연 모델 다운로드·복원 (GPU 및 추가 Python 패키지 불필요).",
        epilog="각 조각과 완성 모델의 크기·SHA256을 검사합니다. 다른 기존 파일은 덮어쓰지 않습니다.",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="모델 저장 경로 (기본: 02.시연모델의 20회학습 폴더).",
    )
    parser.add_argument(
        "--parts-dir", type=Path,
        help="이미 받은 part001·part002가 있는 폴더. 지정하면 다운로드하지 않습니다.",
    )
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST,
        help="크기·해시·다운로드 주소가 기록된 파일 (기본: 시연 모델의 release_manifest.json).",
    )
    parser.add_argument("--base-url", help="Release 다운로드 주소를 직접 지정할 때 사용합니다.")
    args = parser.parse_args(argv)

    if not DOWNLOADER.is_file():
        parser.error("03_Processing/scripts/download_checkpoint.py가 필요합니다. 저장소 전체를 받아 주세요.")
    manifest = args.manifest.expanduser().resolve()
    if not manifest.is_file():
        parser.error(f"모델 배포 정보 파일을 찾을 수 없습니다: {manifest}")

    command = [
        sys.executable, str(DOWNLOADER),
        "--manifest", str(manifest),
        "--output", str(args.output.expanduser().resolve()),
    ]
    if args.parts_dir is not None:
        command.extend(["--parts-dir", str(args.parts_dir.expanduser().resolve())])
    if args.base_url is not None:
        command.extend(["--base-url", args.base_url])
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
