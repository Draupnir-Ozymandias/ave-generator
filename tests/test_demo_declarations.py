from copy import deepcopy
from pathlib import Path

import pytest

from ave_demo_generator.compiler import resolve_demo
from ave_demo_generator.declaration import (
    PLATFORM_SCHEMA_SHA256,
    compile_declaration,
    declaration_mapping_report,
    validate_declaration,
)
from ave_demo_generator.errors import DemoRecipeValidationError
from ave_demo_generator.paths import DEMO_RECIPE_DIR, PLATFORM_DECLARATION_SCHEMA_PATH
from ave_demo_generator.validation import validate_demo_recipe
from ave_light_renderer.canonical import file_sha256, load_json


PLATFORM_SOURCE_SCHEMA = Path(
    "/Users/eric/Projects/media/ave_platform/contracts/ave-demo-declaration-0.1.0.schema.json"
)


def _compiled():
    for path in sorted(DEMO_RECIPE_DIR.glob("*.json")):
        recipe = validate_demo_recipe(load_json(path))
        resolved = resolve_demo(recipe, str(path))
        yield recipe, resolved, compile_declaration(recipe, resolved)


def test_vendored_platform_schema_is_exactly_pinned():
    assert file_sha256(PLATFORM_DECLARATION_SCHEMA_PATH) == PLATFORM_SCHEMA_SHA256
    if PLATFORM_SOURCE_SCHEMA.is_file():
        assert file_sha256(PLATFORM_SOURCE_SCHEMA) == PLATFORM_SCHEMA_SHA256


def test_all_five_declarations_validate_and_use_stable_identity():
    declarations = []
    for recipe, resolved, declaration in _compiled():
        declarations.append(declaration)
        assert declaration["demo_id"] == recipe["demo_id"]
        assert declaration["demo_version"] == recipe["demo_version"]
        assert declaration["declaration_id"] == f"{recipe['demo_id']}@{recipe['demo_version']}"
        assert declaration["source_protocol"]["sha256"] == resolved["recipe_canonical_sha256"]
        assert len({claim["claim_id"] for claim in declaration["claims"]}) == len(declaration["claims"])
        assert validate_declaration(declaration, recipe["duration_seconds"]) == declaration
    assert len(declarations) == 5


def test_smooth_am_uses_canonical_term_and_never_isochronic():
    recipe, _, declaration = next(
        item for item in _compiled() if item[0]["demo_id"] == "ave-demo-002-smooth-am-ramp"
    )
    shape = next(claim for claim in declaration["claims"] if claim["claim_id"] == "audio.modulation.shape")
    assert shape["target"]["value"] == "smooth_amplitude_modulation"
    assert "isochronic" not in str(recipe).lower()


def test_incompatible_target_and_comparison_are_rejected():
    _, _, declaration = next(iter(_compiled()))
    invalid = deepcopy(declaration)
    invalid["claims"][0]["tolerance"] = {"comparison": "exact"}
    with pytest.raises(DemoRecipeValidationError, match="incompatible"):
        validate_declaration(invalid)


def test_mapping_report_exposes_unrepresentable_light_fields_without_inference():
    recipe, _, declaration = next(
        item for item in _compiled() if item[0]["demo_id"] == "ave-demo-004-four-region-light"
    )
    report = declaration_mapping_report(recipe, declaration)
    fields = {item["field"] for item in report["unmapped_generator_fields"]}
    assert "visual.light_recipe.regions.*.intervals.*.color" in fields
    assert "visual.light_recipe.regions.*.intervals" in fields
    assert report["interpretation_invented"] is False
