import numpy as np

from ave_demo_generator.multimodal import audio_reactive_frame, frame_channel_rms


def test_frame_channel_rms_uses_exact_frame_sample_interval():
    sample_rate = 120
    fps = 60
    audio = np.asarray(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 0.5],
            [0.0, 0.5],
        ],
        dtype=np.float32,
    )
    assert frame_channel_rms(audio, sample_rate, fps, 0) == (1.0, 0.0)
    assert frame_channel_rms(audio, sample_rate, fps, 1) == (0.0, 0.5)


def test_audio_reactive_frame_is_black_at_zero_and_contains_no_text_layer():
    black = np.asarray(audio_reactive_frame(0.0, 0.0, size=(320, 180)))
    active = np.asarray(audio_reactive_frame(0.5, 0.25, size=(320, 180)))
    assert np.count_nonzero(black) == 0
    assert np.count_nonzero(active) > 0
    assert set(map(tuple, np.unique(active.reshape(-1, 3), axis=0))) <= {
        (0, 0, 0),
        (48, 128, 255),
        (255, 72, 152),
    }
