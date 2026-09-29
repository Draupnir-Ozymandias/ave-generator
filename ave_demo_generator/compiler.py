from copy import deepcopy

from ave_light_renderer.canonical import canonical_sha256, file_sha256

from . import __version__
from .paths import PROJECT_ROOT
from .validation import validate_demo_recipe


def stage_declaration(stage: dict) -> dict:
    declaration = {
        "stage_id": stage["stage_id"],
        "kind": stage["kind"],
        "start_seconds": stage["start_seconds"],
        "end_seconds": stage["end_seconds"],
    }
    for key in (
        "left_hz", "right_hz", "carrier_hz", "rate", "depth", "duty_cycle",
        "envelope_shape", "edge_shape", "amplitude", "phase_origin_cycles",
    ):
        if key in stage:
            declaration[key] = deepcopy(stage[key])
    if stage["kind"] == "binaural":
        declaration["difference_hz"] = abs(stage["right_hz"] - stage["left_hz"])
        declaration["channel_routing"] = "left_hz->left; right_hz->right"
    elif stage["kind"] in {"smooth_am", "gated_pulse"}:
        declaration["channel_routing"] = "identical_stereo"
    return declaration


def resolve_demo(recipe: dict, recipe_file: str | None = None) -> dict:
    recipe = validate_demo_recipe(recipe)
    resolved = {
        "resolved_demo_version": "1.0.0",
        "generator_version": __version__,
        "demo_id": recipe["demo_id"],
        "recipe_canonical_sha256": canonical_sha256(recipe),
        "recipe_file_sha256": file_sha256(recipe_file) if recipe_file else None,
        "duration_seconds": recipe["duration_seconds"],
        "sample_rate_hz": recipe["sample_rate_hz"],
        "sample_count": round(recipe["duration_seconds"] * recipe["sample_rate_hz"]),
        "fps": recipe["fps"],
        "frame_count": round(recipe["duration_seconds"] * recipe["fps"]),
        "declarations": {
            "record_type": "generator_declaration",
            "record_version": "1.0.0",
            "audio_stages": [stage_declaration(stage) for stage in recipe["audio"]["stages"]],
        },
        "visual": deepcopy(recipe["visual"]),
        "verification": deepcopy(recipe["verification"]),
        "safety": deepcopy(recipe["safety"]),
        "distribution": deepcopy(recipe["distribution"]),
        "limitations": list(recipe["limitations"]),
        "recipe": recipe,
        "warnings": [
            "Generator declarations and checks are not independent Forensics observations.",
            "Evidence maturity describes engineering verification only, not efficacy or exposure safety.",
        ],
    }
    if recipe["visual"]["kind"] == "four_region":
        light_path = PROJECT_ROOT / recipe["visual"]["light_recipe_path"]
        resolved["visual"]["verified_file_sha256"] = file_sha256(light_path)
    resolved["resolved_plan_sha256"] = canonical_sha256(resolved)
    return resolved
