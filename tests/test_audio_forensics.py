from ave_audio_generator.forensics import evaluate_agreement
from ave_audio_generator.protocol import resolve_protocol


def _pair(frequency, digest, evidence_id):
    return {
        "evidence_type": "persistent_carrier_pair",
        "evidence_id": evidence_id,
        "provenance": {"input_sha256": digest},
        "scope": {"time_range_seconds": {"start": 0, "end": 180}},
        "measurements": [
            {"name": "left_carrier_frequency", "value": frequency},
            {"name": "right_carrier_frequency", "value": frequency},
            {"name": "carrier_difference", "value": 0.0},
        ],
    }


def test_forensics_agreement_requires_hash_and_all_declared_carriers(audio_protocol):
    digest = "a" * 64
    resolved = resolve_protocol(audio_protocol)
    evidence = {"evidence": [_pair(value, digest, f"e{index}") for index, value in enumerate((528, 1056, 1584, 2112))]}
    timeline = [
        {"start_seconds": "0", "end_seconds": "10", "difference_hz": "10"},
        {"start_seconds": "5", "end_seconds": "15", "difference_hz": "20"},
        {"start_seconds": "10", "end_seconds": "20", "difference_hz": "30"},
    ]
    agreement = evaluate_agreement(evidence, resolved, digest, timeline)
    assert agreement["passed_for_supported_claims"] is True
    evidence["evidence"].pop()
    assert evaluate_agreement(evidence, resolved, digest, timeline)["passed_for_supported_claims"] is False
    assert evaluate_agreement(evidence, resolved, "b" * 64, timeline)["input_sha256_matches"] is False
