import argparse
import json
import sys
from pathlib import Path

from scipy.io import wavfile

from ave_light_renderer.canonical import load_json, write_json

from .errors import AudioGeneratorError, VerificationError
from .forensics import run_external_forensics
from .manifest import write_final_manifest, write_pre_manifest
from .paths import BASELINE_PROTOCOL_PATH, PROJECT_ROOT
from .protocol import resolve_protocol
from .synthesis import float_to_pcm16, synthesize_audio
from .validation import validate_protocol
from .verification import verify_wav
from .video import mux_av, render_video


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _render(
    protocol_path: Path,
    output_dir: Path,
    duration: float | None,
    with_video: bool,
    video_size: int,
    forensics_repo: Path | None,
) -> dict:
    protocol = validate_protocol(load_json(protocol_path))
    resolved = resolve_protocol(protocol, duration)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = output_dir / "resolved-audio-protocol.json"
    pre_path = output_dir / "audio-render-manifest.pre.json"
    wav_path = output_dir / "audio.wav"
    manifest_path = output_dir / "audio-render-manifest.json"
    write_json(resolved_path, resolved)
    pre = write_pre_manifest(pre_path, resolved, PROJECT_ROOT)

    audio, stats = synthesize_audio(resolved)
    wavfile.write(wav_path, resolved["protocol"]["sample_rate_hz"], float_to_pcm16(audio))
    verification = verify_wav(wav_path, resolved)
    outputs: list[Path] = [resolved_path, wav_path]

    if with_video:
        video_path = render_video(resolved, output_dir / "video.mp4", size=video_size)
        final_video = mux_av(video_path, wav_path, output_dir / "final.mp4")
        outputs.extend([video_path, final_video])

    external = None
    if forensics_repo is not None:
        external = run_external_forensics(wav_path, output_dir / "forensics", forensics_repo, resolved)
        outputs.append(Path(external["evidence_path"]))
        if external["timeline_path"]:
            outputs.append(Path(external["timeline_path"]))

    final = write_final_manifest(
        manifest_path, pre, pre_path, outputs, stats, verification, external
    )
    if not verification["passed"]:
        failed = [item["name"] for item in verification["checks"] if not item["passed"]]
        raise VerificationError(f"rendered WAV failed verification: {failed}")
    return {
        "duration_seconds": resolved["protocol"]["duration_seconds"],
        "sample_count": resolved["sample_count"],
        "wav": str(wav_path),
        "manifest": str(manifest_path),
        "resolved_protocol_sha256": resolved["resolved_protocol_sha256"],
        "verification_passed": True,
        "external_forensics": external,
        "output_hashes": final["outputs"],
    }


def command_validate(args: argparse.Namespace) -> int:
    protocol = validate_protocol(load_json(args.protocol))
    _print({"valid": True, "schema_version": protocol["schema_version"], "protocol_id": protocol["protocol_id"]})
    return 0


def command_render(args: argparse.Namespace) -> int:
    _print(_render(Path(args.protocol), Path(args.output_dir), args.duration, args.with_video, args.video_size, args.forensics_repo))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    resolved = resolve_protocol(validate_protocol(load_json(args.protocol)), args.duration)
    result = verify_wav(args.wav, resolved)
    _print(result)
    return 0 if result["passed"] else 2


def command_milestone0(args: argparse.Namespace) -> int:
    root = Path(args.output_dir)
    results = {
        "ten_second": _render(
            BASELINE_PROTOCOL_PATH, root / "10-second", 10.0,
            args.with_video, args.video_size, None,
        )
    }
    if not args.skip_180:
        results["one_hundred_eighty_second"] = _render(
            BASELINE_PROTOCOL_PATH, root / "180-second", 180.0,
            False, args.video_size, args.forensics_repo,
        )
    _print({"milestone": "audio-baseline-0", "results": results})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ave-audio-generator", description="Corrected deterministic AVE audio baseline generator.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("protocol", nargs="?", default=BASELINE_PROTOCOL_PATH)
    validate.set_defaults(func=command_validate)
    render = subparsers.add_parser("render")
    render.add_argument("protocol", nargs="?", default=BASELINE_PROTOCOL_PATH)
    render.add_argument("--output-dir", type=Path, required=True)
    render.add_argument("--duration", type=float)
    render.add_argument("--with-video", action="store_true")
    render.add_argument("--video-size", type=int, default=512)
    render.add_argument("--forensics-repo", type=Path)
    render.set_defaults(func=command_render)
    verify = subparsers.add_parser("verify")
    verify.add_argument("wav", type=Path)
    verify.add_argument("--protocol", type=Path, default=BASELINE_PROTOCOL_PATH)
    verify.add_argument("--duration", type=float)
    verify.set_defaults(func=command_verify)
    milestone = subparsers.add_parser("milestone0")
    milestone.add_argument("--output-dir", type=Path, default=Path("output/milestone-0"))
    milestone.add_argument("--skip-180", action="store_true")
    milestone.add_argument("--with-video", action="store_true")
    milestone.add_argument("--video-size", type=int, default=512)
    milestone.add_argument("--forensics-repo", type=Path)
    milestone.set_defaults(func=command_milestone0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (AudioGeneratorError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
