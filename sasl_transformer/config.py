"""
Configuration for the SASL Transformer service.

All sensitive values are loaded from environment variables.
Never hardcode API keys or secrets — uses .env file via pydantic-settings.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class SASLTransformerSettings(BaseSettings):
    """
    Settings loaded from environment variables or .env file.

    Optional env vars (app falls back to rule-based translation if keys absent):
        GEMINI_API_KEY: Google Gemini API key for SASL translation.
        GEMINI_MODEL: Which Gemini model to use (default: models/gemini-2.5-flash).
        SIGN_LIBRARY_PATH: Path to your sign library JSON file.
        SASL_CACHE_ENABLED: Whether to cache repeated translations (default: True).
        SASL_CACHE_MAX_SIZE: Max number of cached translations (default: 500).
    """

    # Optional — empty string means LLM translation is skipped, rule-based is used
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key — loaded from GEMINI_API_KEY env var",
    )
    gemini_model: str = Field(
        default="models/gemini-2.5-flash",
        description="Gemini model to use for SASL translation",
    )
    sign_library_path: str = Field(
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sign_library.json"),
        description="Absolute path to the sign library JSON file",
    )
    sasl_cache_enabled: bool = Field(
        default=True,
        description="Cache repeated translations to reduce API calls",
    )
    sasl_cache_max_size: int = Field(
        default=500,
        description="Max number of cached translations",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",   # Ignore other .env vars (OLLAMA_MODEL, WHISPER_MODEL, etc.)
    }


# Singleton instance — import this wherever you need settings
settings = SASLTransformerSettings()
