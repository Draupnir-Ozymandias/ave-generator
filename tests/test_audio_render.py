import importlib

from scipy.io import wavfile

from ave_audio_generator.manifest import write_final_manifest, write_pre_manifest
from ave_audio_generator.protocol import resolve_protocol
from ave_audio_generator.synthesis import float_to_pcm16, synthesize_audio
from ave_audio_generator.verification import verify_wav
from ave_light_renderer.canonical import file_sha256
from ave_light_renderer.paths import PROJECT_ROOT


def test_importing_legacy_entrypoint_has_no_render_side_effect(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    importlib.import_module("main")
    assert list(tmp_path.iterdir()) == []


def test_render_verification_and_manifest_round_trip(tmp_path, audio_protocol):
    resolved = resolve_protocol(audio_protocol, 10.0)
    pre_path = tmp_path / "manifest.pre.json"
    pre = write_pre_manifest(pre_path, resolved, PROJECT_ROOT)
    assert pre_path.exists()
    assert pre["status"] == "pre_render"
    audio, stats = synthesize_audio(resolved)
    wav_path = tmp_path / "audio.wav"
    wavfile.write(wav_path, audio_protocol["sample_rate_hz"], float_to_pcm16(audio))
    verification = verify_wav(wav_path, resolved)
    assert verification["passed"] is True
    manifest_path = tmp_path / "manifest.json"
    manifest = write_final_manifest(manifest_path, pre, pre_path, [wav_path], stats, verification)
    assert manifest["status"] == "complete"
    assert manifest["outputs"][0]["sha256"] == file_sha256(wav_path)
    assert manifest["verification"]["passed"] is True

