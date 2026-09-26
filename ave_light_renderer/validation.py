from pathlib import Path
from typing import Any

from .canonical import load_json
from .errors import RecipeValidationError
from .paths import RECIPE_SCHEMA_PATH


REGION_NAMES = ("top_left", "top_right", "bottom_left", "bottom_right")
SUPPORTED_REFRESH_RATES = (60, 120)


def _jsonschema_validate(
    instance: Any,
    schema: dict,
    schema_path: Path,
    ref_store: dict[str, dict] | None = None,
) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from referencing import Registry, Resource
    except ImportError as exc:
        raise RuntimeError(
            "jsonschema is required; install project dependencies with "
            "python -m pip install -r requirements.txt"
        ) from exc

    registry = Registry()
    for uri, resource_schema in (ref_store or {}).items():
        registry = registry.with_resource(uri, Resource.from_contents(resource_schema))
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        details = []
        for error in errors[:12]:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            leaf_messages = [child.message for child in error.context if not child.context]
            message = "; ".join(leaf_messages) if leaf_messages else error.message
            details.append(f"{location}: {message}")
        raise RecipeValidationError("schema validation failed: " + "; ".join(details))


def validate_recipe(recipe: dict) -> dict:
    schema = load_json(RECIPE_SCHEMA_PATH)
    _jsonschema_validate(recipe, schema, RECIPE_SCHEMA_PATH)

    duration_us = recipe["duration_us"]
    color_mode = recipe["output"]["color_mode"]
    regions = recipe["regions"]
    names = [region["name"] for region in regions]
    if sorted(names) != sorted(REGION_NAMES):
        raise RecipeValidationError(
            f"regions must contain each canonical name exactly once: {REGION_NAMES}"
        )

    all_interval_ids: set[str] = set()
    for region in regions:
        expected_start = 0
        intervals = region["intervals"]
        for interval in intervals:
            interval_id = interval["interval_id"]
            if interval_id in all_interval_ids:
                raise RecipeValidationError(f"duplicate interval_id: {interval_id}")
            all_interval_ids.add(interval_id)
            if interval["start_us"] != expected_start:
                raise RecipeValidationError(
                    f"{region['name']} has a gap, overlap, or non-monotonic interval before "
                    f"{interval_id}: expected start_us={expected_start}, got {interval['start_us']}"
                )
            if interval["end_us"] <= interval["start_us"]:
                raise RecipeValidationError(f"{interval_id} must have end_us > start_us")
            if interval["kind"] == "pulse" and interval["color"]["mode"] != color_mode:
                raise RecipeValidationError(
                    f"{interval_id} color mode {interval['color']['mode']} does not match "
                    f"recipe output mode {color_mode}"
                )
            expected_start = interval["end_us"]
        if expected_start != duration_us:
            raise RecipeValidationError(
                f"{region['name']} timeline ends at {expected_start}, expected {duration_us}"
            )
    return recipe


def validate_refresh_rate(refresh_hz: int) -> None:
    if refresh_hz not in SUPPORTED_REFRESH_RATES:
        raise RecipeValidationError(
            f"refresh rate must be one of {SUPPORTED_REFRESH_RATES}; got {refresh_hz}"
        )
