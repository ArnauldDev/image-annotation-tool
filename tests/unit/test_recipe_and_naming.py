from pathlib import Path

from iat.image_processor import Annotation, LoupeSpec, ProcessingRecipe, compute_associated_paths


def test_compute_associated_paths_raw_suffix():
    raw_path = Path("/workspace/images/carte-electronique-raw.jpg")
    json_path, export_path = compute_associated_paths(raw_path)
    assert json_path == Path("/workspace/images/carte-electronique-iat.json")
    assert export_path == Path("/workspace/images/carte-electronique-iat.jpg")


def test_compute_associated_paths_underscore_raw():
    raw_path = Path("images/IMG_2026_raw.PNG")
    json_path, export_path = compute_associated_paths(raw_path)
    assert json_path == Path("images/IMG_2026-iat.json")
    assert export_path == Path("images/IMG_2026-iat.jpg")


def test_compute_associated_paths_standard_image():
    image_path = Path("photo.jpeg")
    json_path, export_path = compute_associated_paths(image_path)
    assert json_path == Path("photo-iat.json")
    assert export_path == Path("photo-iat.jpg")


def test_compute_associated_paths_includes_export_width_in_default_export_name():
    image_path = Path("images/carte-electronique-raw.jpg")
    json_path, export_path = compute_associated_paths(image_path, export_width=1400)
    assert json_path == Path("images/carte-electronique-iat.json")
    assert export_path == Path("images/carte-electronique-iat-x1400.jpg")


def test_recipe_serialization_includes_stroke_width():
    recipe = ProcessingRecipe(
        source_image="test.jpg",
        stroke_width=5,
        annotations=[
            Annotation(type="rect", x1=10, y1=10, x2=50, y2=50, stroke_width=5),
        ],
    )
    data = recipe.to_dict()
    assert data["stroke_width"] == 5
    assert data["annotations"][0]["stroke_width"] == 5

    restored = ProcessingRecipe.from_dict(data)
    assert restored.stroke_width == 5
    assert restored.annotations[0].stroke_width == 5


def test_recipe_backward_compatibility_when_stroke_width_missing():
    legacy_data = {
        "source_image": "old.jpg",
        "angle": 0.0,
        "brightness": 0.0,
        "contrast": 1.0,
        "annotations": [],
        "loupe": {},
    }
    recipe = ProcessingRecipe.from_dict(legacy_data)
    assert recipe.stroke_width == 3


def test_recipe_serialization_includes_trapezoid_correction():
    recipe = ProcessingRecipe(trapezoid=(0.2, -0.1))

    restored = ProcessingRecipe.from_dict(recipe.to_dict())

    assert restored.trapezoid == (0.2, -0.1, 0.0, 0.0)


def test_recipe_preserves_custom_colour_palette():
    recipe = ProcessingRecipe(custom_colors=["#123456", "#abcdef"])

    restored = ProcessingRecipe.from_json(recipe.to_json())

    assert restored.custom_colors == ["#123456", "#abcdef"]
