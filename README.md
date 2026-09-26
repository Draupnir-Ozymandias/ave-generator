# AVE Generator

AVE Generator contains deterministic, recipe-driven audio and four-region light renderers for offline engineering analysis. Both resolve versioned JSON onto monotonic timelines, write pre-render provenance, and render only from validated parameters.

The original import-time audiovisual prototype and its time-varying phase defect remain preserved in Git history at commit `b31dba4`. The current `main.py` is a guarded compatibility entry point and does nothing when imported.

## Corrected audio baseline

The `ave_audio_generator` package completes the implementation portion of audio Milestone 0:

- a versioned baseline protocol and resolved protocol written before synthesis;
- exclusive discrete frequency accumulation across chunk boundaries, never `f(t) * t`;
- an explicit `fundamental_only` binaural harmonic policy;
- deterministic 44.1 kHz stereo PCM with click-free endpoint fades and 0.9 digital peak headroom;
- black-box checks for duration, routing, carrier, binaural difference, modulation, clipping, endpoints, and audio/visual clock agreement;
- optional checked offline video rendering and FFmpeg muxing; and
- optional AVE Forensics execution with input/evidence hashes and claim-level agreement recorded in the manifest.

Run the complete 10- and 180-second audio acceptance workflow:

```bash
.venv/bin/python -m ave_audio_generator milestone0 \
  --output-dir output/milestone-0 \
  --forensics-repo ../ave_forensics
```

The 180-second Forensics pass verifies the exact WAV identity, persistent 528/1056/1584/2112 Hz carrier structure, and the early binaural-difference ramp through its time-resolved timeline. The current Forensics configuration does not independently reconstruct the later continuous isochronic and harmonic modulation ramps; the Generator’s black-box signal probes cover those programmed values, and this division of coverage is explicit in the manifest.

Render and mux the guarded audiovisual baseline explicitly:

```bash
.venv/bin/python main.py render \
  contracts/examples/baseline-audio-protocol.json \
  --duration 10 --with-video \
  --output-dir output/audio-av-preview
```

## Four-region architecture

The data flow is deliberately one-way:

```text
AVE recipe 1.0.0 -> validation -> deterministic resolved frame plan
                                      |
                                      +-> pre-render manifest
                                      +-> offline pixel renderer -> final manifest

Lumenate export 0.2.0 -> strict adapter -> AVE recipe 1.0.0
```

AVE Generator owns the recipe, compiler, virtual frame plan, renderer, and render manifests. Lumenate forensic interpretations and evidence contracts remain owned by `lumenate_nova_forensics`. The repositories communicate only through pinned, sanitized JSON; no Lumenate code is imported or executed at runtime.

Key paths:

- `contracts/ave-light-render-recipe-1.0.0.schema.json` — generic four-region recipe contract.
- `contracts/examples/synthetic-four-region-recipe.json` — lawful positive fixture with off periods, a constant pulse, ramps, and region divergence.
- `contracts/vendor/lumenate/0.2.0/` — exact pinned protocol and evidence schemas plus their source manifest.
- `contracts/examples/lumenate/` — aligned validation fixture and intentionally incomplete empirical provenance fixture.
- `ave_light_renderer/` — validator, compiler, strict adapter, manifest builder, renderer, and CLI.
- `tests/` — contract, timing, gating, independence, adapter, manifest, and renderer tests.
- `contracts/ave-audio-protocol-1.0.0.schema.json` — corrected audio-baseline contract.
- `contracts/examples/baseline-audio-protocol.json` — frozen 180-second engineering sweep.
- `ave_audio_generator/` — audio resolver, accumulated-phase synthesis, verification, manifests, optional video/muxing, and Forensics runner.

## Recipe and timing model

A recipe contains exactly four independently addressable regions: `top_left`, `top_right`, `bottom_left`, and `bottom_right`. Each region covers the entire monotonic virtual timeline with explicit contiguous `off` or `pulse` intervals. Pulse intervals use constant or linear frequency, duty-cycle, and intensity curves; RGB and grayscale colors are supported. Phase policy and phase origin are explicit.

Compilation samples a rational virtual frame clock at 60 or 120 Hz. Frequency is integrated analytically by accumulation, including linear frequency ramps. The implementation does not evaluate a time-varying oscillator as `sin(2*pi*f(t)*t)`. Requested boundaries and their quantized frame boundaries are retained with timing-error summaries.

The renderer consumes only the resolved plan. Before any pixel rendering, it writes a pre-render manifest containing recipe and plan hashes, renderer and Git state, refresh rate, transition quantization, timing errors, and warnings. The completed manifest adds hashes and byte sizes for the plan and output media. Generated media stays ignored by Git.

## Setup

Python 3.11 or newer and FFmpeg are required.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The Conda definition remains available as an alternative:

```bash
conda env create -f environment.yml
conda activate ave
```

## Safe offline CLI

Run the complete first milestone with one command:

```bash
.venv/bin/python -m ave_light_renderer demo \
  --refresh 60 \
  --output-dir output/four-region-demo
```

That command validates and compiles the synthetic recipe, prints the resolved-plan summary, writes the plan and pre-render manifest, renders a short MP4, finalizes the provenance-rich manifest, adapts the complete aligned Lumenate fixture using an explicit emulator phase choice, and records safe rejection of the incomplete empirical Vitality fixture without inference.

Individual operations:

```bash
# Validate an AVE recipe.
.venv/bin/python -m ave_light_renderer validate \
  contracts/examples/synthetic-four-region-recipe.json

# Compile without pixels or flashing. Use 60 or 120 Hz.
.venv/bin/python -m ave_light_renderer compile \
  contracts/examples/synthetic-four-region-recipe.json --refresh 120

# Render an offline MP4 and manifests.
.venv/bin/python -m ave_light_renderer render \
  contracts/examples/synthetic-four-region-recipe.json \
  --refresh 60 --output-dir output/four-region-preview

# Validate evidence and report whether it is renderable without inference.
.venv/bin/python -m ave_light_renderer check-lumenate \
  contracts/examples/lumenate/vitality-5min-empirical-0.2.0.json

# Adapt a complete 0.2.0 export; phase policy/origin are mandatory AVE choices.
.venv/bin/python -m ave_light_renderer adapt-lumenate \
  contracts/examples/lumenate/aligned-export.json \
  --phase-policy reset --phase-origin 0 \
  --output output/aligned-adapted-recipe.json
```

`check-lumenate` exits with status 2 when evidence is contract-valid but cannot drive rendering. It prints every missing machine-readable field.

## Tests

```bash
.venv/bin/python -m pytest -q
```

The suite covers both renderers: semantic validation, incomplete-input rejection, deterministic hashes and pixels, interval boundaries and off behavior, accumulated phase and chunk continuity, duty gating, stereo routing, headroom and fades, independent visual regions, 60/120 Hz quantization, Forensics agreement evaluation, exact vendored hashes, Lumenate provenance preservation, and render manifests.

## Adapter boundary

The adapter accepts only Lumenate protocol version `0.2.0`. It verifies the exact vendored schema hashes before validation. It preserves the source-file hash, source export identity and timestamp, evidence IDs, per-segment execution layer, clock declarations, confidence, and limitations.

The adapter rejects unsupported versions, non-covering timelines, and every segment missing intensity, RGB color, pulse frequency, duty cycle, or the pulse object itself. It never parses `shape_detail` prose and never replaces nulls with guessed values. Mirroring a single complete evidence timeline into four AVE regions and selecting phase behavior are explicit emulator mappings, not forensic findings about the device.

## Safety posture and exact limitations

This milestone is offline-only. It contains no torch control and no real-time flashing player. It does not access display hardware, react to wall-clock time, or claim exposure safety. A future real-time player is out of scope until the virtual-clock and offline tests pass; it would require explicit photosensitivity acknowledgement, black start/end states, immediate Escape and focus-loss blackout, a monotonic clock, and scheduled-versus-observed callback and dropped-frame logs.

This software does **not** establish or claim:

- neurological entrainment, a desired mental state, therapy, or clinical benefit;
- photosensitivity safety or suitability for human exposure;
- exact equivalence to a Lumenate Nova or any other physical device;
- calibrated luminance or intensity;
- packet-to-photon latency; or
- subframe emitter phase.

The current empirical Vitality export intentionally contains null rendering parameters. It is retained as provenance and a negative test, not treated as a complete stimulus recipe. The aligned export tests the adapter contract, while the synthetic AVE recipe is the positive rendering fixture.

## Output and repository policy

Track source, tests, environment declarations, documentation, schemas, recipes, manifests, and small lawful fixtures. Do not track generated audio/video, virtual environments, caches, secrets, machine-specific configuration, or proprietary source media. The `output/` directory is retained with `.gitkeep`; its generated contents are ignored.

See [AVE_PLATFORM_STATUS_AND_ROADMAP.md](AVE_PLATFORM_STATUS_AND_ROADMAP.md) for the broader platform assessment and music-generation roadmap.
