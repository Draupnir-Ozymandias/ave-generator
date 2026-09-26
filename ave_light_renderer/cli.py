import argparse
import json
import sys
from pathlib import Path

from .adapter import adapt_lumenate_export, renderability_issues, validate_lumenate_export
from .canonical import load_json, write_json
from .compiler import compile_recipe, plan_summary
from .errors import IncompleteEvidenceError, LightRendererError
from .manifest import write_final_manifest, write_pre_render_manifest
from .paths import (
    ALIGNED_EXPORT_PATH,
    PROJECT_ROOT,
    SYNTHETIC_RECIPE_PATH,
    VITALITY_EXPORT_PATH,
)
from .renderer import render_mp4
from .validation import validate_recipe


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _load_valid_recipe(path: str | Path) -> dict:
    return validate_recipe(load_json(path))


def command_validate(args: argparse.Namespace) -> int:
    recipe = _load_valid_recipe(args.recipe)
    _print_json({"valid": True, "recipe_id": recipe["recipe_id"], "schema_version": recipe["schema_version"]})
    return 0


def command_compile(args: argparse.Namespace) -> int:
    plan = compile_recipe(_load_valid_recipe(args.recipe), args.refresh)
    if args.output:
        write_json(args.output, plan)
    _print_json(plan_summary(plan))
    return 0


def _render_workflow(recipe_path: Path, output_dir: Path, refresh: int, size: int) -> dict:
    recipe = _load_valid_recipe(recipe_path)
    plan = compile_recipe(recipe, refresh)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "resolved-plan.json"
    pre_path = output_dir / "render-manifest.pre.json"
    video_path = output_dir / "four-region-preview.mp4"
    manifest_path = output_dir / "render-manifest.json"
    write_json(plan_path, plan)
    pre_manifest = write_pre_render_manifest(pre_path, plan, PROJECT_ROOT)
    render_mp4(plan, video_path, size=size)
    final_manifest = write_final_manifest(
        manifest_path,
        pre_manifest,
        pre_path,
        [plan_path, video_path],
    )
    return {
        "summary": plan_summary(plan),
        "plan": str(plan_path),
        "preview": str(video_path),
        "pre_render_manifest": str(pre_path),
        "manifest": str(manifest_path),
        "output_hashes": final_manifest["outputs"],
    }


def command_render(args: argparse.Namespace) -> int:
    result = _render_workflow(Path(args.recipe), Path(args.output_dir), args.refresh, args.size)
    _print_json(result)
    return 0


def command_adapt(args: argparse.Namespace) -> int:
    path = Path(args.input)
    recipe = adapt_lumenate_export(
        load_json(path),
        path,
        phase_policy=args.phase_policy,
        phase_origin_cycles=args.phase_origin,
    )
    write_json(args.output, recipe)
    _print_json({"adapted": True, "recipe_id": recipe["recipe_id"], "output": str(args.output)})
    return 0


def command_check_lumenate(args: argparse.Namespace) -> int:
    document = validate_lumenate_export(load_json(args.input))
    issues = renderability_issues(document)
    result = {
        "valid_evidence_contract": True,
        "schema_version": document["schema_version"],
        "export_id": document["export_id"],
        "renderable_without_inference": not issues,
        "issues": issues,
    }
    _print_json(result)
    return 0 if not issues else 2


def command_demo(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    render_result = _render_workflow(
        SYNTHETIC_RECIPE_PATH,
        output_dir,
        args.refresh,
        args.size,
    )

    aligned = adapt_lumenate_export(
        load_json(ALIGNED_EXPORT_PATH),
        ALIGNED_EXPORT_PATH,
        phase_policy="reset",
        phase_origin_cycles=0.0,
    )
    aligned_path = output_dir / "aligned-export-adapted-recipe.json"
    write_json(aligned_path, aligned)

    rejection_path = output_dir / "vitality-rejection.json"
    try:
        adapt_lumenate_export(
            load_json(VITALITY_EXPORT_PATH),
            VITALITY_EXPORT_PATH,
            phase_policy="reset",
            phase_origin_cycles=0.0,
        )
    except IncompleteEvidenceError as exc:
        rejection = {
            "rejected_safely": True,
            "reason": str(exc),
            "issue_count": len(exc.issues),
            "issues": exc.issues,
            "inference_used": False,
        }
        write_json(rejection_path, rejection)
    else:
        raise RuntimeError("empirical Vitality fixture unexpectedly adapted without rejection")

    _print_json(
        {
            "milestone": "four-region-offline-e0-e3",
            "synthetic_recipe_valid": True,
            "render": render_result,
            "aligned_lumenate_adapter_fixture": {
                "adapted": True,
                "output": str(aligned_path),
            },
            "empirical_vitality_fixture": {
                "rejected_safely": True,
                "output": str(rejection_path),
            },
            "real_time_flashing": False,
            "torch_control": False,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ave-light-renderer",
        description="Deterministic offline four-region light renderer. No real-time flashing or torch control.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate an AVE light recipe")
    validate.add_argument("recipe")
    validate.set_defaults(func=command_validate)

    compile_parser = subparsers.add_parser("compile", help="compile a recipe without rendering pixels")
    compile_parser.add_argument("recipe")
    compile_parser.add_argument("--refresh", type=int, default=60, choices=(60, 120))
    compile_parser.add_argument("--output", type=Path)
    compile_parser.set_defaults(func=command_compile)

    render = subparsers.add_parser("render", help="compile and render an offline MP4 preview")
    render.add_argument("recipe")
    render.add_argument("--refresh", type=int, default=60, choices=(60, 120))
    render.add_argument("--size", type=int, default=480)
    render.add_argument("--output-dir", type=Path, required=True)
    render.set_defaults(func=command_render)

    adapt = subparsers.add_parser("adapt-lumenate", help="strictly adapt a complete Lumenate 0.2.0 export")
    adapt.add_argument("input")
    adapt.add_argument("--output", type=Path, required=True)
    adapt.add_argument("--phase-policy", choices=("continuous", "reset"), required=True)
    adapt.add_argument("--phase-origin", type=float, required=True)
    adapt.set_defaults(func=command_adapt)

    check = subparsers.add_parser("check-lumenate", help="validate and report renderability without inference")
    check.add_argument("input")
    check.set_defaults(func=command_check_lumenate)

    demo = subparsers.add_parser("demo", help="run the complete safe offline milestone workflow")
    demo.add_argument("--refresh", type=int, default=60, choices=(60, 120))
    demo.add_argument("--size", type=int, default=480)
    demo.add_argument("--output-dir", type=Path, default=Path("output/four-region-demo"))
    demo.set_defaults(func=command_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (LightRendererError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if isinstance(exc, IncompleteEvidenceError) and exc.issues:
            print(json.dumps({"issues": exc.issues}, indent=2, sort_keys=True), file=sys.stderr)
        return 2

