from tools.render_four_region_vibrant import pulse_cycle_index, highlighted_rgb


def test_clockwise_cycle_uses_integral_for_ramp():
    intervals = [{'kind': 'pulse', 'start_us': 0, 'end_us': 2_000_000,
                  'frequency_hz': {'kind': 'linear', 'start': 2, 'end': 6}}]
    assert pulse_cycle_index(intervals, 1) == 3
    assert pulse_cycle_index(intervals, 2) == 8
    assert [i % 4 for i in range(4)] == [0, 1, 2, 3]


def test_highlight_lifts_tint_and_preserves_full_intensity_palette():
    assert highlighted_rgb([255, 80, 20], .45, False) == [255, 80, 20]
    assert highlighted_rgb([255, 80, 20], .45, True) == [255, 159, 126]
