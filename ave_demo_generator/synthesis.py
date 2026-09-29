import numpy as np

from ave_audio_generator.synthesis import PhaseAccumulator, float_to_pcm16


def curve_values(curve: dict, progress: np.ndarray) -> np.ndarray:
    if curve["kind"] == "constant":
        return np.full(len(progress), curve["value_hz"], dtype=np.float64)
    return curve["start_hz"] + (curve["end_hz"] - curve["start_hz"]) * progress


def _edge_fade(length: int, sample_rate: int, seconds: float) -> np.ndarray:
    envelope = np.ones(length, dtype=np.float64)
    count = min(round(seconds * sample_rate), length // 2)
    if count:
        ramp = np.linspace(0.0, 1.0, count, endpoint=False)
        envelope[:count] = ramp
        envelope[-count:] = ramp[::-1]
    return envelope


def synthesize_demo(resolved: dict) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
    recipe = resolved["recipe"]
    sample_rate = recipe["sample_rate_hz"]
    sample_count = resolved["sample_count"]
    audio = np.zeros((sample_count, 2), dtype=np.float64)
    stems: dict[str, np.ndarray] = {}
    stage_summaries: list[dict] = []

    for stage in recipe["audio"]["stages"]:
        start = round(stage["start_seconds"] * sample_rate)
        end = round(stage["end_seconds"] * sample_rate)
        length = end - start
        stage_audio = np.zeros((length, 2), dtype=np.float64)
        progress = np.arange(length, dtype=np.float64) / max(length, 1)
        origin = stage.get("phase_origin_cycles", 0.0)
        summary = {"stage_id": stage["stage_id"], "kind": stage["kind"], "sample_start": start, "sample_end": end}

        if stage["kind"] == "binaural":
            left_phase = PhaseAccumulator(origin).render(np.full(length, stage["left_hz"]), sample_rate)
            right_phase = PhaseAccumulator(origin).render(np.full(length, stage["right_hz"]), sample_rate)
            stage_audio[:, 0] = stage["amplitude"] * np.sin(2 * np.pi * left_phase)
            stage_audio[:, 1] = stage["amplitude"] * np.sin(2 * np.pi * right_phase)
            summary.update({"left_hz": stage["left_hz"], "right_hz": stage["right_hz"], "difference_hz": abs(stage["right_hz"] - stage["left_hz"])})
        elif stage["kind"] in {"smooth_am", "gated_pulse"}:
            carrier_phase = PhaseAccumulator(origin).render(np.full(length, stage["carrier_hz"]), sample_rate)
            rate = curve_values(stage["rate"], progress)
            modulation_phase = PhaseAccumulator(origin).render(rate, sample_rate)
            carrier = np.sin(2 * np.pi * carrier_phase)
            if stage["kind"] == "smooth_am":
                envelope = (1.0 - stage["depth"]) + stage["depth"] * 0.5 * (1.0 + np.sin(2 * np.pi * modulation_phase))
                summary.update({"envelope_shape": "sine", "rate_start_hz": float(rate[0]), "rate_end_hz": float(rate[-1]), "depth": stage["depth"]})
            else:
                envelope = ((modulation_phase % 1.0) < stage["duty_cycle"]).astype(np.float64)
                summary.update({"edge_shape": "hard", "rate_start_hz": float(rate[0]), "rate_end_hz": float(rate[-1]), "duty_cycle": stage["duty_cycle"]})
            mono = stage["amplitude"] * carrier * envelope
            stage_audio[:, 0] = mono
            stage_audio[:, 1] = mono
            summary["carrier_hz"] = stage["carrier_hz"]
        elif stage["kind"] != "silence":
            raise ValueError(f"unsupported stage kind: {stage['kind']}")

        if len(recipe["audio"]["stages"]) > 1:
            stage_audio *= _edge_fade(length, sample_rate, recipe["audio"]["stage_fade_seconds"])[:, None]
        audio[start:end] = stage_audio
        full_stem = np.zeros_like(audio)
        full_stem[start:end] = stage_audio
        stems[stage["stage_id"]] = full_stem
        stage_summaries.append(summary)

    audio *= _edge_fade(sample_count, sample_rate, recipe["audio"]["master_fade_seconds"])[:, None]
    for name in stems:
        stems[name] *= _edge_fade(sample_count, sample_rate, recipe["audio"]["master_fade_seconds"])[:, None]
    raw_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    gain = recipe["audio"]["peak_linear"] / raw_peak if raw_peak else 1.0
    audio *= gain
    for name in stems:
        stems[name] *= gain
    stats = {
        "raw_peak_linear": raw_peak,
        "applied_gain_linear": gain,
        "sample_peak_linear": float(np.max(np.abs(audio))) if audio.size else 0.0,
        "clipped_sample_count": int(np.count_nonzero(np.abs(audio) > 1.0)),
        "channel_rms_dbfs": [
            float(20 * np.log10(max(float(np.sqrt(np.mean(audio[:, channel] ** 2))), 1e-12)))
            for channel in range(2)
        ],
        "stages": stage_summaries,
    }
    return audio.astype(np.float32), {name: value.astype(np.float32) for name, value in stems.items()}, stats


__all__ = ["float_to_pcm16", "synthesize_demo", "curve_values"]
