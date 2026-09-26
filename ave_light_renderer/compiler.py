import math
from fractions import Fraction
from typing import Any

from . import __version__
from .canonical import canonical_sha256
from .validation import REGION_NAMES, validate_recipe, validate_refresh_rate


def _fraction(value: int | float) -> Fraction:
    return Fraction(str(value))


def _curve_value(curve: dict, progress: Fraction) -> Fraction:
    if curve["kind"] == "constant":
        return _fraction(curve["value"])
    start = _fraction(curve["start"])
    end = _fraction(curve["end"])
    return start + (end - start) * progress


def _curve_integral(curve: dict, p0: Fraction, p1: Fraction, duration_seconds: Fraction) -> Fraction:
    if curve["kind"] == "constant":
        return _fraction(curve["value"]) * (p1 - p0) * duration_seconds
    start = _fraction(curve["start"])
    end = _fraction(curve["end"])
    slope = end - start
    normalized_integral = start * (p1 - p0) + slope * (p1 * p1 - p0 * p0) / 2
    return normalized_integral * duration_seconds


def _interval_at(intervals: list[dict], time_us: Fraction, duration_us: int) -> tuple[int, dict]:
    if time_us >= duration_us:
        return len(intervals) - 1, intervals[-1]
    for index, interval in enumerate(intervals):
        if interval["start_us"] <= time_us < interval["end_us"]:
            return index, interval
    raise AssertionError(f"validated timeline has no interval at {float(time_us)} us")


def _to_rgb(color: dict) -> list[int]:
    if color["mode"] == "rgb":
        return list(color["value"])
    value = color["value"]
    return [value, value, value]


def _round_float(value: Fraction | float, places: int = 12) -> float:
    return round(float(value), places)


class _RegionPhase:
    def __init__(self, intervals: list[dict]):
        self.intervals = intervals
        self.phase = Fraction(0)
        self.initialized = False
        self.current_index: int | None = None
        self.time_us = Fraction(0)

    def _enter(self, index: int, interval: dict) -> None:
        if index == self.current_index:
            return
        self.current_index = index
        if interval["kind"] != "pulse":
            return
        origin = _fraction(interval["phase_origin_cycles"])
        if interval["phase_policy"] == "reset" or not self.initialized:
            self.phase = origin
            self.initialized = True

    def advance_to(self, target_us: Fraction, duration_us: int) -> None:
        cursor = self.time_us
        while cursor < target_us:
            index, interval = _interval_at(self.intervals, cursor, duration_us)
            self._enter(index, interval)
            boundary = min(Fraction(interval["end_us"]), target_us)
            if interval["kind"] == "pulse":
                segment_duration_us = Fraction(interval["end_us"] - interval["start_us"])
                p0 = (cursor - interval["start_us"]) / segment_duration_us
                p1 = (boundary - interval["start_us"]) / segment_duration_us
                self.phase += _curve_integral(
                    interval["frequency_hz"],
                    p0,
                    p1,
                    segment_duration_us / 1_000_000,
                )
            cursor = boundary
            if cursor < target_us:
                next_index, next_interval = _interval_at(self.intervals, cursor, duration_us)
                self._enter(next_index, next_interval)
        self.time_us = target_us
        index, interval = _interval_at(self.intervals, target_us, duration_us)
        self._enter(index, interval)

    def frame_state(self, time_us: Fraction, duration_us: int) -> dict:
        index, interval = _interval_at(self.intervals, time_us, duration_us)
        self._enter(index, interval)
        phase_cycles = self.phase % 1
        if interval["kind"] == "off":
            return {
                "interval_id": interval["interval_id"],
                "kind": "off",
                "active": False,
                "frequency_hz": 0.0,
                "duty_cycle": 0.0,
                "intensity": 0.0,
                "phase_cycles": _round_float(phase_cycles),
                "gate_on": False,
                "effective_rgb": [0, 0, 0],
            }

        duration = Fraction(interval["end_us"] - interval["start_us"])
        progress = (time_us - interval["start_us"]) / duration
        frequency = _curve_value(interval["frequency_hz"], progress)
        duty = _curve_value(interval["duty_cycle"], progress)
        intensity = _curve_value(interval["intensity"], progress)
        gate_on = phase_cycles < duty
        base_rgb = _to_rgb(interval["color"])
        effective = [
            int(round(channel * float(intensity))) if gate_on else 0 for channel in base_rgb
        ]
        return {
            "interval_id": interval["interval_id"],
            "kind": "pulse",
            "active": True,
            "frequency_hz": _round_float(frequency),
            "duty_cycle": _round_float(duty),
            "intensity": _round_float(intensity),
            "phase_cycles": _round_float(phase_cycles),
            "gate_on": gate_on,
            "effective_rgb": effective,
        }


def _transition_table(recipe: dict, refresh_hz: int) -> tuple[list[dict], dict]:
    transitions: list[dict] = []
    errors_us: list[float] = []
    for region in recipe["regions"]:
        for interval in region["intervals"][1:]:
            requested_us = interval["start_us"]
            frame_index = math.ceil(requested_us * refresh_hz / 1_000_000)
            quantized_ns = round(frame_index * 1_000_000_000 / refresh_hz)
            error_us = quantized_ns / 1000 - requested_us
            errors_us.append(error_us)
            transitions.append(
                {
                    "region": region["name"],
                    "interval_id": interval["interval_id"],
                    "requested_us": requested_us,
                    "quantized_frame_index": frame_index,
                    "quantized_time_ns": quantized_ns,
                    "error_us": round(error_us, 6),
                }
            )
    max_abs = max((abs(value) for value in errors_us), default=0.0)
    rms = math.sqrt(sum(value * value for value in errors_us) / len(errors_us)) if errors_us else 0.0
    return transitions, {
        "transition_count": len(errors_us),
        "max_abs_us": round(max_abs, 6),
        "rms_us": round(rms, 6),
    }


def compile_recipe(recipe: dict, refresh_hz: int) -> dict:
    validate_recipe(recipe)
    validate_refresh_rate(refresh_hz)
    duration_us = recipe["duration_us"]
    frame_count = math.ceil(duration_us * refresh_hz / 1_000_000)
    region_map = {region["name"]: region for region in recipe["regions"]}
    phases = {
        name: _RegionPhase(region_map[name]["intervals"])
        for name in REGION_NAMES
    }
    frames: list[dict] = []
    for frame_index in range(frame_count):
        time_seconds = Fraction(frame_index, refresh_hz)
        time_us = time_seconds * 1_000_000
        regions: dict[str, dict] = {}
        for name in REGION_NAMES:
            phases[name].advance_to(time_us, duration_us)
            regions[name] = phases[name].frame_state(time_us, duration_us)
        frames.append(
            {
                "frame_index": frame_index,
                "scheduled_time_ns": round(frame_index * 1_000_000_000 / refresh_hz),
                "regions": regions,
            }
        )

    transitions, timing_summary = _transition_table(recipe, refresh_hz)
    recipe_hash = canonical_sha256(recipe)
    plan = {
        "plan_version": "1.0.0",
        "renderer_version": __version__,
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe_hash,
        "source": recipe["source"],
        "duration_us": duration_us,
        "refresh_hz": refresh_hz,
        "frame_count": frame_count,
        "region_order": list(REGION_NAMES),
        "transitions": transitions,
        "timing_error_summary_us": timing_summary,
        "warnings": [
            "Offline software preview only; intensity is not calibrated luminance.",
            "Frame timing is quantized to the requested virtual refresh rate.",
        ],
        "frames": frames,
    }
    plan["resolved_plan_sha256"] = canonical_sha256(plan)
    return plan


def plan_summary(plan: dict) -> dict:
    return {
        "recipe_id": plan["recipe_id"],
        "recipe_sha256": plan["recipe_sha256"],
        "resolved_plan_sha256": plan["resolved_plan_sha256"],
        "refresh_hz": plan["refresh_hz"],
        "duration_us": plan["duration_us"],
        "frame_count": plan["frame_count"],
        "timing_error_summary_us": plan["timing_error_summary_us"],
        "warnings": plan["warnings"],
    }

