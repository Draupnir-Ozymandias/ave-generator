from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ave_light_renderer.canonical import load_json

from .errors import DemoGeneratorError
from .package import build_demo_package
from .paths import DEMO_RECIPE_DIR
from .validation import validate_demo_recipe


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _recipes() -> list[Path]:
    return sorted(DEMO_RECIPE_DIR.glob("*.json"))


def command_list(_: argparse.Namespace) -> int:
    _print({"recipes": [{"path": str(path), "demo_id": load_json(path)["demo_id"]} for path in _recipes()]})
    return 0


def command_validate(args: argparse.Namespace) -> int:
    paths = _recipes() if args.recipe == "all" else [Path(args.recipe)]
    results = []
    for path in paths:
        recipe = validate_demo_recipe(load_json(path))
        results.append({
            "path": str(path),
            "demo_id": recipe["demo_id"],
            "valid": True,
            "evidence_maturity": recipe["verification"]["evidence_maturity"],
        })
    _print({"valid": True, "count": len(results), "recipes": results})
    return 0


def command_build(args: argparse.Namespace) -> int:
    _print(build_demo_package(Path(args.recipe), Path(args.output_dir)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ave-demo-generator",
        description="Build reproducible AVE engineering demo packages. Offline rendering only.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list", help="list tracked portfolio recipes")
    listing.set_defaults(func=command_list)
    validate = subparsers.add_parser("validate", help="validate one recipe or all tracked recipes")
    validate.add_argument("recipe", nargs="?", default="all")
    validate.set_defaults(func=command_validate)
    build = subparsers.add_parser("build", help="build one complete offline demo package")
    build.add_argument("recipe")
    build.add_argument("--output-dir", type=Path, required=True)
    build.set_defaults(func=command_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (DemoGeneratorError, ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
