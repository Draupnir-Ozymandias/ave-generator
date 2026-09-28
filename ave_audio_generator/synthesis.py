from dataclasses import dataclass

import numpy as np

from .protocol import smoothstep, sweep_frequency


@dataclass
class PhaseAccumulator:
    cycles: float = 0.0

    def render(self, frequency_hz: np.ndarray, sample_rate_hz: int) -> np.ndarray:
        increments = np.asarray(frequency_hz, dtype=np.float64) / sample_rate_hz
        phases = np.empty_like(increments)
        if len(increments):
            phases[0] = self.cycles
            if len(increments) > 1:
                phases[1:] = self.cycles + np.cumsum(increments[:-1], dtype=np.float64)
            self.cycles = float(self.cycles + np.sum(increments, dtype=np.float64))
        return phases


def _fade_envelope(indices: np.ndarray, sample_count: int, fade_samples: int) -> np.ndarray:
    envelope = np.ones(len(indices), dtype=np.float64)
    if fade_samples <= 0:
        return envelope
    fade_in = np.clip(indices / fade_samples, 0.0, 1.0)
    fade_out = np.clip((sample_count - 1 - indices) / fade_samples, 0.0, 1.0)
    return envelope * np.minimum(fade_in, fade_out)


def synthesize_audio(resolved: dict, chunk_seconds: float = 1.0) -> tuple[np.ndarray, dict]:
    protocol = resolved["protocol"]
    sample_rate = protocol["sample_rate_hz"]
    sample_count = resolved["sample_count"]
    synthesis = protocol["synthesis"]
    carrier_hz = synthesis["carrier_hz"]
    chunk_samples = max(1, round(chunk_seconds * sample_rate))
    fade_samples = round(protocol["output"]["fade_seconds"] * sample_rate)
    output = np.empty((sample_count, 2), dtype=np.float32)

    shared_carrier = PhaseAccumulator()
    right_fundamental = PhaseAccumulator()
    isochronic_modulator = PhaseAccumulator()
    harmonic_modulator = PhaseAccumulator()
    raw_peak = 0.0

    transition = synthesis["transition_bands_hz"]
    binaural_limit = synthesis["binaural"]["max_difference_hz"]
    iso_min, iso_max = synthesis["isochronic_frequency_range_hz"]
    harmonics = synthesis["harmonics"]

    for start in range(0, sample_count, chunk_samples):
        end = min(sample_count, start + chunk_samples)
        indices = np.arange(start, end, dtype=np.int64)
        times = indices.astype(np.float64) / sample_rate
        sweep = sweep_frequency(resolved, times)

        shared_phase = shared_carrier.render(np.full(len(indices), carrier_hz), sample_rate)
        right_phase = right_fundamental.render(
            carrier_hz + np.minimum(sweep, binaural_limit), sample_rate
        )
        iso_phase = isochronic_modulator.render(np.clip(sweep, iso_min, iso_max), sample_rate)
        harmonic_phase = harmonic_modulator.render(sweep, sample_rate)

        shared_organ = np.zeros(len(indices), dtype=np.float64)
        shared_harmonics = np.zeros(len(indices), dtype=np.float64)
        for partial in harmonics:
            wave = partial["amplitude"] * np.sin(2 * np.pi * partial["multiple"] * shared_phase)
            shared_organ += wave
            if partial["multiple"] != 1:
                shared_harmonics += wave

        left_binaural = shared_organ
        fundamental_amplitude = next(
            item["amplitude"] for item in harmonics if item["multiple"] == 1
        )
        right_binaural = (
            fundamental_amplitude * np.sin(2 * np.pi * right_phase) + shared_harmonics
        )
        iso_pulse = 0.5 * (1.0 + np.sin(2 * np.pi * iso_phase))
        harmonic_pulse = 0.5 * (1.0 + np.sin(2 * np.pi * harmonic_phase))
        isochronic = shared_organ * iso_pulse
        harmonic = shared_organ * harmonic_pulse

        w12 = smoothstep(sweep, *transition["binaural_to_isochronic"])
        w23 = smoothstep(sweep, *transition["isochronic_to_harmonic"])
        w1 = 1.0 - w12
        w2 = w12 * (1.0 - w23)
        w3 = w23
        norm = w1 + w2 + w3
        w1, w2, w3 = w1 / norm, w2 / norm, w3 / norm

        fade = _fade_envelope(indices, sample_count, fade_samples)
        left = (w1 * left_binaural + w2 * isochronic + w3 * harmonic) * fade
        right = (w1 * right_binaural + w2 * isochronic + w3 * harmonic) * fade
        chunk = np.column_stack((left, right))
        output[start:end] = chunk.astype(np.float32)
        raw_peak = max(raw_peak, float(np.max(np.abs(chunk))))

    if raw_peak <= 0:
        raise ValueError("synthesis produced silence")
    peak_target = protocol["output"]["peak_linear"]
    gain = peak_target / raw_peak
    output *= gain
    measured_peak = float(np.max(np.abs(output)))
    rms = np.sqrt(np.mean(np.square(output, dtype=np.float64), axis=0))
    stats = {
        "raw_peak_linear": raw_peak,
        "applied_gain_linear": gain,
        "sample_peak_linear": measured_peak,
        "channel_rms_linear": [float(value) for value in rms],
        "channel_rms_dbfs": [float(20 * np.log10(max(value, 1e-12))) for value in rms],
        "clipped_sample_count": int(np.count_nonzero(np.abs(output) > 1.0)),
    }
    return output, stats


def float_to_pcm16(audio: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
