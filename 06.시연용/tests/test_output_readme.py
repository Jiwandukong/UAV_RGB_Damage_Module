"""Keep the delivered README truthful for GT-only and bundled model images."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from demo512.quantification import _readme


SUMMARY = dict(images=20, rows=629, tiles=489, mapped_rows=588,
               physical_values_exported=583, physical_values_withheld=46)


def test_quantify_default_does_not_advertise_uncreated_model_overlays():
    text = _readme(SUMMARY)
    assert "512라벨오버레이/" in text
    assert "512모델예측오버레이/" not in text
    assert "실행 안내" not in text


def test_bundled_model_images_do_not_change_csv_label_provenance():
    text = _readme(SUMMARY, include_model_overlays=True)
    assert "[512모델예측오버레이/](512모델예측오버레이/)" in text
    assert "CSV·정량값·`tile_overlay_paths_json`은 기존 라벨 기준을 유지합니다." in text
    assert "같은 파일명끼리 대응합니다." in text


def test_published_readme_matches_bundled_documentation():
    path = Path(__file__).resolve().parents[1] / "04.시연산출물/README.md"
    assert path.read_text(encoding="utf-8") == _readme(
        SUMMARY, include_model_overlays=True)
