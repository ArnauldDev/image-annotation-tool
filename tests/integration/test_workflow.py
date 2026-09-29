import json
from pathlib import Path
from PIL import Image

from iat.image_processor import (
    Annotation,
    LoupeSpec,
    ProcessingRecipe,
    apply_recipe,
    compute_associated_paths,
    process_image_with_recipe,
)


def test_full_annotation_workflow_and_json_lifecycle(tmp_path):
    # 1. Create a dummy raw image
    raw_image_path = tmp_path / "circuit-board-raw.jpg"
    img = Image.new("RGB", (300, 200), color="darkblue")
    img.save(raw_image_path, format="JPEG")

    # 2. Derive associated paths
    json_path, export_path = compute_associated_paths(raw_image_path)
    assert json_path == tmp_path / "circuit-board-iat.json"
    assert export_path == tmp_path / "circuit-board-iat.jpg"
    assert not json_path.exists()

    # 3. Build a recipe with annotations and stroke_width
    recipe = ProcessingRecipe(
        source_image=str(raw_image_path),
        angle=90.0,
        stroke_width=4,
        annotations=[
            Annotation(type="rect", x1=20, y1=20, x2=100, y2=80, stroke_width=4, color="#FFFF00"),
            Annotation(type="label", x1=120, y1=50, x2=180, y2=120, text="Condensateur C1", stroke_width=4),
        ],
        loupes=[LoupeSpec(
            id=1,
            enabled=True,
            center_x=150,
            center_y=100,
            radius=40,
            zoom=2.0,
            arrow_end_x=50,
            arrow_end_y=50,
            stroke_width=4,
        )],
        layer_order=["annotation:1", "loupe:1", "annotation:0"],
    )

    # 4. Save JSON recipe
    recipe.save(json_path)
    assert json_path.exists()

    # 5. Load JSON recipe back and verify integrity
    loaded_recipe = ProcessingRecipe.load(json_path)
    assert loaded_recipe.source_image == str(raw_image_path)
    assert loaded_recipe.angle == 90.0
    assert loaded_recipe.stroke_width == 4
    assert len(loaded_recipe.annotations) == 2
    assert loaded_recipe.annotations[0].stroke_width == 4
    assert loaded_recipe.loupe.enabled is True
    assert loaded_recipe.layer_order == ["annotation:1", "loupe:1", "annotation:0"]

    # 6. Process and export image using the recipe
    output_file = process_image_with_recipe(loaded_recipe, export_path)
    assert output_file.exists()
    assert output_file == export_path

    exported_img = Image.open(output_file)
    # Original (300, 200) rotated 90 degrees becomes (200, 300)
    assert exported_img.size == (200, 300)
