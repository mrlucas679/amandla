"""
Configuration for the SASL Transformer service.

All sensitive values are loaded from environment variables.
Never hardcode API keys or secrets — uses .env file via pydantic-settings.

The SASL transformer uses the local Ollama model for English → SASL
translation. No cloud API keys are required.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class SASLTransformerSettings(BaseSettings):
    """
    Settings loaded from environment variables or .env file.

    Env vars used:
        OLLAMA_BASE_URL: URL where Ollama is running (default: http://localhost:11434).
        OLLAMA_MODEL: Which Ollama model to use (default: amandla).
        SIGN_LIBRARY_PATH: Path to your sign library JSON file.
        SASL_CACHE_ENABLED: Whether to cache repeated translations (default: True).
        SASL_CACHE_MAX_SIZE: Max number of cached translations (default: 500).
    """

    # Ollama settings — local AI, no API key needed
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL where Ollama is running — loaded from OLLAMA_BASE_URL env var",
    )
    ollama_model: str = Field(
        default="amandla",
        description="Ollama model name for SASL translation — loaded from OLLAMA_MODEL env var",
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
        # Do NOT set env_file here — backend/main.py calls load_dotenv() once at
        # startup and all modules share os.environ. Loading .env again here would
        # violate the CLAUDE.md constraint of a single load_dotenv() call.
        "case_sensitive": False,
        "extra": "ignore",   # Ignore other env vars (WHISPER_MODEL, etc.)
    }


# Singleton instance — import this wherever you need settings
settings = SASLTransformerSettings()
