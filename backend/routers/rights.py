"""Rights analysis and letter generation endpoints for AMANDLA backend.

Routes:
  POST /rights/analyze — incident description → rights analysis
  POST /rights/letter  — full details → formal complaint letter

DEPRECATED: The Electron frontend uses WebSocket message types
``rights_analyze`` and ``rights_letter`` via the preload bridge.
These routes are kept for backward compatibility and direct API testing only.
"""

import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyseRequest(BaseModel):
    """Request body for POST /rights/analyze."""
    description: str
    incident_type: str = "workplace"


class LetterRequest(BaseModel):
    """Request body for POST /rights/letter."""
    description: str
    user_name: str = "The Complainant"
    employer_name: str
    incident_date: str
    analysis: Optional[dict] = None


@router.post("/rights/analyze")
async def rights_analyze(req: AnalyseRequest):
    """Analyse an incident and return relevant rights / laws."""
    try:
        from backend.services.claude_service import analyse_incident
        result = await analyse_incident(req.description, req.incident_type)
        return result
    except Exception as exc:
        logger.error("[Rights] Analyse failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Rights analysis temporarily unavailable. Please try again."}
        )


@router.post("/rights/letter")
async def rights_letter(req: LetterRequest):
    """Generate a formal complaint letter."""
    try:
        from backend.services.claude_service import generate_rights_letter
        result = await generate_rights_letter(
            incident_description=req.description,
            user_name=req.user_name,
            employer_name=req.employer_name,
            incident_date=req.incident_date,
            analysis=req.analysis or {},
        )
        return result
    except Exception as exc:
        logger.error("[Rights] Letter generation failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Letter generation temporarily unavailable. Please try again."}
        )

