"""
Configuration module for DataFog.

Defines settings and provides a global config instance.
Includes API keys, URLs, timeouts, and other options.
"""

import os
from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings


class DataFogConfig(BaseSettings):
    """
    Configuration settings for DataFog SDK.

    This class defines all the configuration options used throughout the DataFog SDK.
    It includes settings for API authentication, service URLs, timeouts, retries,
    rate limiting, and logging. The configuration can be updated at runtime using
    environment variables or programmatically via the update method.

    All settings have default values that can be overridden as needed. The class
    uses Pydantic for data validation and settings management.
    """

    # API Keys and Authentication
    api_key: str = os.environ.get("DATAFOG_API_KEY", "")

    # Base URLs for different services
    annotator_base_url: str = "http://localhost:8000"
    anonymizer_base_url: str = "http://localhost:8000"

    # Default language
    default_language: str = "en"

    # Timeouts
    request_timeout: int = 30  # seconds

    # Retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.3

    # Rate limiting
    rate_limit_per_minute: Optional[int] = None

    # Logging
    log_level: str = "INFO"

    class Config:
        env_prefix = "DATAFOG_"
        case_sensitive = False

    def update(self, **kwargs):
        """Update configuration with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Invalid configuration key: {key}")


# Create a global instance of the configuration
datafog_config = DataFogConfig()


def get_config() -> DataFogConfig:
    """Get the current configuration"""
    return datafog_config


def configure(**kwargs):
    """Update the global configuration"""
    datafog_config.update(**kwargs)


class OperationType(str, Enum):
    """
    Enum for supported DataFog operations.

    SCAN: Detect and annotate PII in text
    EXTRACT: Extract text from images
    REDACT: Remove PII from text
    REPLACE: Replace PII with fake data
    HASH: Replace PII with a hash
    """

    SCAN = "scan"
    EXTRACT = "extract"
    REDACT = "redact"
    REPLACE = "replace"
    HASH = "hash"
