from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ave_light_renderer.canonical import load_json

from .errors import DemoGeneratorError
from .compiler import resolve_demo
from .declaration import compile_declaration
from .package import build_demo_package
from .paths import DEMO_RECIPE_DIR, PROJECT_ROOT
from .promotion import promote_demo_package, promote_portfolio
from .validation import validate_demo_recipe


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _recipes() -> list[Path]:
    return sorted(DEMO_RECIPE_DIR.glob("*.json"))


def command_list(_: argparse.Namespace) -> int:
    _print({"recipes": [{"path": str(path), "demo_id": load_json(path)["demo_id"], "demo_version": load_json(path)["demo_version"]} for path in _recipes()]})
    return 0


def command_validate(args: argparse.Namespace) -> int:
    paths = _recipes() if args.recipe == "all" else [Path(args.recipe)]
    results = []
    for path in paths:
        recipe = validate_demo_recipe(load_json(path))
        declaration = compile_declaration(recipe, resolve_demo(recipe, str(path)))
        results.append({
            "path": str(path),
            "demo_id": recipe["demo_id"],
            "demo_version": recipe["demo_version"],
            "declaration_id": declaration["declaration_id"],
            "declaration_schema_version": declaration["schema_version"],
            "declaration_valid": True,
            "valid": True,
            "evidence_maturity": recipe["verification"]["evidence_maturity"],
        })
    _print({"valid": True, "count": len(results), "recipes": results})
    return 0


def command_build(args: argparse.Namespace) -> int:
    recipe_path = Path(args.recipe)
    recipe = validate_demo_recipe(load_json(recipe_path))
    output_dir = args.output_dir or PROJECT_ROOT / "output" / "demos" / recipe["demo_id"]
    _print(build_demo_package(recipe_path, Path(output_dir)))
    return 0


def command_promote(args: argparse.Namespace) -> int:
    _print(promote_demo_package(args.package_dir, args.agreement_report))
    return 0


def command_promote_all(args: argparse.Namespace) -> int:
    _print(promote_portfolio(args.packages_root, args.reports_root))
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
    build.add_argument("--output-dir", type=Path, help="must end with the stable demo ID; defaults to output/demos/<demo_id>")
    build.set_defaults(func=command_build)
    promote = subparsers.add_parser(
        "promote",
        help="promote one built package with a canonical AVE Forensics agreement report",
    )
    promote.add_argument("--package-dir", type=Path, required=True)
    promote.add_argument("--agreement-report", type=Path, required=True)
    promote.set_defaults(func=command_promote)
    promote_all = subparsers.add_parser(
        "promote-all",
        help="promote all five built portfolio packages with canonical reports",
    )
    promote_all.add_argument(
        "--packages-root",
        type=Path,
        default=PROJECT_ROOT / "output" / "demos",
    )
    promote_all.add_argument(
        "--reports-root",
        type=Path,
        default=PROJECT_ROOT.parent / "ave_forensics" / "artifacts" / "demo-portfolio",
    )
    promote_all.set_defaults(func=command_promote_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (DemoGeneratorError, ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
