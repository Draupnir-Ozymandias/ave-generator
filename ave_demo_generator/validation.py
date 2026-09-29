import json
from copy import deepcopy
from pathlib import Path

from ave_light_renderer.canonical import file_sha256, load_json
from ave_light_renderer.validation import _jsonschema_validate

from .errors import DemoRecipeValidationError
from .paths import DEMO_SCHEMA_PATH, PROJECT_ROOT


STABLE_DEMO_IDS = {
    "ave-demo-001-binaural-construction",
    "ave-demo-002-smooth-am-ramp",
    "ave-demo-003-gated-pulse-contrast",
    "ave-demo-004-four-region-light",
    "ave-demo-005-staged-av-comparison",
}


def validate_demo_recipe(recipe: dict) -> dict:
    schema = load_json(DEMO_SCHEMA_PATH)
    try:
        _jsonschema_validate(recipe, schema, DEMO_SCHEMA_PATH)
    except Exception as exc:
        raise DemoRecipeValidationError(str(exc)) from exc

    if recipe["demo_id"] not in STABLE_DEMO_IDS:
        raise DemoRecipeValidationError(f"unregistered stable demo_id: {recipe['demo_id']}")

    sample_count = recipe["duration_seconds"] * recipe["sample_rate_hz"]
    if abs(sample_count - round(sample_count)) > 1e-9:
        raise DemoRecipeValidationError("duration_seconds must resolve to an integer sample count")
    frame_count = recipe["duration_seconds"] * recipe["fps"]
    if abs(frame_count - round(frame_count)) > 1e-9:
        raise DemoRecipeValidationError("duration_seconds must resolve to an integer frame count")

    expected_start = 0.0
    stage_ids: set[str] = set()
    shortest_stage = recipe["duration_seconds"]
    for stage in recipe["audio"]["stages"]:
        if stage["stage_id"] in stage_ids:
            raise DemoRecipeValidationError(f"duplicate stage_id: {stage['stage_id']}")
        stage_ids.add(stage["stage_id"])
        if abs(stage["start_seconds"] - expected_start) > 1e-9:
            raise DemoRecipeValidationError(
                f"audio stages must be contiguous: expected {expected_start}, got {stage['start_seconds']}"
            )
        if stage["end_seconds"] <= stage["start_seconds"]:
            raise DemoRecipeValidationError(f"{stage['stage_id']} must have positive duration")
        duration = stage["end_seconds"] - stage["start_seconds"]
        shortest_stage = min(shortest_stage, duration)
        expected_start = stage["end_seconds"]
        if stage["kind"] == "binaural" and stage["left_hz"] == stage["right_hz"]:
            raise DemoRecipeValidationError("binaural stage carriers must differ")
        carrier = stage.get("carrier_hz", max(stage.get("left_hz", 0), stage.get("right_hz", 0)))
        if carrier >= recipe["sample_rate_hz"] / 2:
            raise DemoRecipeValidationError(f"{stage['stage_id']} carrier must remain below Nyquist")
    if abs(expected_start - recipe["duration_seconds"]) > 1e-9:
        raise DemoRecipeValidationError("audio stages must cover the full demo duration")
    if recipe["audio"]["stage_fade_seconds"] * 2 > shortest_stage:
        raise DemoRecipeValidationError("stage fade exceeds the shortest stage")
    if recipe["audio"]["master_fade_seconds"] * 2 > recipe["duration_seconds"]:
        raise DemoRecipeValidationError("master fade exceeds the demo duration")

    if recipe["visual"]["kind"] == "four_region":
        light_path = (PROJECT_ROOT / recipe["visual"]["light_recipe_path"]).resolve()
        try:
            light_path.relative_to(PROJECT_ROOT)
        except ValueError as exc:
            raise DemoRecipeValidationError("light_recipe_path must stay inside the Generator repository") from exc
        if not light_path.is_file():
            raise DemoRecipeValidationError(f"missing light recipe: {light_path}")
        if file_sha256(light_path) != recipe["visual"]["light_recipe_sha256"]:
            raise DemoRecipeValidationError("light recipe SHA-256 mismatch")
        light_recipe = load_json(light_path)
        if light_recipe["duration_us"] != round(recipe["duration_seconds"] * 1_000_000):
            raise DemoRecipeValidationError("light recipe duration does not match demo duration")

    serialized = json.dumps(recipe).lower()
    if '"kind": "smooth_am"' in serialized and "isochronic" in recipe["title"].lower():
        raise DemoRecipeValidationError("smooth AM must not be titled as isochronic")
    return deepcopy(recipe)


def load_and_validate(path: str | Path) -> dict:
    return validate_demo_recipe(load_json(path))
