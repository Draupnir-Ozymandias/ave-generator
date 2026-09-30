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
| 1 | `ave-demo-001-binaural-construction` | Separate 440/450 Hz stereo carriers and declared 10 Hz difference | `exploratory` |
| 2 | `ave-demo-002-smooth-am-ramp` | 440 Hz carrier with continuous smooth amplitude modulation from 4–20 Hz | `exploratory` |
| 3 | `ave-demo-003-gated-pulse-contrast` | 440 Hz carrier with a hard 12 Hz, 25% duty gate | `exploratory` |
| 4 | `ave-demo-004-four-region-light` | Four independently scheduled synthetic light regions | `exploratory` |
| 5 | `ave-demo-005-staged-av-comparison` | Time-separated contrast of the three audio constructions | `exploratory` |

The labels are intentionally conservative. A passing Generator check is not independent evidence and cannot promote a label.

## Contract and package layout

Stable demo IDs are permanent. Each recipe carries an independent semantic `demo_version`, and its normalized declaration identity is `<demo_id>@<demo_version>`. Generator vendors the exact AVE Platform declaration `0.1.0` schema at SHA-256 `aca39c90191762cde5048dfefc6f732d9e0c43e2da668194f2cc6cb04175ab45`.

`contracts/ave-demo-recipe-1.1.0.schema.json` requires:

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
<demo-id>-recipe.json              source Generator recipe
<demo-id>-resolved-protocol.json   resolved Generator protocol
<demo-id>-declaration.json         normalized Platform 0.1.0 declaration
<demo-id>-declaration-mapping.json explicit fields not cleanly representable
render-manifest.pre.json           provenance written before media rendering
audio/stereo.wav                   analysis and distribution master
audio/left.wav, audio/right.wav    channel-isolated files
audio/stems/*.wav                  full-timeline construction stems
presentation-video.silent.mp4      deterministic explanatory visuals
presentation.mp4                   audio/video distribution preview
multimodal-detector*.mp4           Demo 005 unlabeled AV clock-analysis pair
generator-validation.json          same-repository integrity checks
verification-request.json          blind-analysis request without declared values
PACKAGE_README.md                   purpose, reproduction, limitations, safety
render-manifest.json               hashes and separated evidence records
```

For a four-region package, the resolved light plan and raw four-region preview are included as additional files.

The final manifest keeps these records separate:

- `generator_declaration`: normalized measurable targets and tolerances;
- `resolved_protocol`: the complete Generator rendering instruction set;
- `generator_validation`: same-repository measurements and integrity checks;
- `forensics_observation`: initially null, later supplied by AVE Forensics; and
- `field_level_agreement`: initially null, later supplied by AVE Forensics or a contract-defined adjudicator.

## Reproduce

```bash
.venv/bin/python -m ave_demo_generator validate all

.venv/bin/python -m ave_demo_generator build \
  contracts/examples/demos/ave-demo-001-binaural-construction.json

.venv/bin/python -m pytest -q
```

Generated media remains under ignored `output/`; source recipes, schemas, tests, and documentation remain tracked.

## Independent verification handoff

For Demo 1, the detector phase receives only `audio/stereo.wav` and the `detector_input` portion of `verification-request.json`. Forensics records the exact input hash and persists duration, carrier, interchannel-difference, routing, and peak observations without loading expected values or tolerances. Only afterward does the comparison phase load `ave-demo-001-binaural-construction-declaration.json` by hash and return a versioned observation record plus field-level agreement report.

For Demo 005, the authorized detector input is `multimodal-detector.mp4`. It muxes the rendered stereo master with a 60 fps text-free video whose two colored bars encode only the contemporaneous per-frame left/right RMS calculated on the same virtual clock. The verification request asks only for `clock_alignment` and explicitly attests that expected values, tolerances, target schedules, stage boundaries, and construction labels are absent. The labeled `presentation.mp4` is never the blind detector input.

Generator can adopt that report as an immutable attachment in a later package revision. Until then, Demo 1 remains `exploratory`, even though Generator's own black-box checks pass.

### 2026-09-29 trial analysis

The first packaged stereo WAV (`bf33db23ab1dbe60fce35c3a7ccc9cd1a016aa5e0cd69b2ce8c9dd57d5257517`) was analyzed with the current local AVE Forensics checkout. Its human-readable output measured 12.0 seconds, 440.00 Hz left, 450.00 Hz right, a 10.0 Hz candidate difference, peak 0.799988, and no periodic pulse. Its canonical evidence export preserved the exact input hash and no-pulse result, but did not emit canonical carrier/difference evidence objects or a field-level agreement record. The raw run also records that the Forensics checkout was dirty, so it is useful diagnostic evidence rather than a release-grade verification attachment.

This confirms both the signal's basic analyzability and the remaining contract work. Generator does not copy the human-readable findings into the reserved observation/agreement fields.

## Unresolved dependencies

- AVE Forensics needs a finalized cross-repository demo observation/agreement envelope. Its current analyzer can produce evidence for Demo 1, but the portfolio-specific field report remains external to this repository.
- Demo 2 needs independent reconstruction of a time-varying smooth AM envelope.
- Demo 3 needs an independent gate-rate, duty-cycle, and edge-shape observation contract.
- Demo 4 needs a visual-plan analyzer or field-level comparison contract; it makes no calibrated-luminance or physical-device-equivalence claim.
- Demo 5 still depends on AVE Forensics independently comparing the newly authorized multimodal detector artifact and completing its clean-provenance stage/clock report.
- Lumenate empirical exports remain optional provenance inputs. Null or incomplete device parameters are never filled by inference.

## Declaration mapping limitations

Declaration `0.1.0` cleanly represents scalar, interval, category, boolean, and single linear-curve measurement claims. It does not represent package policy/provenance fields, RGB/grayscale tuples, or a compound piecewise four-region schedule as one target. Those values remain in the hashed recipe and resolved protocol and are listed in each package's declaration-mapping report with `interpretation_invented: false`.

## Safety and claim boundary

These are offline engineering demonstrations, not exposure protocols. Digital amplitude is not calibrated SPL, RGB values are not calibrated luminance, and no package establishes photosensitivity safety, neurological entrainment, a desired mental state, therapeutic benefit, exact device equivalence, packet-to-photon latency, or subframe emitter phase.
