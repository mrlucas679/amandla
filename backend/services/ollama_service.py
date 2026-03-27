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
        # Format the prompt for Ollama
        prompt = f"Analyze these hand landmarks and identify the SASL sign: {json.dumps(landmark_data)}"

        async with httpx.AsyncClient(timeout=10.0) as client:
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
        logger.error("Ollama request timeout")
        return {
            'sign': 'UNKNOWN',
            'confidence': 0.0,
            'description': 'Recognition timeout'
        }
    except Exception as e:
        logger.error(f"Sign recognition error: {e}")
        return {
            'sign': 'UNKNOWN',
            'confidence': 0.0,
            'description': str(e)
        }


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

