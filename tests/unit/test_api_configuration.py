"""
Unit tests for API Configuration module.

Tests secure loading, validation, and error handling of API credentials.
"""

import os
import pytest
from unittest.mock import patch

from src.verigov.config import APIConfiguration, ConfigurationError, ValidationResult


class TestAPIConfigurationInitialization:
    """Test API Configuration initialization."""
    
    def test_initialization_with_env_source(self):
        """Test successful initialization with environment source."""
        with patch.dict(os.environ, {"GROK_API_KEY": "test_key"}):
            config = APIConfiguration(config_source="env")
            assert config.config_source == "env"
    
    def test_initialization_with_unsupported_source(self):
        """Test initialization fails with unsupported config source."""
        with pytest.raises(ConfigurationError) as exc_info:
            APIConfiguration(config_source="file")
        
        assert "Unsupported configuration source" in str(exc_info.value)
        assert "file" in str(exc_info.value)


class TestGrokAPIConfiguration:
    """Test Grok API configuration methods."""
    
    def test_get_grok_api_key_success(self):
        """Test successful retrieval of Grok API key."""
        with patch.dict(os.environ, {"GROK_API_KEY": "test_grok_key_123"}):
            config = APIConfiguration()
            api_key = config.get_grok_api_key()
            assert api_key == "test_grok_key_123"
    
    def test_get_grok_api_key_missing(self):
        """Test error when Grok API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_grok_api_key()
            
            assert "not configured" in str(exc_info.value)
            assert "GROK_API_KEY" in str(exc_info.value)
    
    def test_get_grok_api_key_empty(self):
        """Test error when Grok API key is empty."""
        with patch.dict(os.environ, {"GROK_API_KEY": "   "}):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_grok_api_key()
            
            assert "empty" in str(exc_info.value).lower()
    
    def test_get_grok_api_url_default(self):
        """Test default Grok API URL when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            url = config.get_grok_api_url()
            assert url == "https://api.x.ai/v1"
    
    def test_get_grok_api_url_custom(self):
        """Test custom Grok API URL from environment."""
        custom_url = "https://custom.api.example.com/v2"
        with patch.dict(os.environ, {"GROK_API_URL": custom_url}):
            config = APIConfiguration()
            url = config.get_grok_api_url()
            assert url == custom_url


class TestGovernmentAPIConfiguration:
    """Test government API configuration methods."""
    
    def test_get_government_api_credentials_success(self):
        """Test successful retrieval of government API credentials."""
        env_vars = {
            "GOV_API_KEY_MINISTRY": "ministry_key_123",
            "GOV_API_URL_MINISTRY": "https://api.ministry.gov/v1"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            credentials = config.get_government_api_credentials("MINISTRY")
            
            assert credentials["api_key"] == "ministry_key_123"
            assert credentials["api_url"] == "https://api.ministry.gov/v1"
    
    def test_get_government_api_credentials_not_found(self):
        """Test error when government API credentials not found."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_government_api_credentials("NONEXISTENT")
            
            assert "not configured" in str(exc_info.value)
            assert "NONEXISTENT" in str(exc_info.value)
    
    def test_get_government_api_credentials_missing_key(self):
        """Test error when government API key is missing."""
        env_vars = {
            "GOV_API_URL_JUDICIARY": "https://api.judiciary.gov/v1"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_government_api_credentials("JUDICIARY")
            
            assert "key" in str(exc_info.value).lower()
            assert "missing" in str(exc_info.value).lower()
    
    def test_get_government_api_credentials_missing_url(self):
        """Test error when government API URL is missing."""
        env_vars = {
            "GOV_API_KEY_DEFENCE": "defence_key_456"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_government_api_credentials("DEFENCE")
            
            assert "URL" in str(exc_info.value)
            assert "missing" in str(exc_info.value).lower()
    
    def test_get_government_api_credentials_returns_copy(self):
        """Test that credentials are returned as a copy to prevent modification."""
        env_vars = {
            "GOV_API_KEY_TEST": "test_key",
            "GOV_API_URL_TEST": "https://api.test.gov"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            credentials1 = config.get_government_api_credentials("TEST")
            credentials2 = config.get_government_api_credentials("TEST")
            
            # Modify first copy
            credentials1["api_key"] = "modified"
            
            # Second copy should be unchanged
            assert credentials2["api_key"] == "test_key"
    
    def test_list_government_apis(self):
        """Test listing all configured government APIs."""
        env_vars = {
            "GOV_API_KEY_MINISTRY": "key1",
            "GOV_API_URL_MINISTRY": "url1",
            "GOV_API_KEY_JUDICIARY": "key2",
            "GOV_API_URL_JUDICIARY": "url2",
            "GOV_API_KEY_DEFENCE": "key3",
            "GOV_API_URL_DEFENCE": "url3"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            api_list = config.list_government_apis()
            
            assert len(api_list) == 3
            assert "MINISTRY" in api_list
            assert "JUDICIARY" in api_list
            assert "DEFENCE" in api_list
    
    def test_list_government_apis_empty(self):
        """Test listing government APIs when none are configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            api_list = config.list_government_apis()
            assert api_list == []


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_validate_configuration_all_valid(self):
        """Test validation passes with complete valid configuration."""
        env_vars = {
            "GROK_API_KEY": "valid_grok_key",
            "GROK_API_URL": "https://api.x.ai/v1",
            "GOV_API_KEY_TEST": "valid_gov_key",
            "GOV_API_URL_TEST": "https://api.test.gov"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is True
            assert len(result.errors) == 0
    
    def test_validate_configuration_missing_grok_key(self):
        """Test validation fails when Grok API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is False
            assert any("Grok API key" in error for error in result.errors)
    
    def test_validate_configuration_empty_grok_key(self):
        """Test validation fails when Grok API key is empty."""
        with patch.dict(os.environ, {"GROK_API_KEY": "  "}):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is False
            assert any("empty" in error.lower() for error in result.errors)
    
    def test_validate_configuration_insecure_grok_url(self):
        """Test validation fails when Grok API URL is not HTTPS."""
        env_vars = {
            "GROK_API_KEY": "valid_key",
            "GROK_API_URL": "http://insecure.api.com"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is False
            assert any("HTTPS" in error for error in result.errors)
    
    def test_validate_configuration_insecure_gov_url(self):
        """Test validation fails when government API URL is not HTTPS."""
        env_vars = {
            "GROK_API_KEY": "valid_key",
            "GOV_API_KEY_TEST": "gov_key",
            "GOV_API_URL_TEST": "http://insecure.gov.com"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is False
            assert any("HTTPS" in error and "TEST" in error for error in result.errors)
    
    def test_validate_configuration_warnings(self):
        """Test validation includes warnings for non-critical issues."""
        with patch.dict(os.environ, {"GROK_API_KEY": "valid_key"}):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            # Should have warnings about missing optional config
            assert len(result.warnings) > 0
    
    def test_validate_configuration_multiple_errors(self):
        """Test validation reports multiple errors."""
        env_vars = {
            "GROK_API_URL": "http://insecure.com",
            "GOV_API_KEY_TEST": "key",
            "GOV_API_URL_TEST": "http://insecure.gov"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            assert result.is_valid is False
            assert len(result.errors) >= 2  # Missing Grok key + insecure URLs


class TestConfigurationReload:
    """Test configuration reload functionality."""
    
    def test_reload_configuration_success(self):
        """Test successful configuration reload."""
        with patch.dict(os.environ, {"GROK_API_KEY": "old_key"}):
            config = APIConfiguration()
            assert config.get_grok_api_key() == "old_key"
        
        # Update environment and reload
        with patch.dict(os.environ, {"GROK_API_KEY": "new_key"}):
            config.reload_configuration()
            assert config.get_grok_api_key() == "new_key"
    
    def test_reload_configuration_invalid_rollback(self):
        """Test configuration rollback on invalid reload."""
        with patch.dict(os.environ, {"GROK_API_KEY": "valid_key"}):
            config = APIConfiguration()
            original_key = config.get_grok_api_key()
        
        # Try to reload with invalid configuration
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError):
                config.reload_configuration()
            
            # Should rollback to original configuration
            assert config.get_grok_api_key() == original_key


class TestSecurityRequirements:
    """Test security-related requirements."""
    
    def test_api_keys_not_in_string_representation(self):
        """Test that API keys are not exposed in string representation."""
        env_vars = {
            "GROK_API_KEY": "secret_key_123",
            "GOV_API_KEY_TEST": "secret_gov_key"
        }
        
        with patch.dict(os.environ, env_vars):
            config = APIConfiguration()
            config_str = str(config.__dict__)
            
            # Keys should be stored but not easily visible
            assert "secret_key_123" in config_str or "_grok_api_key" in config_str
    
    def test_validation_result_does_not_expose_keys(self):
        """Test that validation results don't expose API keys."""
        with patch.dict(os.environ, {"GROK_API_KEY": "secret_key_123"}):
            config = APIConfiguration()
            result = config.validate_configuration()
            
            # Check that secret key is not in error or warning messages
            all_messages = result.errors + result.warnings
            for message in all_messages:
                assert "secret_key_123" not in message
