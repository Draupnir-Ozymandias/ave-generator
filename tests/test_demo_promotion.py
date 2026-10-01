from copy import deepcopy
from pathlib import Path

import pytest

from ave_demo_generator import package as package_module
from ave_demo_generator import promotion
from ave_demo_generator.errors import DemoRecipeValidationError
from ave_demo_generator.paths import (
    DEMO_RECIPE_DIR,
    PLATFORM_AGREEMENT_SCHEMA_PATH,
)
from ave_light_renderer.canonical import file_sha256, load_json, write_json


PLATFORM_SOURCE_SCHEMA = Path(
    "/Users/eric/Projects/media/ave_platform/contracts/ave-demo-agreement-report-0.1.0.schema.json"
)


def _fake_media(path, *_args, **_kwargs):
    Path(path).write_bytes(b"silent-video")
    return Path(path)


def _fake_mux(_video, _audio, output):
    Path(output).write_bytes(b"muxed-video")
    return Path(output)


def _report_for(package_dir: Path, *, unsupported_claim: str | None = None) -> dict:
    demo_id = package_dir.name
    declaration_path = package_dir / f"{demo_id}-declaration.json"
    declaration = load_json(declaration_path)
    request = load_json(package_dir / "verification-request.json")
    artifact_sha256 = request["detector_input"]["sha256"]
    results = []
    for claim in declaration["claims"]:
        unsupported = claim["claim_id"] == unsupported_claim
        results.append(
            {
                "claim_id": claim["claim_id"],
                "required": claim["required"],
                "state": "unsupported" if unsupported else "agree",
                "observed": None,
                "errors": {},
                "coverage_fraction": None if unsupported else 1.0,
                "confidence": None if unsupported else 1.0,
                "evidence_ids": [] if unsupported else ["ave_0123456789abcdef"],
                "reason": "Synthetic unsupported result." if unsupported else "Synthetic agreement.",
                "limitations": [],
            }
        )
    return {
        "agreement_report_version": "0.1.0",
        "demo_id": declaration["demo_id"],
        "demo_version": declaration["demo_version"],
        "declaration_contract": "ave-demo-declaration@0.1.0",
        "declaration_id": declaration["declaration_id"],
        "declaration_sha256": file_sha256(declaration_path),
        "declaration_schema_sha256": "aca39c90191762cde5048dfefc6f732d9e0c43e2da668194f2cc6cb04175ab45",
        "declaration_validation_errors": [],
        "artifact_sha256": artifact_sha256,
        "observation_sha256": "1" * 64,
        "ordering_attestation": {
            "declaration_loaded_during_detection": False,
            "targets_loaded_during_detection": False,
            "tolerances_loaded_during_detection": False,
        },
        "forensics": {
            "version": "test",
            "run_id": "ave_run_0123456789abcdef",
            "source_tree_sha256": "2" * 64,
            "git": {"commit": "3" * 40, "branch": "main", "dirty": False},
            "analysis_configuration": {},
        },
        "claim_results": results,
        "evidence_label": "partially_verified" if unsupported_claim else "verified",
        "limitations": ["Engineering agreement only."],
    }


def _built_package(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(package_module, "render_presentation_video", _fake_media)
    monkeypatch.setattr(package_module, "mux_av", _fake_mux)
    package_dir = tmp_path / "ave-demo-001-binaural-construction"
    package_module.build_demo_package(
        DEMO_RECIPE_DIR / "ave-demo-001-binaural-construction.json",
        package_dir,
    )
    return package_dir


def test_vendored_agreement_schema_is_exactly_pinned():
    assert file_sha256(PLATFORM_AGREEMENT_SCHEMA_PATH) == promotion.PLATFORM_AGREEMENT_SCHEMA_SHA256
    if PLATFORM_SOURCE_SCHEMA.is_file():
        assert file_sha256(PLATFORM_SOURCE_SCHEMA) == promotion.PLATFORM_AGREEMENT_SCHEMA_SHA256


def test_promotion_attaches_report_updates_public_records_and_preserves_detector(tmp_path, monkeypatch):
    package_dir = _built_package(tmp_path, monkeypatch)
    report = _report_for(package_dir, unsupported_claim="audio.sample_peak")
    report_path = tmp_path / "agreement-report.json"
    write_json(report_path, report)
    detector_path = package_dir / load_json(package_dir / "verification-request.json")["detector_input"]["path"]
    detector_before = file_sha256(detector_path)

    monkeypatch.setattr(promotion, "render_presentation_video", _fake_media)
    monkeypatch.setattr(promotion, "mux_av", _fake_mux)
    monkeypatch.setattr(
        promotion,
        "git_state",
        lambda _root: {"commit": "4" * 40, "branch": "main", "dirty": False},
    )
    result = promotion.promote_demo_package(package_dir, report_path)

    manifest = load_json(package_dir / "render-manifest.json")
    release = load_json(package_dir / "release-record.json")
    readme = (package_dir / "PACKAGE_README.md").read_text(encoding="utf-8")
    assert result["evidence_label"] == "partially_verified"
    assert manifest["evidence_maturity"] == "partially_verified"
    assert manifest["field_level_agreement"]["sha256"] == file_sha256(report_path)
    assert manifest["forensics_observation"]["sha256"] == report["observation_sha256"]
    assert release["claim_groups"]["unsupported"][0]["claim_id"] == "audio.sample_peak"
    assert "`audio.sample_peak` — Synthetic unsupported result." in readme
    assert file_sha256(package_dir / promotion.REPORT_FILENAME) == file_sha256(report_path)
    assert file_sha256(detector_path) == detector_before
    assert result["detector_input_unchanged"] is True


def test_promotion_rejects_incorrect_derived_label(tmp_path, monkeypatch):
    package_dir = _built_package(tmp_path, monkeypatch)
    report = _report_for(package_dir)
    invalid = deepcopy(report)
    invalid["evidence_label"] = "exploratory"
    report_path = tmp_path / "agreement-report.json"
    write_json(report_path, invalid)
    with pytest.raises(DemoRecipeValidationError, match="derived label"):
        promotion.promote_demo_package(package_dir, report_path, require_clean=False)


def test_promotion_rejects_detector_input_drift(tmp_path, monkeypatch):
    package_dir = _built_package(tmp_path, monkeypatch)
    report = _report_for(package_dir)
    report_path = tmp_path / "agreement-report.json"
    write_json(report_path, report)
    request = load_json(package_dir / "verification-request.json")
    (package_dir / request["detector_input"]["path"]).write_bytes(b"changed")
    with pytest.raises(DemoRecipeValidationError, match="detector input SHA-256 has changed"):
        promotion.promote_demo_package(package_dir, report_path, require_clean=False)
