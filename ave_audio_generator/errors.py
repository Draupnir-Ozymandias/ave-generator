class AudioGeneratorError(Exception):
    """Base class for expected audio-generator failures."""


class ProtocolValidationError(AudioGeneratorError):
    """The audio protocol is structurally or semantically invalid."""


class VerificationError(AudioGeneratorError):
    """A rendered artifact does not satisfy its declared tolerances."""

