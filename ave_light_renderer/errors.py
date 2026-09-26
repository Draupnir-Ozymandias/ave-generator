class LightRendererError(Exception):
    """Base class for expected renderer failures."""


class RecipeValidationError(LightRendererError):
    """A render recipe is structurally or semantically invalid."""


class AdapterValidationError(LightRendererError):
    """A forensic export fails its immutable producer contract."""


class IncompleteEvidenceError(LightRendererError):
    """Forensic evidence is valid but cannot losslessly drive rendering."""

    def __init__(self, message: str, issues: list[dict] | None = None):
        super().__init__(message)
        self.issues = issues or []

