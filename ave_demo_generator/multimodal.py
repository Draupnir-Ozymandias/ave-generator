"""Target-free audiovisual detector artifacts for blind clock analysis."""

from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw


def frame_channel_rms(
    audio: np.ndarray,
    sample_rate_hz: int,
    fps: int,
    frame_index: int,
) -> tuple[float, float]:
    """Measure channel energy over the exact sample interval for one video frame."""
    start = round(frame_index * sample_rate_hz / fps)
    end = round((frame_index + 1) * sample_rate_hz / fps)
    frame_audio = audio[start:end]
    if len(frame_audio) == 0:
        return 0.0, 0.0
    rms = np.sqrt(np.mean(np.square(frame_audio, dtype=np.float64), axis=0))
    return float(rms[0]), float(rms[1])


def audio_reactive_frame(
    left_rms: float,
    right_rms: float,
    size: tuple[int, int] = (640, 360),
) -> Image.Image:
    """Encode channel energy without text, target values, or construction labels."""
    width, height = size
    image = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(8, width // 32)
    gap = max(8, height // 24)
    usable_width = width - 2 * margin
    bar_height = (height - 2 * margin - gap) // 2
    left_width = round(usable_width * min(max(left_rms, 0.0), 1.0))
    right_width = round(usable_width * min(max(right_rms, 0.0), 1.0))
    if left_width:
        draw.rectangle(
            (margin, margin, margin + left_width - 1, margin + bar_height - 1),
            fill=(48, 128, 255),
        )
    right_top = margin + bar_height + gap
    if right_width:
        draw.rectangle(
            (margin, right_top, margin + right_width - 1, right_top + bar_height - 1),
            fill=(255, 72, 152),
        )
    return image


def render_audio_reactive_detector_video(
    path: str | Path,
    audio: np.ndarray,
    sample_rate_hz: int,
    fps: int,
    size: tuple[int, int] = (640, 360),
) -> Path:
    """Render an unlabeled virtual-clock video derived only from rendered audio."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame_count = round(len(audio) / sample_rate_hz * fps)
    writer = imageio.get_writer(
        target,
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=None,
        ffmpeg_log_level="error",
        output_params=[
            "-movflags",
            "+faststart",
            "-metadata",
            "creation_time=1970-01-01T00:00:00Z",
        ],
    )
    try:
        for frame_index in range(frame_count):
            levels = frame_channel_rms(audio, sample_rate_hz, fps, frame_index)
            writer.append_data(np.asarray(audio_reactive_frame(*levels, size=size)))
    finally:
        writer.close()
    return target
