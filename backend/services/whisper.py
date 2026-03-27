"""Whisper service wrapper for AMANDLA.

Provides a simple transcribe_bytes(data: bytes) -> str function.

If `faster_whisper` is available and a model is configured, it may be used; otherwise
the function returns a mocked transcription for local development.
"""
import tempfile
import os
import sys

def transcribe_bytes(data: bytes) -> str:
    """Return transcribed text from audio bytes.

    This is a development-friendly placeholder. It will try to use faster_whisper if available,
    but will fall back to returning a mocked string so the backend flow can be tested without heavy models.
    """
    # Try to use faster_whisper if installed (but model files are required and may not be present)
    try:
        from faster_whisper import WhisperModel
        # Note: using faster-whisper requires a model (e.g., 'small', 'medium') to be available locally.
        # We avoid automatic model downloads here to keep the dev environment light.
        print('[Whisper] faster_whisper present but model loading is disabled in scaffold; using mock')
    except Exception:
        # Not available or not configured — return mocked text
        print('[Whisper] faster_whisper not available; returning mock transcription')
        return 'mock transcription'

    # If faster_whisper were fully configured, you'd load model and transcribe here.
    # To keep this scaffold fast and reliable we skip that step.
    return 'mock transcription'

