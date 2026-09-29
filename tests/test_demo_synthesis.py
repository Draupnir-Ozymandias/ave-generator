import numpy as np

from ave_demo_generator.compiler import resolve_demo
from ave_demo_generator.paths import DEMO_RECIPE_DIR
from ave_demo_generator.synthesis import curve_values, synthesize_demo
from ave_demo_generator.presentation import _modulation_cycles
from ave_light_renderer.canonical import load_json


def _resolve(name: str):
    path = DEMO_RECIPE_DIR / name
    return resolve_demo(load_json(path), str(path))


def _peak(signal: np.ndarray, rate: int) -> float:
    windowed = signal * np.hanning(len(signal))
    index = int(np.argmax(np.abs(np.fft.rfft(windowed))))
    return index * rate / len(signal)


def test_binaural_channels_and_difference_are_rendered_deterministically():
    resolved = _resolve("ave-demo-001-binaural-construction.json")
    first, stems, _ = synthesize_demo(resolved)
    second, _, _ = synthesize_demo(resolved)
    assert first.tobytes() == second.tobytes()
    assert set(stems) == {"binaural-10hz"}
    rate = resolved["sample_rate_hz"]
    probe = first[rate : -rate]
    left = _peak(probe[:, 0], rate)
    right = _peak(probe[:, 1], rate)
    assert abs(left - 440.0) < 0.2
    assert abs(right - 450.0) < 0.2
    assert abs((right - left) - 10.0) < 0.2


def test_linear_rate_curve_has_requested_endpoints():
    curve = {"kind": "linear", "start_hz": 4.0, "end_hz": 20.0}
    values = curve_values(curve, np.asarray([0.0, 0.5, 1.0]))
    assert np.allclose(values, [4.0, 12.0, 20.0])


def test_presentation_phase_integrates_linear_rate_instead_of_multiplying_rate_by_time():
    stage = {
        "start_seconds": 0.0,
        "end_seconds": 10.0,
        "rate": {"kind": "linear", "start_hz": 4.0, "end_hz": 20.0},
        "phase_origin_cycles": 0.0,
    }
    cycles = _modulation_cycles(stage, np.asarray([0.0, 5.0, 10.0]))
    assert np.allclose(cycles, [0.0, 40.0, 120.0])
    assert cycles[1] != 12.0 * 5.0


def test_smooth_am_is_not_a_hard_gate_and_gated_pulse_has_off_samples():
    smooth, _, _ = synthesize_demo(_resolve("ave-demo-002-smooth-am-ramp.json"))
    gated, _, _ = synthesize_demo(_resolve("ave-demo-003-gated-pulse-contrast.json"))
    interior = slice(5000, -5000)
    smooth_zero_fraction = np.mean(smooth[interior, 0] == 0.0)
    gated_zero_fraction = np.mean(gated[interior, 0] == 0.0)
    assert smooth_zero_fraction < 0.01
    assert gated_zero_fraction > 0.65
    assert np.array_equal(gated[:, 0], gated[:, 1])


def test_staged_stems_are_isolated_and_sum_to_mix():
    resolved = _resolve("ave-demo-005-staged-av-comparison.json")
    audio, stems, _ = synthesize_demo(resolved)
    combined = np.sum(np.stack(list(stems.values())), axis=0)
    assert np.allclose(combined, audio, atol=1e-7)
    for stage, stem in zip(resolved["declarations"]["audio_stages"], stems.values()):
        start = round(stage["start_seconds"] * resolved["sample_rate_hz"])
        end = round(stage["end_seconds"] * resolved["sample_rate_hz"])
        assert not np.any(stem[:start])
        assert not np.any(stem[end:])
