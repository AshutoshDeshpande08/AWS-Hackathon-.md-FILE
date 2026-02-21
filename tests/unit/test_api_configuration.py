"""
Unit tests for API Configuration module.

Tests secure loading, validation, and error handling of API credentials.
"""

import os
import pytest
from unittest.mock import patch

from src.verigov.config import APIConfiguration, ConfigurationError, ValidationResult


def test_initialization_with_env_source():
    """Test successful initialization with environment source."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}):
        config = APIConfiguration(config_source="env")
        assert config.config_source == "env"

def test_initialization_with_unsupported_source():
    """Test initialization fails with unsupported config source."""
    with pytest.raises(ConfigurationError) as exc_info:
        APIConfiguration(config_source="file")

    assert "Unsupported configuration source" in str(exc_info.value)
    assert "file" in str(exc_info.value)

def test_get_groq_api_key_success():
    """Test successful retrieval of Groq AI key."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key_123"}):
        config = APIConfiguration()
        api_key = config.get_groq_api_key()
        assert api_key == "test_groq_key_123"

def test_get_groq_api_key_missing():
    """Test error when Groq AI key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        config = APIConfiguration()

        with pytest.raises(ConfigurationError) as exc_info:
            config.get_groq_api_key()

        assert "not configured" in str(exc_info.value)
        assert "GROQ_API_KEY" in str(exc_info.value)

def test_get_groq_api_key_empty():
    """Test error when Groq AI key is empty."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "   "}):
        config = APIConfiguration()

        with pytest.raises(ConfigurationError) as exc_info:
            config.get_groq_api_key()

        assert "empty" in str(exc_info.value).lower()

def test_get_groq_api_url_default():
    """Test default Groq AI URL when not configured."""
    with patch.dict(os.environ, {}, clear=True):
        config = APIConfiguration()
        url = config.get_groq_api_url()
        assert url == "https://api.x.ai/v1"

def test_get_groq_api_url_custom():
    """Test custom Groq AI URL from environment."""
    custom_url = "https://custom.api.example.com/v2"
    with patch.dict(os.environ, {"GROQ_API_URL": custom_url}):
        config = APIConfiguration()
        url = config.get_groq_api_url()
        assert url == custom_url

def test_validate_configuration_all_valid():
    """Test validation passes with complete valid configuration."""
    env_vars = {
        "GROQ_API_KEY": "valid_groq_key",
        "GROQ_API_URL": "https://api.x.ai/v1",
        "GOV_API_KEY_TEST": "valid_gov_key",
        "GOV_API_URL_TEST": "https://api.test.gov"
    }

    with patch.dict(os.environ, env_vars):
        config = APIConfiguration()
        result = config.validate_configuration()

        assert result.is_valid is True
        assert len(result.errors) == 0
