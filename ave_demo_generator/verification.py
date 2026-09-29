"""Generator-side black-box checks for rendered demo audio.

These checks validate Generator output. They are deliberately not represented as
independent AVE Forensics observations or field-level agreement decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile

from ave_audio_generator.verification import _spectral_peak


def _check(name: str, passed: bool, measured: Any, expected: Any, tolerance: Any = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "status": "passed" if passed else "failed",
        "measured": measured,
        "expected": expected,
    }
    if tolerance is not None:
        result["tolerance"] = tolerance
    return result


def verify_demo_audio(path: Path, resolved: dict[str, Any]) -> dict[str, Any]:
    """Measure a rendered WAV without relying on recipe construction state."""
    sample_rate, raw = wavfile.read(path)
    if raw.ndim == 1:
        raw = raw[:, None]
    if np.issubdtype(raw.dtype, np.integer):
        scale = float(max(abs(np.iinfo(raw.dtype).min), np.iinfo(raw.dtype).max))
        audio = raw.astype(np.float64) / scale
    else:
        audio = raw.astype(np.float64)

    expected_rate = int(resolved["sample_rate_hz"])
    expected_samples = int(resolved["sample_count"])
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    checks = [
        _check("sample_rate_hz", sample_rate == expected_rate, int(sample_rate), expected_rate),
        _check("channel_count", audio.shape[1] == 2, int(audio.shape[1]), 2),
        _check("sample_count", audio.shape[0] == expected_samples, int(audio.shape[0]), expected_samples),
        _check("no_clipped_samples", peak < 1.0, peak, "< 1.0"),
    ]

    stage_results: list[dict[str, Any]] = []
    for stage in resolved["declarations"]["audio_stages"]:
        stage_result: dict[str, Any] = {
            "stage_id": stage["stage_id"],
            "type": stage["kind"],
            "checks": [],
        }
        if stage["kind"] != "binaural":
            stage_result["status"] = "not_evaluated"
            stage_result["reason"] = (
                "No independent-equivalent Generator black-box check is claimed for this stage type."
            )
            stage_results.append(stage_result)
            continue

        start = int(round(stage["start_seconds"] * sample_rate))
        end = int(round(stage["end_seconds"] * sample_rate))
        margin = min(int(sample_rate), max(0, (end - start) // 5))
        segment = audio[start + margin : end - margin]
        if len(segment) < int(sample_rate):
            segment = audio[start:end]

        left_declared = float(stage["left_hz"])
        right_declared = float(stage["right_hz"])
        left_peak = _spectral_peak(segment[:, 0], sample_rate, left_declared - 30.0, left_declared + 30.0)
        right_peak = _spectral_peak(segment[:, 1], sample_rate, right_declared - 30.0, right_declared + 30.0)
        tolerance = 0.25
        stage_checks = [
            _check("left_carrier_hz", abs(left_peak - left_declared) <= tolerance, left_peak, left_declared, tolerance),
            _check("right_carrier_hz", abs(right_peak - right_declared) <= tolerance, right_peak, right_declared, tolerance),
            _check(
                "interchannel_difference_hz",
                abs(abs(right_peak - left_peak) - abs(right_declared - left_declared)) <= tolerance,
                abs(right_peak - left_peak),
                abs(right_declared - left_declared),
                tolerance,
            ),
        ]
        stage_result["checks"] = stage_checks
        stage_result["status"] = "passed" if all(c["status"] == "passed" for c in stage_checks) else "failed"
        stage_results.append(stage_result)

    all_evaluated = [*checks]
    for stage in stage_results:
        all_evaluated.extend(stage["checks"])
    passed = all(check["status"] == "passed" for check in all_evaluated)
    return {
        "record_type": "generator_validation",
        "record_version": "1.0.0",
        "scope": "deterministic build integrity and limited black-box output checks",
        "independence": False,
        "is_forensics_observation": False,
        "is_field_level_agreement": False,
        "passed": passed,
        "checks": checks,
        "stage_results": stage_results,
        "limitations": [
            "This record was produced by the same repository that declared and rendered the stimulus.",
            "It cannot substitute for independent AVE Forensics observation or agreement adjudication.",
            "Carrier measurements do not establish perceptual, neurological, therapeutic, or safety effects.",
        ],
    }
