# Minimal type stub for imageio-ffmpeg.
# Provides enough type information for Pyright/JetBrains to resolve the
# import without requiring the full package stubs.

def get_ffmpeg_exe() -> str:
    """Return the path to the bundled ffmpeg executable."""
    ...

def get_ffmpeg_version() -> str:
    """Return the version string of the bundled ffmpeg."""
    ...

