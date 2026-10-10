# Single-square white pulse render

Date: 2026-10-10. Status: **complete; ready for independent analysis**.
Evidence label: `exploratory`.

Single full 640×640 square; white RGB [255,255,255] at software intensity 1.0
during the original pulse ON gate, black RGB [0,0,0] during the OFF gate and
source off intervals. No colors, quadrants, internal gutters or audio. Exactly
300s at 120 fps. Source off: 0–1.5s and 298–300s. Original 34-interval Vitality
frequency/duty curves and accumulated phase remain unchanged. No duty clamp.

```sh
.venv/bin/python tools/render_single_square.py \
  --treatment contracts/examples/vitality-single-square-white-treatment.json \
  --output-dir output/single-square-white-300s
```

Output: `/Users/eric/Projects/media/ave_generator/output/single-square-white-300s`.
Primary filename: `single-square-white-300s.mp4`. Adjacent static contact sheet,
base timing recipe, single-square recipe, treatment, resolved plan, pre/final
manifests, warning README and blind request form the reproducible package.
The workflow pins the original timing recipe file SHA-256
`ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508`.
It uses the single-square extension rather than claiming the square conforms
to the four-region layout schema. Pixel output is driven by the resolved plan.

WARNING: flashing white light; do not autoplay. Full software intensity is
uncalibrated and does not establish exposure safety. No physiological,
therapeutic or Nova-equivalence claim. Frame sampling can miss short pulses.
Previous videos are preserved. New workflow source files remain uncommitted;
the render manifest honestly records dirty Git state and workflow hash.

## Completed validation

68 tests pass. FFprobe decoded 36,000 H.264 frames at 120 fps, 640×640,
duration 300.000000s, no audio stream. All eight manifest output hashes and
sizes match. Every virtual frame retains the original gate state, frequency,
duty and phase; RGB is exactly white for gate ON and black otherwise. Counts:
8467 white frames, 27113 active pulse-off black frames and 420 source-off black
frames. Static contact sheet inspected. Previous videos retain their hashes.

| Artifact | SHA-256 |
| --- | --- |
| MP4 | `5e3f6732715194039bec1176e0fedbf8309fca1ceb293068c1e120139657919a` |
| Recipe file | `3b94c61ae451883fe5fd58d343f79b91ada7eaa3bed2a0effede5c29210921ba` |
| Treatment file | `ea0a3fc2e33fe22c034b12b0d8a775488f7ff8ad28f80e19ffdb0b6786a52a45` |
| Plan file | `97f13552f386c5535f83585651a11575490fac303ddf1f01872619b98f0785f6` |
| Plan canonical record | `d93238b924f302723d5c8b4f6afad58ad0466f1862c79c198aaa2ed85fd1875d` |
| Final manifest | `2f4375b8f801924ddfcc3603e33077d2a4346d2b10f595749671324b16e21424` |
| Contact sheet | `71a3491a2b8baf989047a19960766d4c80d11cb46c015c1663513636b0b6ba34` |

Primary artifact:
`/Users/eric/Projects/media/ave_generator/output/single-square-white-300s/single-square-white-300s.mp4`.
Static review artifact: adjacent `contact-sheet.png`. Video was not autoplayed.
