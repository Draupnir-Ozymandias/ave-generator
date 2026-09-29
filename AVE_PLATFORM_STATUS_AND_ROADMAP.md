# AVE Platform Status and Roadmap

> Portfolio update (2026-09-29): the platform's immediate priority is a five-demo reproducible engineering portfolio. AVE Generator now uses the permanent `ave-demo-001` through `ave-demo-005` identities, independent semantic demo versions, and schema-valid Platform declaration `0.1.0` records. All five recipes have deterministic audio/stem synthesis, explanatory video packaging, explicit declaration-mapping reports, separate declaration/check/observation/agreement records, and detector requests containing no expected values or tolerances. The first binaural package builds successfully but remains conservatively `exploratory` until AVE Forensics returns its independent field-level report. See `docs/DEMO_PORTFOLIO_IMPLEMENTATION.md`.
>
> Implementation update (2026-09-26): the isolated `ave_light_renderer` package implements the first offline four-region screen-emulator milestone, and the new `ave_audio_generator` package corrects the legacy time-varying phase defect behind a guarded CLI. Ten- and 180-second audio renders pass black-box carrier, modulation, routing, duration, fade, and headroom checks. AVE Forensics independently confirms the exact input identity, persistent carrier structure, and early binaural-difference ramp; its current configuration does not reconstruct the later continuous modulation ramps, which remains an explicit verification-coverage limitation.

**Prepared:** 2026-08-03
**Scope:** `ave_generator`, `ave_forensics`, and the conversation titled “binaural meditation and entrainment”

## Executive status

The project has two useful but uneven halves:

- **AVE Generator** is a working proof of concept that renders a three-minute stereo WAV, a synchronized 60 fps yin-yang animation, and a final MP4. It is not yet a reliable experimental stimulus generator because its time-varying audio phase is calculated incorrectly, its configuration is hard-coded, and it has no meaningful tests or provenance manifest.
- **AVE Forensics** is an emerging analysis laboratory. Its named v0.4 modules—carrier tracking, envelope analysis, phase analysis, and modulation-spectrum reconstruction—are implemented. The current synthetic suite passes all 15 tests. The modulation-spectrum milestone is present locally but not committed.
- **The platform opportunity** is to connect them through a versioned protocol/evidence contract: Forensics measures techniques; a human-reviewed recipe translator turns measurements into an original protocol; Generator renders it; Forensics verifies the rendered artifact; Laboratory records the experiment and evaluates outcomes.

The immediate priority is not a graphical interface or more effects. It is a trustworthy, round-trip signal pipeline with known ground truth.

## What the prior conversation established

The conversation evolved from tone and binaural-beat generation into a broader audiovisual and eventually audio/visual/haptic research system. Its durable decisions are:

1. Analyze techniques, not proprietary content.
2. Change one variable at a time.
3. Use Forensics to measure, Generator to create, and a Laboratory layer to design and interpret experiments.
4. Preserve exact parameters, versions, inputs, outputs, and observations for reproducibility.
5. Treat physiological and mental-state effects as hypotheses until independently validated.
6. Keep optional visual and haptic modalities synchronized to the same protocol timeline.

Some earlier statements in the conversation were too confident. A carrier such as 528 Hz, a breathing-rate envelope, a binaural difference, or a low-frequency haptic pulse can be specified and measured; none alone establishes relaxation, parasympathetic activation, a clinical benefit, or a particular altered state.

## Repository status

### AVE Generator

Current contents are a single 122-line script, a one-line import smoke test, dependency files, a backup script, and rendered artifacts. The directory is not currently a Git repository.

Working output verified:

- `output/audio.wav`: 180 seconds, stereo PCM, 44.1 kHz, 16-bit.
- `output/video.mp4`: 1024 × 1024, 60 fps.
- `output/final.mp4`: 180 seconds, H.264 video plus stereo AAC; approximately 64 MB.
- `main.py` and `test.py` compile successfully.

Implemented prototype features:

- Linear displayed target ramp from 0 to 360 Hz.
- Smoothed blending among nominal binaural, isochronic, and harmonic phases.
- Additive “organ” timbre using the carrier and first three overtones.
- Integrated visual rotation and live Hz/RPM/phase telemetry.
- FFmpeg muxing.

Material limitations:

- All settings and output paths are hard-coded.
- Rendering happens at import time and is not exposed as reusable functions or a CLI.
- The output directory is assumed to exist.
- FFmpeg failures are not checked.
- The generator normalizes only to full-scale peak; there is no headroom, loudness target, limiter, listening-level guidance, or artifact check.
- There is no fade handling, seeded randomness, metadata manifest, recipe file, batch mode, or resumable render.
- `test.py` checks only whether NumPy imports.
- The output is square 1024 × 1024 despite the conversation settling on a 1080p/60 publishing target.
- Several features discussed in the conversation—breath pacing, subharmonics, reverb, stereo drift, aura, radial field, and haptics—are not present in the current source.

### Critical signal-generation defect

For a time-varying frequency, the code uses expressions equivalent to:

```python
sin(2 * pi * frequency(t) * t)
```

That expression is correct only for a constant frequency. If `frequency(t)` is a linear ramp, its instantaneous frequency is `frequency(t) + t * frequency'(t)`. In this generator that doubles the intended ramp component.

Consequences:

- During the nominal binaural ramp, the fundamental interaural difference evolves at roughly twice the displayed target.
- Each organ harmonic also multiplies that difference, producing several simultaneous interaural differences rather than one controlled binaural beat.
- Isochronic and high-frequency modulation ramps are likewise not the frequencies shown by the telemetry.
- The visual angle correctly integrates the displayed ramp, so the audio and visual are not actually frequency-locked.

The correct synthesis pattern is phase accumulation:

```python
phase[n] = phase[n - 1] + 2 * pi * frequency[n] / sample_rate
signal[n] = sin(phase[n])
```

or the vectorized equivalent using a cumulative sum. Fixing this, and proving it with synthetic tests, is milestone zero.

### AVE Forensics

Repository state:

- Branch `main` matches `origin/main` at commit `21a031bd5` for committed work.
- Local uncommitted work adds the Modulation Spectrum Analyzer and its console/report integration.
- The local corpus is about 6.9 GB and is correctly excluded from version control.
- `README.md` and `config.py` are empty; the substantive mission and architecture are in `AVE_FORENSICS_MISSION.md`.
- Dependencies are unpinned and there is no package metadata or command-line entry point.
- The execution path is a 314-line `main.py` with an absolute path to one Brain.fm file.

Implemented analysis capabilities:

- Audio loading and metadata.
- Global and windowed spectra.
- Stereo correlation and candidate inter-channel differences.
- Time-resolved candidate tracking.
- Persistent carrier tracking and cross-channel pairing.
- Carrier-envelope extraction and modulation-depth/spectrum measurement.
- Phase offset, phase locking, and stable phase-rotation analysis.
- Persistent, episodic, ramping, shared, and channel-specific modulation reconstruction.
- Console, CSV, Markdown, and plot outputs.

Validation status:

```text
15 tests passed in 0.78 seconds
```

The tests cover carrier tracking/pairing, known amplitude modulation, invalid filters, phase offsets and detuning, independent-noise rejection, persistent and multiple modulation rates, a modulation ramp, a no-modulation control, and channel-specific modulation.

Strongest current real-recording reconstruction:

```text
Shared carrier: approximately 98.67 Hz
Stereo behavior: phase locked
Amplitude modulation: approximately 0.625 Hz
Coverage: 57 of 59 windows (96.6%)
Stereo modulation difference: approximately 0 Hz
```

This supports persistent shared amplitude modulation around a common carrier. It does **not** support calling the 0.625 Hz component a binaural carrier difference, and it does not by itself establish a delta-state physiological response.

Current reporting risk:

The older Markdown/protocol report still promotes peak-difference candidates into labels such as “delta relaxation / sleep-depth candidate.” Those labels are not yet reconciled with the stronger carrier, phase, envelope, and modulation evidence. Until the evidence schema and corroboration rules are implemented, these intent labels should be treated as exploratory output, not generator instructions.

## Recommended platform architecture

Keep the responsibilities separate, but connect them with shared, versioned data contracts.

```text
Reference or synthetic stimulus
            |
            v
      AVE Forensics
  measurements + confidence
            |
            v
 Human-reviewed technique recipe
  no copied audio or proprietary content
            |
            v
       AVE Generator
 music + entrainment + optional visual/haptic stems
            |
            v
  Rendered artifact + manifest
            |
            v
      AVE Forensics
 expected-vs-observed verification
            |
            v
      AVE Laboratory
 protocol, controls, outcomes, adverse events, conclusions
```

Recommended code ownership:

- `ave_generator`: synthesis, composition, mixing, rendering, presets, and artifact manifests.
- `ave_forensics`: measurements, evidence objects, reconstruction, comparison, and verification.
- `ave-laboratory` later: hypotheses, experiment definitions, datasets, consent/protocol records, and outcome analysis.
- `ave-schema` only when both codebases need it: a small shared package defining protocol, evidence, and manifest schemas. Do not create a large monorepo yet.

## Core data contracts

### 1. Forensic evidence

Each detection should carry:

- Type and schema version.
- Source hash and analysis Git commit.
- Time range and channel/modality.
- Measured values and units.
- Method, window, hop, FFT/filter, and thresholds.
- Supporting observations.
- Confidence and known false-positive modes.
- Classification level: measurement, detection, association, reconstruction, or hypothesis.

### 2. Generator protocol

A protocol should describe:

- A neutral profile name such as `calm_experiment_alpha_01`, not a guaranteed outcome.
- Hypothesized state and evidence/rationale.
- Ordered stages with duration and transition curves.
- Independent carrier, interaural difference, amplitude modulation, pulse, spatial, musical, visual, and haptic parameters.
- Sample rate, bit depth, channel layout, render format, and loudness/headroom policy.
- Safety flags and intended listening equipment.
- Random seed, generator version, source recipe, and parent experiment.

### 3. Render manifest

Every render should produce a JSON manifest containing the exact resolved timeline, hashes of every output, warnings, measured peaks/loudness, and the results of forensic verification.

## Roadmap

### Completed cross-cutting foundation — visual protocol and offline rendering

The four-region screen-emulator work deliberately proves parts of later milestones without changing the critical-path requirement to finish the audio baseline first.

#### Milestone 2V — Deterministic visual protocol compiler (complete)

- Versioned four-region AVE light-render recipe with a monotonic virtual clock.
- Explicit off intervals; constant and linear frequency, duty-cycle, and intensity curves; RGB and grayscale output; and explicit phase policy/origin.
- Deterministic accumulated-phase compilation at 60 and 120 Hz.
- Requested-versus-quantized transition records and timing-error summaries.
- Pre-render and completed manifests with recipe, plan, output, renderer, and Git provenance.
- Strict, hash-pinned Lumenate `0.2.0` JSON adapter that rejects incomplete evidence without prose parsing or inferred values.

**Exit criterion met:** the synthetic visual fixture can be changed through JSON, compiled without flashing, rendered offline, and reproduced byte-for-byte with a provenance-rich manifest.

#### Milestone 6A — Offline four-region visual renderer (complete)

- Four independently addressable screen regions driven only by the resolved plan.
- Deterministic offline MP4 and image-sequence rendering primitives.
- Explicit black/off behavior and a synthetic fixture with region-specific divergence.
- Automated tests for boundaries, gating, phase accumulation, independence, quantization, deterministic pixels, and incomplete-input rejection.
- No torch control and no real-time flashing path.

**Exit criterion met for the offline subsystem only:** virtual modality timing is measurable and independently addressable. This does not complete Milestone 6 because there is no shared audio/visual master timeline, calibrated physical output, haptic renderer, or exposure-ready real-time player.

The next critical-path work remains Milestone 0. After the audio baseline is corrected and verified, Milestone 2V should become the visual stem of the broader protocol compiler rather than a separate competing contract.

### Milestone 0 — Freeze and correct the baseline

**Status (2026-09-26): implementation complete; independent Forensics coverage is partial and explicitly bounded.** The original prototype is frozen in Git history, `main.py` is guarded, phase is accumulated across chunks, the fundamental-only binaural policy is explicit, endpoints and headroom are controlled, FFmpeg is checked, and synthetic/black-box tests cover programmed signal behavior. Both 10- and 180-second renders pass. AVE Forensics agrees on source identity, the 528/1056/1584/2112 Hz carrier structure, and the early 10/20/30 Hz binaural timeline observations. Its default analysis does not reconstruct the later continuous 40–80 Hz isochronic and 84–360 Hz harmonic modulation ramps; Generator-side black-box probes currently verify those values.

Goal: turn the present script into a trustworthy reference generator.

- Initialize Git for `ave_generator`; commit the current prototype and outputs policy.
- Move synthesis into functions and add a guarded CLI entry point.
- Replace all time-varying `f(t) * t` expressions with integrated phase accumulators.
- Make harmonic behavior explicit: either one controlled binaural difference on the fundamental, or a deliberately defined difference per partial.
- Add click-free fades, headroom, validation, output-directory creation, and checked FFmpeg execution.
- Add synthetic tests that estimate instantaneous carrier, beat, AM, duration, stereo routing, and audiovisual timeline agreement.
- Run the corrected generator output through AVE Forensics and require expected-versus-observed tolerances.

**Exit criterion:** a 10-second and 180-second baseline render reproduce every programmed frequency within declared tolerances, and the manifest agrees with Forensics for every claim that the current Forensics configuration supports. Unsupported ramp coverage must remain machine-readable and must not be presented as independently verified.

### Milestone 1 — Finish and stabilize Forensics v0.4

Goal: make its conclusions safe to consume programmatically.

- Review, commit, and push the modulation-spectrum milestone.
- Add a real README, version declaration, pinned/locked environment, and CLI accepting an input path and output directory.
- Replace the hard-coded recording path and centralize configuration.
- Define evidence objects and integrate carrier, envelope, phase, and modulation results into one report.
- Prevent intent hypotheses from outranking contradictory cross-module evidence.
- Add generator-produced fixtures as positive controls and ordinary music/noise as negative controls.

**Exit criterion:** one command produces a self-contained, provenance-rich report whose headline conclusions are supported by multiple modules.

### Milestone 2 — Build the protocol compiler

Goal: make generation recipe-driven instead of code-edit-driven.

- Define and validate `protocol.json` with a formal schema.
- Compile stages and curves into a sample-accurate master timeline.
- Support fixed, ramped, and stepped carriers/modulators independently.
- Produce deterministic builds from a seed.
- Generate a resolved protocol and render manifest before expensive rendering begins.

**Exit criterion:** changing a mental-state hypothesis or musical design requires editing a recipe, not Python.

### Milestone 3 — Add a real music engine

Goal: embed controlled stimulation inside listenable original music.

- Separate the **music bed** from the **stimulation layer**.
- Add tempo, meter, key/mode, chord progression, harmonic rhythm, arrangement sections, timbre presets, drones, noise beds, and automation lanes.
- Begin with deterministic MIDI/additive/subtractive synthesis; add lawfully licensed samples later.
- Preserve a low-level calibration stem so entrainment features remain measurable beneath richer timbres.
- Export stems: music, carriers, modulation, voice if any, haptic low-frequency stem, and full mix.
- Add masking and audibility checks so musical density does not silently erase the programmed stimulus.

**Exit criterion:** several musically distinct renders share the same verified stimulation protocol, allowing timbre/arrangement A/B tests without changing the signal hypothesis.

### Milestone 4 — Create experimental state profiles

Goal: encode hypotheses without presenting them as established effects.

Start with three profiles, each with an active control and a sham/control condition:

- `relaxation_exploratory`: gentle musical pacing with a stable alpha or alpha-to-theta candidate.
- `meditation_exploratory`: staged alpha-to-theta candidate with sparse arrangement and optional breath cueing.
- `focus_exploratory`: stable alpha/beta candidate with less spatial motion and controlled musical complexity.

Do not use a 0–360 Hz sweep as a mental-state protocol. Keep that sweep as a calibration/perceptual demo. Experimental profiles should use stable plateaus, controlled transitions, and a small number of independently testable variables.

For each profile compare, at minimum:

1. Music only.
2. Music plus the hypothesized stimulation.
3. A credible sham with equal expectation and similar sound.

**Exit criterion:** blinded files can be generated, verified, randomized, and decoded only after outcomes are recorded.

### Milestone 5 — Laboratory workflow and product interface

Goal: make the system usable without sacrificing reproducibility.

- Build batch rendering and an experiment registry before a GUI.
- Add a local web interface only after the schemas and CLI stabilize.
- UI flow: choose experimental profile → choose musical design → inspect timeline → render preview → verify → render master → register experiment.
- Store subjective ratings, equipment, exposure, environment, adherence, and adverse events separately from source code.
- Add comparison views that show the programmed protocol beside the Forensics reconstruction.

**Exit criterion:** a non-programmer can create a reproducible experiment without editing source code, and every result can be traced to exact code and parameters.

### Milestone 6 — Add visual and haptic modalities

Goal: extend a validated audio workflow, not multiply uncontrolled variables.

- Drive audio, video, and haptic output from the same master timeline.
- Export haptic content as a separate calibrated low-frequency stem, respecting device bandwidth and amplitude limits.
- Add visual stimulation only with explicit flicker/contrast controls, warnings, and a non-flashing mode.
- Test audio-only first, then one added modality at a time.
- Define a Multisensory Coherence metric only as an engineering synchronization score, not an efficacy measure.

**Exit criterion:** modality timing and amplitude are measurable, device-specific, and independently switchable for controlled comparisons.

### Milestone 7 — Human evaluation and evidence

Goal: learn what the system does, not confirm what its designers hope it does.

- Begin with usability and tolerability in healthy adult volunteers, not treatment claims.
- Pre-register outcomes and analysis where practical.
- Use randomized, blinded, controlled designs and validated outcome instruments.
- If claiming neural entrainment, measure EEG with an analysis plan that distinguishes stimulus artifact from neural response.
- If working with patients or collecting identifiable health data, obtain qualified legal/regulatory guidance and appropriate ethics/IRB review before enrollment.
- Record and report null results and adverse events.

**Exit criterion:** any state/efficacy claim is proportional to controlled evidence and clearly separated from engineering measurements.

## Evidence and safety posture

The current research base warrants experimentation, not promises. A 2023 systematic review found highly inconsistent EEG entrainment results across 14 heterogeneous studies. A 2025 randomized crossover study reported that effects depended on carrier, beat frequency, onset, and masking noise, illustrating why the platform must preserve every parameter. A 2026 review reported possible benefits across some outcomes but emphasized heterogeneity and small samples.

Recommended language:

> “Generates reproducible auditory stimulation protocols designed to test hypotheses about relaxation, meditation, focus, sleep, or other states.”

Avoid until supported:

> “Causes the selected brain state,” “stimulates the parasympathetic nervous system,” “treats anxiety,” or similar therapeutic promises.

Visual flicker is a separate safety concern; flashing and high-contrast patterns can provoke symptoms or seizures in susceptible people. Clinical or patient-facing work also changes the ethical and regulatory boundary. In the United States, general-wellness positioning must remain unrelated to diagnosis, cure, mitigation, prevention, or treatment of disease to fit FDA’s low-risk wellness policy; covered human-subject research generally requires informed consent and appropriate IRB oversight.

## Recommended next development step

Close the remaining independent-verification gap, then begin the music engine without changing the corrected stimulation layer:

1. Add or configure AVE Forensics analyses for continuous isochronic and harmonic modulation ramps.
2. Promote those results into canonical evidence and compare them automatically with the resolved Generator protocol.
3. Treat the corrected baseline as an immutable calibration stem.
4. Begin **Milestone 3** with a separate deterministic musical-bed layer and stem export.
5. Add masking and audibility checks before mixing the bed and stimulation layers.

This sequence keeps the scientific signal measurable while allowing the experience to become genuinely musical. The music layer must not silently alter the calibration stem or convert engineering measurements into efficacy claims.

## References

- Ingendoh RM, Posny ES, Heine A. [Binaural beats to entrain the brain? A systematic review](https://pubmed.ncbi.nlm.nih.gov/37205669/). *PLOS ONE* (2023).
- Melnichuk A, Cooper RK Jr, Hawk LW Jr. [A parametric investigation of binaural beats for brain entrainment and enhancing sustained attention](https://www.nature.com/articles/s41598-025-88517-z). *Scientific Reports* (2025).
- Elnazer HY. [Music and binaural beat interventions for young adults: a systematic review](https://pubmed.ncbi.nlm.nih.gov/41656644/). *Acta Neuropsychiatrica* (2026).
- U.S. FDA. [General Wellness: Policy for Low Risk Devices](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices) (January 2026).
- HHS Office for Human Research Protections. [Informed Consent FAQs](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/faq/informed-consent/index.html).
- Epilepsy Foundation. [Photosensitivity and Seizures](https://www.epilepsy.com/what-is-epilepsy/seizure-triggers/photosensitivity).
