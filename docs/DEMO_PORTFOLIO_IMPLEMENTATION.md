# AVE Demo Portfolio — Generator Implementation and Handoff

**Status date:** 2026-10-01
**Repository:** AVE Generator
**Implementation branch:** `codex/release-promotion`
**Promotion implementation revision:** `1fc698a444ccf732095ba5cc5de8fef3886691c8`

## Responsibility boundary

AVE Generator owns declarative recipes, deterministic synthesis, offline rendering, media/stem packaging, Generator-side build checks, and provenance manifests. AVE Forensics owns independent observations and field-level `agree`, `disagree`, or `unsupported` results. Lumenate Nova Forensics may supply evidence-backed light-pattern ideas with provenance and limitations, but it does not supply missing render values by inference and does not block synthetic demos.

The repositories exchange versioned, sanitized JSON and hashed media. Generator does not import either forensic repository at runtime.

## Tracked portfolio

| Order | Demo ID | Engineering distinction | Canonical label |
|---:|---|---|---|
| 1 | `ave-demo-001-binaural-construction` | Separate 440/450 Hz stereo carriers and declared 10 Hz difference | `verified` — 6 agree |
| 2 | `ave-demo-002-smooth-am-ramp` | 440 Hz carrier with continuous smooth amplitude modulation from 4–20 Hz | `verified` — 7 agree |
| 3 | `ave-demo-003-gated-pulse-contrast` | 440 Hz carrier with a hard 12 Hz, 25% duty gate | `verified` — 8 agree |
| 4 | `ave-demo-004-four-region-light` | Four independently scheduled synthetic light regions | `partially_verified` — 6 agree, 1 not evaluated |
| 5 | `ave-demo-005-staged-av-comparison` | Time-separated contrast of the three audio constructions | `partially_verified` — 11 agree, 2 unsupported |

The labels above come from the attached canonical AVE Forensics agreement reports, not Generator checks. Demo 004 leaves `light.recipe.identity` not evaluated because a source recipe hash is not observable from rendered pixels. Demo 005 leaves `stage.smooth_am.construction` and `stage.smooth_am.rate` unsupported because measured confidence `0.749983` is below the declared `0.75` threshold. No report contains `disagree` or `invalid_declaration` results.

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
forensics-agreement-report.json     immutable canonical report attachment
release-record.json                 exact claim groups and promotion hashes
```

For a four-region package, the resolved light plan and raw four-region preview are included as additional files.

The final manifest keeps these records separate:

- `generator_declaration`: normalized measurable targets and tolerances;
- `resolved_protocol`: the complete Generator rendering instruction set;
- `generator_validation`: same-repository measurements and integrity checks;
- `forensics_observation`: initially null, then a hash-only reference to the independent observation; and
- `field_level_agreement`: initially null, then an attached immutable AVE Forensics report reference.

The recipe and declaration retain their original authoring identity. Promotion is an overlay and does not rewrite them. It validates the exact vendored Platform agreement-report `0.1.0` schema at SHA-256 `f4a2ce98dc407b0aa7f40dcfc636de98e6c8d498feda84ecec9e5b3a36292315`, derives the evidence label independently, confirms every declaration claim has exactly one result, and refuses dirty Forensics provenance or detector-input drift.

## Reproduce

```bash
.venv/bin/python -m ave_demo_generator validate all

.venv/bin/python -m ave_demo_generator build \
  contracts/examples/demos/ave-demo-001-binaural-construction.json

.venv/bin/python -m ave_demo_generator promote-all

.venv/bin/python -m pytest -q
```

Generated media remains under ignored `output/`; source recipes, schemas, tests, and documentation remain tracked.

## Independent verification handoff

For Demo 1, the detector phase receives only `audio/stereo.wav` and the `detector_input` portion of `verification-request.json`. Forensics records the exact input hash and persists duration, carrier, interchannel-difference, routing, and peak observations without loading expected values or tolerances. Only afterward does the comparison phase load `ave-demo-001-binaural-construction-declaration.json` by hash and return a versioned observation record plus field-level agreement report.

For Demo 005, the authorized detector input is `multimodal-detector.mp4`. It muxes the rendered stereo master with a 60 fps text-free video whose two colored bars encode only the contemporaneous per-frame left/right RMS calculated on the same virtual clock. The verification request asks only for `clock_alignment` and explicitly attests that expected values, tolerances, target schedules, stage boundaries, and construction labels are absent. The labeled `presentation.mp4` is never the blind detector input.

Generator now adopts each canonical report as an immutable attachment after validating it. Presentation cards paginate the canonical label, result counts, every agreed claim ID, and every unsupported or not-evaluated claim with its exact reason. Generator's own black-box checks remain separate and cannot promote a label.

## 2026-10-01 release-candidate promotion

All five packages were promoted from clean Generator revision `1fc698a444ccf732095ba5cc5de8fef3886691c8`. The analyzed detector inputs remained byte-identical. Generated media and package files remain ignored build artifacts; this table is the tracked promotion record.

| Demo | Detector input SHA-256 | Agreement report SHA-256 | Promoted presentation SHA-256 | Package outputs SHA-256 | Final manifest SHA-256 |
|---|---|---|---|---|---|
| `ave-demo-001-binaural-construction` | `bf33db23ab1dbe60fce35c3a7ccc9cd1a016aa5e0cd69b2ce8c9dd57d5257517` | `7e2c5392d4f0121675c46b112b7c365982cfb72ee2e1743f7965b4f8d4ee9aed` | `736f6f5703d0e03555b063e908d9533b280b5af29e0089c4f33867b868c35f18` | `d84ae0c97f2a311389f0e7a156457cae45bd3f905cc26246de251c9b6bb5b66e` | `79898611588cc6b981336214e25688680c9a101bd9e86a3d1f51055f7a553937` |
| `ave-demo-002-smooth-am-ramp` | `0ace18a789ebbcc01fa6e7ddf307b8bf75658b2681bc146880e5a389ebd72925` | `7433edd5c7f25f19a0629f529031f7e2bd7288a347d22f316ef6daa76d1a953a` | `5ff972d21a3f44265acea831c838659f708690b159dea4ebfd69f5db286b424b` | `2b5751e6dd189a59dcf89a1ebe6dee9858bf8aee4a7e371d3285821d17d21d4a` | `5f81a8f5b364b2e27b901a56532a743aeab087923f868a6f594761511eebc541` |
| `ave-demo-003-gated-pulse-contrast` | `1c709614de6433b50fa5032df3baa89d3574d33750115934ca662e893f5901b0` | `7dd6382d737c90acfeeb8dad02c9ac0036cc0d91f9befddb5e45ae01a54c01a7` | `af41ee0479f2a6bd6d5324fd2edb909de2c91758ae2b04fb8f171a48e5ac1c11` | `c4803f7e29eef79b69d14b764894a621c374dc92cfe7c48e5f699f43ed0fc7ab` | `d77b35003e93a7ed7129124b00612af84711989b1179afcb858930cf26d5e4e1` |
| `ave-demo-004-four-region-light` | `e168b28756061651f13f67bdaf96ff7b0c943171d4d522e205010847951f9cfc` | `056c69e3367abea21ae7a81d75cbab302e68abfce5a26e979da154a737d3579f` | `34256625db476485c9b62c33636ed2f8b9a1c023b23992be5ab53b52d1f88466` | `25af0969f263c449cee961303af6f98f4ef7010d649c426099b65250ea9dc069` | `f2b5132fd5dcaddb1efdf526d9ced99f052a29d915060df57fa655f961e2db73` |
| `ave-demo-005-staged-av-comparison` | `3ee279c73e3484b5d6b28969dd444049c94f537c5ed5a779925e21e43b261822` | `df0badb738ff8943c1ce32a017a44c56857ecb3cde259b6e2f5818198d41156e` | `ab6dde0424773ce2160f2d76a1cf8fe26f8af035bee843b425c245eba1849f7d` | `78c6f4f978bad6b8ad7978b8d941ede2d8d8856fd846f55e2b4112af682b33fa` | `3a7bd4783c5a51dea79395b268bfc555cec9b0fc06b2bb6b83ed5246bb1b0d4a` |

The portfolio release-index content SHA-256 is `5e3766fd2eab8916f00efb5f8c6f9b5d109b79d0870e162f678a4b00e61c6206`.

### 2026-09-29 trial analysis

The first packaged stereo WAV (`bf33db23ab1dbe60fce35c3a7ccc9cd1a016aa5e0cd69b2ce8c9dd57d5257517`) was analyzed with the current local AVE Forensics checkout. Its human-readable output measured 12.0 seconds, 440.00 Hz left, 450.00 Hz right, a 10.0 Hz candidate difference, peak 0.799988, and no periodic pulse. Its canonical evidence export preserved the exact input hash and no-pulse result, but did not emit canonical carrier/difference evidence objects or a field-level agreement record. The raw run also records that the Forensics checkout was dirty, so it is useful diagnostic evidence rather than a release-grade verification attachment.

This confirms both the signal's basic analyzability and the remaining contract work. Generator does not copy the human-readable findings into the reserved observation/agreement fields.

## Remaining limitations, not release blockers

- Demo 004 source-recipe identity remains unobservable from rendered pixels and is explicitly `not_evaluated`.
- Demo 005 smooth-AM construction and rate remain `unsupported`; confidence `0.749983` must not be rounded to the `0.75` support threshold.
- Encoded video cadence is not physical display refresh, encoded AV alignment is not acoustic/display latency, digital amplitude is not calibrated SPL, and RGB is not calibrated luminance.
- Lumenate empirical exports remain optional provenance inputs. Null or incomplete device parameters are never filled by inference.
- Platform owns final public release review; Generator has completed the requested share-ready release candidates.

## Declaration mapping limitations

Declaration `0.1.0` cleanly represents scalar, interval, category, boolean, and single linear-curve measurement claims. It does not represent package policy/provenance fields, RGB/grayscale tuples, or a compound piecewise four-region schedule as one target. Those values remain in the hashed recipe and resolved protocol and are listed in each package's declaration-mapping report with `interpretation_invented: false`.

## Safety and claim boundary

These are offline engineering demonstrations, not exposure protocols. Digital amplitude is not calibrated SPL, RGB values are not calibrated luminance, and no package establishes photosensitivity safety, neurological entrainment, a desired mental state, therapeutic benefit, exact device equivalence, packet-to-photon latency, or subframe emitter phase.
