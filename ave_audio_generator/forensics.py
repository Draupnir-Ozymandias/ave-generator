import json
import os
import subprocess
import csv
from pathlib import Path

from ave_light_renderer.canonical import file_sha256


def evaluate_agreement(
    evidence: dict,
    resolved: dict,
    wav_hash: str,
    timeline_rows: list[dict] | None = None,
) -> dict:
    evidence_items = evidence.get("evidence", [])
    evidence_input_hashes = sorted(
        {
            item.get("provenance", {}).get("input_sha256")
            for item in evidence_items
            if item.get("provenance", {}).get("input_sha256")
        }
    )
    detected_pairs = []
    for item in evidence_items:
        if item.get("evidence_type") != "persistent_carrier_pair":
            continue
        measurements = {entry["name"]: entry["value"] for entry in item.get("measurements", [])}
        detected_pairs.append(
            {
                "left_hz": measurements.get("left_carrier_frequency"),
                "right_hz": measurements.get("right_carrier_frequency"),
                "difference_hz": measurements.get("carrier_difference"),
                "time_range_seconds": item.get("scope", {}).get("time_range_seconds"),
                "evidence_id": item.get("evidence_id"),
            }
        )
    synthesis = resolved["protocol"]["synthesis"]
    expected_shared = sorted(
        synthesis["carrier_hz"] * partial["multiple"]
        for partial in synthesis["harmonics"]
    )
    matched_shared = sorted(
        expected
        for expected in expected_shared
        if any(
            pair["left_hz"] is not None
            and pair["right_hz"] is not None
            and abs(pair["left_hz"] - expected) <= 0.5
            and abs(pair["right_hz"] - expected) <= 0.5
            for pair in detected_pairs
        )
    )
    transition_start = resolved["transition_times"]["binaural_to_isochronic"]["start_seconds"]
    sweep = synthesis["sweep"]
    duration = resolved["protocol"]["duration_seconds"]
    timeline_comparisons = []
    for row in timeline_rows or []:
        if not row.get("difference_hz"):
            continue
        midpoint = (float(row["start_seconds"]) + float(row["end_seconds"])) / 2
        if midpoint > transition_start:
            continue
        expected = min(
            sweep["start_hz"]
            + (sweep["end_hz"] - sweep["start_hz"]) * midpoint / duration,
            synthesis["binaural"]["max_difference_hz"],
        )
        measured = float(row["difference_hz"])
        timeline_comparisons.append(
            {
                "midpoint_seconds": midpoint,
                "expected_difference_hz": expected,
                "measured_difference_hz": measured,
                "error_hz": measured - expected,
                "passed": abs(measured - expected) <= 0.5,
            }
        )
    timeline_passed = bool(timeline_comparisons) and all(
        item["passed"] for item in timeline_comparisons
    )
    return {
        "passed_for_supported_claims": (
            evidence_input_hashes == [wav_hash]
            and matched_shared == expected_shared
            and timeline_passed
        ),
        "input_sha256_matches": evidence_input_hashes == [wav_hash],
        "expected_shared_carriers_hz": expected_shared,
        "matched_shared_carriers_hz": matched_shared,
        "detected_persistent_pairs": detected_pairs,
        "binaural_timeline_comparisons": timeline_comparisons,
        "binaural_timeline_passed": timeline_passed,
        "claim_coverage": {
            "persistent_carrier_structure": "verified",
            "binaural_difference_ramp": "verified from AVE Forensics time-resolved timeline",
            "isochronic_and_harmonic_modulation_ramps": "not independently reconstructed by this Forensics configuration",
            "generator_black_box_signal_probes": "recorded separately in the render manifest verification block",
        },
    }


def run_external_forensics(
    wav_path: str | Path,
    output_dir: str | Path,
    forensics_repo: str | Path,
    resolved: dict,
) -> dict:
    repository = Path(forensics_repo).resolve()
    python = repository / ".venv" / "bin" / "python"
    entrypoint = repository / "main.py"
    if not python.exists() or not entrypoint.exists():
        raise RuntimeError("AVE Forensics repository lacks .venv/bin/python or main.py")
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    cache_root = target / ".cache"
    for cache_name in ("numba", "matplotlib", "xdg"):
        (cache_root / cache_name).mkdir(parents=True, exist_ok=True)
    process_environment = os.environ.copy()
    process_environment.update(
        {
            "NUMBA_CACHE_DIR": str(cache_root / "numba"),
            "MPLCONFIGDIR": str(cache_root / "matplotlib"),
            "XDG_CACHE_HOME": str(cache_root / "xdg"),
        }
    )
    try:
        completed = subprocess.run(
            [str(python), "-B", str(entrypoint), str(Path(wav_path).resolve()), "--output-dir", str(target)],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
            env=process_environment,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "no subprocess output")[-4000:]
        raise RuntimeError(f"AVE Forensics failed with exit {exc.returncode}: {details}") from exc
    evidence_path = target / "ave_evidence.json"
    if not evidence_path.exists():
        raise RuntimeError("AVE Forensics completed without ave_evidence.json")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    wav_hash = file_sha256(wav_path)
    timeline_path = target / "ave_timeline.csv"
    timeline_rows = []
    if timeline_path.exists():
        with timeline_path.open("r", encoding="utf-8", newline="") as handle:
            timeline_rows = list(csv.DictReader(handle))
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=False, capture_output=True, text=True
    )
    types = sorted({item.get("evidence_type", "unknown") for item in evidence.get("evidence", [])})
    agreement = evaluate_agreement(evidence, resolved, wav_hash, timeline_rows)
    return {
        "status": "complete",
        "repository": str(repository),
        "git_commit": git.stdout.strip() if git.returncode == 0 else "unknown",
        "evidence_path": str(evidence_path),
        "evidence_sha256": file_sha256(evidence_path),
        "timeline_path": str(timeline_path) if timeline_path.exists() else None,
        "timeline_sha256": file_sha256(timeline_path) if timeline_path.exists() else None,
        "evidence_count": evidence.get("evidence_count", len(evidence.get("evidence", []))),
        "evidence_types": types,
        "agreement": agreement,
        "console_tail": completed.stdout[-2000:],
    }
