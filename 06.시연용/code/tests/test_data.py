import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from demo512.data import CLASSES, OVERLAY_ALPHA, prepare_dataset, rasterize_annotation, round_points, sha256_file


def shape(label, points):
    return {
        "label": label,
        "shape_type": "linestrip" if label == "CRC" else "polygon",
        "points": points,
        "group_id": None,
        "flags": {},
    }


def source_release(root: Path, size=(9, 7), shapes=None):
    image_root = root / "01_Dataset" / "images"
    label_root = root / "01_Dataset" / "labels"
    image_root.mkdir(parents=True)
    label_root.mkdir(parents=True)
    stem = "DJI_20260826114456_1000_V"
    image = np.arange(size[0] * size[1] * 3, dtype=np.uint8).reshape(size[1], size[0], 3)
    image_path = image_root / f"{stem}.JPG"
    Image.fromarray(image).save(image_path, quality=95)
    label_path = label_root / f"{stem}.json"
    label_path.write_bytes((json.dumps({
        "imagePath": image_path.name, "imageWidth": size[0], "imageHeight": size[1],
        "shapes": shapes or [],
    }, indent=2) + "\r\n").encode())
    (root / "README.md").write_bytes(b"Preserve original release bytes.\r\n")
    return image_path, label_path


def read_mask(root, path):
    with Image.open(root / path) as image:
        return np.asarray(image).copy()


def test_crc_horizontal_is_exact_integer_one_pixel():
    mask = np.asarray(rasterize_annotation(shape("CRC", [[1, 3], [6, 3]]), (9, 8)))
    expected = np.zeros((8, 9), dtype=np.uint8)
    expected[3, 1:7] = 255
    np.testing.assert_array_equal(mask, expected)
    assert round_points([[0.5, 1.5], [-0.5, -1.5], [2.49, 2.51]]) == [(1, 2), (-1, -2), (2, 3)]


def test_crc_diagonal_has_one_pixel_per_step():
    mask = np.asarray(rasterize_annotation(shape("CRC", [[1, 1], [6, 6]]), (8, 8)))
    expected = np.zeros((8, 8), dtype=np.uint8)
    expected[np.arange(1, 7), np.arange(1, 7)] = 255
    np.testing.assert_array_equal(mask, expected)


def test_polygons_are_filled_and_classes_are_independent():
    polygon = shape("DLM", [[1, 1], [4, 1], [4, 4], [1, 4]])
    mask = np.asarray(rasterize_annotation(polygon, (7, 7)))
    assert np.count_nonzero(mask) == 16
    assert mask[2, 2] == 255
    assert set(np.unique(mask)) == {0, 255}
    with pytest.raises(ValueError, match="requires linestrip"):
        rasterize_annotation({**polygon, "label": "CRC"}, (7, 7))


def test_tiling_preserves_pixels_boundaries_padding_and_instances(tmp_path):
    root = tmp_path / "source"
    shapes = [
        shape("CRC", [[0, 2], [8, 2]]),
        shape("CRC", [[0, 0], [6, 6]]),
        shape("CRC", [[4, 2], [4, 5]]),
        shape("DLM", [[1, 1], [5, 1], [5, 4], [1, 4]]),
        shape("SPL", [[3, 2], [7, 2], [7, 5], [3, 5]]),
    ]
    source_image, source_label = source_release(root, shapes=shapes)
    original_bytes = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    output = tmp_path / "prepared"
    manifest = prepare_dataset(root, output, tile_size=4)
    assert manifest["overlay"]["alpha"] == OVERLAY_ALPHA == 0.5
    assert manifest["summary"]["tiles"] == 6
    assert manifest["summary"]["fully_valid_tiles"] == 2
    assert manifest["summary"]["padded_tiles"] == 4
    assert manifest["summary"]["annotations"] == {"CRC": 3, "DLM": 1, "SPL": 1}
    reconstructed_image = np.zeros((8, 12, 3), dtype=np.uint8)
    reconstructed_masks = {label: np.zeros((8, 12), dtype=np.uint8) for label in CLASSES}
    for tile in manifest["tiles"]:
        y0, x0 = tile["y0"], tile["x0"]
        image = read_mask(output, tile["image_path"])
        reconstructed_image[y0:y0 + 4, x0:x0 + 4] = image
        valid = read_mask(output, tile["valid_mask_path"])
        expected_valid = np.zeros((4, 4), dtype=np.uint8)
        expected_valid[:tile["valid_height"], :tile["valid_width"]] = 255
        np.testing.assert_array_equal(valid, expected_valid)
        assert not np.any(image[valid == 0])
        for label in CLASSES:
            mask = read_mask(output, tile["mask_paths"][label])
            reconstructed_masks[label][y0:y0 + 4, x0:x0 + 4] = mask
            assert tile["positive_pixels"][label] == np.count_nonzero(mask)
            assert not np.any(mask[valid == 0])
        assert tile["is_negative"] == (not any(tile["positive_pixels"].values()))
        assert tile["training_eligible"] == (not tile["is_negative"])
        assert tile["training_classes"] == [label for label in CLASSES if tile["positive_pixels"][label] > 0]
    with Image.open(source_image) as image:
        expected_image = np.asarray(image.convert("RGB"))
    np.testing.assert_array_equal(reconstructed_image[:7, :9], expected_image)
    assert not reconstructed_image[7:, :].any()
    assert not reconstructed_image[:, 9:].any()
    for label in CLASSES:
        expected = np.zeros((7, 9), dtype=np.uint8)
        for annotation in shapes:
            if annotation["label"] == label:
                expected |= np.asarray(rasterize_annotation(annotation, (9, 7)))
        np.testing.assert_array_equal(reconstructed_masks[label][:7, :9], expected)
    assert np.all(reconstructed_masks["CRC"][2, :9] == 255)
    # Pixel (4, 2) has three class labels; none is erased from binary training GT.
    assert all(reconstructed_masks[label][2, 4] == 255 for label in CLASSES)
    tile = next(tile for tile in manifest["tiles"] if tile["x0"] == 4 and tile["y0"] == 0)
    original_pixel = read_mask(output, tile["image_path"])[2, 0]
    expected_pixel = ((1 - OVERLAY_ALPHA) * original_pixel + OVERLAY_ALPHA * np.array([0, 255, 0])).astype(np.uint8)
    np.testing.assert_array_equal(read_mask(output, tile["overlay_path"])[2, 0], expected_pixel)
    crc_instances = [item for item in tile["instances"] if item["label"] == "CRC"]
    assert len(crc_instances) == 2
    assert len({item["damage_id"] for item in crc_instances}) == 2
    for instance in crc_instances:
        assert read_mask(output, instance["instance_mask_path"])[2, 0] == 255
    source = manifest["sources"][0]
    assert [item["shape_index"] for item in source["annotations"]] == list(range(5))
    assert [item["original_shape"] for item in source["annotations"]] == shapes
    assert source["image_sha256"] == sha256_file(source_image)
    assert source["label_sha256"] == sha256_file(source_label)
    assert source["source_year"] == 2026
    for relative, data in original_bytes.items():
        assert (root / relative).read_bytes() == data
        assert (output / "원본자료" / root.name / relative).read_bytes() == data
    assert str(tmp_path) not in (output / "dataset.json").read_text()
    assert json.loads((output / "dataset.json").read_text()) == manifest


def test_no_overwrite_and_negative_tiles(tmp_path):
    root = tmp_path / "source"
    source_release(root, size=(5, 5))
    output = tmp_path / "output"
    manifest = prepare_dataset(root, output, tile_size=4)
    assert manifest["summary"]["negative_tiles"] == 4
    assert manifest["summary"]["positive_tiles"] == 0
    assert manifest["summary"]["training_eligible_tiles"] == 0
    assert manifest["summary"]["excluded_background_tiles"] == 4
    assert manifest["summary"]["training_pairs"] == 0
    assert manifest["summary"]["training_pairs_by_class"] == {"CRC": 0, "DLM": 0, "SPL": 0}
    assert all(not tile["training_classes"] for tile in manifest["tiles"])
    before = (output / "dataset.json").read_bytes()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        prepare_dataset(root, output, tile_size=4)
    assert (output / "dataset.json").read_bytes() == before
    empty_output = tmp_path / "already_exists"
    empty_output.mkdir()
    with pytest.raises(FileExistsError):
        prepare_dataset(root, empty_output, tile_size=4)


def test_invalid_source_does_not_publish_partial_dataset(tmp_path):
    root = tmp_path / "source"
    source_release(root, shapes=[shape("UNSUPPORTED", [[0, 0], [1, 1], [2, 0]])])
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Unsupported label"):
        prepare_dataset(root, output, tile_size=4)
    assert not output.exists()
    assert not list(tmp_path.glob(".output.staging-*"))
    assert not (tmp_path / ".output.prepare.lock").exists()


def test_output_must_not_be_inside_original_release(tmp_path):
    root = tmp_path / "source"
    source_release(root)
    with pytest.raises(ValueError, match="outside"):
        prepare_dataset(root, root / "output")


@pytest.mark.parametrize("tile_size", [0, -1, 0.5, True])
def test_invalid_tile_size(tmp_path, tile_size):
    with pytest.raises(ValueError, match="positive integer"):
        prepare_dataset(tmp_path / "source", tmp_path / "output", tile_size=tile_size)
