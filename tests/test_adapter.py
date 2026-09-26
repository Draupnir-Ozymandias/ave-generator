from copy import deepcopy

import pytest

from ave_light_renderer.adapter import (
    adapt_lumenate_export,
    renderability_issues,
    validate_lumenate_export,
    verify_vendored_contract,
)
from ave_light_renderer.canonical import file_sha256, load_json
from ave_light_renderer.errors import AdapterValidationError, IncompleteEvidenceError
from ave_light_renderer.paths import (
    ALIGNED_EXPORT_PATH,
    LUMENATE_EVIDENCE_SCHEMA_PATH,
    LUMENATE_SCHEMA_PATH,
    VITALITY_EXPORT_PATH,
)


def test_vendored_contract_hashes_are_exact():
    verify_vendored_contract()
    assert file_sha256(LUMENATE_SCHEMA_PATH) == "e6b6bf3fdf9d29a7a63d1f5f059584277d1296224aff227724e9620438ed265a"
    assert file_sha256(LUMENATE_EVIDENCE_SCHEMA_PATH) == "7edee601724e13ceb2308482a9f1135acbdb850360de149f1ac009374f26ce18"


def test_aligned_export_validates_and_preserves_provenance():
    document = load_json(ALIGNED_EXPORT_PATH)
    validate_lumenate_export(document)
    assert renderability_issues(document) == []
    recipe = adapt_lumenate_export(document, ALIGNED_EXPORT_PATH, "reset", 0.0)
    provenance = recipe["adapter_provenance"]
    assert recipe["source"]["sha256"] == "6b108a02999b02d7dbc782753b7d18215bc82b7b027b25b0844509f330b5866f"
    assert provenance["source_schema_version"] == "0.2.0"
    assert provenance["evidence_ids"] == ["ave_fedcba9876543210"]
    assert provenance["execution_layers"] == ["session_declaration"]
    assert provenance["clocks"] == document["clocks"]
    assert provenance["confidence"] == document["confidence"]
    assert provenance["limitations"] == document["limitations"]
    assert provenance["mapping"]["shape_detail_used"] is False
    assert provenance["mapping"]["null_inference_used"] is False
    assert len(recipe["regions"]) == 4
    first_interval = recipe["regions"][0]["intervals"][0]
    assert first_interval["source_provenance"] == {
        "source_segment_id": "segment-001",
        "evidence_ids": ["ave_fedcba9876543210"],
        "execution_layer": "session_declaration",
    }


def test_empirical_vitality_fails_safely_without_inference():
    document = load_json(VITALITY_EXPORT_PATH)
    validate_lumenate_export(document)
    issues = renderability_issues(document)
    assert len(issues) == 34
    with pytest.raises(IncompleteEvidenceError) as caught:
        adapt_lumenate_export(document, VITALITY_EXPORT_PATH, "reset", 0.0)
    assert len(caught.value.issues) == 34
    assert "intensity" in caught.value.issues[0]["missing"]


def test_unsupported_protocol_version_is_rejected():
    document = deepcopy(load_json(ALIGNED_EXPORT_PATH))
    document["schema_version"] = "0.3.0"
    with pytest.raises(AdapterValidationError, match="unsupported"):
        validate_lumenate_export(document)


def test_adapter_requires_explicit_phase_choice():
    document = load_json(ALIGNED_EXPORT_PATH)
    with pytest.raises(AdapterValidationError, match="phase policy"):
        adapt_lumenate_export(document, ALIGNED_EXPORT_PATH, "unknown", 0.0)


def test_adapter_does_not_parse_shape_detail_to_fill_nulls():
    document = deepcopy(load_json(ALIGNED_EXPORT_PATH))
    document["segments"][1]["pulse"]["frequency_hz"] = None
    document["segments"][1]["pulse"]["shape_detail"] = "frequency 10->12 Hz"
    with pytest.raises(IncompleteEvidenceError) as caught:
        adapt_lumenate_export(document, ALIGNED_EXPORT_PATH, "reset", 0.0)
    assert caught.value.issues == [
        {"segment_id": "segment-002", "missing": ["pulse.frequency_hz"]}
    ]
