import json

from PIL import Image, ImageChops

# pyrefly: ignore [missing-import]
from iat.image_processor import (
    Annotation,
    LoupeSpec,
    ProcessingRecipe,
    apply_brightness_contrast,
    apply_trapezoid_correction,
    draw_annotations,
    draw_loupe,
    load_image,
    resize_with_aspect_ratio,
    rotate_image,
)


def test_load_image_from_raw_source(temp_image_file):
    image = load_image(temp_image_file)
    assert image.mode in {"RGB", "RGBA", "L"}
    assert image.size[0] > 0 and image.size[1] > 0


def test_resize_with_aspect_ratio_prefers_width_when_two_values_are_given():
    image = Image.new("RGB", (100, 50))

    resized_by_width = resize_with_aspect_ratio(image, width=200)
    assert resized_by_width.size == (200, 100)

    resized_by_height = resize_with_aspect_ratio(image, height=75)
    assert resized_by_height.size == (150, 75)

    resized_when_both_given = resize_with_aspect_ratio(image, width=200, height=60)
    assert resized_when_both_given.size == (200, 100)


def test_rotation_and_brightness_are_applied_without_changing_size():
    image = Image.new("RGB", (100, 50))

    rotated = rotate_image(image, 90)
    assert rotated.size == (50, 100)

    adjusted = apply_brightness_contrast(image, brightness=20, contrast=1.5)
    assert adjusted.size == image.size
    assert adjusted.mode == image.mode


def test_trapezoid_correction_preserves_canvas_size_and_changes_pixels():
    image = Image.new("RGB", (100, 60), "black")
    for x in range(20, 80):
        for y in range(10, 50):
            image.putpixel((x, y), (255, 255, 255))

    corrected = apply_trapezoid_correction(image, top_inset=0.2, bottom_inset=0.0)

    assert corrected.size == image.size
    assert ImageChops.difference(corrected, image).getbbox() is not None


def test_annotations_support_reversed_rectangles_and_boxed_labels():
    image = Image.new("RGB", (200, 150), "black")

    rendered = draw_annotations(
        image,
        [
            Annotation(type="rect", x1=160, y1=120, x2=20, y2=30, color="#ffff00"),
            Annotation(type="label", x1=10, y1=10, x2=140, y2=100, text="Détail", color="#00ff00"),
        ],
    )

    assert rendered.size == image.size
    assert rendered.getpixel((20, 30)) != (0, 0, 0)
    assert rendered.getpixel((140, 100)) != (0, 0, 0)


def test_legacy_recipe_without_annotation_ids_is_migrated_on_load(tmp_path):
    # Ancien format : les annotations n'ont pas de clé "id" et layer_order
    # référence leur position dans le tableau ("annotation:<index>").
    legacy_recipe = {
        "source_image": "photo-raw.jpg",
        "angle": 0.5,
        "brightness": 0.0,
        "contrast": 1.0,
        "trapezoid": [0.0, 0.0, 0.0, 0.0],
        "crop": None,
        "export": {"width": 800, "height": 600},
        "stroke_width": 4,
        "annotations": [
            {"type": "label", "x1": 10, "y1": 10, "x2": 50, "y2": 50, "text": "A", "color": "#ff0000"},
            {"type": "rect", "x1": 60, "y1": 60, "x2": 100, "y2": 100, "color": "#00ff00"},
            {"type": "circle", "x1": 120, "y1": 120, "x2": 160, "y2": 160, "color": "#0000ff"},
        ],
        "loupes": [{"id": 1, "enabled": True, "center_x": 5, "center_y": 5, "radius": 10, "zoom": 2}],
        "custom_colors": [],
        "layer_order": ["annotation:1", "loupe:1", "annotation:0", "annotation:2"],
    }
    path = tmp_path / "legacy-iat.json"
    path.write_text(json.dumps(legacy_recipe), encoding="utf-8")

    recipe = ProcessingRecipe.load(path)

    # Chaque annotation chargée porte désormais un id entier unique.
    ids = [annotation.id for annotation in recipe.annotations]
    assert ids == [1, 2, 3]
    assert len(set(ids)) == len(ids)

    # Aucune donnée n'a été perdue pendant la migration.
    assert [annotation.type for annotation in recipe.annotations] == ["label", "rect", "circle"]
    assert recipe.annotations[0].text == "A"
    assert recipe.annotations[0].color == "#ff0000"
    assert recipe.annotations[1].color == "#00ff00"
    assert recipe.annotations[2].color == "#0000ff"

    # layer_order est converti des index positionnels vers les ids, sans
    # corrompre l'ordre relatif (front-to-back) ni les jetons de loupe.
    assert recipe.layer_order == ["annotation:2", "loupe:1", "annotation:1", "annotation:3"]

    # La recette migrée se ré-enregistre avec les ids persistés (chaque
    # annotation sérialisée porte une clé "id"), et un second chargement
    # est stable (idempotent) : plus aucune conversion n'a lieu.
    saved = json.loads(recipe.to_json())
    assert all("id" in annotation for annotation in saved["annotations"])
    reloaded = ProcessingRecipe.from_dict(saved)
    assert [annotation.id for annotation in reloaded.annotations] == ids
    assert reloaded.layer_order == recipe.layer_order


def test_loupe_zooms_the_arrow_target_not_its_display_position():
    image = Image.new("RGB", (120, 120), "blue")
    for x in range(10, 31):
        for y in range(90, 111):
            image.putpixel((x, y), (255, 0, 0))

    rendered = draw_loupe(
        image,
        LoupeSpec(
            enabled=True,
            center_x=80,
            center_y=25,
            radius=15,
            zoom=2,
            arrow_start_x=80,
            arrow_start_y=25,
            arrow_end_x=20,
            arrow_end_y=100,
        ),
    )

    # Sample slightly off-centre to avoid the arrow line itself, which is
    # legitimately drawn across the loupe's centre point.
    assert rendered.getpixel((85, 20))[0] > 200
