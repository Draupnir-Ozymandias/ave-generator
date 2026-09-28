from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_SCHEMA_PATH = PROJECT_ROOT / "contracts" / "ave-audio-protocol-1.0.0.schema.json"
BASELINE_PROTOCOL_PATH = PROJECT_ROOT / "contracts" / "examples" / "baseline-audio-protocol.json"

