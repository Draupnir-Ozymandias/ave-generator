from tools.render_single_square import square_state


def test_single_square_distinguishes_source_off_from_active_pulse_off():
    treatment = {'on_rgb': [0, 255, 0], 'off_rgb': [255, 0, 255], 'source_off_rgb': [0, 0, 0]}
    assert square_state({'kind': 'off', 'gate_on': False}, treatment) == ('source_off', [0, 0, 0])
    assert square_state({'kind': 'pulse', 'gate_on': True}, treatment) == ('pulse_on_green', [0, 255, 0])
    assert square_state({'kind': 'pulse', 'gate_on': False}, treatment) == ('pulse_off_magenta', [255, 0, 255])


def test_white_square_maps_active_and_source_off_to_black():
    treatment = {'on_rgb': [255, 255, 255], 'off_rgb': [0, 0, 0], 'source_off_rgb': [0, 0, 0],
                 'on_state': 'pulse_on_white', 'off_state': 'pulse_off_black'}
    assert square_state({'kind': 'pulse', 'gate_on': True}, treatment) == ('pulse_on_white', [255, 255, 255])
    assert square_state({'kind': 'pulse', 'gate_on': False}, treatment) == ('pulse_off_black', [0, 0, 0])
    assert square_state({'kind': 'off', 'gate_on': False}, treatment) == ('source_off', [0, 0, 0])
