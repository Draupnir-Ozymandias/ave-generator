# Five-minute four-region render

Date: 2026-10-10. Status: **artifact ready for independent Forensics analysis**.
Rendered 36,000 frames from the reviewed 34-interval Vitality schedule.
Independent encoded-video verification remains pending.

Primary detector/reference artifact:
`/Users/eric/Projects/media/ave_generator/output/four-region-replication-300s/four-region-300s.mp4`

MP4 SHA-256: `ec3bcf1ffbf79250cdf407f9c88b7d91a352cba5171e7f09d91a4f16f711091e`.
Static contact sheet:
`/Users/eric/Projects/media/ave_generator/output/four-region-replication-300s/contact-sheet.png`.
This is a new exploratory replication artifact; accepted Demo 004 and Demo 005
release packages have not been replaced.

Repository: `/Users/eric/Projects/media/ave_generator` (underscore). The former
hyphen path does not exist. Existing main and all five accepted portfolio demos
are preserved.

The primary output will be exactly 300 seconds at 120 fps, with four matched
synchronous regions, black gutters, and source-declared black intervals at
0–1.5s and 298–300s (active interval 1.5–298s). Warnings accompany the static
contact sheet and README; the detector video has clean pixels. Display color, normalized intensity,
layout, and phase are explicit Generator choices. Capture evidence does not
establish physical or physiological equivalence.

The nine files pinned by Lumenate's existing handoff `SOURCE_MANIFEST.json` were
verified successfully, as did all four underlying catalog source artifacts.
The new replication brief is pinned at SHA-256
`12fdba74698043a4b2e67bd9f00c8926eaeed3380b8c58e9f8b1360e15dd86c2`.
Its table was manually transcribed into the versioned Generator recipe
`contracts/examples/vitality-matched-four-region-300s.json`; no generic prose
adapter or inference from null fields was used. Recipe file SHA-256:
`ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508`.

## Reproduce

```sh
.venv/bin/python tools/render_four_region_replication.py \
  --recipe contracts/examples/vitality-matched-four-region-300s.json \
  --expected-sha256 ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508 \
  --output-dir output/four-region-replication-300s
```

The renderer verifies recipe hash, exact duration, matched region schedules,
and initial/final off intervals before compiling. It integrates instantaneous
frequency through adjacent active intervals and resets once at 1.5s.
Color is white, normalized software intensity 0.25, effective on RGB [64,64,64],
region canvas 640×640, black gutter parameter 8px. No audio is included.
The run records the current main commit with a dirty flag because this new
workflow is not yet committed; it does not claim clean-source release provenance.

Short 1% duty gates can be shorter than one 8.333ms frame. Gate visibility
diagnostics count represented versus missed analytic cycles. This is a Generator
diagnostic and is separate from Forensics observations; duty is never clamped.

Validation: 64 tests pass. No physiological equivalence, therapeutic benefit,
exposure safety, calibrated luminance, optical duty, physical phase, or latency
claim is made. Initial evidence label: `exploratory`.

Completed outputs: ignored `output/four-region-replication-300s/`, containing the
recipe, resolved plan, pre/final manifests, MP4, static contact sheet, and blind
verification request. No autoplay or real-time player is used.

## Completed validation and hashes

FFprobe decoded all 36,000 frames: H.264, 640×640, constant 120/1 fps,
exact duration 300.000000 seconds, no audio stream. Static contact sheet reviewed.
All segment transitions land on exact frame boundaries (maximum transition
error 0µs); individual pulse gates remain frame-quantized.

| Artifact | SHA-256 |
| --- | --- |
| MP4 | `ec3bcf1ffbf79250cdf407f9c88b7d91a352cba5171e7f09d91a4f16f711091e` |
| Recipe file | `ad17b27b1f70c5bc797ba517ac315497a8bea81db6f07c3eb7cd268226bd9508` |
| Recipe canonical record | `ecf1275d375eb674eb787ccba3748d459dadb20fa0d12c6d0d82f35eaac59f1b` |
| Resolved plan file | `8b4e4d6e3ea80dde42da5906a6b7fbc7abff6640b0ec68f9b6eedff99899d1ae` |
| Resolved plan canonical record | `dad2426472c1d6473c6441fa0c1acd366b85893e09bca0c6ca8f76cc4dfbbd2b` |
| Final manifest | `fa896463a67397e91efeda0645fff1dbd20b117460270090ab8dcab18e01379b` |
| Contact sheet | `585423e222e7eb55b91ce23bba56558bead46fd2489182e811a3e3b61e791a47` |
| Blind request | `29ebfbf1875cfd73d0eae8f41a6bb76e1ae1c1964bb3df78938db766ddfdca78` |

Virtual-plan gate diagnostics: 3160.2 accumulated cycles, 3161 analytic gate
opportunities, 3090 cycles represented by at least one on sample, 71 without an
on sample; total on frames 8467. This illustrates the 120 fps visibility deficit
at narrow duty values. It does not measure physical pulses or encoded-video
agreement. There is no 60 fps or visibility-enhanced derivative in this package.

Forensics should first consume only the clean MP4 and blind request, persist
streaming region/timing observations, then compare the separately provided
recipe and plan. The lightweight request is for this new replication study;
it is not a portfolio declaration/agreement record and has no assigned stable
portfolio demo ID. Platform owns subsequent identity assignment and evidence
label promotion. `FOUR_REGION_VALIDATION.md` in Forensics records the long-video
streaming prerequisite and measurement limits. No independent result is claimed
here.
