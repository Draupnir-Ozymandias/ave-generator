from copy import deepcopy

import pytest

from ave_audio_generator.errors import ProtocolValidationError
from ave_audio_generator.protocol import accumulated_sweep_cycles, resolve_protocol, sweep_frequency
from ave_audio_generator.validation import validate_protocol


def test_baseline_audio_protocol_validates(audio_protocol):
    assert validate_protocol(audio_protocol)["protocol_id"] == "corrected-baseline-sweep-v1"


def test_rejects_aliased_harmonics(audio_protocol):
    invalid = deepcopy(audio_protocol)
    invalid["synthesis"]["carrier_hz"] = 6000
    with pytest.raises(ProtocolValidationError, match="Nyquist"):
        validate_protocol(invalid)


def test_rejects_unordered_transition_bands(audio_protocol):
    invalid = deepcopy(audio_protocol)
    invalid["synthesis"]["transition_bands_hz"]["isochronic_to_harmonic"] = [40, 50]
    with pytest.raises(ProtocolValidationError, match="strictly ordered"):
        validate_protocol(invalid)


def test_rejects_nonintegral_sample_count_and_missing_fundamental(audio_protocol):
    invalid_duration = deepcopy(audio_protocol)
    invalid_duration["duration_seconds"] = 1.000001
    with pytest.raises(ProtocolValidationError, match="integer sample count"):
        validate_protocol(invalid_duration)
    invalid_harmonics = deepcopy(audio_protocol)
    invalid_harmonics["synthesis"]["harmonics"] = [{"multiple": 2, "amplitude": 0.5}]
    with pytest.raises(ProtocolValidationError, match="fundamental"):
        validate_protocol(invalid_harmonics)


def test_resolved_protocol_has_integrated_phase_and_shared_visual_clock(audio_protocol):
    import numpy as np

    resolved = resolve_protocol(audio_protocol, 10.0)
    times = np.asarray([0.0, 2.0, 10.0])
    assert sweep_frequency(resolved, times).tolist() == pytest.approx([0.0, 72.0, 360.0])
    assert accumulated_sweep_cycles(resolved, times).tolist() == pytest.approx([0.0, 72.0, 1800.0])
    assert resolved["phase_model"]["time_varying_frequency_times_time_used"] is False
    assert resolved["visual_timeline"]["duration_seconds"] == 10.0
