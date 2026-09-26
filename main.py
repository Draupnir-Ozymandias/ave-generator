"""Guarded compatibility entry point for the corrected AVE audio generator."""

from ave_audio_generator.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
