import numpy as np

from tools.render_audio_white_strobe import pulse_linked_gain, encoded_gate_gain


def test_smooth_am_uses_integrated_phase_and_stays_in_declared_range():
    intervals = [{'kind': 'off', 'start_us': 0, 'end_us': 1_000_000},
                 {'kind': 'pulse', 'start_us': 1_000_000, 'end_us': 3_000_000,
                  'frequency_hz': {'kind': 'linear', 'start': 2, 'end': 6}}]
    t = np.array([0., 1., 1.5, 2., 3.])
    gain = pulse_linked_gain(t, intervals)
    assert gain[0] == gain[1] == gain[3] == gain[4] == 1
    assert np.isclose(gain[2], .85)
    assert np.all((gain >= .70) & (gain <= 1))


def test_encoded_gate_smoothing_is_chunk_independent_and_bounded():
    rate = 48000
    gate = np.zeros(36000)
    gate[239:241] = 1
    t = np.arange(rate, 3 * rate) / rate
    whole = encoded_gate_gain(t, gate, rate)
    chunked = np.concatenate([encoded_gate_gain(t[:rate], gate, rate), encoded_gate_gain(t[rate:], gate, rate)])
    assert np.allclose(whole, chunked, atol=1e-12)
    assert whole.max() > .99
    assert whole.min() >= .70
