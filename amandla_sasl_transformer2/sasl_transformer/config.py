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
    
    Required env vars:
        ANTHROPIC_API_KEY: Your Anthropic API key for Claude.
    
    Optional env vars:
        ANTHROPIC_MODEL: Which Claude model to use (default: claude-sonnet-4-20250514).
        SASL_MAX_TOKENS: Max tokens for the translation response (default: 1024).
        SASL_TEMPERATURE: Temperature for translation (default: 0.1 for consistency).
        SIGN_LIBRARY_PATH: Path to your sign library JSON file.
        SASL_CACHE_ENABLED: Whether to cache repeated translations (default: True).
        SASL_CACHE_MAX_SIZE: Max number of cached translations (default: 500).
    """

    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key — loaded from ANTHROPIC_API_KEY env var",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use for SASL translation",
    )
    sasl_max_tokens: int = Field(
        default=1024,
        description="Max tokens for the translation response",
    )
    sasl_temperature: float = Field(
        default=0.1,
        description="Low temperature for consistent, deterministic translations",
    )
    sign_library_path: str = Field(
        default="data/sign_library.json",
        description="Path to the JSON file containing your sign library",
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
    }


# Singleton instance — import this wherever you need settings
settings = SASLTransformerSettings()
