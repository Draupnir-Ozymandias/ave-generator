"""Synthetic color/highlight overlay on the accumulated-phase Vitality schedule."""

import argparse
import math
import sys
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw

from ave_light_renderer.canonical import canonical_sha256, file_sha256, load_json, write_json
from ave_light_renderer.compiler import compile_recipe
from ave_light_renderer.manifest import write_pre_render_manifest, write_final_manifest
from ave_light_renderer.paths import PROJECT_ROOT
from ave_light_renderer.renderer import frame_image, render_mp4
from tools.render_four_region_replication import validate_replication


def pulse_cycle_index(intervals, time_seconds):
    """Exact integrated frequency, including ramps; never frequency(t)*time."""
    time = Fraction(str(time_seconds))
    phase = Fraction(0)
    for interval in intervals:
        start = Fraction(interval['start_us'], 1_000_000)
        end = Fraction(interval['end_us'], 1_000_000)
        if time < start:
            break
        if interval['kind'] == 'pulse':
            duration = end - start
            local = min(time, end) - start
            curve = interval['frequency_hz']
            if curve['kind'] == 'constant':
                phase += Fraction(str(curve['value'])) * local
            else:
                f0 = Fraction(str(curve['start']))
                slope = (Fraction(str(curve['end'])) - f0) / duration
                phase += f0 * local + slope * local * local / 2
        if time < end:
            break
    return math.floor(phase)


def highlighted_rgb(base, mix, highlighted):
    return [round(v + mix * (255 - v)) for v in base] if highlighted else list(base)


def render(treatment_path, output_dir):
    treatment = load_json(treatment_path)
    if treatment['treatment_version'] != '1.0.0':
        raise ValueError('Unsupported visual treatment version')
    base_path = PROJECT_ROOT / treatment['base_recipe']
    if file_sha256(base_path) != treatment['base_recipe_sha256']:
        raise ValueError('Base recipe hash mismatch')
    reference = PROJECT_ROOT / treatment['reference_media']
    if file_sha256(reference) != treatment['reference_media_sha256']:
        raise ValueError('Reference media hash mismatch')
    base = validate_replication(load_json(base_path))
    recipe = deepcopy(base)
    recipe['recipe_id'] = treatment['treatment_id']
    recipe['output']['color_mode'] = 'rgb'
    recipe['source']['visual_treatment'] = treatment
    recipe['source']['visual_treatment_sha256'] = file_sha256(treatment_path)
    recipe['limitations'].extend(treatment['limitations'])
    palette = dict(zip(treatment['clockwise_order'], treatment['palette_rgb']))
    for region in recipe['regions']:
        for interval in region['intervals']:
            if interval['kind'] == 'pulse':
                interval['color'] = {'mode': 'rgb', 'value': palette[region['name']]}
                interval['intensity'] = {'kind': 'constant', 'value': treatment['intensity']}
    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / 'recipe.json'
    treatment_copy = output_dir / 'visual-treatment.json'
    write_json(recipe_path, recipe)
    write_json(treatment_copy, treatment)
    plan = compile_recipe(recipe, 120)
    intervals = base['regions'][0]['intervals']
    for frame in plan['frames']:
        cycle = pulse_cycle_index(intervals, Fraction(frame['frame_index'], 120))
        highlight = treatment['clockwise_order'][cycle % 4]
        frame['highlight_region'] = highlight
        frame['analytic_pulse_cycle'] = cycle
        for name, state in frame['regions'].items():
            if state['gate_on']:
                state['effective_rgb'] = highlighted_rgb(
                    palette[name], treatment['highlight_white_mix'], name == highlight
                )
    plan['visual_treatment'] = treatment
    plan['compiler_extension'] = 'ave-vibrant-treatment-1.0.0'
    plan.pop('resolved_plan_sha256')
    plan['resolved_plan_sha256'] = canonical_sha256(plan)
    plan_path = output_dir / 'resolved-plan.json'
    pre_path = output_dir / 'render-manifest.pre.json'
    write_json(plan_path, plan)
    pre = write_pre_render_manifest(pre_path, plan, PROJECT_ROOT)
    pre['visual_treatment'] = treatment
    pre['workflow_sha256'] = file_sha256(Path(__file__))
    write_json(pre_path, pre)
    video = output_dir / 'four-region-vibrant-300s.mp4'
    render_mp4(plan, video, size=640, gutter=8)
    # Include four consecutive analytic cycles, proving all highlight positions.
    selected = [0]
    for cycle in range(300, 304):
        selected.append(next(f['frame_index'] for f in plan['frames']
                             if f['analytic_pulse_cycle'] == cycle and f['regions']['top_left']['gate_on']))
    selected.append(len(plan['frames']) - 1)
    sheet = Image.new('RGB', (960, 740), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 12), 'WARNING: FLASHING LIGHT. Static contact sheet only. SYNTHETIC clockwise color highlight.', fill='white')
    for i, index in enumerate(selected):
        frame = plan['frames'][index]
        x, y = (i % 3) * 320, 60 + (i // 3) * 340
        sheet.paste(frame_image(frame, size=640, gutter=8).resize((300, 300)), (x, y))
        draw.text((x + 8, y + 306), f"{index / 120:.3f}s | {frame['highlight_region']}", fill='white')
    contact = output_dir / 'contact-sheet.png'
    sheet.save(contact)
    readme = output_dir / 'README.md'
    readme.write_text('# WARNING: flashing light; do not autoplay\n\n'
                      'Exploratory synthetic vibrant variant. 300s / 120 fps / no audio.\n'
                      'Full software intensity 1.0; uncalibrated. Colors and highlight are Generator choices.\n'
                      'Clockwise highlight advances per analytic pulse; one lap per four pulses.\n'
                      'Timing/duty and all four hard pulse gates follow the original recipe.\n'
                      'Short gates can be missed; no duty clamp. No safety, efficacy or Nova-equivalence claim.\n', encoding='utf-8')
    request = output_dir / 'verification-request.json'
    write_json(request, {'request_version': '1.0.0', 'request_type': 'independent_blind_visual_analysis',
                        'detector_input': {'path': video.name, 'sha256': file_sha256(video),
                                           'expected_values_present': False, 'expected_tolerances_present': False,
                                           'target_schedules_present': False},
                        'workflow': 'Observe and persist evidence before reading recipe or visual treatment.'})
    final = write_final_manifest(output_dir / 'render-manifest.json', pre, pre_path,
                                [recipe_path, treatment_copy, plan_path, video, contact, readme, request])
    print(final['outputs'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--treatment', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    render(args.treatment, args.output_dir)
