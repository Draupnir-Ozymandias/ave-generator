# AVE Demo Portfolio — Generator Implementation and Handoff

**Status date:** 2026-09-29
**Repository:** AVE Generator
**Implementation branch:** `codex/demo-portfolio-foundation`

## Responsibility boundary

AVE Generator owns declarative recipes, deterministic synthesis, offline rendering, media/stem packaging, Generator-side build checks, and provenance manifests. AVE Forensics owns independent observations and field-level `agree`, `disagree`, or `unsupported` results. Lumenate Nova Forensics may supply evidence-backed light-pattern ideas with provenance and limitations, but it does not supply missing render values by inference and does not block synthetic demos.

The repositories exchange versioned, sanitized JSON and hashed media. Generator does not import either forensic repository at runtime.

## Tracked portfolio

| Order | Demo ID | Engineering distinction | Current label |
|---:|---|---|---|
| 1 | `binaural-difference-10hz-demo-v1` | Separate 440/450 Hz stereo carriers and declared 10 Hz difference | `exploratory` |
| 2 | `smooth-am-ramp-4-to-20hz-demo-v1` | 440 Hz carrier with continuous sine-envelope AM ramp | `exploratory` |
| 3 | `gated-pulse-12hz-duty25-demo-v1` | 440 Hz carrier with a hard 12 Hz, 25% duty gate | `exploratory` |
| 4 | `four-region-independent-schedules-demo-v1` | Four independently scheduled synthetic light regions | `exploratory` |
| 5 | `staged-binaural-smooth-am-gated-demo-v1` | Time-separated contrast of the three audio constructions | `exploratory` |

The labels are intentionally conservative. A passing Generator check is not independent evidence and cannot promote a label.

## Contract and package layout

`contracts/ave-demo-recipe-1.0.0.schema.json` requires:

- a monotonic, contiguous stage timeline;
- one of `silence`, `binaural`, `smooth_am`, or `gated_pulse` for each audio stage;
- explicit amplitude, phase origin, and modulation rate curves;
- a continuous sine envelope for smooth AM;
- hard edges and an explicit duty cycle for gated pulses;
- exactly one evidence-maturity label: `verified`, `partially_verified`, or `exploratory`;
- required observation fields and agreement tolerances;
- visible safety limitations; and
- original-synthetic redistribution provenance.

A built package contains:

```text
recipe.json                         source Generator recipe
resolved-demo.json                 resolved Generator declaration
render-manifest.pre.json           provenance written before media rendering
audio/stereo.wav                   analysis and distribution master
audio/left.wav, audio/right.wav    channel-isolated files
audio/stems/*.wav                  full-timeline construction stems
presentation-video.silent.mp4      deterministic explanatory visuals
presentation.mp4                   audio/video distribution preview
generator-validation.json          same-repository integrity checks
verification-request.json          blind-analysis request without declared values
PACKAGE_README.md                   purpose, reproduction, limitations, safety
render-manifest.json               hashes and separated evidence records
```

For a four-region package, the resolved light plan and raw four-region preview are included as additional files.

The final manifest keeps these records separate:

- `generator_declaration`: what Generator intended to render;
- `generator_validation`: same-repository measurements and integrity checks;
- `forensics_observation`: initially null, later supplied by AVE Forensics; and
- `field_level_agreement`: initially null, later supplied by AVE Forensics or a contract-defined adjudicator.

## Reproduce

```bash
.venv/bin/python -m ave_demo_generator validate all

.venv/bin/python -m ave_demo_generator build \
  contracts/examples/demos/binaural-difference-10hz-demo-v1.json \
  --output-dir output/demos/binaural-difference-10hz-demo-v1

.venv/bin/python -m pytest -q
```

Generated media remains under ignored `output/`; source recipes, schemas, tests, and documentation remain tracked.

## Independent verification handoff

For Demo 1, provide only `audio/stereo.wav` and `verification-request.json` to AVE Forensics for the first analysis pass. Forensics should record the exact input hash and observe duration, left/right carriers, interchannel difference, channel routing, and sample peak without reading Generator-declared values. It should then compare those observations with `resolved-demo.json` using the supplied tolerances and return a versioned observation record plus field-level agreement report.

Generator can adopt that report as an immutable attachment in a later package revision. Until then, Demo 1 remains `exploratory`, even though Generator's own black-box checks pass.

### 2026-09-29 trial analysis

The first packaged stereo WAV (`bf33db23ab1dbe60fce35c3a7ccc9cd1a016aa5e0cd69b2ce8c9dd57d5257517`) was analyzed with the current local AVE Forensics checkout. Its human-readable output measured 12.0 seconds, 440.00 Hz left, 450.00 Hz right, a 10.0 Hz candidate difference, peak 0.799988, and no periodic pulse. Its canonical evidence export preserved the exact input hash and no-pulse result, but did not emit canonical carrier/difference evidence objects or a field-level agreement record. The raw run also records that the Forensics checkout was dirty, so it is useful diagnostic evidence rather than a release-grade verification attachment.

This confirms both the signal's basic analyzability and the remaining contract work. Generator does not copy the human-readable findings into the reserved observation/agreement fields.

## Unresolved dependencies

- AVE Forensics needs a finalized cross-repository demo observation/agreement envelope. Its current analyzer can produce evidence for Demo 1, but the portfolio-specific field report remains external to this repository.
- Demo 2 needs independent reconstruction of a time-varying smooth AM envelope.
- Demo 3 needs an independent gate-rate, duty-cycle, and edge-shape observation contract.
- Demo 4 needs a visual-plan analyzer or field-level comparison contract; it makes no calibrated-luminance or physical-device-equivalence claim.
- Demo 5 should not be promoted until the three construction kinds can be classified independently by stage.
- Lumenate empirical exports remain optional provenance inputs. Null or incomplete device parameters are never filled by inference.

## Safety and claim boundary

These are offline engineering demonstrations, not exposure protocols. Digital amplitude is not calibrated SPL, RGB values are not calibrated luminance, and no package establishes photosensitivity safety, neurological entrainment, a desired mental state, therapeutic benefit, exact device equivalence, packet-to-photon latency, or subframe emitter phase.
