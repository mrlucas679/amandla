"""
Ollama Sign Recognition Service
Uses the local amandla model to recognize SASL signs from landmark data
"""
import os
import json
import logging
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "amandla")


async def recognize_sign(landmark_data: dict) -> dict:
    """
    Send landmark data to Ollama amandla model for sign recognition.

    Args:
        landmark_data: Dict with hand landmark positions from MediaPipe

    Returns:
        Dict with 'sign', 'confidence', and 'description'
    """
    try:
        # Build a named-landmark prompt that matches the Modelfile's expected format.
        # Convert raw list (or dict with 'landmarks' key) to [{id, name, x, y, z}].
        _LANDMARK_NAMES = [
            "WRIST","THUMB_CMC","THUMB_MCP","THUMB_IP","THUMB_TIP",
            "INDEX_FINGER_MCP","INDEX_FINGER_PIP","INDEX_FINGER_DIP","INDEX_FINGER_TIP",
            "MIDDLE_FINGER_MCP","MIDDLE_FINGER_PIP","MIDDLE_FINGER_DIP","MIDDLE_FINGER_TIP",
            "RING_FINGER_MCP","RING_FINGER_PIP","RING_FINGER_DIP","RING_FINGER_TIP",
            "PINKY_MCP","PINKY_PIP","PINKY_DIP","PINKY_TIP",
        ]
        raw_landmarks = landmark_data.get("landmarks", landmark_data) if isinstance(landmark_data, dict) else landmark_data
        named = []
        for i, pt in enumerate(raw_landmarks[:21]):
            named.append({
                "id":   i,
                "name": _LANDMARK_NAMES[i] if i < len(_LANDMARK_NAMES) else f"pt{i}",
                "x":    round(pt.get("x", 0.0), 4),
                "y":    round(pt.get("y", 0.0), 4),
                "z":    round(pt.get("z", 0.0), 4),
            })
        prompt = f"Landmarks: {json.dumps(named)}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1
                }
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code}")
                return {
                    'sign': 'UNKNOWN',
                    'confidence': 0.0,
                    'description': 'Sign recognition failed'
                }

            data = response.json()
            response_text = data.get('response', '').strip()

            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                logger.info(f"Sign recognized: {result.get('sign')} (conf={result.get('confidence')})")
                return result
            except json.JSONDecodeError:
                logger.warning(f"Ollama returned non-JSON: {response_text[:100]}")
                return {
                    'sign': 'UNKNOWN',
                    'confidence': 0.0,
                    'description': 'Invalid response format'
                }

    except asyncio.TimeoutError:
        logger.warning("Ollama request timeout — trying NVIDIA NIM fallback")
        return await _recognize_via_nim(landmark_data)
    except Exception as e:
        logger.error(f"Sign recognition error: {e}")
        return await _recognize_via_nim(landmark_data)


async def _recognize_via_nim(landmark_data: dict) -> dict:
    """
    Fallback sign recognition using NVIDIA NIM (llama) when Ollama is unavailable.
    Only active when NVIDIA_ENABLED=true and NVIDIA_API_KEY is set.
    """
    try:
        from backend.services.nvidia_service import generate_with_nim, is_available
        if not is_available():
            return {'sign': 'UNKNOWN', 'confidence': 0.0, 'description': 'Ollama unavailable, NVIDIA disabled'}

        prompt = (
            "You are a South African Sign Language recognition engine. "
            "Identify the SASL sign from these MediaPipe hand landmarks. "
            f"Landmarks: {json.dumps(landmark_data)}. "
            'Reply ONLY with JSON: {"sign": "NAME", "confidence": 0.85, "description": "..."}'
        )
        raw = await generate_with_nim(prompt)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].replace("json", "").strip()
        result = json.loads(raw)
        logger.info(f"[NIM] Sign recognised: {result.get('sign')} (conf={result.get('confidence')})")
        return result
    except Exception as e:
        logger.error(f"[NIM] Fallback recognition failed: {e}")
        return {'sign': 'UNKNOWN', 'confidence': 0.0, 'description': f'All recognition failed: {e}'}


async def health_check() -> bool:
    """Check if Ollama service is running and amandla model is available"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is running
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")

            if response.status_code != 200:
                logger.warning(f"Ollama health check failed: {response.status_code}")
                return False

            # Check if amandla model exists
            data = response.json()
            models = [m.get('name', '').split(':')[0] for m in data.get('models', [])]

            if OLLAMA_MODEL in models:
                logger.info(f"Ollama {OLLAMA_MODEL} model is available")
                return True
            else:
                logger.warning(f"Ollama model '{OLLAMA_MODEL}' not found. Available: {models}")
                return False

    except Exception as e:
        logger.error(f"Ollama health check error: {e}")
        return False

