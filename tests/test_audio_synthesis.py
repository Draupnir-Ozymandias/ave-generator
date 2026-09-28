import numpy as np
import pytest

from ave_audio_generator.protocol import resolve_protocol
from ave_audio_generator.synthesis import PhaseAccumulator, float_to_pcm16, synthesize_audio


def test_phase_accumulator_uses_exclusive_frequency_integral():
    accumulator = PhaseAccumulator(0.125)
    frequencies = np.asarray([1.0, 2.0, 3.0, 4.0])
    phases = accumulator.render(frequencies, 10)
    assert phases.tolist() == pytest.approx([0.125, 0.225, 0.425, 0.725])
    assert accumulator.cycles == pytest.approx(1.125)


def test_phase_accumulation_is_chunk_continuous():
    frequencies = np.linspace(3.0, 9.0, 1000, endpoint=False)
    expected = PhaseAccumulator().render(frequencies, 100)
    chunked = PhaseAccumulator()
    actual = np.concatenate([chunked.render(frequencies[:333], 100), chunked.render(frequencies[333:], 100)])
    assert actual == pytest.approx(expected, abs=1e-12)


def test_synthesis_is_deterministic_chunk_independent_and_has_headroom(audio_protocol):
    protocol = dict(audio_protocol)
    protocol["sample_rate_hz"] = 8000
    protocol["duration_seconds"] = 1.0
    protocol["synthesis"] = dict(audio_protocol["synthesis"])
    protocol["synthesis"]["carrier_hz"] = 440.0
    resolved = resolve_protocol(protocol)
    first, first_stats = synthesize_audio(resolved, chunk_seconds=0.1)
    second, second_stats = synthesize_audio(resolved, chunk_seconds=0.37)
    assert np.array_equal(float_to_pcm16(first), float_to_pcm16(second))
    assert first_stats["sample_peak_linear"] == pytest.approx(0.9, abs=1e-6)
    assert first_stats["clipped_sample_count"] == 0
    assert second_stats["clipped_sample_count"] == 0
    assert np.max(np.abs(first[[0, -1]])) == 0.0


def test_fundamental_only_binaural_policy_leaves_shared_isochronic_stereo(audio_protocol):
    protocol = dict(audio_protocol)
    protocol["sample_rate_hz"] = 8000
    protocol["duration_seconds"] = 2.0
    protocol["synthesis"] = dict(audio_protocol["synthesis"])
    protocol["synthesis"]["carrier_hz"] = 440.0
    resolved = resolve_protocol(protocol)
    audio, _ = synthesize_audio(resolved)
    center = round((60 / 360) * 2.0 * 8000)
    assert audio[center, 0] == pytest.approx(audio[center, 1], abs=1e-7)
