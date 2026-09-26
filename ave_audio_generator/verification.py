from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, hilbert, sosfiltfilt

from .errors import VerificationError


def _window(audio: np.ndarray, sample_rate: int, center: float, width: float) -> np.ndarray:
    start = max(0, round((center - width / 2) * sample_rate))
    end = min(len(audio), round((center + width / 2) * sample_rate))
    return audio[start:end]


def _bandpass(signal: np.ndarray, sample_rate: int, low: float, high: float) -> np.ndarray:
    sos = butter(4, [low, high], btype="bandpass", fs=sample_rate, output="sos")
    return sosfiltfilt(sos, signal)


def _spectral_peak(signal: np.ndarray, sample_rate: int, low: float, high: float) -> float:
    windowed = (signal - np.mean(signal)) * np.hanning(len(signal))
    spectrum = np.abs(np.fft.rfft(windowed))
    frequencies = np.fft.rfftfreq(len(windowed), 1 / sample_rate)
    mask = (frequencies >= low) & (frequencies <= high)
    selected = np.flatnonzero(mask)
    index = selected[int(np.argmax(spectrum[mask]))]
    if 0 < index < len(spectrum) - 1:
        alpha, beta, gamma = np.log(np.maximum(spectrum[index - 1:index + 2], 1e-20))
        denominator = alpha - 2 * beta + gamma
        offset = 0.5 * (alpha - gamma) / denominator if denominator else 0.0
    else:
        offset = 0.0
    return float((index + offset) * sample_rate / len(windowed))


def _envelope_peak(signal: np.ndarray, sample_rate: int, expected: float) -> float:
    carrier_band = _bandpass(signal, sample_rate, 350.0, 700.0)
    envelope = np.abs(hilbert(carrier_band))
    return _spectral_peak(envelope, sample_rate, max(1.0, expected - 25), expected + 25)


def verify_wav(path: str | Path, resolved: dict) -> dict:
    sample_rate, pcm = wavfile.read(path)
    protocol = resolved["protocol"]
    checks: list[dict] = []

    def record(name: str, passed: bool, measured, expected, tolerance=None) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "measured": measured,
                "expected": expected,
                "tolerance": tolerance,
            }
        )

    record("sample_rate_hz", sample_rate == protocol["sample_rate_hz"], sample_rate, protocol["sample_rate_hz"])
    record("channel_count", pcm.ndim == 2 and pcm.shape[1] == 2, pcm.shape[1] if pcm.ndim == 2 else 1, 2)
    record("sample_count", len(pcm) == resolved["sample_count"], len(pcm), resolved["sample_count"])
    if pcm.ndim != 2 or pcm.shape[1] != 2:
        raise VerificationError("verification requires stereo PCM")
    audio = pcm.astype(np.float64) / 32767.0
    peak = float(np.max(np.abs(audio)))
    peak_target = protocol["output"]["peak_linear"]
    record("headroom", peak <= peak_target + 1 / 32767, peak, peak_target, 1 / 32767)
    endpoint_peak = float(np.max(np.abs(audio[[0, -1]])))
    record("black_equivalent_audio_endpoints", endpoint_peak <= 1 / 32767, endpoint_peak, 0.0, 1 / 32767)

    duration = protocol["duration_seconds"]
    sweep_end = protocol["synthesis"]["sweep"]["end_hz"]
    carrier = protocol["synthesis"]["carrier_hz"]
    probe_width = min(2.0, max(0.2, duration / 50))
    frequency_tolerance = max(1.0, sweep_end * probe_width / duration / 2 + 1.5)

    binaural_sweep = 20.0
    binaural_time = duration * binaural_sweep / sweep_end
    low = _window(audio, sample_rate, binaural_time, probe_width)
    left_carrier = _spectral_peak(low[:, 0], sample_rate, carrier - 50, carrier + 50)
    right_carrier = _spectral_peak(low[:, 1], sample_rate, carrier - 10, carrier + 70)
    record("left_carrier_hz", abs(left_carrier - carrier) <= frequency_tolerance, left_carrier, carrier, frequency_tolerance)
    record("right_binaural_fundamental_hz", abs(right_carrier - (carrier + binaural_sweep)) <= frequency_tolerance, right_carrier, carrier + binaural_sweep, frequency_tolerance)

    for name, modulation_hz in (("isochronic_modulation_hz", 60.0), ("harmonic_modulation_hz", 120.0)):
        center = duration * modulation_hz / sweep_end
        probe = _window(audio[:, 0], sample_rate, center, probe_width)
        measured = _envelope_peak(probe, sample_rate, modulation_hz)
        tolerance = max(2.0, sweep_end * probe_width / duration / 2 + 2.0)
        record(name, abs(measured - modulation_hz) <= tolerance, measured, modulation_hz, tolerance)

    mid = _window(audio, sample_rate, duration * 60.0 / sweep_end, probe_width)
    stereo_delta = float(np.max(np.abs(mid[:, 0] - mid[:, 1])))
    record("shared_isochronic_stereo_routing", stereo_delta <= 2 / 32767, stereo_delta, 0.0, 2 / 32767)
    record(
        "audio_visual_duration_agreement",
        resolved["visual_timeline"]["duration_seconds"] == duration,
        resolved["visual_timeline"]["duration_seconds"],
        duration,
    )
    passed = all(item["passed"] for item in checks)
    return {"verification_version": "1.0.0", "passed": passed, "checks": checks}

