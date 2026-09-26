from pathlib import Path

from ave_light_renderer.canonical import canonical_sha256, file_sha256, write_json
from ave_light_renderer.manifest import git_state

from . import __version__


def write_pre_manifest(path: str | Path, resolved: dict, project_root: Path) -> dict:
    state = git_state(project_root)
    manifest = {
        "manifest_version": "1.0.0",
        "status": "pre_render",
        "protocol_id": resolved["protocol"]["protocol_id"],
        "requested_protocol_sha256": resolved["requested_protocol_sha256"],
        "resolved_protocol_sha256": resolved["resolved_protocol_sha256"],
        "resolved_protocol": resolved,
        "generator": {
            "name": "ave-audio-generator",
            "version": __version__,
            "git_commit": state["commit"],
            "git_dirty": state["dirty"],
        },
        "warnings": list(resolved["protocol"]["limitations"]),
        "outputs": [],
        "verification": None,
    }
    write_json(path, manifest)
    return manifest


def write_final_manifest(
    path: str | Path,
    pre_manifest: dict,
    pre_manifest_path: str | Path,
    outputs: list[str | Path],
    synthesis_stats: dict,
    verification: dict,
    external_forensics: dict | None = None,
) -> dict:
    manifest = dict(pre_manifest)
    manifest["status"] = "complete" if verification["passed"] else "verification_failed"
    manifest["pre_render_manifest"] = {
        "path": Path(pre_manifest_path).name,
        "sha256": file_sha256(pre_manifest_path),
    }
    manifest["outputs"] = [
        {"path": Path(item).name, "bytes": Path(item).stat().st_size, "sha256": file_sha256(item)}
        for item in outputs
    ]
    manifest["synthesis_measurements"] = synthesis_stats
    manifest["verification"] = verification
    manifest["external_forensics"] = external_forensics
    unsigned = dict(manifest)
    manifest["manifest_content_sha256"] = canonical_sha256(unsigned)
    write_json(path, manifest)
    return manifest

