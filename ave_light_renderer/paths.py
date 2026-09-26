from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECIPE_SCHEMA_PATH = PROJECT_ROOT / "contracts" / "ave-light-render-recipe-1.0.0.schema.json"
SYNTHETIC_RECIPE_PATH = PROJECT_ROOT / "contracts" / "examples" / "synthetic-four-region-recipe.json"
LUMENATE_VENDOR_DIR = PROJECT_ROOT / "contracts" / "vendor" / "lumenate" / "0.2.0"
LUMENATE_SCHEMA_PATH = LUMENATE_VENDOR_DIR / "lumenate-protocol-export-0.2.0.schema.json"
LUMENATE_EVIDENCE_SCHEMA_PATH = LUMENATE_VENDOR_DIR / "ave-evidence-object-1.0.0.schema.json"
LUMENATE_SOURCE_MANIFEST_PATH = LUMENATE_VENDOR_DIR / "SOURCE_MANIFEST.json"
ALIGNED_EXPORT_PATH = PROJECT_ROOT / "contracts" / "examples" / "lumenate" / "aligned-export.json"
VITALITY_EXPORT_PATH = PROJECT_ROOT / "contracts" / "examples" / "lumenate" / "vitality-5min-empirical-0.2.0.json"

