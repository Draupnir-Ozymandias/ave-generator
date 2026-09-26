from copy import deepcopy

import pytest

from ave_light_renderer.errors import RecipeValidationError
from ave_light_renderer.validation import validate_recipe, validate_refresh_rate


def test_synthetic_recipe_is_valid(synthetic_recipe):
    assert validate_recipe(synthetic_recipe)["recipe_id"] == "synthetic-four-region-demo"


def test_requires_exactly_four_canonical_regions(synthetic_recipe):
    invalid = deepcopy(synthetic_recipe)
    invalid["regions"][3]["name"] = "top_left"
    with pytest.raises(RecipeValidationError, match="canonical name"):
        validate_recipe(invalid)


def test_rejects_timeline_gap(synthetic_recipe):
    invalid = deepcopy(synthetic_recipe)
    invalid["regions"][0]["intervals"][1]["start_us"] += 1
    with pytest.raises(RecipeValidationError, match="gap, overlap, or non-monotonic"):
        validate_recipe(invalid)


def test_rejects_incomplete_pulse_parameters(synthetic_recipe):
    invalid = deepcopy(synthetic_recipe)
    del invalid["regions"][0]["intervals"][1]["phase_policy"]
    with pytest.raises(RecipeValidationError, match="phase_policy"):
        validate_recipe(invalid)


def test_rejects_color_mode_mismatch(synthetic_recipe):
    invalid = deepcopy(synthetic_recipe)
    invalid["regions"][0]["intervals"][1]["color"] = {
        "mode": "grayscale",
        "value": 200,
    }
    with pytest.raises(RecipeValidationError, match="does not match"):
        validate_recipe(invalid)


def test_accepts_grayscale_recipe(synthetic_recipe):
    recipe = deepcopy(synthetic_recipe)
    recipe["output"]["color_mode"] = "grayscale"
    for region in recipe["regions"]:
        for interval in region["intervals"]:
            if interval["kind"] == "pulse":
                interval["color"] = {"mode": "grayscale", "value": 180}
    assert validate_recipe(recipe)["output"]["color_mode"] == "grayscale"


@pytest.mark.parametrize("refresh", [59, 61, 90, 144])
def test_rejects_unsupported_refresh_rates(refresh):
    with pytest.raises(RecipeValidationError, match="60, 120"):
        validate_refresh_rate(refresh)

