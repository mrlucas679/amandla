"""
FastAPI routes for the SASL Transformer service.

Add these routes to your existing Amandla backend by importing the router:

    from sasl_transformer.routes import router as sasl_router
    app.include_router(sasl_router, prefix="/api/sasl")

Endpoints:
    POST /api/sasl/translate      — Translate English text to SASL gloss
    GET  /api/sasl/health         — Health check
    GET  /api/sasl/library/stats  — Sign library statistics
    POST /api/sasl/cache/clear    — Clear the translation cache
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from sasl_transformer.config import settings
from sasl_transformer.models import TranslationRequest, TranslationResponse
from sasl_transformer.transformer import SASLTransformer

logger = logging.getLogger(__name__)

# Module-level transformer instance (initialised on first use)
_transformer: Optional[SASLTransformer] = None


def get_transformer() -> SASLTransformer:
    """
    Get or create the SASLTransformer singleton.

    The transformer is created lazily on first request,
    not at import time, so the app starts fast.
    """
    global _transformer
    if _transformer is None:
        _transformer = SASLTransformer()
    return _transformer


# Create the router
router = APIRouter(tags=["SASL Translation"])


@router.post("/translate", response_model=TranslationResponse)
async def translate_to_sasl(request: TranslationRequest) -> TranslationResponse:
    """
    Translate an English sentence into SASL gloss notation.

    This is the main endpoint your frontend calls after Whisper
    gives you the English text. The response contains:
    - gloss_text: The SASL sentence for display to the deaf user
    - tokens: Ordered list for the avatar animation queue
    - non_manual_markers: Facial expressions/head movements
    - unknown_words: Words that will be fingerspelled

    Example request:
        POST /api/sasl/translate
        {
            "english_text": "I went to the store yesterday to buy milk",
            "include_non_manual": true
        }

    Example response:
        {
            "original_english": "I went to the store yesterday to buy milk",
            "gloss_text": "YESTERDAY STORE MILK BUY I GO FINISH",
            "tokens": [...],
            "non_manual_markers": [],
            "unknown_words": ["STORE"]
        }
    """
    try:
        transformer = get_transformer()
        response = await transformer.translate(request)
        return response

    except ValueError as e:
        logger.error("Translation value error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Translation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Translation service temporarily unavailable. Please try again.",
        )


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns the service status and configuration info.
    Useful for monitoring and debugging.
    """
    transformer = get_transformer()
    return {
        "status": "healthy",
        "model": settings.gemini_model,
        "sign_library_size": transformer.sign_library.total_signs,
        "cache_enabled": settings.sasl_cache_enabled,
    }


@router.get("/library/stats")
async def library_stats() -> dict:
    """
    Get sign library statistics.

    Returns info about how many signs are loaded,
    which categories exist, etc.
    """
    transformer = get_transformer()
    library = transformer.sign_library

    return {
        "total_signs": library.total_signs,
        "categories": library.list_categories(),
    }


@router.post("/cache/clear")
async def clear_cache() -> dict:
    """
    Clear the translation cache.

    Useful after updating grammar rules or when
    debugging translation issues.
    """
    transformer = get_transformer()
    cleared = transformer.clear_cache()

    return {
        "status": "cache_cleared",
        "entries_cleared": cleared,
    }
