"""Promote built demo packages using pinned, independently authored reports."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from ave_audio_generator.video import mux_av
from ave_light_renderer.canonical import canonical_sha256, file_sha256, load_json, write_json
from ave_light_renderer.manifest import git_state
from ave_light_renderer.validation import _jsonschema_validate

from .declaration import PLATFORM_SCHEMA_SHA256
from .errors import DemoRecipeValidationError
from .paths import (
    PLATFORM_AGREEMENT_SCHEMA_PATH,
    PLATFORM_AGREEMENT_SOURCE_MANIFEST_PATH,
    PROJECT_ROOT,
)
from .presentation import render_presentation_video


PLATFORM_AGREEMENT_SCHEMA_SHA256 = (
    "f4a2ce98dc407b0aa7f40dcfc636de98e6c8d498feda84ecec9e5b3a36292315"
)
PROMOTION_VERSION = "1.0.0"
REPORT_FILENAME = "forensics-agreement-report.json"
RELEASE_RECORD_FILENAME = "release-record.json"


def _derive_label(results: list[dict[str, Any]]) -> str:
    required = [result for result in results if result["required"]]
    states = {result["state"] for result in required}
    if required and states == {"agree"}:
        return "verified"
    if (
        any(result["state"] == "agree" for result in required)
        and not states.intersection({"disagree", "invalid_declaration"})
        and states.intersection({"unsupported", "not_evaluated"})
    ):
        return "partially_verified"
    return "exploratory"


def _validate_report_schema(report: dict[str, Any]) -> None:
    if file_sha256(PLATFORM_AGREEMENT_SCHEMA_PATH) != PLATFORM_AGREEMENT_SCHEMA_SHA256:
        raise DemoRecipeValidationError("vendored AVE Platform agreement schema hash mismatch")
    source = load_json(PLATFORM_AGREEMENT_SOURCE_MANIFEST_PATH)
    if source["source_sha256"] != PLATFORM_AGREEMENT_SCHEMA_SHA256:
        raise DemoRecipeValidationError("AVE Platform agreement source manifest hash mismatch")
    try:
        _jsonschema_validate(
            report,
            load_json(PLATFORM_AGREEMENT_SCHEMA_PATH),
            PLATFORM_AGREEMENT_SCHEMA_PATH,
        )
    except Exception as exc:
        raise DemoRecipeValidationError(str(exc)) from exc


def _claim_groups(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        state: []
        for state in ("agree", "unsupported", "not_evaluated", "disagree", "invalid_declaration")
    }
    for result in report["claim_results"]:
        groups[result["state"]].append(
            {
                "claim_id": result["claim_id"],
                "reason": result["reason"],
                "limitations": result["limitations"],
            }
        )
    return groups


def _validate_package_report(
    package_dir: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    report = load_json(report_path)
    _validate_report_schema(report)
    manifest_path = package_dir / "render-manifest.json"
    request_path = package_dir / "verification-request.json"
    if not manifest_path.is_file() or not request_path.is_file():
        raise DemoRecipeValidationError(f"{package_dir} is not a complete built demo package")
    manifest = load_json(manifest_path)
    request = load_json(request_path)
    demo_id = manifest["demo_id"]
    declaration_path = package_dir / manifest["generator_declaration"]["path"]
    declaration = load_json(declaration_path)

    identity_fields = ("demo_id", "demo_version", "declaration_id")
    for field in identity_fields:
        expected = declaration[field]
        if report[field] != expected:
            raise DemoRecipeValidationError(
                f"agreement report {field} {report[field]!r} does not match package {expected!r}"
            )
    declaration_sha256 = file_sha256(declaration_path)
    if report["declaration_sha256"] != declaration_sha256:
        raise DemoRecipeValidationError("agreement report declaration SHA-256 does not match package")
    if report["declaration_schema_sha256"] != PLATFORM_SCHEMA_SHA256:
        raise DemoRecipeValidationError("agreement report declaration-schema SHA-256 is unsupported")
    if report["declaration_validation_errors"]:
        raise DemoRecipeValidationError("agreement report records declaration validation errors")
    if report["forensics"]["git"]["dirty"]:
        raise DemoRecipeValidationError("agreement report was not produced from a clean Forensics revision")

    declared_claims = [claim["claim_id"] for claim in declaration["claims"]]
    reported_claims = [result["claim_id"] for result in report["claim_results"]]
    if len(reported_claims) != len(set(reported_claims)):
        raise DemoRecipeValidationError("agreement report contains duplicate claim results")
    if set(reported_claims) != set(declared_claims):
        raise DemoRecipeValidationError("agreement report claim set does not match the declaration")
    derived = _derive_label(report["claim_results"])
    if report["evidence_label"] != derived:
        raise DemoRecipeValidationError(
            f"agreement report label {report['evidence_label']} does not match derived label {derived}"
        )

    detector_path = package_dir / request["detector_input"]["path"]
    if not detector_path.is_file():
        raise DemoRecipeValidationError("verification request detector input is missing")
    detector_sha256 = file_sha256(detector_path)
    if request["detector_input"]["sha256"] != detector_sha256:
        raise DemoRecipeValidationError("detector input SHA-256 has changed since blind-analysis request")

    artifact_matches: list[str] = []
    for output in manifest["outputs"]:
        candidate = package_dir / output["path"]
        if candidate.is_file() and file_sha256(candidate) == report["artifact_sha256"]:
            artifact_matches.append(output["path"])
    if not artifact_matches:
        raise DemoRecipeValidationError(
            f"Forensics artifact SHA-256 is not present in Generator package {demo_id}"
        )
    return report, declaration, manifest, request, detector_sha256


def _readme(
    recipe: dict[str, Any],
    resolved: dict[str, Any],
    report: dict[str, Any],
    report_sha256: str,
    detector_path: str,
    detector_sha256: str,
    presentation_sha256: str,
) -> str:
    groups = _claim_groups(report)

    def section(title: str, state: str) -> str:
        rows = groups[state]
        if not rows:
            return f"### {title}\n\nNone."
        return f"### {title}\n\n" + "\n".join(
            f"- `{row['claim_id']}` — {row['reason']}" for row in rows
        )

    return f"""# {recipe['title']}

Evidence maturity: **{report['evidence_label']}**

This label is derived from the attached independent AVE Forensics agreement report. It describes
engineering agreement only; it is not a neurological, therapeutic, efficacy, or safety finding.

## Purpose

{recipe['purpose']}

## Independent verification

{section('Supported fields', 'agree')}

{section('Unsupported fields', 'unsupported')}

{section('Not evaluated', 'not_evaluated')}

{section('Disagreements', 'disagree')}

{section('Invalid declarations', 'invalid_declaration')}

The Generator declaration, persisted Forensics observation, and field-level agreement are separate
records. The attached report attests that declaration values and tolerances were not loaded during
detection.

## Reproduce

From the AVE Generator repository root:

```sh
ave-demo-generator build contracts/examples/demos/{recipe['demo_id']}.json --output-dir output/demos/{recipe['demo_id']}
ave-demo-generator promote --package-dir output/demos/{recipe['demo_id']} --agreement-report ../ave_forensics/artifacts/demo-portfolio/{recipe['demo_id']}/agreement-report.json
```

The second command requires an already-built package and refuses report, declaration, detector-input,
identity, schema, or evidence-label drift.

## Safety and limitations

{recipe['safety']['warning']}

{recipe['safety']['headphones_assumption']}

{chr(10).join(f'- {item}' for item in recipe['limitations'])}

{chr(10).join(f'- {item}' for item in report['limitations'])}

Digital amplitude is not calibrated SPL. Visual RGB values are not calibrated luminance. Encoded
audio/video timing is not physical acoustic or display latency. This package makes no claim of
neurological entrainment, mental-state change, therapy, efficacy, or human-exposure safety.

## Provenance

- Declaration: `{report['declaration_id']}`
- Recipe canonical SHA-256: `{resolved['recipe_canonical_sha256']}`
- Resolved plan SHA-256: `{resolved['resolved_plan_sha256']}`
- Detector input: `{detector_path}`
- Detector-input SHA-256: `{detector_sha256}`
- Attached Forensics report: `{REPORT_FILENAME}`
- Forensics report SHA-256: `{report_sha256}`
- Forensics observation SHA-256: `{report['observation_sha256']}`
- Forensics Git commit: `{report['forensics']['git']['commit']}`
- Promoted presentation SHA-256: `{presentation_sha256}`
- Media origin: `{recipe['distribution']['media_origin']}`
- Redistributable: `{str(recipe['distribution']['redistributable']).lower()}`
"""


def _output_record(path: Path, package_dir: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(package_dir).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def promote_demo_package(
    package_dir: Path,
    agreement_report_path: Path,
    *,
    require_clean: bool = True,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    agreement_report_path = agreement_report_path.resolve()
    report, declaration, manifest, request, detector_sha256 = _validate_package_report(
        package_dir, agreement_report_path
    )
    source_state = git_state(PROJECT_ROOT)
    if require_clean and source_state["dirty"]:
        raise DemoRecipeValidationError(
            "release promotion requires a clean Generator worktree for provenance"
        )

    recipe_path = package_dir / f"{report['demo_id']}-recipe.json"
    resolved_path = package_dir / f"{report['demo_id']}-resolved-protocol.json"
    recipe = load_json(recipe_path)
    resolved = load_json(resolved_path)
    report_sha256 = file_sha256(agreement_report_path)
    attached_report_path = package_dir / REPORT_FILENAME
    release_record_path = package_dir / RELEASE_RECORD_FILENAME
    presentation_path = package_dir / "presentation.mp4"
    silent_path = package_dir / "presentation-video.silent.mp4"
    previous_release = load_json(release_record_path) if release_record_path.is_file() else None
    original_presentation_sha256 = (
        previous_release["presentation"]["pre_promotion_sha256"]
        if previous_release is not None
        else file_sha256(presentation_path)
    )

    shutil.copyfile(agreement_report_path, attached_report_path)
    temporary_silent = package_dir / ".promotion-presentation.silent.mp4"
    temporary_presentation = package_dir / ".promotion-presentation.mp4"
    git_version = source_state["commit"] + ("+dirty" if source_state["dirty"] else "")
    render_presentation_video(
        temporary_silent,
        recipe,
        resolved,
        git_version,
        size=(recipe["visual"].get("width", 960), recipe["visual"].get("height", 540)),
        agreement={"report": report, "report_sha256": report_sha256},
    )
    mux_av(temporary_silent, package_dir / "audio" / "stereo.wav", temporary_presentation)
    temporary_silent.replace(silent_path)
    temporary_presentation.replace(presentation_path)
    presentation_sha256 = file_sha256(presentation_path)

    detector_relative_path = request["detector_input"]["path"]
    readme_path = package_dir / "PACKAGE_README.md"
    readme_path.write_text(
        _readme(
            recipe,
            resolved,
            report,
            report_sha256,
            detector_relative_path,
            detector_sha256,
            presentation_sha256,
        ),
        encoding="utf-8",
    )

    paths = {output["path"] for output in manifest["outputs"]}
    paths.update({REPORT_FILENAME, "PACKAGE_README.md", "presentation.mp4", "presentation-video.silent.mp4"})
    paths.discard(RELEASE_RECORD_FILENAME)
    material_outputs = [
        _output_record(package_dir / relative, package_dir)
        for relative in sorted(paths)
        if (package_dir / relative).is_file()
    ]
    promoted_materials_sha256 = canonical_sha256(material_outputs)
    groups = _claim_groups(report)
    state_counts = dict(sorted(Counter(result["state"] for result in report["claim_results"]).items()))
    release_record = {
        "release_record_version": PROMOTION_VERSION,
        "demo_id": report["demo_id"],
        "demo_version": report["demo_version"],
        "declaration_id": report["declaration_id"],
        "evidence_label": report["evidence_label"],
        "claim_state_counts": state_counts,
        "claim_groups": groups,
        "generator": {
            "git_commit": source_state["commit"],
            "git_dirty": source_state["dirty"],
        },
        "forensics_agreement": {
            "path": REPORT_FILENAME,
            "sha256": report_sha256,
            "agreement_report_version": report["agreement_report_version"],
            "observation_sha256": report["observation_sha256"],
            "artifact_sha256": report["artifact_sha256"],
            "git_commit": report["forensics"]["git"]["commit"],
        },
        "detector_input": {
            "path": detector_relative_path,
            "sha256": detector_sha256,
            "unchanged_during_promotion": True,
        },
        "presentation": {
            "path": "presentation.mp4",
            "pre_promotion_sha256": original_presentation_sha256,
            "promoted_sha256": presentation_sha256,
        },
        "promoted_materials_sha256": promoted_materials_sha256,
        "limitations": report["limitations"],
    }
    write_json(release_record_path, release_record)
    output_records = material_outputs + [_output_record(release_record_path, package_dir)]
    output_records.sort(key=lambda output: output["path"])
    package_outputs_sha256 = canonical_sha256(output_records)

    manifest.update(
        {
            "evidence_maturity": report["evidence_label"],
            "forensics_observation": {
                "sha256": report["observation_sha256"],
                "attached": False,
                "authority": "AVE Forensics",
            },
            "field_level_agreement": {
                "path": REPORT_FILENAME,
                "sha256": report_sha256,
                "agreement_report_version": report["agreement_report_version"],
                "evidence_label": report["evidence_label"],
                "claim_state_counts": state_counts,
                "authority": "AVE Forensics",
            },
            "release_promotion": {
                "promotion_version": PROMOTION_VERSION,
                "generator_git_commit": source_state["commit"],
                "generator_git_dirty": source_state["dirty"],
                "detector_input_unchanged": True,
                "detector_input_sha256": detector_sha256,
                "promoted_presentation_sha256": presentation_sha256,
                "promoted_materials_sha256": promoted_materials_sha256,
                "package_outputs_sha256": package_outputs_sha256,
            },
            "outputs": output_records,
        }
    )
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_content_sha256"}
    manifest["manifest_content_sha256"] = canonical_sha256(unsigned)
    manifest_path = package_dir / "render-manifest.json"
    write_json(manifest_path, manifest)

    if file_sha256(package_dir / detector_relative_path) != detector_sha256:
        raise DemoRecipeValidationError("detector input changed during release promotion")
    return {
        "demo_id": report["demo_id"],
        "demo_version": report["demo_version"],
        "evidence_label": report["evidence_label"],
        "claim_state_counts": state_counts,
        "detector_input_sha256": detector_sha256,
        "detector_input_unchanged": True,
        "agreement_report_sha256": report_sha256,
        "presentation_sha256": presentation_sha256,
        "promoted_materials_sha256": promoted_materials_sha256,
        "package_outputs_sha256": package_outputs_sha256,
        "render_manifest_sha256": file_sha256(manifest_path),
    }


def promote_portfolio(
    packages_root: Path,
    reports_root: Path,
    *,
    require_clean: bool = True,
) -> dict[str, Any]:
    packages_root = packages_root.resolve()
    reports_root = reports_root.resolve()
    results = []
    for package_dir in sorted(packages_root.glob("ave-demo-[0-9][0-9][0-9]-*")):
        report_path = reports_root / package_dir.name / "agreement-report.json"
        if not report_path.is_file():
            raise DemoRecipeValidationError(f"canonical agreement report missing: {report_path}")
        results.append(
            promote_demo_package(package_dir, report_path, require_clean=require_clean)
        )
    if len(results) != 5:
        raise DemoRecipeValidationError(f"expected five canonical demo packages, found {len(results)}")
    index = {
        "release_index_version": PROMOTION_VERSION,
        "portfolio_status": "share_ready_release_candidates",
        "demos": results,
        "limitations": [
            "Engineering agreement does not establish neurological entrainment, efficacy, therapy, or exposure safety.",
            "Digital amplitude is not calibrated SPL and RGB values are not calibrated luminance.",
        ],
    }
    index["release_index_content_sha256"] = canonical_sha256(index)
    write_json(packages_root / "release-index.json", index)
    return index
