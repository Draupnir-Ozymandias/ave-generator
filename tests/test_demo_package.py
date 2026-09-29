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
    target = tmp_path / "ave-demo-001-binaural-construction"
    result = package_module.build_demo_package(
        DEMO_RECIPE_DIR / "ave-demo-001-binaural-construction.json", target
    )
    manifest = load_json(target / "render-manifest.json")
    request = load_json(target / "verification-request.json")

    assert result["generator_validation_passed"] is True
    assert manifest["generator_declaration"]["path"] == "ave-demo-001-binaural-construction-declaration.json"
    assert manifest["generator_declaration"]["declaration_id"] == "ave-demo-001-binaural-construction@1.0.0"
    assert manifest["resolved_protocol"]["path"] == "ave-demo-001-binaural-construction-resolved-protocol.json"
    assert manifest["generator_validation"]["passed"] is True
    assert manifest["forensics_observation"] is None
    assert manifest["field_level_agreement"] is None
    assert manifest["evidence_maturity"] == "exploratory"
    assert request["detector_input"]["sha256"] == file_sha256(target / "audio" / "stereo.wav")
    assert request["generator_declared_values_in_detector_input"] is False
    assert request["detector_input"]["expected_values_present"] is False
    assert request["detector_input"]["expected_tolerances_present"] is False
    assert request["detector_input"]["target_schedules_present"] is False
    assert "carrier_frequency_hz" in request["requested_observation_metrics"]
    assert request["comparison_after_observation"]["do_not_load_before_evidence_is_persisted"] is True


def test_four_region_package_uses_target_free_rendered_video_for_detection(tmp_path, monkeypatch):
    def fake_render(path, *_args, **_kwargs):
        Path(path).write_bytes(b"rendered-video")

    def fake_mux(_video, _audio, output):
        Path(output).write_bytes(b"muxed-video")
        return Path(output)

    def fake_light_render(_plan, path, **_kwargs):
        Path(path).write_bytes(b"four-region-video")
        return Path(path)

    monkeypatch.setattr(package_module, "render_presentation_video", fake_render)
    monkeypatch.setattr(package_module, "render_mp4", fake_light_render)
    monkeypatch.setattr(package_module, "mux_av", fake_mux)
    target = tmp_path / "ave-demo-004-four-region-light"
    package_module.build_demo_package(
        DEMO_RECIPE_DIR / "ave-demo-004-four-region-light.json", target
    )
    request = load_json(target / "verification-request.json")
    declaration = load_json(target / "ave-demo-004-four-region-light-declaration.json")

    assert request["request_type"] == "independent_blind_visual_analysis"
    assert request["detector_input"]["path"] == "four-region-preview.mp4"
    assert request["detector_input"]["media_type"] == "video/mp4"
    assert request["detector_input"]["sha256"] == file_sha256(target / "four-region-preview.mp4")
    assert request["detector_input"]["expected_values_present"] is False
    assert request["detector_input"]["expected_tolerances_present"] is False
    assert request["detector_input"]["target_schedules_present"] is False
    assert "region_count" in request["requested_observation_metrics"]
    assert "independent_region_schedules" in request["requested_observation_metrics"]
    serialized_request = str(request)
    for claim in declaration["claims"]:
        assert str(claim["target"]) not in serialized_request
