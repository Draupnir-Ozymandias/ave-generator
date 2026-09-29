"""Build self-contained, provenance-rich AVE engineering demo packages."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from scipy.io import wavfile

from ave_audio_generator.synthesis import float_to_pcm16
from ave_audio_generator.video import mux_av
from ave_light_renderer.canonical import canonical_sha256, file_sha256, load_json, write_json
from ave_light_renderer.compiler import compile_recipe
from ave_light_renderer.manifest import git_state
from ave_light_renderer.renderer import render_mp4
from ave_light_renderer.validation import validate_recipe as validate_light_recipe

from . import __version__
from .compiler import resolve_demo
from .declaration import compile_declaration, declaration_mapping_report
from .errors import DemoRecipeValidationError
from .paths import PROJECT_ROOT
from .presentation import render_presentation_video
from .synthesis import synthesize_demo
from .validation import load_and_validate
from .verification import verify_demo_audio


def _relative_output(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def _package_readme(recipe: dict, resolved: dict) -> str:
    return f"""# {recipe['title']}

Evidence maturity: **{recipe['verification']['evidence_maturity']}**

## Purpose

{recipe['purpose']}

## Reproduce

From the AVE Generator repository root:

```sh
ave-demo-generator build contracts/examples/demos/{recipe['demo_id']}.json --output-dir output/demos/{recipe['demo_id']}
```

`{recipe['demo_id']}-declaration.json` is the normalized Generator declaration.
`generator-validation.json` contains same-repository build checks, not independent observations.
Submit `verification-request.json` and the named artifact to AVE Forensics. Detector execution must
persist observations before it loads declaration targets or tolerances.

## Safety and limitations

{recipe['safety']['warning']}

{recipe['safety']['headphones_assumption']}

{chr(10).join(f'- {item}' for item in recipe['limitations'])}

Digital amplitude is not calibrated SPL. Visual RGB values are not calibrated luminance. This
package makes no claim of neurological entrainment, mental-state change, therapy, efficacy, or
human-exposure safety.

## Provenance

- Recipe canonical SHA-256: `{resolved['recipe_canonical_sha256']}`
- Resolved plan SHA-256: `{resolved['resolved_plan_sha256']}`
- Media origin: `{recipe['distribution']['media_origin']}`
- Redistributable: `{str(recipe['distribution']['redistributable']).lower()}`
"""


def build_demo_package(recipe_path: Path, output_dir: Path) -> dict[str, Any]:
    recipe_path = recipe_path.resolve()
    recipe = load_and_validate(recipe_path)
    resolved = resolve_demo(recipe, str(recipe_path))
    declaration = compile_declaration(recipe, resolved)
    mapping_report = declaration_mapping_report(recipe, declaration)
    if output_dir.name != recipe["demo_id"]:
        raise DemoRecipeValidationError(
            f"canonical output directory must end with stable demo ID {recipe['demo_id']}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    stems_dir = audio_dir / "stems"
    audio_dir.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)

    source_state = git_state(PROJECT_ROOT)
    git_version = source_state["commit"] + ("+dirty" if source_state["dirty"] else "")
    recipe_copy = output_dir / f"{recipe['demo_id']}-recipe.json"
    resolved_path = output_dir / f"{recipe['demo_id']}-resolved-protocol.json"
    declaration_path = output_dir / f"{recipe['demo_id']}-declaration.json"
    mapping_path = output_dir / f"{recipe['demo_id']}-declaration-mapping.json"
    pre_path = output_dir / "render-manifest.pre.json"
    shutil.copyfile(recipe_path, recipe_copy)
    write_json(resolved_path, resolved)
    write_json(declaration_path, declaration)
    write_json(mapping_path, mapping_report)
    pre_manifest = {
        "manifest_version": "1.1.0",
        "status": "pre_render",
        "demo_id": recipe["demo_id"],
        "demo_version": recipe["demo_version"],
        "declaration_id": declaration["declaration_id"],
        "evidence_maturity": recipe["verification"]["evidence_maturity"],
        "recipe": {
            "canonical_sha256": resolved["recipe_canonical_sha256"],
            "file_sha256": resolved["recipe_file_sha256"],
        },
        "resolved_plan": {
            "sha256": resolved["resolved_plan_sha256"],
            "sample_count": resolved["sample_count"],
            "frame_count": resolved["frame_count"],
        },
        "declaration": {
            "schema_version": declaration["schema_version"],
            "path": declaration_path.name,
            "sha256": file_sha256(declaration_path),
        },
        "generator": {
            "name": "ave-demo-generator",
            "version": __version__,
            "git_commit": source_state["commit"],
            "git_dirty": source_state["dirty"],
        },
        "record_boundaries": {
            "generator_declaration": declaration_path.name,
            "resolved_protocol": resolved_path.name,
            "generator_validation": "generator-validation.json (written after render)",
            "forensics_observation": None,
            "field_level_agreement": None,
        },
        "safety": recipe["safety"],
        "limitations": recipe["limitations"],
        "outputs": [],
    }
    write_json(pre_path, pre_manifest)

    audio, stems, synthesis_stats = synthesize_demo(resolved)
    stereo_path = audio_dir / "stereo.wav"
    left_path = audio_dir / "left.wav"
    right_path = audio_dir / "right.wav"
    wavfile.write(stereo_path, recipe["sample_rate_hz"], float_to_pcm16(audio))
    wavfile.write(left_path, recipe["sample_rate_hz"], float_to_pcm16(audio[:, 0]))
    wavfile.write(right_path, recipe["sample_rate_hz"], float_to_pcm16(audio[:, 1]))
    stem_paths: list[Path] = []
    for stage_id, stem in stems.items():
        stem_path = stems_dir / f"{stage_id}.wav"
        wavfile.write(stem_path, recipe["sample_rate_hz"], float_to_pcm16(stem))
        stem_paths.append(stem_path)

    silent_video = output_dir / "presentation-video.silent.mp4"
    render_presentation_video(
        silent_video,
        recipe,
        resolved,
        git_version,
        size=(recipe["visual"].get("width", 960), recipe["visual"].get("height", 540)),
    )
    presentation_path = mux_av(silent_video, stereo_path, output_dir / "presentation.mp4")

    light_outputs: list[Path] = []
    light_video_path: Path | None = None
    if recipe["visual"]["kind"] == "four_region":
        light_recipe_path = PROJECT_ROOT / recipe["visual"]["light_recipe_path"]
        light_recipe = validate_light_recipe(load_json(light_recipe_path))
        light_plan = compile_recipe(light_recipe, recipe["fps"])
        light_plan_path = output_dir / "four-region-resolved-plan.json"
        light_video_path = output_dir / "four-region-preview.mp4"
        write_json(light_plan_path, light_plan)
        render_mp4(light_plan, light_video_path, size=480)
        light_outputs.extend([light_plan_path, light_video_path])

    generator_validation = verify_demo_audio(stereo_path, resolved)
    validation_path = output_dir / "generator-validation.json"
    write_json(validation_path, generator_validation)
    if recipe["visual"]["kind"] == "four_region":
        if light_video_path is None:
            raise RuntimeError("four-region detector artifact was not rendered")
        detector_path = light_video_path
        detector_relative_path = detector_path.relative_to(output_dir).as_posix()
        detector_media_type = "video/mp4"
        request_type = "independent_blind_visual_analysis"
    else:
        detector_path = stereo_path
        detector_relative_path = detector_path.relative_to(output_dir).as_posix()
        detector_media_type = "audio/wav"
        request_type = "independent_blind_audio_analysis"

    verification_request = {
        "request_version": "1.1.0",
        "request_type": request_type,
        "demo_id": recipe["demo_id"],
        "demo_version": recipe["demo_version"],
        "declaration_id": declaration["declaration_id"],
        "detector_input": {
            "path": detector_relative_path,
            "media_type": detector_media_type,
            "sha256": file_sha256(detector_path),
            "expected_values_present": False,
            "expected_tolerances_present": False,
            "target_schedules_present": False,
        },
        "requested_observation_metrics": sorted({claim["metric"] for claim in declaration["claims"]}),
        "workflow": [
            "Record and verify the detector_input artifact SHA-256.",
            "Run detectors without loading the declaration's targets or tolerances.",
            "Persist independent observations and evidence IDs.",
            "Only then load comparison_after_observation and issue field-level results.",
        ],
        "comparison_after_observation": {
            "declaration_path": declaration_path.name,
            "declaration_sha256": file_sha256(declaration_path),
            "do_not_load_before_evidence_is_persisted": True,
        },
        "requested_result_values": ["agree", "disagree", "unsupported"],
        "generator_declared_values_in_detector_input": False,
        "notes": [
            "AVE Forensics owns observations and field-level agreement results.",
            "Unsupported fields must remain unsupported; do not infer absent values.",
        ],
    }
    request_path = output_dir / "verification-request.json"
    write_json(request_path, verification_request)
    readme_path = output_dir / "PACKAGE_README.md"
    readme_path.write_text(_package_readme(recipe, resolved), encoding="utf-8")

    material_outputs = [
        recipe_copy, resolved_path, declaration_path, mapping_path, stereo_path, left_path, right_path,
        *stem_paths, silent_video, presentation_path, *light_outputs,
        validation_path, request_path, readme_path,
    ]
    output_records = [_relative_output(path, output_dir) for path in material_outputs]
    final_manifest = {
        **pre_manifest,
        "status": "complete" if generator_validation["passed"] else "generator_validation_failed",
        "pre_render_manifest": {"path": pre_path.name, "sha256": file_sha256(pre_path)},
        "generator_declaration": {
            "path": declaration_path.name,
            "sha256": file_sha256(declaration_path),
            "record_sha256": canonical_sha256(declaration),
            "schema_version": declaration["schema_version"],
            "declaration_id": declaration["declaration_id"],
        },
        "resolved_protocol": {
            "path": resolved_path.name,
            "sha256": file_sha256(resolved_path),
            "resolved_plan_sha256": resolved["resolved_plan_sha256"],
        },
        "declaration_mapping": {
            "path": mapping_path.name,
            "sha256": file_sha256(mapping_path),
            "unmapped_field_count": len(mapping_report["unmapped_generator_fields"]),
            "interpretation_invented": False,
        },
        "generator_validation": {
            "path": validation_path.name,
            "sha256": file_sha256(validation_path),
            "passed": generator_validation["passed"],
        },
        "forensics_observation": None,
        "field_level_agreement": None,
        "synthesis_measurements": synthesis_stats,
        "outputs": output_records,
    }
    unsigned = dict(final_manifest)
    final_manifest["manifest_content_sha256"] = canonical_sha256(unsigned)
    manifest_path = output_dir / "render-manifest.json"
    write_json(manifest_path, final_manifest)

    return {
        "demo_id": recipe["demo_id"],
        "demo_version": recipe["demo_version"],
        "declaration_id": declaration["declaration_id"],
        "declaration": str(declaration_path),
        "evidence_maturity": recipe["verification"]["evidence_maturity"],
        "output_dir": str(output_dir),
        "presentation": str(presentation_path),
        "manifest": str(manifest_path),
        "generator_validation_passed": generator_validation["passed"],
        "resolved_plan_sha256": resolved["resolved_plan_sha256"],
        "forensics_observation": None,
        "field_level_agreement": None,
    }
