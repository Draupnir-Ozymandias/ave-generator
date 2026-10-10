# Vibrant five-minute four-region variant

Date: 2026-10-10. Status: **complete; ready for independent analysis**.
Evidence maturity: `exploratory`.

Reference stills inspected at 1.0s and 2.5s from
`output/four-region-repro/four-region-preview.mp4`, SHA-256
`e168b28756061651f13f67bdaf96ff7b0c943171d4d522e205010847951f9cfc`.
Orange, blue, green and magenta were visible. Base palette from that reference's
resolved plan is TL [255,80,20], TR [40,160,255], BR [220,80,255],
BL [120,255,80]. The original reference and grayscale 300s replication are preserved.

## Visual interpretation

All four base colors use normalized software intensity 1.0. The dominant
quadrant is tinted by mixing 45% white into its color; other quadrants retain
the saturated full-intensity palette. Highlight advances clockwise once per
analytic pulse: TL → TR → BR → BL. One full lap spans four pulses. This follows
Platform's clarified instruction and avoids hiding a complete rotation inside
a narrow on-gate. Accumulated pulse phase is integrated exactly through the
frequency ramps; missed encoded pulses still advance the analytic highlight.

All four gates retain the 34-interval source timeline, original duty curves,
and phase policy. No gate is lengthened and there is no duty clamp. Total
duration is 300s; source off intervals remain 0–1.5s and 298–300s. Output is
640×640, 120 fps H.264, black gutters, no audio. Color, full intensity, and
rotation are synthetic Generator choices, not observed Lumenate regional behavior.

The standard light recipe embeds the versioned visual treatment under source
metadata. The resolved plan declares compiler extension
`ave-vibrant-treatment-1.0.0`, applies the treatment to effective pixels, then
recomputes its canonical hash. The pixel renderer consumes that final plan.
Reproduction requires the following workflow, rather than the generic light
CLI alone, which does not implement this synthetic visual extension.

```sh
.venv/bin/python tools/render_four_region_vibrant.py \
  --treatment contracts/examples/vitality-vibrant-treatment.json \
  --output-dir output/four-region-vibrant-300s
```

The workflow pins base recipe and reference-media hashes. It records Git state
and workflow hash before rendering. New sources are uncommitted, so provenance
reports the working tree as dirty. This is not a clean-source release.

## Artifacts

Output directory:
`/Users/eric/Projects/media/ave_generator/output/four-region-vibrant-300s`.
Completed files: `four-region-vibrant-300s.mp4`, `contact-sheet.png`, `recipe.json`,
`visual-treatment.json`, `resolved-plan.json`, pre/final manifests,
`verification-request.json`, and warning README.

WARNING: flashing light / photosensitivity risk. Do not autoplay. Intensity 1.0
is a software setting, not calibrated luminance or a safe exposure level.
No physiological, therapeutic, safety or Nova-equivalence claim is made.
Forensics must observe encoded output independently before any label promotion.

## Completed validation

66 tests pass. FFprobe decoded exactly 36,000 frames at 120 fps, 640×640 H.264,
duration 300.000000s, with no audio stream. All seven manifest output hashes and
sizes validate. All 36,000 virtual frames retain the original frequency, duty,
phase and gate state across all four regions. Endpoint frames are black. The
original grayscale MP4 retains SHA-256
`ec3bcf1ffbf79250cdf407f9c88b7d91a352cba5171e7f09d91a4f16f711091e`.
Contact sheet inspected and confirms the four consecutive clockwise highlight
positions. No video was played automatically.

| Artifact | SHA-256 |
| --- | --- |
| MP4 | `579cfb266f88c7ee4eb3e83bb95a3d89d44a44cb8b230c6abb29a33af6b305e5` |
| Recipe file | `03116d99be9ff99f45dd1c350baf6be998fa9d34051b2dad31db137a69096425` |
| Visual treatment file | `ad91d5c9eb0bc4071a0cc80f0a7014b8d445fa41bb7136e65401cff823cb9559` |
| Resolved plan file | `c4d308e0243a1c83b596e3ecb80bff7a50f3918fdd0ca204cb74556aa1ae78ae` |
| Resolved plan canonical record | `3c05225e940bbadf309def27adddb7ee45daa49437ec29176b3874ec9c5aeb8b` |
| Final manifest | `57f096b227b5a790a709772b629d8880b77581ba3494a37280e5a44c05667ed8` |
| Contact sheet | `0ab344daf03a8854f04a67d537b15139bffe4e1f2861524e8cb5a55d0c84a731` |

Direct primary media path:
`/Users/eric/Projects/media/ave_generator/output/four-region-vibrant-300s/four-region-vibrant-300s.mp4`.
The static review path is the adjacent `contact-sheet.png`. These outputs are
ignored generated artifacts; new workflow, treatment and tests are uncommitted.
