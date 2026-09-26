from pathlib import Path


def _layout(size: int, gutter: int) -> dict[str, tuple[int, int, int, int]]:
    if size < 32:
        raise ValueError("render size must be at least 32 pixels")
    if gutter < 1 or gutter * 3 >= size:
        raise ValueError("gutter is incompatible with render size")
    half = size // 2
    return {
        "top_left": (0, 0, half - gutter, half - gutter),
        "top_right": (half + gutter, 0, size, half - gutter),
        "bottom_left": (0, half + gutter, half - gutter, size),
        "bottom_right": (half + gutter, half + gutter, size, size),
    }


def frame_image(frame: dict, size: int = 480, gutter: int = 4):
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required for offline rendering") from exc

    image = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for region_name, bounds in _layout(size, gutter).items():
        draw.rectangle(bounds, fill=tuple(frame["regions"][region_name]["effective_rgb"]))
    return image


def render_image_sequence(
    plan: dict,
    output_dir: str | Path,
    size: int = 480,
    gutter: int = 4,
) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for frame in plan["frames"]:
        path = target / f"frame-{frame['frame_index']:06d}.png"
        frame_image(frame, size=size, gutter=gutter).save(path, format="PNG", optimize=False)
        paths.append(path)
    return paths


def render_mp4(
    plan: dict,
    output_path: str | Path,
    size: int = 480,
    gutter: int = 4,
) -> Path:
    try:
        import imageio.v2 as imageio
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("imageio and numpy are required for MP4 rendering") from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        path,
        fps=plan["refresh_hz"],
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=None,
        ffmpeg_log_level="error",
        output_params=["-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z"],
    )
    try:
        for frame in plan["frames"]:
            writer.append_data(np.asarray(frame_image(frame, size=size, gutter=gutter)))
    finally:
        writer.close()
    return path

