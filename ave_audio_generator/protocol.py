from copy import deepcopy

from ave_light_renderer.canonical import canonical_sha256

from . import __version__
from .validation import validate_protocol


def smoothstep(value, edge0: float, edge1: float):
    import numpy as np

    normalized = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return normalized * normalized * (3.0 - 2.0 * normalized)


def resolve_protocol(protocol: dict, duration_seconds: float | None = None) -> dict:
    requested = validate_protocol(protocol)
    resolved = deepcopy(requested)
    if duration_seconds is not None:
        if duration_seconds <= 0:
            raise ValueError("duration override must be positive")
        resolved["duration_seconds"] = float(duration_seconds)
        validate_protocol(resolved)

    synthesis = resolved["synthesis"]
    sweep = synthesis["sweep"]
    duration = resolved["duration_seconds"]
    span = sweep["end_hz"] - sweep["start_hz"]

    def time_for_frequency(frequency_hz: float) -> float:
        return duration * (frequency_hz - sweep["start_hz"]) / span

    transition_times = {}
    for name, band in synthesis["transition_bands_hz"].items():
        transition_times[name] = {
            "start_seconds": time_for_frequency(band[0]),
            "end_seconds": time_for_frequency(band[1]),
        }

    resolved_document = {
        "resolved_protocol_version": "1.0.0",
        "generator_version": __version__,
        "requested_protocol_sha256": canonical_sha256(requested),
        "protocol": resolved,
        "sample_count": round(duration * resolved["sample_rate_hz"]),
        "transition_times": transition_times,
        "phase_model": {
            "method": "exclusive_discrete_frequency_accumulation",
            "equation": "phase[n] = phase[0] + sum(f[k] / sample_rate, k=0..n-1)",
            "time_varying_frequency_times_time_used": False,
        },
        "visual_timeline": {
            "clock": "same monotonic zero-origin protocol clock",
            "sweep_start_hz": sweep["start_hz"],
            "sweep_end_hz": sweep["end_hz"],
            "duration_seconds": duration,
        },
    }
    resolved_document["resolved_protocol_sha256"] = canonical_sha256(resolved_document)
    return resolved_document


def sweep_frequency(resolved: dict, times):
    protocol = resolved["protocol"]
    sweep = protocol["synthesis"]["sweep"]
    return sweep["start_hz"] + (sweep["end_hz"] - sweep["start_hz"]) * (
        times / protocol["duration_seconds"]
    )


def accumulated_sweep_cycles(resolved: dict, times):
    protocol = resolved["protocol"]
    sweep = protocol["synthesis"]["sweep"]
    duration = protocol["duration_seconds"]
    slope = (sweep["end_hz"] - sweep["start_hz"]) / duration
    return sweep["start_hz"] * times + 0.5 * slope * times * times

