from copy import deepcopy

import pytest

from ave_demo_generator.errors import DemoRecipeValidationError
from ave_demo_generator.paths import DEMO_RECIPE_DIR
from ave_demo_generator.validation import validate_demo_recipe
from ave_light_renderer.canonical import load_json


def _recipes():
    return [load_json(path) for path in sorted(DEMO_RECIPE_DIR.glob("*.json"))]


def test_portfolio_defines_exactly_five_valid_recipes():
    recipes = [validate_demo_recipe(recipe) for recipe in _recipes()]
    assert len(recipes) == 5
    assert len({recipe["demo_id"] for recipe in recipes}) == 5
    assert {recipe["verification"]["evidence_maturity"] for recipe in recipes} == {"exploratory"}
    assert {recipe["demo_version"] for recipe in recipes} == {"1.0.0"}
    assert {recipe["demo_id"] for recipe in recipes} == {
        "ave-demo-001-binaural-construction",
        "ave-demo-002-smooth-am-ramp",
        "ave-demo-003-gated-pulse-contrast",
        "ave-demo-004-four-region-light",
        "ave-demo-005-staged-av-comparison",
    }


def test_smooth_am_and_gated_pulse_are_structurally_distinct():
    stages = [stage for recipe in _recipes() for stage in recipe["audio"]["stages"]]
    smooth = [stage for stage in stages if stage["kind"] == "smooth_am"]
    gated = [stage for stage in stages if stage["kind"] == "gated_pulse"]
    assert smooth and gated
    assert all(stage["envelope_shape"] == "sine" and "duty_cycle" not in stage for stage in smooth)
    assert all(stage["edge_shape"] == "hard" and 0 < stage["duty_cycle"] < 1 for stage in gated)


def test_incomplete_or_semantically_unsafe_recipe_is_rejected():
    recipe = deepcopy(_recipes()[0])
    del recipe["verification"]
    with pytest.raises(DemoRecipeValidationError):
        validate_demo_recipe(recipe)

    smooth = next(recipe for recipe in _recipes() if recipe["demo_id"] == "ave-demo-002-smooth-am-ramp")
    smooth["title"] = "Isochronic ramp"
    with pytest.raises(DemoRecipeValidationError, match="must not be titled"):
        validate_demo_recipe(smooth)


def test_audio_stages_must_be_contiguous():
    staged = next(recipe for recipe in _recipes() if recipe["demo_id"] == "ave-demo-005-staged-av-comparison")
    staged["audio"]["stages"][1]["start_seconds"] += 0.1
    with pytest.raises(DemoRecipeValidationError, match="contiguous"):
        validate_demo_recipe(staged)


def test_four_region_reference_hash_is_enforced():
    light = next(recipe for recipe in _recipes() if recipe["visual"]["kind"] == "four_region")
    light["visual"]["light_recipe_sha256"] = "0" * 64
    with pytest.raises(DemoRecipeValidationError, match="SHA-256 mismatch"):
        validate_demo_recipe(light)
