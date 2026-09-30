from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCHEMA_PATH = PROJECT_ROOT / "contracts" / "ave-demo-recipe-1.1.0.schema.json"
DEMO_RECIPE_DIR = PROJECT_ROOT / "contracts" / "examples" / "demos"
PLATFORM_DECLARATION_SCHEMA_PATH = (
    PROJECT_ROOT
    / "contracts"
    / "vendor"
    / "ave-platform"
    / "0.1.0"
    / "ave-demo-declaration-0.1.0.schema.json"
)
PLATFORM_DECLARATION_SOURCE_MANIFEST_PATH = PLATFORM_DECLARATION_SCHEMA_PATH.parent / "SOURCE_MANIFEST.json"
