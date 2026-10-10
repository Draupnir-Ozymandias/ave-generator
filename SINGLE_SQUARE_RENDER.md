# Single-square green/magenta render

Date: 2026-10-10. Status: **complete; ready for independent analysis**.
Evidence label: `exploratory`.

The new synthetic treatment fills one full 640×640 square, with no quadrants,
internal gutters, labels, or rotation. Green [0,255,0] corresponds to the original
Vitality pulse ON state; magenta [255,0,255] corresponds to pulse OFF during the
active interval. Source off intervals 0–1.5s and 298–300s remain black. Total
duration is exactly 300s at 120 fps with no audio. Software intensity is 1.0.

This interpretation follows Platform's relayed instruction. It changes the
active optical blackout into magenta, so the result is complementary-color
switching rather than a grayscale light-pulse reproduction. Colors/intensity
are synthetic and do not claim captured Lumenate behavior. Original duty,
frequency, integrated phase and segment timing are retained. Narrow green gates
can be omitted by 120 fps sampling; no duty is increased.

## Reproduce

```sh
.venv/bin/python tools/render_single_square.py \
  --treatment contracts/examples/vitality-single-square-treatment.json \
  --output-dir output/single-square-green-magenta-300s
```

The workflow pins the original 34-interval recipe at SHA-256
`ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508`.
It compiles the original accumulated-phase virtual plan, then maps each frame's
on/off state to the declared complementary RGB. The standalone single-square
recipe and plan use extension versions `recipe_version: 1.0.0` and
`plan_version: single-square-1.0.0`; they are not claimed to conform to the
four-region recipe schema. The original four-region timing recipe is attached
separately. Pixel rendering consumes only the resolved single-square frames.
The manifest records Git dirty state and workflow hash before rendering.

Output directory:
`/Users/eric/Projects/media/ave_generator/output/single-square-green-magenta-300s`.
Files: `single-square-green-magenta-300s.mp4`, `contact-sheet.png`, `recipe.json`,
`base-timing-recipe.json`, `visual-treatment.json`, `resolved-plan.json`,
pre/final manifests, README, and a blind verification request.

Forensics should measure chromatic-state transitions; a black-versus-nonblack
detector alone cannot recover active green/magenta gates. Persist observations
before reading the recipe and treatment. Label promotion remains external.

WARNING: flashing complementary colors; do not autoplay. Full software intensity
does not establish calibrated luminance or exposure safety. No neurological,
therapeutic, safety, optical duty, latency, or Nova-equivalence claim is made.
All previous artifacts are preserved. New source files remain uncommitted;
media and generated JSON remain ignored output artifacts.

## Validation and artifact identities

67 tests pass. FFprobe decoded exactly 36,000 H.264 frames, 640×640, 120 fps,
300.000000 seconds and no audio. All eight output hashes and file sizes match
the final manifest. Every virtual frame retains original frequency/duty/phase/
gate state. Static contact sheet reviewed: full square without subdivisions.
Virtual counts: green 8467 frames, magenta 27113 frames, source black 420 frames.
No video was autoplayed. Previous grayscale and vibrant MP4 hashes are unchanged.

| Artifact | SHA-256 |
| --- | --- |
| MP4 | `98c596729ff6c26a2fb9b28ff3557d6f8e90626bc505dc5081a37d0fe0ba3274` |
| Recipe file | `d2e0dc087e2978f8f8be9570316862fad42fff44dfbbd1bf0da7bf669fc72d27` |
| Treatment file | `c8d080bd08772ce947d39dc5f622260c20a6177ac86500a6afafff7c84cc0763` |
| Plan file | `4951b6bcac8d7f683c203c4bdf3521a4c6ea5d01aef041c493cb9caaab6876ef` |
| Plan canonical record | `03f3c4f99488c8bf27667fbf4092cfa40dce46b76b16c75b69cd0326fdd6cdb4` |
| Final manifest | `92b6398c19fae1d987ee3ca73714030d7853aad25914647a9e845f0f01a3598a` |
| Contact sheet | `44b2e9785dabed8ffc15a3757f4fe3615371cca208d961b6aae752077c33d3fe` |

Primary artifact:
`/Users/eric/Projects/media/ave_generator/output/single-square-green-magenta-300s/single-square-green-magenta-300s.mp4`.
Static review artifact: adjacent `contact-sheet.png`.
