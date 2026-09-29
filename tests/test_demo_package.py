from pathlib import Path

from ave_demo_generator import package as package_module
from ave_demo_generator.paths import DEMO_RECIPE_DIR
from ave_light_renderer.canonical import file_sha256, load_json


def test_package_separates_declarations_checks_and_external_observations(tmp_path, monkeypatch):
    def fake_render(path, *_args, **_kwargs):
        Path(path).write_bytes(b"silent-video")

    def fake_mux(_video, _audio, output):
        Path(output).write_bytes(b"muxed-video")
        return Path(output)

    monkeypatch.setattr(package_module, "render_presentation_video", fake_render)
    monkeypatch.setattr(package_module, "mux_av", fake_mux)
    target = tmp_path / "package"
    result = package_module.build_demo_package(
        DEMO_RECIPE_DIR / "binaural-difference-10hz-demo-v1.json", target
    )
    manifest = load_json(target / "render-manifest.json")
    request = load_json(target / "verification-request.json")

    assert result["generator_validation_passed"] is True
    assert manifest["generator_declaration"]["path"] == "resolved-demo.json"
    assert manifest["generator_validation"]["passed"] is True
    assert manifest["forensics_observation"] is None
    assert manifest["field_level_agreement"] is None
    assert manifest["evidence_maturity"] == "exploratory"
    assert request["input"]["sha256"] == file_sha256(target / "audio" / "stereo.wav")
    assert request["generator_declared_values_included"] is False
    assert "left_carrier_hz" in request["required_observation_fields"]
