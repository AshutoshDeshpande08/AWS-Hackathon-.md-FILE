"""
Configuration module for VeriGov AI.

Provides secure API configuration management and credential handling.
"""

from .api_configuration import (
    APIConfiguration,
    ConfigurationError,
    ValidationResult,
)

__all__ = [
    "APIConfiguration",
    "ConfigurationError",
    "ValidationResult",
]
