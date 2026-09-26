from pathlib import Path

from ave_light_renderer.canonical import file_sha256
from ave_light_renderer.compiler import compile_recipe
from ave_light_renderer.manifest import (
    write_final_manifest,
    write_pre_render_manifest,
)
from ave_light_renderer.paths import PROJECT_ROOT
from ave_light_renderer.renderer import frame_image


def test_frame_pixels_are_deterministic_and_regions_are_separate(synthetic_recipe):
    plan = compile_recipe(synthetic_recipe, 60)
    frame = plan["frames"][30]
    first = frame_image(frame, size=64, gutter=2).tobytes()
    second = frame_image(frame, size=64, gutter=2).tobytes()
    assert first == second
    image = frame_image(frame, size=64, gutter=2)
    assert image.getpixel((8, 8)) != image.getpixel((56, 56))
    assert image.getpixel((31, 31)) == (0, 0, 0)


def test_manifest_exists_before_render_and_final_has_hashes(tmp_path, synthetic_recipe):
    plan = compile_recipe(synthetic_recipe, 60)
    pre_path = tmp_path / "render-manifest.pre.json"
    pre = write_pre_render_manifest(pre_path, plan, PROJECT_ROOT)
    assert pre_path.exists()
    assert pre["status"] == "pre_render"
    assert pre["outputs"] == []
    assert pre["resolved_plan"]["sha256"] == plan["resolved_plan_sha256"]

    output = tmp_path / "frame.png"
    frame_image(plan["frames"][30], size=64, gutter=2).save(output)
    manifest_path = tmp_path / "render-manifest.json"
    final = write_final_manifest(manifest_path, pre, pre_path, [output])
    assert final["status"] == "complete"
    assert final["outputs"][0]["sha256"] == file_sha256(output)
    assert final["pre_render_manifest"]["sha256"] == file_sha256(pre_path)
    assert manifest_path.exists()

