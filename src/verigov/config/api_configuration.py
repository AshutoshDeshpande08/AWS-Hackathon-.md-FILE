"""
API Configuration Module for VeriGov AI.

This module provides secure management of API credentials and connection settings.
It loads configuration from environment variables and validates settings before use.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


# Configure logging - never log API keys
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid."""
    pass


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class APIConfiguration:
    """
    Manages API credentials and connection settings securely.
    
    Loads configuration from environment variables and provides
    validated access to API keys and credentials. Never logs or
    exposes credentials in plain text.
    """
    
    def __init__(self, config_source: str = "env"):
        """
        Initialize API configuration.
        
        Args:
            config_source: Source of configuration ("env" for environment variables)
        
        Raises:
            ConfigurationError: If config_source is not supported
        """
        if config_source != "env":
            raise ConfigurationError(
                f"Unsupported configuration source: {config_source}. "
                "Only 'env' is currently supported."
            )
        
        self.config_source = config_source
        self._groq_api_key: Optional[str] = None
        self._groq_api_url: Optional[str] = None
        self._gov_api_credentials: Dict[str, Dict[str, str]] = {}
        
        # Load configuration on initialization
        self._load_configuration()
        
        logger.info("API Configuration initialized from environment variables")
    
    def _load_configuration(self) -> None:
        """
        Load configuration from environment variables.
        
        Loads Groq AI settings and scans for government API credentials.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Load Groq AI configuration
        self._groq_api_key = os.getenv("GROQ_API_KEY")
        self._groq_api_url = os.getenv("GROQ_API_URL", "https://api.x.ai/v1")
        
        # Load government API credentials
        # Scan for GOV_API_KEY_* and GOV_API_URL_* patterns
        for key, value in os.environ.items():
            if key.startswith("GOV_API_KEY_"):
                # Extract the API name (e.g., "1" from "GOV_API_KEY_1")
                api_name = key.replace("GOV_API_KEY_", "")
                
                if api_name not in self._gov_api_credentials:
                    self._gov_api_credentials[api_name] = {}
                
                self._gov_api_credentials[api_name]["api_key"] = value
            
            elif key.startswith("GOV_API_URL_"):
                api_name = key.replace("GOV_API_URL_", "")
                
                if api_name not in self._gov_api_credentials:
                    self._gov_api_credentials[api_name] = {}
                
                self._gov_api_credentials[api_name]["api_url"] = value
        
        logger.info(
            f"Configuration loaded: Groq AI configured, "
            f"{len(self._gov_api_credentials)} government API(s) found"
        )
    
    def get_groq_api_key(self) -> str:
        """
        Retrieve Groq AI API key with error handling.

        Returns:
            str: The Groq AI API key

        Raises:
            ConfigurationError: If the API key is missing or invalid
        """
        if not self._groq_api_key:
            raise ConfigurationError("Groq AI API key is not configured (GROQ_API_KEY).")

        if not self._groq_api_key.strip():
            raise ConfigurationError("Groq AI API key is empty (GROQ_API_KEY).")

        return self._groq_api_key
    
    def get_groq_api_url(self) -> str:
        """
        Retrieve Groq AI URL.
        
        Returns:
            str: The Groq AI URL (defaults to https://api.x.ai/v1)
        """
        return self._groq_api_url or "https://api.x.ai/v1"
    
    def get_government_api_credentials(self, api_name: str) -> Dict[str, str]:
        """
        Retrieve government API credentials with secure storage.
        
        Args:
            api_name: Name/identifier of the government API
        
        Returns:
            Dict containing 'api_key' and 'api_url' for the specified API
        
        Raises:
            ConfigurationError: If credentials are not found or incomplete
        """
        if api_name not in self._gov_api_credentials:
            raise ConfigurationError(
                f"Government API credentials for '{api_name}' are not configured. "
                f"Please set GOV_API_KEY_{api_name} and GOV_API_URL_{api_name} "
                "environment variables."
            )
        
        credentials = self._gov_api_credentials[api_name]
        
        # Validate that both key and URL are present
        if "api_key" not in credentials:
            raise ConfigurationError(
                f"Government API key for '{api_name}' is missing. "
                f"Please set GOV_API_KEY_{api_name} environment variable."
            )
        
        if "api_url" not in credentials:
            raise ConfigurationError(
                f"Government API URL for '{api_name}' is missing. "
                f"Please set GOV_API_URL_{api_name} environment variable."
            )
        
        # Log access without exposing credentials
        logger.debug(f"Government API credentials for '{api_name}' retrieved successfully")
        
        return credentials.copy()  # Return a copy to prevent modification
    
    def list_government_apis(self) -> list[str]:
        """
        List all configured government API names.
        
        Returns:
            List of government API identifiers
        """
        return list(self._gov_api_credentials.keys())
    
    def validate_configuration(self) -> ValidationResult:
        """
        Validate the current configuration.

        Returns:
            ValidationResult: The result of the validation.
        """
        errors = []
        warnings = []

        # Validate Groq AI API key
        if not self._groq_api_key:
            errors.append("Groq AI key is not configured (GROQ_API_KEY).")
        elif not self._groq_api_key.strip():
            errors.append("Groq AI key is empty (GROQ_API_KEY).")

        # Validate Groq AI API URL
        if not self._groq_api_url:
            errors.append("Groq AI URL is not configured (GROQ_API_URL).")
        elif not self._groq_api_url.startswith("https://"):
            errors.append("Groq AI URL must use HTTPS protocol (GROQ_API_URL).")

        # Validate government API credentials
        for api_name, credentials in self._gov_api_credentials.items():
            if "api_url" in credentials and not credentials["api_url"].startswith("https://"):
                errors.append(f"Government API '{api_name}' URL must use HTTPS protocol.")

        if not self._gov_api_credentials:
            warnings.append("No government API credentials configured. Set GOV_API_KEY_* and GOV_API_URL_* environment variables if needed.")

        is_valid = not errors
        if not is_valid:
            logger.error(f"Configuration validation failed with {len(errors)} error(s): {errors}")

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def reload_configuration(self) -> None:
        """
        Reload the configuration from environment variables.
        """
        self._groq_api_key = os.getenv("GROQ_API_KEY")
        self._groq_api_url = os.getenv("GROQ_API_URL", "https://api.x.ai/v1")
        self._gov_api_credentials.clear()
        self._load_configuration()
        logger.info("Configuration reloaded successfully.")
