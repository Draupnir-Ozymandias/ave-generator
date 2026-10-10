"""Prepare a dry excerpt, then optionally apply declared pulse-linked smooth AM."""

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.io import wavfile
from scipy.signal import welch, find_peaks
from scipy.ndimage import gaussian_filter1d

from ave_light_renderer.canonical import file_sha256, write_json, load_json, canonical_sha256
from ave_light_renderer.manifest import git_state
from ave_light_renderer.paths import PROJECT_ROOT


def pulse_linked_gain(times, intervals, depth=0.30, fade_seconds=0.05):
    gain = np.ones_like(times, dtype=np.float64)
    cycles = 0.0
    active = [i for i in intervals if i['kind'] == 'pulse']
    active_start = active[0]['start_us'] / 1e6
    active_end = active[-1]['end_us'] / 1e6
    for interval in intervals:
        if interval['kind'] == 'off':
            continue
        start, end = interval['start_us'] / 1e6, interval['end_us'] / 1e6
        duration = end - start
        curve = interval['frequency_hz']
        f0 = curve.get('value', curve.get('start'))
        slope = 0.0 if curve['kind'] == 'constant' else (curve['end'] - f0) / duration
        mask = (times >= start) & (times < end)
        local = times[mask] - start
        phase = cycles + f0 * local + 0.5 * slope * local * local
        taper = np.minimum(np.clip((times[mask] - active_start) / fade_seconds, 0, 1),
                           np.clip((active_end - times[mask]) / fade_seconds, 0, 1))
        envelope = 0.5 + 0.5 * np.cos(2 * np.pi * phase)
        gain[mask] = 1 - depth * taper * (1 - envelope)
        cycles += f0 * duration + 0.5 * slope * duration * duration
    return gain


def video_packet_hash(path):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-c:v', 'copy',
                           '-f', 'hash', '-hash', 'sha256', '-'], check=True,
                          capture_output=True, text=True).stdout.strip()


def encoded_gate_gain(times, gate, sample_rate, depth=0.30, sigma_seconds=0.0025):
    """Centered Gaussian smoothing with halos so audio chunks do not change phase."""
    halo = int(np.ceil(4 * sigma_seconds * sample_rate)) + 2
    extended = times[0] + np.arange(-halo, len(times) + halo) / sample_rate
    indices = np.floor(extended * 120 + 1e-9).astype(int)
    valid = (indices >= 0) & (indices < len(gate))
    sampled = np.zeros_like(extended)
    sampled[valid] = gate[indices[valid]]
    smoothed = gaussian_filter1d(sampled, sigma_seconds * sample_rate, mode='constant', truncate=4)
    smooth = smoothed[halo:halo + len(times)]
    taper = np.minimum(np.clip((times - 1.5) / .05, 0, 1), np.clip((298 - times) / .05, 0, 1))
    return 1 - depth * taper * (1 - smooth)


def workflow(source, video, output_dir, prepare_only=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    dry = output_dir / 'dry-first-300s.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-t', '300', '-map', '0:a:0',
                    '-c:a', 'pcm_s16le', str(dry)], check=True)
    sample_rate, audio = wavfile.read(dry, mmap=True)
    if audio.shape != (300 * sample_rate, 2):
        raise ValueError('Expected exact 300s stereo excerpt')
    dry_peak = 0.0
    for start in range(0, len(audio), sample_rate):
        chunk = audio[start:start + sample_rate].astype(np.float64) / 32768
        dry_peak = max(dry_peak, float(np.max(np.abs(chunk))))
    # Signal spectra are reported independently of modulation targets.
    # Full excerpt mono Welch; deterministic stride only for memory management.
    mono = audio.astype(np.float32).mean(axis=1) / 32768
    frequencies, power = welch(mono, fs=sample_rate, nperseg=sample_rate * 4)
    candidates, _ = find_peaks(power)
    selected = candidates[np.argsort(power[candidates])[-12:][::-1]]
    analysis = {'analysis_version': '1.0.0', 'owner': 'AVE Generator', 'independent_forensics': False,
                'source_sha256': file_sha256(source), 'excerpt_seconds': [0, 300],
                'sample_rate_hz': sample_rate, 'sample_count': len(audio), 'channels': 2,
                'dry_peak_linear': dry_peak, 'welch_spectral_peaks_hz': frequencies[selected].tolist(),
                'note': 'Spectral component peaks are not envelope modulation rates or physiological evidence.'}
    write_json(output_dir / 'generator-audio-inspection.json', analysis)
    del mono
    if prepare_only:
        print(json.dumps(analysis, indent=2), flush=True)
        return
    base_path = PROJECT_ROOT / 'contracts/examples/vitality-matched-four-region-300s.json'
    if file_sha256(base_path) != 'ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508':
        raise ValueError('Timing recipe hash mismatch')
    intervals = load_json(base_path)['regions'][0]['intervals']
    white_plan_path = video.parent / 'resolved-plan.json'
    white_manifest = load_json(video.parent / 'render-manifest.json')
    white_record = next(o for o in white_manifest['outputs'] if o['path'] == video.name)
    if file_sha256(video) != white_record['sha256']:
        raise ValueError('White-video manifest hash mismatch')
    plan_record = next(o for o in white_manifest['outputs'] if o['path'] == 'resolved-plan.json')
    if file_sha256(white_plan_path) != plan_record['sha256']:
        raise ValueError('White resolved-plan hash mismatch')
    white_plan = load_json(white_plan_path)
    gate = np.array([f['gate_on'] for f in white_plan['frames']], dtype=float)
    attenuation = min(1.0, 10 ** (-1 / 20) / max(dry_peak, 1e-12))
    declaration = {
        'protocol_version': '1.0.0', 'duration_seconds': 300, 'excerpt_start_seconds': 0,
        'source_audio_sha256': file_sha256(source), 'source_video_sha256': file_sha256(video),
        'dry_excerpt_sha256': file_sha256(dry), 'timing_recipe_sha256': file_sha256(base_path),
        'audio_shape': 'gaussian_smoothed_encoded_gate_amplitude_modulation', 'depth_fraction': 0.30,
        'gain_range': [0.70, 1.0], 'phase_reference': 'original encoded white frame gates',
        'white_resolved_plan_sha256': file_sha256(white_plan_path),
        'smoothing_sigma_seconds': 0.0025, 'smoothing_support_each_side_seconds': 0.01,
        'peak_policy': 'centered symmetric smoothing; envelope maxima centered in visible white gate runs',
        'active_interval_seconds': [1.5, 298], 'modulation_depth_endpoint_ramp_seconds': 0.05,
        'outside_active_interval': 'dry audio with same global attenuation',
        'global_attenuation_linear': attenuation, 'sample_peak_ceiling_dbfs': -1,
        'audio_pitch_shift': False, 'video_policy': 'copy original video packets',
        'limitations': ['The smoothed audio envelope changes abrupt gate edges and has a 0.70 floor; it is not a hard zero/off pulse.',
                        'Audio follows represented white frame gates; gates omitted by video sampling do not generate extra audio peaks.',
                        'Centered 2.5ms-sigma smoothing spreads transitions up to 10ms either side of the encoded edge.',
                        'AM changes amplitude and introduces spectral sidebands; source carrier frequencies are not retuned.',
                        'AAC encoding can add delay and alter peaks; physical AV latency is unmeasured.',
                        'Source is third-party audio. Local derivative is not a redistribution license.',
                        'No efficacy, entrainment or exposure-safety claim.']}
    declaration_path = output_dir / 'audio-render-protocol.json'
    write_json(declaration_path, declaration)
    manifest = {'manifest_version': '1.0.0', 'status': 'pre_render', 'generator': git_state(PROJECT_ROOT),
                'workflow_sha256': file_sha256(Path(__file__)), 'protocol_sha256': file_sha256(declaration_path),
                'declaration': declaration, 'evidence_maturity': 'exploratory', 'outputs': []}
    write_json(output_dir / 'render-manifest.pre.json', manifest)
    synchronized = output_dir / 'pulse-linked-smooth-am.wav'
    peak = 0.0
    with wave.open(str(synchronized), 'wb') as writer:
        writer.setnchannels(2)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        for start in range(0, len(audio), sample_rate):
            samples = audio[start:start + sample_rate].astype(np.float64) / 32768
            times = np.arange(start, start + len(samples)) / sample_rate
            samples *= encoded_gate_gain(times, gate, sample_rate)[:, None] * attenuation
            peak = max(peak, float(np.max(np.abs(samples))))
            writer.writeframes(np.round(samples * 32768).clip(-32768, 32767).astype('<i2').tobytes())
    final_video = output_dir / 'audio-white-strobe-300s.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-i', str(synchronized),
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                    '-t', '300', '-movflags', '+faststart', str(final_video)], check=True)
    before, after = video_packet_hash(video), video_packet_hash(final_video)
    if before != after:
        raise ValueError('Video packets changed during muxing')
    manifest.update({'status': 'complete', 'synchronized_wav_peak_linear': peak,
                     'original_video_packet_hash': before, 'muxed_video_packet_hash': after,
                     'video_packets_preserved': True,
                     'outputs': [{'path': p.name, 'sha256': file_sha256(p), 'bytes': p.stat().st_size}
                                 for p in [dry, synchronized, final_video, declaration_path,
                                           output_dir / 'generator-audio-inspection.json']]})
    manifest['manifest_content_sha256'] = canonical_sha256(manifest)
    write_json(output_dir / 'render-manifest.json', manifest)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    workflow(args.source, args.video, args.output_dir, args.prepare_only)
