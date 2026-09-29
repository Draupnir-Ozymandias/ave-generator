"""Deterministic explanatory video for AVE demo packages."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


BACKGROUND = (9, 13, 22)
PANEL = (18, 27, 42)
TEXT = (235, 241, 248)
MUTED = (156, 171, 189)
ACCENT = (79, 209, 197)
WARNING = (247, 181, 76)
LEFT = (78, 145, 255)
RIGHT = (255, 105, 160)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "Arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _write_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, font: Any, fill: Any, spacing: int = 8) -> int:
    approx = max(16, int(width / max(8, getattr(font, "size", 18) * 0.56)))
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=approx) or [""])
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line or "Ag", font=font)
        y += bbox[3] - bbox[1] + spacing
    return y


def _active_stage(resolved: dict[str, Any], t: float) -> dict[str, Any]:
    stages = resolved["declarations"]["audio_stages"]
    for stage in stages:
        if stage["start_seconds"] <= t < stage["end_seconds"]:
            return stage
    return stages[-1]


def _rate(stage: dict[str, Any], t: np.ndarray) -> np.ndarray:
    curve = stage.get("rate")
    if not curve:
        return np.zeros_like(t)
    if curve["kind"] == "constant":
            return np.full_like(t, float(curve["value_hz"]))
    duration = stage["end_seconds"] - stage["start_seconds"]
    progress = np.clip((t - stage["start_seconds"]) / duration, 0.0, 1.0)
    return float(curve["start_hz"]) + progress * (float(curve["end_hz"]) - float(curve["start_hz"]))


def _modulation_cycles(stage: dict[str, Any], t: np.ndarray) -> np.ndarray:
    """Integrate the declared rate curve; never approximate phase as f(t) * t."""
    local = np.clip(t - stage["start_seconds"], 0.0, stage["end_seconds"] - stage["start_seconds"])
    curve = stage["rate"]
    origin = float(stage.get("phase_origin_cycles", 0.0))
    if curve["kind"] == "constant":
        return origin + float(curve["value_hz"]) * local
    duration = stage["end_seconds"] - stage["start_seconds"]
    slope = (float(curve["end_hz"]) - float(curve["start_hz"])) / duration
    return origin + float(curve["start_hz"]) * local + 0.5 * slope * local * local


def _draw_live_panel(draw: ImageDraw.ImageDraw, resolved: dict[str, Any], t: float, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    stage = _active_stage(resolved, t)
    draw.rounded_rectangle(box, radius=18, fill=PANEL)
    draw.text((x0 + 25, y0 + 20), f"LIVE CONSTRUCTION · {stage['stage_id']}", font=_font(20, True), fill=ACCENT)
    draw.text((x0 + 25, y0 + 53), stage["kind"].replace("_", " ").upper(), font=_font(32, True), fill=TEXT)

    graph = (x0 + 35, y0 + 115, x1 - 35, y1 - 55)
    gx0, gy0, gx1, gy1 = graph
    mid = (gy0 + gy1) / 2
    draw.line((gx0, mid, gx1, mid), fill=(65, 78, 96), width=2)
    count = max(200, gx1 - gx0)
    local_duration = min(0.04, max(0.01, stage["end_seconds"] - stage["start_seconds"]))
    times = np.linspace(t, t + local_duration, count)
    stage_local = times - stage["start_seconds"]

    if stage["kind"] == "binaural":
        left = np.sin(2 * math.pi * float(stage["left_hz"]) * stage_local)
        right = np.sin(2 * math.pi * float(stage["right_hz"]) * stage_local)
        scale = (gy1 - gy0) * 0.20
        xs = np.linspace(gx0, gx1, count)
        draw.line(list(zip(xs, mid - scale + left * scale * 0.7)), fill=LEFT, width=2)
        draw.line(list(zip(xs, mid + scale + right * scale * 0.7)), fill=RIGHT, width=2)
        detail = f"Left {stage['left_hz']:.1f} Hz  ·  Right {stage['right_hz']:.1f} Hz  ·  Difference {abs(stage['right_hz'] - stage['left_hz']):.1f} Hz"
    elif stage["kind"] == "smooth_am":
        modulation_cycles = _modulation_cycles(stage, times)
        envelope = 1.0 - float(stage["depth"]) + float(stage["depth"]) * (0.5 + 0.5 * np.sin(2 * math.pi * modulation_cycles))
        carrier = np.sin(2 * math.pi * float(stage["carrier_hz"]) * stage_local)
        signal = envelope * carrier
        xs = np.linspace(gx0, gx1, count)
        scale = (gy1 - gy0) * 0.38
        draw.line(list(zip(xs, mid + signal * scale)), fill=ACCENT, width=2)
        detail = f"{stage['carrier_hz']:.1f} Hz carrier · smooth sine envelope · no hard gate"
    elif stage["kind"] == "gated_pulse":
        phase = np.mod(_modulation_cycles(stage, times), 1.0)
        gate = (phase < float(stage["duty_cycle"])).astype(float)
        carrier = np.sin(2 * math.pi * float(stage["carrier_hz"]) * stage_local)
        xs = np.linspace(gx0, gx1, count)
        scale = (gy1 - gy0) * 0.38
        draw.line(list(zip(xs, mid + gate * carrier * scale)), fill=WARNING, width=2)
        detail = f"{stage['carrier_hz']:.1f} Hz carrier · hard gate · {stage['duty_cycle'] * 100:.0f}% duty"
    else:
        detail = "Silence stage; visual schedule is resolved separately."
    draw.text((gx0, y1 - 35), detail, font=_font(17), fill=MUTED)


def _card_for_time(t: float, duration: float) -> str:
    position = t / duration
    if position < 0.15:
        return "title"
    if position < 0.30:
        return "construction"
    if position < 0.68:
        return "live"
    if position < 0.80:
        return "verification"
    if position < 0.92:
        return "boundary"
    return "provenance"


def render_presentation_video(path: Path, recipe: dict[str, Any], resolved: dict[str, Any], git_version: str, size: tuple[int, int] = (960, 540)) -> None:
    """Render silent explanatory frames. Audio muxing is a packaging concern."""
    width, height = size
    fps = int(resolved["fps"])
    duration = float(resolved["duration_seconds"])
    label = recipe["verification"]["evidence_maturity"]
    writer = imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        macro_block_size=None,
        ffmpeg_log_level="error",
        output_params=["-pix_fmt", "yuv420p", "-metadata", "creation_time=1970-01-01T00:00:00Z"],
    )
    try:
        for frame_index in range(int(resolved["frame_count"])):
            t = frame_index / fps
            card = _card_for_time(t, duration)
            image = Image.new("RGB", size, BACKGROUND)
            draw = ImageDraw.Draw(image)
            draw.text((42, 28), "AVE ENGINEERING DEMO", font=_font(17, True), fill=ACCENT)
            badge_color = ACCENT if label == "verified" else WARNING
            badge = label.upper()
            badge_box = draw.textbbox((0, 0), badge, font=_font(16, True))
            badge_width = badge_box[2] - badge_box[0] + 28
            draw.rounded_rectangle((width - 42 - badge_width, 22, width - 42, 58), radius=13, outline=badge_color, width=2)
            draw.text((width - 28 - badge_width, 31), badge, font=_font(16, True), fill=badge_color)

            if card == "title":
                y = _write_wrapped(draw, recipe["title"], (52, 145), width - 104, _font(44, True), TEXT, 12)
                y = _write_wrapped(draw, recipe["purpose"], (54, y + 22), width - 108, _font(22), MUTED)
                draw.text((54, min(y + 22, height - 80)), f"{recipe['demo_id']}@{recipe['demo_version']}", font=_font(17), fill=ACCENT)
            elif card == "construction":
                draw.text((52, 112), "DECLARED CONSTRUCTION", font=_font(34, True), fill=TEXT)
                lines = []
                for stage in resolved["declarations"]["audio_stages"]:
                    if stage["kind"] == "binaural":
                        lines.append(f"{stage['stage_id']}: separate {stage['left_hz']:.1f} / {stage['right_hz']:.1f} Hz channels")
                    elif stage["kind"] == "smooth_am":
                        lines.append(f"{stage['stage_id']}: smooth sine amplitude envelope")
                    elif stage["kind"] == "gated_pulse":
                        lines.append(f"{stage['stage_id']}: hard gate at {stage['duty_cycle'] * 100:.0f}% duty")
                    else:
                        lines.append(f"{stage['stage_id']}: silence")
                _write_wrapped(draw, "\n".join(lines), (55, 190), width - 110, _font(24), MUTED, 14)
                draw.text((55, height - 70), "Declaration ≠ independent observation", font=_font(20, True), fill=WARNING)
            elif card == "live":
                _draw_live_panel(draw, resolved, t, (42, 82, width - 42, height - 68))
            elif card == "verification":
                draw.text((52, 112), "VERIFICATION STATE", font=_font(34, True), fill=TEXT)
                body = f"Evidence maturity: {label.upper()}\n\nGenerator build checks are attached. Independent AVE Forensics observations and field-level agreement remain separate records."
                _write_wrapped(draw, body, (55, 185), width - 110, _font(24), MUTED, 13)
            elif card == "boundary":
                draw.text((52, 105), "BOUNDARIES", font=_font(34, True), fill=WARNING)
                _write_wrapped(draw, "Engineering demonstration only. Use headphones only if appropriate for the declared stereo construction. Stop if uncomfortable. No calibrated sound level, neurological entrainment, therapeutic outcome, or safety claim.", (55, 178), width - 110, _font(23), TEXT, 12)
            else:
                draw.text((52, 105), "REPRODUCIBLE PROVENANCE", font=_font(34, True), fill=TEXT)
                details = f"Declaration\n{recipe['demo_id']}@{recipe['demo_version']}\n\nRecipe SHA-256\n{resolved['recipe_canonical_sha256']}\n\nResolved plan SHA-256\n{resolved['resolved_plan_sha256']}\n\nGenerator Git\n{git_version}"
                _write_wrapped(draw, details, (55, 165), width - 110, _font(19), MUTED, 8)

            progress = max(2, int((frame_index + 1) / resolved["frame_count"] * (width - 84)))
            draw.rectangle((42, height - 24, width - 42, height - 18), fill=(37, 50, 67))
            draw.rectangle((42, height - 24, 42 + progress, height - 18), fill=ACCENT)
            writer.append_data(np.asarray(image))
    finally:
        writer.close()
