from copy import deepcopy

import pytest

from ave_light_renderer.compiler import compile_recipe


def _frame(plan, seconds: float):
    return plan["frames"][round(seconds * plan["refresh_hz"])]


@pytest.mark.parametrize("refresh", [60, 120])
def test_compilation_is_deterministic(synthetic_recipe, refresh):
    first = compile_recipe(deepcopy(synthetic_recipe), refresh)
    second = compile_recipe(deepcopy(synthetic_recipe), refresh)
    assert first == second
    assert first["resolved_plan_sha256"] == second["resolved_plan_sha256"]
    assert first["frame_count"] == 4 * refresh


@pytest.mark.parametrize("refresh", [60, 120])
def test_off_and_boundary_behavior(synthetic_recipe, refresh):
    plan = compile_recipe(synthetic_recipe, refresh)
    for state in plan["frames"][0]["regions"].values():
        assert state["kind"] == "off"
        assert state["effective_rgb"] == [0, 0, 0]
    for state in _frame(plan, 0.5)["regions"].values():
        assert state["kind"] == "pulse"
    for state in _frame(plan, 3.5)["regions"].values():
        assert state["kind"] == "off"
        assert state["gate_on"] is False


def test_linear_frequency_uses_accumulated_phase(synthetic_recipe):
    plan = compile_recipe(synthetic_recipe, 60)
    # TL carries 9 complete cycles from 0.5s to 2.0s. From 2.0s to 2.5s,
    # the 6->12 Hz linear ramp accumulates exactly 3.5 cycles, so phase=.5.
    state = _frame(plan, 2.5)["regions"]["top_left"]
    assert state["frequency_hz"] == pytest.approx(8.0)
    assert state["phase_cycles"] == pytest.approx(0.5, abs=1e-10)


def test_region_tracks_are_independent(synthetic_recipe):
    plan = compile_recipe(synthetic_recipe, 120)
    frame = _frame(plan, 0.5)
    assert frame["regions"]["top_left"]["frequency_hz"] == 6.0
    assert frame["regions"]["bottom_right"]["frequency_hz"] == 9.0
    assert frame["regions"]["top_left"]["duty_cycle"] == 0.5
    assert frame["regions"]["bottom_right"]["duty_cycle"] == 0.25


def test_duty_gate_uses_integrated_phase(synthetic_recipe):
    recipe = deepcopy(synthetic_recipe)
    for region in recipe["regions"]:
        pulse = region["intervals"][1]
        pulse["frequency_hz"] = {"kind": "constant", "value": 2.0}
        pulse["duty_cycle"] = {"kind": "constant", "value": 0.25}
        pulse["phase_origin_cycles"] = 0.0
    plan = compile_recipe(recipe, 120)
    assert _frame(plan, 0.5)["regions"]["top_left"]["gate_on"] is True
    assert _frame(plan, 0.625)["regions"]["top_left"]["phase_cycles"] == pytest.approx(0.25)
    assert _frame(plan, 0.625)["regions"]["top_left"]["gate_on"] is False


def test_reset_and_continuous_phase_policies_diverge(synthetic_recipe):
    continuous = compile_recipe(deepcopy(synthetic_recipe), 60)
    reset_recipe = deepcopy(synthetic_recipe)
    reset_recipe["regions"][0]["intervals"][2]["phase_policy"] = "reset"
    reset_recipe["regions"][0]["intervals"][2]["phase_origin_cycles"] = 0.2
    reset = compile_recipe(reset_recipe, 60)
    assert _frame(continuous, 2.0)["regions"]["top_left"]["phase_cycles"] == pytest.approx(0.0)
    assert _frame(reset, 2.0)["regions"]["top_left"]["phase_cycles"] == pytest.approx(0.2)


def test_sixty_and_one_twenty_hz_quantization_is_reported(synthetic_recipe):
    recipe = deepcopy(synthetic_recipe)
    for region in recipe["regions"]:
        intervals = region["intervals"]
        intervals[0]["end_us"] = 500001
        intervals[1]["start_us"] = 500001
    plan60 = compile_recipe(recipe, 60)
    plan120 = compile_recipe(recipe, 120)
    transition60 = next(item for item in plan60["transitions"] if item["requested_us"] == 500001)
    transition120 = next(item for item in plan120["transitions"] if item["requested_us"] == 500001)
    assert transition60["quantized_frame_index"] == 31
    assert transition120["quantized_frame_index"] == 61
    assert transition60["error_us"] > transition120["error_us"] > 0
    assert plan60["timing_error_summary_us"]["max_abs_us"] > 0

