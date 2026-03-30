"""Speech upload endpoint for AMANDLA backend.

Route:
  POST /speech — audio upload → Whisper transcription → SASL signs

DEPRECATED: The Electron frontend uses the WebSocket message type
``speech_upload`` via the preload bridge instead of this endpoint.
This route is kept for backward compatibility and direct API testing
(e.g. scripts/post_speech_test.py). Do not call it from renderer code.
"""

import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.shared import MAX_AUDIO_BYTES
from backend.services.sasl_pipeline import text_to_sasl_signs

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed audio MIME types — only accept known formats to prevent abuse
_ALLOWED_AUDIO_MIMES = {
    "audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg",
    "audio/wav", "audio/x-wav", "audio/mp3",
}


@router.post("/speech")
async def upload_speech(
    audio: UploadFile = File(...),
    mime_type: str = Form(default="audio/webm"),
):
    """Receive audio upload, transcribe with Whisper, convert to sign names.

    Returns:
        JSON with text, signs, language, confidence, sasl_gloss, original_english.
    """
    # Strip codec suffix (e.g. "audio/webm;codecs=opus" → "audio/webm")
    base_mime = mime_type.split(";")[0].strip().lower()
    if base_mime not in _ALLOWED_AUDIO_MIMES:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    content = await audio.read()
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB)")
    logger.info("[Speech] Received %s size=%d mime=%s", audio.filename, len(content), base_mime)

    try:
        from backend.services.whisper_service import transcribe_audio
        result = await transcribe_audio(content, base_mime)

        if result.get("error") and not result.get("text"):
            logger.warning("[Speech] Transcription returned error: %s", result["error"])

        text = result.get("text", "").strip()
        sasl = await text_to_sasl_signs(text)

        return {
            "text": text,
            "original_english": text,
            "sasl_gloss": sasl["text"],
            "signs": sasl["signs"],
            "language": result.get("language", "en"),
            "confidence": result.get("confidence", 0.0),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Speech] Transcription error: %s", exc, exc_info=True)
        return {
            "text": "", "signs": [], "language": "en", "confidence": 0.0,
            "error": "Speech processing failed. Please try again or type your message.",
        }

