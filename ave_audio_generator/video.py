import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .protocol import accumulated_sweep_cycles, sweep_frequency


def draw_yinyang(angle_degrees: float, size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, size, size), fill="white")
    draw.pieslice((0, 0, size, size), 90, 270, fill="black")
    draw.ellipse((size // 4, 0, size * 3 // 4, size // 2), fill="white")
    draw.ellipse((size // 4, size // 2, size * 3 // 4, size), fill="black")
    radius = size // 12
    draw.ellipse((size // 2 - radius, size // 4 - radius, size // 2 + radius, size // 4 + radius), fill="black")
    draw.ellipse((size // 2 - radius, size * 3 // 4 - radius, size // 2 + radius, size * 3 // 4 + radius), fill="white")
    return image.rotate(-angle_degrees)


def render_video(resolved: dict, path: str | Path, fps: int = 60, size: int = 512) -> Path:
    import imageio.v2 as imageio

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    duration = resolved["protocol"]["duration_seconds"]
    frame_count = round(duration * fps)
    writer = imageio.get_writer(
        target,
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=None,
        ffmpeg_log_level="error",
        output_params=["-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z"],
    )
    try:
        for frame_index in range(frame_count):
            time_seconds = frame_index / fps
            time_array = np.asarray([time_seconds])
            frequency = float(sweep_frequency(resolved, time_array)[0])
            angle = float(accumulated_sweep_cycles(resolved, time_array)[0] * 360.0)
            image = draw_yinyang(angle, size)
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), f"{frequency:.1f} Hz | {frequency * 60:.0f} RPM", fill="gold")
            writer.append_data(np.asarray(image))
    finally:
        writer.close()
    return target


def mux_av(video_path: str | Path, audio_path: str | Path, output_path: str | Path) -> Path:
    target = Path(output_path)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return target

