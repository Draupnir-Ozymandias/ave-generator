"""Render a configured single square from the original integrated pulse gates."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

from ave_light_renderer.canonical import canonical_sha256, file_sha256, load_json, write_json
from ave_light_renderer.compiler import compile_recipe
from ave_light_renderer.manifest import write_pre_render_manifest, write_final_manifest
from ave_light_renderer.paths import PROJECT_ROOT
from tools.render_four_region_replication import validate_replication


def square_state(state, treatment):
    if state['kind'] == 'off':
        return 'source_off', list(treatment['source_off_rgb'])
    if state['gate_on']:
        return treatment.get('on_state', 'pulse_on_green'), list(treatment['on_rgb'])
    return treatment.get('off_state', 'pulse_off_magenta'), list(treatment['off_rgb'])


def render(treatment_path, output_dir):
    treatment = load_json(treatment_path)
    if treatment['treatment_version'] != '1.0.0':
        raise ValueError('Unsupported single-square treatment version')
    base_path = PROJECT_ROOT / treatment['base_recipe']
    if file_sha256(base_path) != treatment['base_recipe_sha256']:
        raise ValueError('Base recipe hash mismatch')
    base = validate_replication(load_json(base_path))
    original_plan = compile_recipe(base, treatment['refresh_hz'])
    output_dir.mkdir(parents=True, exist_ok=True)
    base_copy = output_dir / 'base-timing-recipe.json'
    base_copy.write_bytes(base_path.read_bytes())
    recipe_path = output_dir / 'recipe.json'
    recipe = {
        'recipe_version': '1.0.0', 'recipe_id': treatment['treatment_id'],
        'duration_us': base['duration_us'], 'timing_recipe_sha256': file_sha256(base_path),
        'clock': base['clock'], 'visual_treatment': treatment,
        'source': base['source'],
        'active_timing_intervals': base['regions'][0]['intervals'],
    }
    write_json(recipe_path, recipe)
    treatment_copy = output_dir / 'visual-treatment.json'
    write_json(treatment_copy, treatment)
    frames = []
    for frame in original_plan['frames']:
        state = frame['regions']['top_left']
        name, rgb = square_state(state, treatment)
        frames.append({
            'frame_index': frame['frame_index'], 'scheduled_time_ns': frame['scheduled_time_ns'],
            'state': name, 'effective_rgb': rgb, 'source_interval_id': state['interval_id'],
            'gate_on': state['gate_on'], 'frequency_hz': state['frequency_hz'],
            'duty_cycle': state['duty_cycle'], 'phase_cycles': state['phase_cycles'],
        })
    plan = {
        'plan_version': 'single-square-1.0.0', 'renderer_version': 'single-square-1.0.0',
        'recipe_id': recipe['recipe_id'], 'recipe_sha256': canonical_sha256(recipe),
        'source': recipe['source'], 'duration_us': base['duration_us'],
        'refresh_hz': treatment['refresh_hz'], 'frame_count': len(frames),
        'source_resolved_plan_sha256': original_plan['resolved_plan_sha256'],
        'transitions': original_plan['transitions'],
        'timing_error_summary_us': original_plan['timing_error_summary_us'],
        'warnings': treatment['limitations'], 'visual_treatment': treatment, 'frames': frames,
    }
    plan['resolved_plan_sha256'] = canonical_sha256(plan)
    plan_path = output_dir / 'resolved-plan.json'
    write_json(plan_path, plan)
    pre_path = output_dir / 'render-manifest.pre.json'
    pre = write_pre_render_manifest(pre_path, plan, PROJECT_ROOT)
    pre['renderer']['name'] = 'ave-single-square-renderer'
    pre['renderer']['version'] = '1.0.0'
    pre['workflow_sha256'] = file_sha256(Path(__file__))
    pre['visual_treatment'] = treatment
    write_json(pre_path, pre)
    video = output_dir / treatment.get('video_filename', 'single-square-green-magenta-300s.mp4')
    size = treatment['size_px']
    on_state = treatment.get('on_state', 'pulse_on_green')
    off_state = treatment.get('off_state', 'pulse_off_magenta')
    images = {name: np.full((size, size, 3), rgb, dtype=np.uint8)
              for name, rgb in [('source_off', treatment['source_off_rgb']),
                               (on_state, treatment['on_rgb']),
                               (off_state, treatment['off_rgb'])]}
    writer = imageio.get_writer(video, fps=plan['refresh_hz'], codec='libx264', macro_block_size=None,
                               ffmpeg_log_level='error', output_params=['-pix_fmt', 'yuv420p',
                               '-movflags', '+faststart', '-metadata', 'creation_time=1970-01-01T00:00:00Z'])
    try:
        for frame in plan['frames']:
            writer.append_data(images[frame['state']])
    finally:
        writer.close()
    selected = [0]
    for name in [on_state, off_state]:
        selected.append(next(f['frame_index'] for f in frames
                             if f['frame_index'] >= 37 * 120 and f['state'] == name))
    selected.append(len(frames) - 1)
    sheet = Image.new('RGB', (1280, 390), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 12), treatment.get('contact_caption', 'WARNING: FLASHING LIGHT. STATIC REVIEW ONLY. Exploratory synthetic complementary-color switching.'), fill='white')
    for i, index in enumerate(selected):
        frame = frames[index]
        x = i * 320
        sheet.paste(Image.fromarray(images[frame['state']]).resize((300, 300)), (x, 50))
        draw.text((x + 8, 360), f"{index / 120:.3f}s | {frame['state']}", fill='white')
    contact = output_dir / 'contact-sheet.png'
    sheet.save(contact)
    readme = output_dir / 'README.md'
    readme.write_text(treatment.get('readme_text', '# WARNING: flashing complementary colors; do not autoplay\n\n'
                      'Single 640px square, no quadrants or gutters. 300 seconds at 120 fps, no audio.\n'
                      'Green during original pulse ON; magenta during pulse OFF within active intervals.\n'
                      'Source off intervals 0–1.5s and 298–300s stay black.\n'
                      'Synthetic color treatment, software intensity 1.0; uncalibrated.\n'
                      'Original timing/duty/phase retained; no duty clamp.\n'
                      'Exploratory; no exposure-safety, therapeutic or Nova-equivalence claim.\n'), encoding='utf-8')
    request_path = output_dir / 'verification-request.json'
    write_json(request_path, {
        'request_version': '1.0.0', 'request_type': 'independent_blind_visual_analysis',
        'detector_input': {'path': video.name, 'sha256': file_sha256(video),
                           'expected_values_present': False, 'expected_tolerances_present': False,
                           'target_schedules_present': False},
        'workflow': 'Observe color-state transitions before reading recipe or treatment; use chromatic states rather than black/on threshold alone.',
    })
    final = write_final_manifest(output_dir / 'render-manifest.json', pre, pre_path,
                                [base_copy, recipe_path, treatment_copy, plan_path, video, contact, readme, request_path])
    print(final['outputs'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--treatment', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    render(args.treatment, args.output_dir)
