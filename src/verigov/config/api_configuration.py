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
        self._grok_api_key: Optional[str] = None
        self._grok_api_url: Optional[str] = None
        self._gov_api_credentials: Dict[str, Dict[str, str]] = {}
        
        # Load configuration on initialization
        self._load_configuration()
        
        logger.info("API Configuration initialized from environment variables")
    
    def _load_configuration(self) -> None:
        """
        Load configuration from environment variables.
        
        Loads Grok API settings and scans for government API credentials.
        """
        # Load Grok API configuration
        self._grok_api_key = os.getenv("GROK_API_KEY")
        self._grok_api_url = os.getenv("GROK_API_URL", "https://api.x.ai/v1")
        
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
            f"Configuration loaded: Grok API configured, "
            f"{len(self._gov_api_credentials)} government API(s) found"
        )
    
    def get_grok_api_key(self) -> str:
        """
        Retrieve Grok API key with error handling.
        
        Returns:
            str: The Grok API key
        
        Raises:
            ConfigurationError: If API key is missing or invalid
        """
        if not self._grok_api_key:
            raise ConfigurationError(
                "Grok API key is not configured. "
                "Please set the GROK_API_KEY environment variable."
            )
        
        if not self._grok_api_key.strip():
            raise ConfigurationError(
                "Grok API key is empty. "
                "Please provide a valid GROK_API_KEY environment variable."
            )
        
        # Log access without exposing the key
        logger.debug("Grok API key retrieved successfully")
        
        return self._grok_api_key
    
    def get_grok_api_url(self) -> str:
        """
        Retrieve Grok API URL.
        
        Returns:
            str: The Grok API URL (defaults to https://api.x.ai/v1)
        """
        return self._grok_api_url or "https://api.x.ai/v1"
    
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
        Validate all configuration settings.
        
        Checks for required keys, valid formats, and completeness.
        
        Returns:
            ValidationResult with validation status, errors, and warnings
        """
        errors = []
        warnings = []
        
        # Validate Grok API configuration
        if not self._grok_api_key:
            errors.append("Grok API key is not configured (GROK_API_KEY)")
        elif not self._grok_api_key.strip():
            errors.append("Grok API key is empty")
        
        if not self._grok_api_url:
            warnings.append("Grok API URL not set, using default: https://api.x.ai/v1")
        elif not self._grok_api_url.startswith("https://"):
            errors.append("Grok API URL must use HTTPS protocol")
        
        # Validate government API credentials
        for api_name, credentials in self._gov_api_credentials.items():
            if "api_key" not in credentials or not credentials["api_key"].strip():
                errors.append(f"Government API '{api_name}' has missing or empty API key")
            
            if "api_url" not in credentials:
                errors.append(f"Government API '{api_name}' is missing API URL")
            elif not credentials["api_url"].startswith("https://"):
                errors.append(
                    f"Government API '{api_name}' URL must use HTTPS protocol"
                )
        
        # Check if any government APIs are configured
        if not self._gov_api_credentials:
            warnings.append(
                "No government API credentials configured. "
                "Set GOV_API_KEY_* and GOV_API_URL_* environment variables if needed."
            )
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Configuration validation passed")
        else:
            logger.error(f"Configuration validation failed with {len(errors)} error(s)")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def reload_configuration(self) -> None:
        """
        Reload configuration from environment variables.
        
        Useful when environment variables have been updated at runtime.
        
        Raises:
            ConfigurationError: If new configuration is invalid
        """
        logger.info("Reloading configuration from environment variables")
        
        # Store old configuration for rollback
        old_grok_key = self._grok_api_key
        old_grok_url = self._grok_api_url
        old_gov_creds = self._gov_api_credentials.copy()
        
        try:
            # Clear and reload
            self._grok_api_key = None
            self._grok_api_url = None
            self._gov_api_credentials = {}
            
            self._load_configuration()
            
            # Validate new configuration
            validation = self.validate_configuration()
            
            if not validation.is_valid:
                # Rollback on validation failure
                self._grok_api_key = old_grok_key
                self._grok_api_url = old_grok_url
                self._gov_api_credentials = old_gov_creds
                
                raise ConfigurationError(
                    f"Configuration reload failed validation: {', '.join(validation.errors)}"
                )
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            # Rollback on any error
            self._grok_api_key = old_grok_key
            self._grok_api_url = old_grok_url
            self._gov_api_credentials = old_gov_creds
            
            logger.error(f"Configuration reload failed: {e}")
            raise ConfigurationError(f"Failed to reload configuration: {e}")
