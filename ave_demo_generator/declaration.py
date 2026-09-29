"""Compile and validate the AVE Platform demo declaration boundary."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ave_light_renderer.canonical import canonical_sha256, file_sha256, load_json
from ave_light_renderer.validation import _jsonschema_validate

from .errors import DemoRecipeValidationError
from .paths import PLATFORM_DECLARATION_SCHEMA_PATH, PLATFORM_DECLARATION_SOURCE_MANIFEST_PATH


PLATFORM_SCHEMA_SHA256 = "aca39c90191762cde5048dfefc6f732d9e0c43e2da668194f2cc6cb04175ab45"


def _scope(
    modality: str,
    channels: list[str] | None = None,
    regions: list[str] | None = None,
    start: float | None = None,
    end: float | None = None,
) -> dict[str, Any]:
    return {
        "modality": modality,
        "channels": channels or [],
        "regions": regions or [],
        "time_range_seconds": None if start is None else {"start": start, "end": end},
    }


def _absolute_claim(
    claim_id: str,
    evidence_type: str,
    metric: str,
    unit: str,
    scope: dict[str, Any],
    value: float,
    error: float,
    *,
    required: bool = True,
    coverage: float | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    tolerance: dict[str, Any] = {"comparison": "absolute", "max_absolute_error": error}
    if coverage is not None:
        tolerance["minimum_coverage_fraction"] = coverage
    if confidence is not None:
        tolerance["minimum_confidence"] = confidence
    return {
        "claim_id": claim_id,
        "required": required,
        "evidence_type": evidence_type,
        "metric": metric,
        "unit": unit,
        "scope": scope,
        "target": {"kind": "scalar", "value": value},
        "tolerance": tolerance,
    }


def _exact_claim(
    claim_id: str,
    evidence_type: str,
    metric: str,
    unit: str,
    scope: dict[str, Any],
    value: str | bool,
    *,
    required: bool = True,
    coverage: float | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    tolerance: dict[str, Any] = {"comparison": "exact"}
    if coverage is not None:
        tolerance["minimum_coverage_fraction"] = coverage
    if confidence is not None:
        tolerance["minimum_confidence"] = confidence
    return {
        "claim_id": claim_id,
        "required": required,
        "evidence_type": evidence_type,
        "metric": metric,
        "unit": unit,
        "scope": scope,
        "target": {"kind": "boolean" if isinstance(value, bool) else "category", "value": value},
        "tolerance": tolerance,
    }


def _common_audio_claims(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _absolute_claim(
            "audio.duration",
            "media_identity",
            "duration_seconds",
            "s",
            _scope("audio", ["left", "right"]),
            recipe["duration_seconds"],
            0.001,
        ),
        _absolute_claim(
            "audio.sample_peak",
            "media_identity",
            "sample_peak_linear",
            "linear",
            _scope("audio", ["left", "right"]),
            recipe["audio"]["peak_linear"],
            0.0001,
        ),
    ]


def _claims_001(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    stage = recipe["audio"]["stages"][0]
    full = _scope("audio", ["left", "right"], start=0.0, end=recipe["duration_seconds"])
    return _common_audio_claims(recipe) + [
        _absolute_claim("audio.left_carrier.frequency", "persistent_carrier", "carrier_frequency_hz", "Hz", _scope("audio", ["left"], start=0.0, end=recipe["duration_seconds"]), stage["left_hz"], 0.5, coverage=0.8, confidence=0.75),
        _absolute_claim("audio.right_carrier.frequency", "persistent_carrier", "carrier_frequency_hz", "Hz", _scope("audio", ["right"], start=0.0, end=recipe["duration_seconds"]), stage["right_hz"], 0.5, coverage=0.8, confidence=0.75),
        _absolute_claim("audio.interchannel_difference", "binaural_candidate", "interchannel_frequency_difference_hz", "Hz", full, abs(stage["right_hz"] - stage["left_hz"]), 0.25, coverage=0.8, confidence=0.75),
        _exact_claim("audio.channel_routing", "channel_routing", "channel_routing_class", "category", full, "separate_left_right_carriers", coverage=0.8, confidence=0.75),
    ]


def _claims_002(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    stage = recipe["audio"]["stages"][0]
    full = _scope("audio", ["left", "right"], start=0.0, end=recipe["duration_seconds"])
    return _common_audio_claims(recipe) + [
        _absolute_claim("audio.carrier.frequency", "persistent_carrier", "carrier_frequency_hz", "Hz", full, stage["carrier_hz"], 0.5, coverage=0.85, confidence=0.75),
        _exact_claim("audio.modulation.shape", "broadband_pulse_pattern", "amplitude_shape_class", "category", full, "smooth_amplitude_modulation", coverage=0.85, confidence=0.75),
        {
            "claim_id": "audio.modulation.rate_curve",
            "required": True,
            "evidence_type": "continuous_modulation_ramp",
            "metric": "modulation_rate_hz",
            "unit": "Hz",
            "scope": full,
            "target": {
                "kind": "linear_curve",
                "start": {"time_seconds": 0.0, "value": stage["rate"]["start_hz"]},
                "end": {"time_seconds": recipe["duration_seconds"], "value": stage["rate"]["end_hz"]},
            },
            "tolerance": {
                "comparison": "curve_fit",
                "max_point_error": 0.5,
                "max_rmse": 0.5,
                "max_time_error_seconds": 0.25,
                "minimum_coverage_fraction": 0.85,
                "minimum_confidence": 0.75,
            },
        },
        _absolute_claim("audio.modulation.depth", "carrier_envelope", "modulation_depth_fraction", "fraction", full, stage["depth"], 0.05, coverage=0.85, confidence=0.75),
        _exact_claim("audio.stereo_relationship", "channel_routing", "stereo_relationship", "category", full, "identical_stereo", coverage=0.85, confidence=0.75),
    ]


def _claims_003(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    stage = recipe["audio"]["stages"][0]
    full = _scope("audio", ["left", "right"], start=0.0, end=recipe["duration_seconds"])
    return _common_audio_claims(recipe) + [
        _absolute_claim("audio.carrier.frequency", "persistent_carrier", "carrier_frequency_hz", "Hz", full, stage["carrier_hz"], 0.5, coverage=0.85, confidence=0.75),
        _absolute_claim("audio.pulse.rate", "broadband_pulse_pattern", "pulse_rate_hz", "Hz", full, stage["rate"]["value_hz"], 0.25, coverage=0.85, confidence=0.75),
        _absolute_claim("audio.pulse.duty_cycle", "broadband_pulse_pattern", "duty_cycle_fraction", "fraction", full, stage["duty_cycle"], 0.02, coverage=0.85, confidence=0.75),
        _exact_claim("audio.pulse.shape", "broadband_pulse_pattern", "amplitude_shape_class", "category", full, "hard_gated_pulse", coverage=0.85, confidence=0.75),
        _exact_claim("audio.pulse.explicit_off_state", "broadband_pulse_pattern", "explicit_off_state", "boolean", full, True, coverage=0.85, confidence=0.75),
        _exact_claim("audio.stereo_relationship", "channel_routing", "stereo_relationship", "category", full, "identical_stereo", coverage=0.85, confidence=0.75),
    ]


def _claims_004(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    regions = ["top_left", "top_right", "bottom_left", "bottom_right"]
    full = _scope("light", regions=regions, start=0.0, end=recipe["duration_seconds"])
    return [
        _absolute_claim("light.duration", "resolved_light_plan", "duration_seconds", "s", full, recipe["duration_seconds"], 0.001),
        _absolute_claim("light.region_count", "resolved_light_plan", "region_count", "count", full, 4, 0),
        _exact_claim("light.region_independence", "resolved_light_plan", "independent_region_schedules", "boolean", full, True),
        _exact_claim("light.explicit_off_intervals", "resolved_light_plan", "explicit_off_intervals", "boolean", full, True),
        _absolute_claim("video.refresh_rate", "media_identity", "refresh_rate_hz", "Hz", _scope("video", regions=regions), recipe["fps"], 0),
        _absolute_claim("video.frame_count", "media_identity", "frame_count", "frames", _scope("video", regions=regions), recipe["duration_seconds"] * recipe["fps"], 0),
        _exact_claim("light.recipe.identity", "plan_identity", "source_recipe_sha256", "sha256", full, recipe["visual"]["light_recipe_sha256"]),
    ]


def _claims_005(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    stages = recipe["audio"]["stages"]
    binaural, smooth, gated = stages
    all_audio = _scope("audio", ["left", "right"], start=0.0, end=recipe["duration_seconds"])
    claims = _common_audio_claims(recipe) + [
        _absolute_claim("timeline.stage_count", "stage_timeline", "stage_count", "count", all_audio, 3, 0),
        _absolute_claim("timeline.transition.first", "stage_timeline", "transition_time_seconds", "s", all_audio, binaural["end_seconds"], 0.001),
        _absolute_claim("timeline.transition.second", "stage_timeline", "transition_time_seconds", "s", all_audio, smooth["end_seconds"], 0.001),
        _exact_claim("stage.binaural.construction", "stage_classification", "construction_class", "category", _scope("audio", ["left", "right"], start=binaural["start_seconds"], end=binaural["end_seconds"]), "binaural_construction", coverage=0.8, confidence=0.75),
        _absolute_claim("stage.binaural.difference", "binaural_candidate", "interchannel_frequency_difference_hz", "Hz", _scope("audio", ["left", "right"], start=binaural["start_seconds"], end=binaural["end_seconds"]), abs(binaural["right_hz"] - binaural["left_hz"]), 0.25, coverage=0.8, confidence=0.75),
        _exact_claim("stage.smooth_am.construction", "stage_classification", "construction_class", "category", _scope("audio", ["left", "right"], start=smooth["start_seconds"], end=smooth["end_seconds"]), "smooth_amplitude_modulation", coverage=0.8, confidence=0.75),
        _absolute_claim("stage.smooth_am.rate", "carrier_envelope", "modulation_rate_hz", "Hz", _scope("audio", ["left", "right"], start=smooth["start_seconds"], end=smooth["end_seconds"]), smooth["rate"]["value_hz"], 0.25, coverage=0.8, confidence=0.75),
        _exact_claim("stage.gated_pulse.construction", "stage_classification", "construction_class", "category", _scope("audio", ["left", "right"], start=gated["start_seconds"], end=gated["end_seconds"]), "hard_gated_pulse", coverage=0.8, confidence=0.75),
        _absolute_claim("stage.gated_pulse.rate", "broadband_pulse_pattern", "pulse_rate_hz", "Hz", _scope("audio", ["left", "right"], start=gated["start_seconds"], end=gated["end_seconds"]), gated["rate"]["value_hz"], 0.25, coverage=0.8, confidence=0.75),
        _absolute_claim("stage.gated_pulse.duty_cycle", "broadband_pulse_pattern", "duty_cycle_fraction", "fraction", _scope("audio", ["left", "right"], start=gated["start_seconds"], end=gated["end_seconds"]), gated["duty_cycle"], 0.02, coverage=0.8, confidence=0.75),
        _exact_claim("timeline.audio_video_clock_alignment", "multimodal_timeline", "clock_alignment", "boolean", _scope("multimodal", ["left", "right"], start=0.0, end=recipe["duration_seconds"]), True),
    ]
    return claims


CLAIM_BUILDERS = {
    "ave-demo-001-binaural-construction": _claims_001,
    "ave-demo-002-smooth-am-ramp": _claims_002,
    "ave-demo-003-gated-pulse-contrast": _claims_003,
    "ave-demo-004-four-region-light": _claims_004,
    "ave-demo-005-staged-av-comparison": _claims_005,
}


def validate_declaration(declaration: dict[str, Any], duration_seconds: float | None = None) -> dict[str, Any]:
    if file_sha256(PLATFORM_DECLARATION_SCHEMA_PATH) != PLATFORM_SCHEMA_SHA256:
        raise DemoRecipeValidationError("vendored AVE Platform declaration schema hash mismatch")
    source_manifest = load_json(PLATFORM_DECLARATION_SOURCE_MANIFEST_PATH)
    if source_manifest["source_sha256"] != PLATFORM_SCHEMA_SHA256:
        raise DemoRecipeValidationError("AVE Platform declaration source manifest hash mismatch")
    try:
        _jsonschema_validate(
            declaration,
            load_json(PLATFORM_DECLARATION_SCHEMA_PATH),
            PLATFORM_DECLARATION_SCHEMA_PATH,
        )
    except Exception as exc:
        raise DemoRecipeValidationError(str(exc)) from exc

    expected_id = f"{declaration['demo_id']}@{declaration['demo_version']}"
    if declaration["declaration_id"] != expected_id:
        raise DemoRecipeValidationError(f"declaration_id must be {expected_id}")
    claim_ids = [claim["claim_id"] for claim in declaration["claims"]]
    if len(claim_ids) != len(set(claim_ids)):
        raise DemoRecipeValidationError("declaration claim_id values must be unique")
    compatible = {
        "exact": {"category", "boolean"},
        "absolute": {"scalar"},
        "relative": {"scalar"},
        "absolute_or_relative": {"scalar"},
        "interval_containment": {"interval"},
        "curve_fit": {"linear_curve"},
    }
    for claim in declaration["claims"]:
        comparison = claim["tolerance"]["comparison"]
        target_kind = claim["target"]["kind"]
        if target_kind not in compatible[comparison]:
            raise DemoRecipeValidationError(
                f"{claim['claim_id']} has incompatible {target_kind}/{comparison} target and tolerance"
            )
        time_range = claim["scope"]["time_range_seconds"]
        if time_range is not None:
            if time_range["end"] <= time_range["start"]:
                raise DemoRecipeValidationError(f"{claim['claim_id']} has a non-positive time range")
            if duration_seconds is not None and time_range["end"] > duration_seconds + 1e-9:
                raise DemoRecipeValidationError(f"{claim['claim_id']} extends beyond the artifact")
    return deepcopy(declaration)


def compile_declaration(recipe: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    builder = CLAIM_BUILDERS.get(recipe["demo_id"])
    if builder is None:
        raise DemoRecipeValidationError(f"no declaration mapping for stable demo ID {recipe['demo_id']}")
    declaration = {
        "schema_version": "0.1.0",
        "demo_id": recipe["demo_id"],
        "demo_version": recipe["demo_version"],
        "declaration_id": f"{recipe['demo_id']}@{recipe['demo_version']}",
        "title": recipe["title"],
        "purpose": recipe["purpose"],
        "clock": {"origin": "artifact_start", "unit": "s"},
        "source_protocol": {
            "schema_version": recipe["schema_version"],
            "protocol_id": f"{recipe['demo_id']}@{recipe['demo_version']}",
            "sha256": resolved["recipe_canonical_sha256"],
        },
        "claims": builder(recipe),
        "limitations": list(recipe["limitations"]) + [
            "Agreement covers declared engineering measurements only, not neurological entrainment, efficacy, therapy, or exposure safety."
        ],
    }
    return validate_declaration(declaration, recipe["duration_seconds"])


def declaration_mapping_report(recipe: dict[str, Any], declaration: dict[str, Any]) -> dict[str, Any]:
    unmapped = [
        {
            "field": "verification.evidence_maturity",
            "reason": "Evidence maturity is derived/reporting state, not a producer measurement target; it remains in the render manifest.",
        },
        {
            "field": "safety",
            "reason": "Safety posture is package policy text, not a measurable declaration claim.",
        },
        {
            "field": "distribution",
            "reason": "Media-origin and redistribution provenance remain package metadata, outside declaration 0.1.0.",
        },
    ]
    if recipe["visual"]["kind"] == "four_region":
        unmapped.extend(
            [
                {
                    "field": "visual.light_recipe.regions.*.intervals.*.color",
                    "reason": "Declaration 0.1.0 has no RGB/grayscale tuple target type or color unit.",
                },
                {
                    "field": "visual.light_recipe.regions.*.intervals",
                    "reason": "Declaration 0.1.0 cannot encode a compound piecewise schedule in one target; the complete schedule remains in the hashed resolved light plan.",
                },
            ]
        )
    return {
        "mapping_report_version": "1.0.0",
        "demo_id": recipe["demo_id"],
        "demo_version": recipe["demo_version"],
        "declaration_id": declaration["declaration_id"],
        "declaration_schema_version": declaration["schema_version"],
        "declaration_canonical_sha256": canonical_sha256(declaration),
        "mapped_claim_ids": [claim["claim_id"] for claim in declaration["claims"]],
        "unmapped_generator_fields": unmapped,
        "interpretation_invented": False,
    }
