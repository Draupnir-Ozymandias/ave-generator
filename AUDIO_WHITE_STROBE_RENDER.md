# Audio and white-strobe rendering

Date: 2026-10-10. Status: **complete; ready for independent validation**.
User explicitly selected pulse-synchronized
volume modulation while preserving pitch.

Source: `ave_forensics/samples/brainfm/meditate/unguided/AuraCleansing_120bpm_15m.mp3`.
FFprobe identifies 900s stereo MP3 at 44.1kHz. Default excerpt is the first
300s. Independent Forensics JSON reports under
`ave_forensics/artifacts/audio-white-alignment/` find strong audible components
at 73.5Hz and approximately 147Hz, envelope components including approximately
8Hz and 16Hz, and little natural association with the white gates. Detrended
frame-RMS correlation is 0.000605 left and -0.000166 right. Those findings do
not mean the source music follows the time-varying Vitality schedule.

The production workflow applies smooth amplitude modulation driven by the
actual white frame gates, as recommended in Forensics' alignment comparison.
Depth is 0.30, gain 0.70–1.0. A centered Gaussian filter with 2.5ms sigma and
10ms support each side smooths frame-gate edges. Envelope maxima align with
the centers of visible white gate runs. Audio chunks use sample halos so chunk
boundaries do not alter this timing. It is not a hard-gated zero/off waveform.
Depth ramps across 50ms at 1.5s and 298s;
outside that interval audio remains dry with the same global attenuation.
Global normalization only attenuates if needed for a -1dBFS PCM peak ceiling.
No resampling or pitch shift; AM introduces amplitude changes and sidebands.

Output directory: `output/audio-white-strobe-300s/`. It contains
the dry excerpt, synchronized WAV, final MP4, protocol, inspection JSON and
pre/final manifests. Existing white-video packets will be stream-copied and
their payload hashes compared. No autoplay. Third-party source audio and local
derivatives remain ignored and are not licensed for redistribution by this work.

```sh
.venv/bin/python tools/render_audio_white_strobe.py \
  --source ../ave_forensics/samples/brainfm/meditate/unguided/AuraCleansing_120bpm_15m.mp3 \
  --video output/single-square-white-300s/single-square-white-300s.mp4 \
  --output-dir output/audio-white-strobe-300s --prepare-only
```

Removing `--prepare-only` reproduces the complete audiovisual render.
Generator inspection is separate from independent Forensics evidence.
No neurological entrainment, efficacy, therapy or exposure-safety claim is made.

## Completed artifacts

Primary output:
`/Users/eric/Projects/media/ave_generator/output/audio-white-strobe-300s/audio-white-strobe-300s.mp4`.
Dry excerpt: adjacent `dry-first-300s.wav`. Synchronized audio:
`pulse-linked-smooth-am.wav`. No artifact was autoplayed. Existing white MP4
retains its original hash and packet content.

| Artifact | SHA-256 |
| --- | --- |
| Source MP3 | `e374fd7502db23306f04c7dc0447a1a26031309726b127602147e75320cf0b36` |
| Dry 300s WAV | `beaf5c27ca62ad49e2470ddbf913c052055bb46258bf3270686e53687eccd13a` |
| Synchronized WAV | `c27bf7187e15b4e5bc1df1fe5547b6c99a8ce3b1934657393c49e666840e11da` |
| Audiovisual MP4 | `40654548585103e4ac456a7bad3fcf9f75f20d099877d6ef5c05794e01707d64` |
| Protocol file | `9e7948246422b5f6c55adc9e9b0a0390c3bb45651a80af9249efcd6537929cde` |
| Final manifest | `5d7a305f05223ee525ceecc18caf3c0e25af36293a641164a591f918fd8e22a6` |

Video packet SHA-256 before/after muxing:
`8e5f5c8ffbc856fe78e4db20c2262aea60498c6da1f25cc6a19a9787cd3ebed0`.
Generator source is uncommitted, recorded as dirty at main commit
`db13ab79f451d0267100f0d4da302d6a5cc53c35`; workflow hash is pinned in manifest.
Generated third-party media derivatives remain ignored and local.

## Validation and exact limitations

70 tests pass, including integrated-phase behavior and chunk-independent
Gaussian smoothing. All five output hashes/sizes and manifest content hash
validate. Both WAVs have exactly 13,230,000 stereo frames at 44.1kHz. Synchronized
PCM sample peak is 0.726471; source dry peak is 0.807373. Global attenuation is
1.0 because the dry signal already has sufficient headroom.

FFprobe confirms 36,000 H.264 frames, 640×640 at 120 fps; AAC stereo 44.1kHz;
both streams start at 0.000000 and have duration 300.000000s. Decoded AAC peaks
at -2.776393dBFS (no clipping). Decoder output has 13,230,080 samples due to
AAC tail padding, approximately 1.81ms beyond the exact WAV sample count;
container duration is 300s. Encoded stream alignment does not establish physical
acoustic/display latency or independent physiological synchronization.

Forensics' source-only observation SHA-256 is
`2ca26cf98396e856ec3f5e2eecddf91ebb69ee7842d1291c33471d632cec0fbb`;
its source-versus-white comparison hash is
`06ffddc698b5d82c64ca6246cb7aa306af3288a39d93d12147477b0565f50cad`.
Those reports describe the original source, not independent validation of this
new modulated artifact. The expected human-readable brief was unavailable;
the persisted JSON results supplied the findings. Platform/Forensics should
measure the new WAV/MP4 independently before promoting the `exploratory` label.
