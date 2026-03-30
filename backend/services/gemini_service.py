# DEPRECATED — All AI now uses local Ollama. This stub file is kept only
# to prevent ImportError if any legacy code references it.
# Scheduled for removal in next cleanup sprint.
"""
Gemini service STUB — DEPRECATED.

AMANDLA now uses Ollama (local AI) for all AI tasks.
This file is kept as a stub so any old import statements
don't crash the app. All functions return None.

To use the actual AI features, see:
  - backend/services/ollama_client.py   (text → signs)
  - backend/services/ollama_service.py  (landmark recognition)
  - backend/services/claude_service.py  (rights analysis via Ollama)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Gemini is no longer used. Always returns False."""
    return False


async def analyse_incident(description: str, incident_type: str = "workplace") -> Optional[dict]:
    """Deprecated — returns None. Use claude_service.analyse_incident() instead."""
    return None


async def generate_rights_letter(**kwargs) -> Optional[dict]:
    """Deprecated — returns None. Use claude_service.generate_rights_letter() instead."""
    return None


async def signs_to_english(signs: list) -> Optional[str]:
    """Deprecated — returns None. Ollama handles this in backend/main.py."""
    return None


async def classify_text_to_signs(text: str) -> Optional[list]:
    """Deprecated — returns None. Use ollama_client.classify_text_to_signs() instead."""
    return None

