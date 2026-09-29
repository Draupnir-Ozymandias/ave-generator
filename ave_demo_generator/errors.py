class DemoGeneratorError(Exception):
    """Base class for expected demo-generation failures."""


class DemoRecipeValidationError(DemoGeneratorError):
    """A demo recipe is structurally or semantically invalid."""
