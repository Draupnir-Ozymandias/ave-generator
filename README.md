# AVE Generator

AVE Generator is an early audiovisual-stimulation prototype. It currently creates a three-minute stereo audio track, renders a synchronized rotating yin-yang visualization with live telemetry, and combines both streams into an MP4 with FFmpeg.

The present code is a preserved experimental baseline, not a validated medical or therapeutic product. See [AVE_PLATFORM_STATUS_AND_ROADMAP.md](AVE_PLATFORM_STATUS_AND_ROADMAP.md) for the technical assessment, known signal-generation issue, scientific boundaries, and planned evolution into a recipe-driven music-generation platform verified by AVE Forensics.

## Current prototype

- Python 3.11 environment definition.
- 44.1 kHz, 16-bit stereo WAV generation.
- Nominal binaural, isochronic, and harmonic phases.
- Additive organ-like timbre centered on a 528 Hz artistic carrier choice.
- 1024 × 1024 video at 60 fps.
- Frequency/RPM/phase telemetry.
- FFmpeg audio/video muxing.

The current time-varying audio oscillator math is known to be incorrect and must be replaced with sample-accurate phase accumulation before the output is used as an experimental stimulus. The roadmap identifies this as Milestone 0.

## Setup

Create the Conda environment:

```bash
conda env create -f environment.yml
conda activate ave
python -m pip install -r requirements.txt
```

FFmpeg must also be installed and available on `PATH`.

## Run

```bash
python main.py
```

The script writes generated files beneath `output/`:

- `audio.wav`
- `video.mp4`
- `final.mp4`

## Output policy

Generated audio and video are intentionally excluded from Git because they are large, reproducible build artifacts. The repository tracks the empty `output/` directory with `.gitkeep`, but not its contents.

Future versions should track compact protocol recipes and render manifests containing parameters, code version, random seed, checksums, and forensic verification results. Small synthetic test fixtures may be explicitly allow-listed when automated tests require them. Commercial or copyrighted source media must not be committed.

## Repository policy

Track:

- Source code and tests.
- Environment and dependency declarations.
- Documentation and architecture decisions.
- Protocol schemas, recipes, manifests, and small lawful fixtures added later.

Do not track:

- Generated audio/video renders.
- Virtual environments or Python caches.
- Local secrets and machine-specific configuration.
- Commercial, proprietary, or otherwise non-redistributable media.

## Scientific posture

The software is intended to generate reproducible signals for engineering analysis and controlled experimentation. A programmed carrier, beat, pulse, or modulation rate does not establish physiological entrainment, a particular mental state, or clinical efficacy. Those questions require appropriately designed human research and independent measurements.
