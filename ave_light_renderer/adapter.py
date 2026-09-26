from copy import deepcopy
from pathlib import Path

from . import __version__
from .canonical import file_sha256, load_json
from .errors import AdapterValidationError, IncompleteEvidenceError
from .paths import (
    LUMENATE_EVIDENCE_SCHEMA_PATH,
    LUMENATE_SCHEMA_PATH,
    LUMENATE_SOURCE_MANIFEST_PATH,
)
from .validation import REGION_NAMES, _jsonschema_validate, validate_recipe


SUPPORTED_LUMENATE_VERSION = "0.2.0"
EXPECTED_PROTOCOL_SCHEMA_SHA256 = "e6b6bf3fdf9d29a7a63d1f5f059584277d1296224aff227724e9620438ed265a"
EXPECTED_EVIDENCE_SCHEMA_SHA256 = "7edee601724e13ceb2308482a9f1135acbdb850360de149f1ac009374f26ce18"


def verify_vendored_contract() -> None:
    source_manifest = load_json(LUMENATE_SOURCE_MANIFEST_PATH)
    expected = {
        "contracts/lumenate-protocol-export-0.2.0.schema.json": (
            LUMENATE_SCHEMA_PATH,
            EXPECTED_PROTOCOL_SCHEMA_SHA256,
        ),
        "contracts/ave-evidence-object-1.0.0.schema.json": (
            LUMENATE_EVIDENCE_SCHEMA_PATH,
            EXPECTED_EVIDENCE_SCHEMA_SHA256,
        ),
    }
    manifest_hashes = {
        item["path"]: item["sha256"] for item in source_manifest["artifacts"]
    }
    for manifest_path, (local_path, expected_hash) in expected.items():
        actual = file_sha256(local_path)
        if actual != expected_hash:
            raise AdapterValidationError(
                f"vendored schema hash mismatch for {manifest_path}: "
                f"expected {expected_hash}, got {actual}"
            )
        if manifest_hashes.get(manifest_path) != actual:
            raise AdapterValidationError(
                f"vendored SOURCE_MANIFEST does not pin {manifest_path}"
            )


def validate_lumenate_export(document: dict) -> dict:
    verify_vendored_contract()
    version = document.get("schema_version")
    if version != SUPPORTED_LUMENATE_VERSION:
        raise AdapterValidationError(
            f"unsupported Lumenate protocol version: {version!r}; "
            f"only {SUPPORTED_LUMENATE_VERSION} is supported"
        )
    schema = load_json(LUMENATE_SCHEMA_PATH)
    evidence_schema = load_json(LUMENATE_EVIDENCE_SCHEMA_PATH)
    evidence_uri = (
        "https://example.invalid/lumenate-nova/contracts/"
        "ave-evidence-object-1.0.0.schema.json"
    )
    try:
        _jsonschema_validate(
            document,
            schema,
            LUMENATE_SCHEMA_PATH,
            ref_store={
                evidence_uri: evidence_schema,
                evidence_schema["$id"]: evidence_schema,
            },
        )
    except Exception as exc:
        if isinstance(exc, AdapterValidationError):
            raise
        raise AdapterValidationError(str(exc)) from exc
    return document


def renderability_issues(document: dict) -> list[dict]:
    issues: list[dict] = []
    for segment in document["segments"]:
        missing: list[str] = []
        if segment.get("intensity") is None:
            missing.append("intensity")
        if segment.get("color_rgb") is None:
            missing.append("color_rgb")
        pulse = segment.get("pulse")
        if pulse is None:
            missing.append("pulse")
        else:
            if pulse.get("frequency_hz") is None:
                missing.append("pulse.frequency_hz")
            if pulse.get("duty_cycle") is None:
                missing.append("pulse.duty_cycle")
        if missing:
            issues.append({"segment_id": segment["segment_id"], "missing": missing})
    return issues


def adapt_lumenate_export(
    document: dict,
    source_path: str | Path,
    phase_policy: str,
    phase_origin_cycles: float,
) -> dict:
    validate_lumenate_export(document)
    if phase_policy not in {"continuous", "reset"}:
        raise AdapterValidationError("an explicit emulator phase policy is required")
    if not 0 <= phase_origin_cycles < 1:
        raise AdapterValidationError("phase_origin_cycles must be in [0, 1)")

    issues = renderability_issues(document)
    if issues:
        raise IncompleteEvidenceError(
            f"Lumenate export {document['export_id']} is valid evidence but cannot drive rendering: "
            f"{len(issues)} segment(s) lack machine-readable parameters",
            issues=issues,
        )

    segments = sorted(document["segments"], key=lambda item: (item["start_ms"], item["end_ms"]))
    expected_start = 0
    for segment in segments:
        if segment["start_ms"] != expected_start or segment["end_ms"] <= segment["start_ms"]:
            raise IncompleteEvidenceError(
                "Lumenate segments are not a complete monotonic, non-overlapping timeline",
                issues=[{"segment_id": segment["segment_id"], "missing": ["complete_monotonic_timeline"]}],
            )
        expected_start = segment["end_ms"]
    if expected_start != document["session"]["duration_ms"]:
        raise IncompleteEvidenceError(
            "Lumenate segments do not cover the declared session duration",
            issues=[{"segment_id": None, "missing": ["full_duration_coverage"]}],
        )

    input_hash = file_sha256(source_path)
    evidence_ids = sorted(
        {evidence_id for segment in segments for evidence_id in segment["evidence_ids"]}
    )
    execution_layers = sorted({segment["execution_layer"] for segment in segments})
    intervals = []
    for segment in segments:
        pulse = segment["pulse"]
        intervals.append(
            {
                "interval_id": segment["segment_id"],
                "kind": "pulse",
                "start_us": segment["start_ms"] * 1000,
                "end_us": segment["end_ms"] * 1000,
                "frequency_hz": {"kind": "constant", "value": pulse["frequency_hz"]},
                "duty_cycle": {"kind": "constant", "value": pulse["duty_cycle"]},
                "intensity": {"kind": "constant", "value": segment["intensity"]},
                "color": {"mode": "rgb", "value": segment["color_rgb"]},
                "phase_policy": phase_policy,
                "phase_origin_cycles": phase_origin_cycles,
                "source_provenance": {
                    "source_segment_id": segment["segment_id"],
                    "evidence_ids": sorted(segment["evidence_ids"]),
                    "execution_layer": segment["execution_layer"],
                },
            }
        )

    recipe = {
        "schema_version": "1.0.0",
        "recipe_id": f"adapted-{document['export_id']}",
        "renderer_version": __version__,
        "source": {
            "kind": "lumenate_protocol_export",
            "source_id": document["export_id"],
            "sha256": input_hash,
            "schema_version": document["schema_version"],
        },
        "clock": {"kind": "monotonic_virtual", "unit": "us", "origin_us": 0},
        "duration_us": document["session"]["duration_ms"] * 1000,
        "output": {"color_mode": "rgb", "background_rgb": [0, 0, 0]},
        "safety": {
            "offline_only": True,
            "photosensitivity_warning": "Offline emulator preview; not calibrated or approved for exposure.",
            "calibrated_intensity": False,
        },
        "regions": [],
        "adapter_provenance": {
            "adapter": "lumenate-protocol-0.2.0-to-ave-light-recipe-1.0.0",
            "source_export_sha256": input_hash,
            "source_export_id": document["export_id"],
            "source_created_at": document["created_at"],
            "source_schema_version": document["schema_version"],
            "evidence_ids": evidence_ids,
            "execution_layers": execution_layers,
            "clocks": document["clocks"],
            "confidence": document["confidence"],
            "limitations": document["limitations"],
            "mapping": {
                "regions": "single evidence timeline mirrored to four independently addressable AVE regions",
                "phase_policy": phase_policy,
                "phase_origin_cycles": phase_origin_cycles,
                "phase_provenance": "explicit AVE emulator choice; not measured Lumenate behavior",
                "shape_detail_used": False,
                "null_inference_used": False,
            },
        },
        "limitations": list(document["limitations"]) + [
            "Four-region mirroring is an AVE emulator mapping, not evidence of Nova channel topology.",
            "Phase policy and origin are explicit emulator choices, not observed device behavior.",
            "No shape_detail prose was parsed and no null value was inferred.",
            "Output is not physically equivalent to Nova and intensity is not calibrated.",
        ],
    }
    for name in REGION_NAMES:
        region_intervals = deepcopy(intervals)
        for interval in region_intervals:
            interval["interval_id"] = f"{name}-{interval['interval_id']}"
        recipe["regions"].append({"name": name, "intervals": region_intervals})
    return validate_recipe(recipe)
