import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from .canonical import canonical_sha256, file_sha256, write_json


def git_state(project_root: Path) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": revision.stdout.strip() if revision.returncode == 0 else "unknown",
        "dirty": status.returncode != 0 or bool(status.stdout.strip()),
    }


def build_pre_render_manifest(plan: dict, project_root: Path) -> dict:
    source_state = git_state(project_root)
    return {
        "manifest_version": "1.0.0",
        "status": "pre_render",
        "recipe": {
            "recipe_id": plan["recipe_id"],
            "sha256": plan["recipe_sha256"],
            "source": plan["source"],
        },
        "resolved_plan": {
            "sha256": plan["resolved_plan_sha256"],
            "duration_us": plan["duration_us"],
            "frame_count": plan["frame_count"],
            "refresh_hz": plan["refresh_hz"],
        },
        "renderer": {
            "name": "ave-light-renderer",
            "version": __version__,
            "git_commit": source_state["commit"],
            "git_dirty": source_state["dirty"],
            "mode": "offline_virtual_clock",
        },
        "requested_and_quantized_transitions": plan["transitions"],
        "timing_error_summary_us": plan["timing_error_summary_us"],
        "warnings": list(plan["warnings"]),
        "outputs": [],
    }


def finalize_manifest(pre_manifest: dict, pre_manifest_path: Path, outputs: list[Path]) -> dict:
    manifest = dict(pre_manifest)
    manifest["status"] = "complete"
    manifest["pre_render_manifest"] = {
        "path": pre_manifest_path.name,
        "sha256": file_sha256(pre_manifest_path),
    }
    manifest["outputs"] = [
        {
            "path": path.name,
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in outputs
    ]
    unsigned = dict(manifest)
    manifest["manifest_content_sha256"] = canonical_sha256(unsigned)
    return manifest


def write_pre_render_manifest(path: str | Path, plan: dict, project_root: Path) -> dict:
    manifest = build_pre_render_manifest(plan, project_root)
    write_json(path, manifest)
    return manifest


def write_final_manifest(
    path: str | Path,
    pre_manifest: dict,
    pre_manifest_path: str | Path,
    outputs: list[str | Path],
) -> dict:
    manifest = finalize_manifest(
        pre_manifest,
        Path(pre_manifest_path),
        [Path(item) for item in outputs],
    )
    write_json(path, manifest)
    return manifest
