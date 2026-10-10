"""Render a pinned 300-second matched-region recipe and a static review sheet."""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ave_light_renderer.canonical import file_sha256, load_json, write_json
from ave_light_renderer.compiler import compile_recipe, plan_summary
from ave_light_renderer.manifest import write_pre_render_manifest, write_final_manifest
from ave_light_renderer.paths import PROJECT_ROOT
from ave_light_renderer.renderer import frame_image
from ave_light_renderer.validation import validate_recipe


def validate_replication(recipe):
    validate_recipe(recipe)
    if recipe['duration_us'] != 300_000_000:
        raise ValueError('Primary replication recipe must be exactly 300 seconds')
    schedules = []
    for region in recipe['regions']:
        intervals = region['intervals']
        if intervals[0]['kind'] != 'off' or intervals[-1]['kind'] != 'off':
            raise ValueError('Every region must start and end off')
        schedules.append([{k: v for k, v in interval.items() if k != 'interval_id'} for interval in intervals])
    if any(schedule != schedules[0] for schedule in schedules[1:]):
        raise ValueError('Primary replication requires matched synchronous region schedules')
    return recipe


def decorated_frame(frame, size=640):
    image = Image.new('RGB', (size, size + 80), 'black')
    image.paste(frame_image(frame, size=size, gutter=8), (0, 80))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
    except OSError:
        font = ImageFont.load_default(size=16)
    draw.text((12, 10), 'WARNING: FLASHING LIGHT — PHOTOSENSITIVITY RISK', fill=(255, 190, 70), font=font)
    draw.text((12, 35), 'EXPLORATORY engineering render. No exposure-safety claim.', fill='white', font=font)
    draw.text((12, 58), 'Matched four-region timing; display intensity is uncalibrated.', fill=(180, 180, 180), font=font)
    return image


def render(recipe_path, expected_sha256, output_dir):
    if file_sha256(recipe_path) != expected_sha256:
        raise ValueError('Producer recipe hash does not match expected SHA-256')
    recipe = validate_replication(load_json(recipe_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_copy = output_dir / 'recipe.json'
    recipe_copy.write_bytes(recipe_path.read_bytes())
    plan = compile_recipe(recipe, 120)
    total_cycles = 0.0
    represented_cycles = set()
    intervals = recipe['regions'][0]['intervals']
    segment_base = {}
    for interval in intervals:
        segment_base[interval['interval_id']] = total_cycles
        if interval['kind'] == 'pulse':
            frequency = interval['frequency_hz']
            mean = frequency.get('value', (frequency.get('start', 0) + frequency.get('end', 0)) / 2)
            total_cycles += mean * (interval['end_us'] - interval['start_us']) / 1e6
    by_id = {interval['interval_id']: interval for interval in intervals}
    for frame in plan['frames']:
        state = frame['regions']['top_left']
        if state['gate_on']:
            interval = by_id[state['interval_id']]
            t = frame['frame_index'] / 120 - interval['start_us'] / 1e6
            duration = (interval['end_us'] - interval['start_us']) / 1e6
            frequency = interval['frequency_hz']
            start = frequency.get('value', frequency.get('start'))
            slope = 0 if frequency['kind'] == 'constant' else (frequency['end'] - start) / duration
            phase = segment_base[state['interval_id']] + start * t + 0.5 * slope * t * t
            represented_cycles.add(math.floor(phase + 1e-9))
    quantization_path = output_dir / 'gate-quantization.json'
    write_json(quantization_path, {
        'version': '1.0.0', 'refresh_hz': 120, 'total_analytic_cycles': total_cycles,
        'analytic_gate_count': math.ceil(total_cycles),
        'gates_with_at_least_one_on_sample': len(represented_cycles),
        'gates_without_on_sample': math.ceil(total_cycles) - len(represented_cycles),
        'on_frame_count': sum(f['regions']['top_left']['gate_on'] for f in plan['frames']),
        'method': 'For this continuous-phase, single-active-span recipe, compare analytic cycle IDs against virtual-frame on samples.',
        'limitations': ['Generator diagnostic, not independent encoded-video observation.',
                        'Each visible gate is quantized to one or more 8.333ms frames; short gates can be missed.'],
    })
    readme = output_dir / 'README.md'
    readme.write_text('# WARNING: flashing light / photosensitivity risk\n\n'
                      'Do not autoplay. This exploratory offline engineering video is not an exposure protocol.\n'
                      'Exactly 300 seconds, 120 fps; four matched regions and black gutters.\n'
                      'Active schedule: 1.5–298s; source-declared off: 0–1.5s and 298–300s.\n'
                      'No audio. Software intensity 0.25 is not calibrated luminance or a safe exposure level.\n'
                      'Short gates may be missing due to frame sampling; see gate-quantization.json.\n'
                      'No neurological, therapeutic, safety or Nova-equivalence claim.\n', encoding='utf-8')
    plan_path = output_dir / 'resolved-plan.json'
    pre_path = output_dir / 'render-manifest.pre.json'
    write_json(plan_path, plan)
    pre = write_pre_render_manifest(pre_path, plan, PROJECT_ROOT)
    pre['presentation'] = {'width': 640, 'height': 640, 'warning_banner_height': 0,
                           'evidence_maturity': 'exploratory', 'audio': False}
    write_json(pre_path, pre)
    video = output_dir / 'four-region-300s.mp4'
    writer = imageio.get_writer(video, fps=120, codec='libx264', macro_block_size=None,
                               ffmpeg_log_level='error', output_params=['-pix_fmt', 'yuv420p',
                               '-movflags', '+faststart', '-metadata', 'creation_time=1970-01-01T00:00:00Z'])
    try:
        for frame in plan['frames']:
            writer.append_data(np.asarray(frame_image(frame, size=640, gutter=8)))
    finally:
        writer.close()
    # Still images only: choose timeline landmarks and first on-frame nearby.
    sheet = Image.new('RGB', (960, 3 * 270), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    times = [0, 5, 15, 37, 56, 100, 160, 230, 299.99]
    for index, seconds in enumerate(times):
        selected = min(int(seconds * 120), len(plan['frames']) - 1)
        if 0 < seconds < 299:
            for candidate in range(selected, min(selected + 120, len(plan['frames']))):
                if plan['frames'][candidate]['regions']['top_left']['gate_on']:
                    selected = candidate
                    break
        thumb = decorated_frame(plan['frames'][selected]).resize((240, 270))
        x, y = (index % 3) * 320, (index // 3) * 270
        sheet.paste(thumb, (x, y))
        draw.text((x + 243, y + 100), f'{selected / 120:.3f}s', fill='white')
    contact = output_dir / 'contact-sheet.png'
    sheet.save(contact)
    request_path = output_dir / 'verification-request.json'
    write_json(request_path, {
        'request_version': '1.0.0', 'request_type': 'independent_blind_visual_analysis',
        'requested_observation_metrics': ['duration_seconds', 'frame_count', 'refresh_rate_hz',
                                         'region_count', 'region_state_equality', 'off_intervals',
                                         'rising_edges', 'encoded_duty', 'windowed_rate'],
        'artifact': {'path': video.name, 'sha256': file_sha256(video)},
        'detector_input': {'path': video.name, 'media_type': 'video/mp4', 'sha256': file_sha256(video),
                           'expected_values_present': False, 'expected_tolerances_present': False,
                           'target_schedules_present': False, 'stage_boundaries_present': False,
                           'construction_labels_present': False},
        'note': 'Clean four-region video; warnings are in adjacent static documentation. Persist observations before reading recipe or plan.',
    })
    final = write_final_manifest(output_dir / 'render-manifest.json', pre, pre_path,
                                [recipe_copy, plan_path, video, contact, request_path, quantization_path, readme])
    print(plan_summary(plan), flush=True)
    print(final['outputs'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    render(args.recipe, args.expected_sha256, args.output_dir)
