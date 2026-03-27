"""
Data models for the SASL Transformer service.

These models define the contract between your frontend (React + Three.js avatar)
and the backend translation service. The avatar reads GlossTokens to know what
to sign and in what order; the UI reads the gloss_text for display.
"""

from enum import Enum
from pydantic import BaseModel, Field


class SignType(str, Enum):
    """How the avatar should render each token."""

    SIGN = "sign"               # Full sign exists in your library
    FINGERSPELL = "fingerspell" # Word not in library — spell letter by letter
    CLASSIFIER = "classifier"   # Use a classifier handshape (for describing size/shape/movement)
    NUMBER = "number"           # Numeric sign
    SKIP = "skip"               # Word dropped in SASL (articles, auxiliary verbs, etc.)


class GlossToken(BaseModel):
    """
    A single token in the SASL gloss output.

    The avatar animation queue processes these in order. Each token tells
    the avatar what to sign, how to sign it, and whether it exists in
    your sign library.

    Attributes:
        gloss: The SASL gloss word (uppercase, base form). Example: "STORE"
        original_english: The original English word this came from. Example: "store"
        sign_type: How the avatar should render this token.
        in_library: Whether this sign exists in your sign library.
        position: The order position in the SASL sentence (0-indexed).
        notes: Optional notes for the avatar (e.g. "use two-handed sign",
               "non-manual marker: raised eyebrows for question").
    """

    gloss: str = Field(
        ...,
        description="SASL gloss word in uppercase (e.g. 'STORE', 'GO', 'FINISH')",
    )
    original_english: str = Field(
        ...,
        description="The original English word before transformation",
    )
    sign_type: SignType = Field(
        default=SignType.SIGN,
        description="How the avatar should render this token",
    )
    in_library: bool = Field(
        default=False,
        description="Whether this sign exists in your sign library",
    )
    position: int = Field(
        ...,
        description="Order position in the SASL sentence (0-indexed)",
    )
    notes: str = Field(
        default="",
        description="Optional rendering notes for the avatar",
    )


class TranslationRequest(BaseModel):
    """
    Request to translate an English sentence into SASL gloss.

    Attributes:
        english_text: The English sentence from Whisper STT.
        include_non_manual: Whether to include non-manual markers
            (facial expressions, head movements) in the gloss notes.
        context: Optional previous sentence for better context-aware translation.
    """

    english_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="English sentence from Whisper STT to translate",
    )
    include_non_manual: bool = Field(
        default=True,
        description="Include non-manual markers (eyebrow raise for questions, etc.)",
    )
    context: str = Field(
        default="",
        description="Previous sentence for context-aware translation",
    )


class TranslationResponse(BaseModel):
    """
    Response containing the SASL translation.

    The frontend uses this to:
    1. Drive the avatar animation queue (tokens list, in SASL order)
    2. Display the SASL gloss text on screen for the deaf user to read
    3. Show the original English text for reference (optional)

    Attributes:
        original_english: The original English input.
        gloss_text: The full SASL gloss sentence as a readable string.
            Example: "YESTERDAY STORE MILK BUY I GO-FINISH"
        tokens: Ordered list of GlossTokens for the avatar animation queue.
        non_manual_markers: List of non-manual markers to apply during signing.
        unknown_words: Words not found in the sign library (will be fingerspelled).
        translation_notes: Any notes about the translation choices made.
    """

    original_english: str = Field(
        ...,
        description="The original English sentence",
    )
    gloss_text: str = Field(
        ...,
        description="Full SASL gloss sentence for display to the deaf user",
    )
    tokens: list[GlossToken] = Field(
        ...,
        description="Ordered tokens for the avatar animation queue",
    )
    non_manual_markers: list[str] = Field(
        default_factory=list,
        description="Non-manual markers (e.g. 'raised eyebrows', 'head tilt')",
    )
    unknown_words: list[str] = Field(
        default_factory=list,
        description="Words not found in the sign library",
    )
    translation_notes: str = Field(
        default="",
        description="Notes about translation choices",
    )
