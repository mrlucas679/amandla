"""Whisper service wrapper for AMANDLA.

Provides transcribe_bytes(data, mime_type) -> str.
Delegates to whisper_service.py which handles model loading,
audio conversion, and NVIDIA Parakeet fallback.
"""
import os
import sys
import tempfile

# Ensure project root is on path so backend.services imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def transcribe_bytes(data: bytes, mime_type: str = "audio/wav") -> str:
    """Transcribe audio bytes to text using Whisper.

    Converts audio to WAV, runs the faster-whisper model, and returns
    the transcribed string. Returns an empty string on any failure so
    callers never need to handle exceptions.

    Args:
        data:      Raw audio bytes (any format supported by ffmpeg).
        mime_type: MIME type hint for format detection (e.g. "audio/webm").

    Returns:
        Transcribed text string, or '' on failure.
    """
    try:
        from backend.services.whisper_service import convert_audio_to_wav, get_model

        # Convert to 16 kHz mono WAV
        wav_bytes = convert_audio_to_wav(data, mime_type)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            model = get_model()  # lazy-loads; thread-safe after first call
            segments, _info = model.transcribe(tmp_path, beam_size=5, language=None)
            text = " ".join(seg.text for seg in segments).strip()
            return text
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except Exception as e:
        print(f"[Whisper] transcribe_bytes error: {e}")
        return ""