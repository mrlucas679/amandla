"""
Whisper Speech-to-Text Service
Transcribes audio using faster-whisper (local, no API key needed)
"""
import io
import os
import time
import tempfile
import asyncio
import subprocess
import logging
from faster_whisper import WhisperModel
from dotenv import load_dotenv
import imageio_ffmpeg

load_dotenv()

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# Load model once on startup
logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE} on {WHISPER_DEVICE}")
try:
    model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type="int8")
    logger.info("Whisper model loaded successfully")
except Exception as e:
    logger.warning(f"Failed to load Whisper model: {e}")
    model = None


def convert_audio_to_wav(audio_bytes: bytes) -> bytes:
    """
    Convert any audio format (webm, ogg, mp4) to wav using ffmpeg.
    Browser MediaRecorder outputs webm/opus — Whisper needs wav.
    """
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as inp:
        inp.write(audio_bytes)
        inp_path = inp.name

    out_path = inp_path.replace('.webm', '.wav')

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg_exe, '-y', '-i', inp_path, '-ar', '16000', '-ac', '1', '-f', 'wav', out_path],
            capture_output=True, timeout=15
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

        with open(out_path, 'rb') as f:
            return f.read()
    finally:
        try:
            os.unlink(inp_path)
            os.unlink(out_path)
        except Exception:
            pass


async def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Transcribe audio bytes using Whisper.
    Returns dict with 'text', 'language', and 'confidence'.
    """
    if not model:
        return {
            'text': '',
            'language': 'en',
            'confidence': 0.0,
            'error': 'Whisper model not loaded'
        }

    start = time.time()

    try:
        # Convert from webm/opus to wav
        wav_bytes = await asyncio.get_event_loop().run_in_executor(
            None, convert_audio_to_wav, audio_bytes
        )

        # Write wav to temp file for Whisper
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            # Transcribe
            segments, info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: model.transcribe(tmp_path, beam_size=5)
            )

            elapsed = time.time() - start
            text = " ".join([seg.text.strip() for seg in segments])

            logger.info(f"Transcribed {len(wav_bytes)} bytes in {elapsed:.2f}s: '{text[:50]}...'")

            return {
                'text': text,
                'language': info.language,
                'confidence': 0.85,  # Whisper doesn't return per-utterance confidence
                'duration_ms': int(elapsed * 1000)
            }
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            'text': '',
            'language': 'en',
            'confidence': 0.0,
            'error': str(e)
        }

