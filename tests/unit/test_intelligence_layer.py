"""
Unit tests for Intelligence Layer module.

Tests semantic analysis, entity extraction, retry logic, and error handling.
"""

import os
import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from src.verigov.verification.intelligence_layer import (
    IntelligenceLayer,
    Entity,
    EntityType,
    SemanticMatch,
    SemanticAnalysis,
    ComparisonResult,
    IntelligenceError,
    RateLimitError,
    APIQuotaExceededError
)
from src.verigov.config import APIConfiguration, ConfigurationError


@pytest.fixture
def mock_api_config():
    """Create a mock API configuration."""
    with patch.dict(os.environ, {"GROK_API_KEY": "test_key_123"}):
        return APIConfiguration()


@pytest.fixture
def intelligence_layer(mock_api_config):
    """Create an IntelligenceLayer instance with mock config."""
    return IntelligenceLayer(mock_api_config)


class TestIntelligenceLayerInitialization:
    """Test Intelligence Layer initialization."""
    
    def test_initialization_success(self, mock_api_config):
        """Test successful initialization with valid config."""
        layer = IntelligenceLayer(mock_api_config)
        assert layer.api_config == mock_api_config
        assert layer.max_retries == 3
        assert layer.initial_retry_delay == 1.0
        assert layer.timeout == 30
    
    def test_initialization_custom_params(self, mock_api_config):
        """Test initialization with custom parameters."""
        layer = IntelligenceLayer(
            mock_api_config,
            max_retries=5,
            initial_retry_delay=2.0,
            timeout=60
        )
        assert layer.max_retries == 5
        assert layer.initial_retry_delay == 2.0
        assert layer.timeout == 60
    
    def test_initialization_missing_api_key(self):
        """Test initialization fails with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfiguration()
            
            with pytest.raises(ConfigurationError):
                IntelligenceLayer(config)


class TestEntityDataClass:
    """Test Entity data class."""
    
    def test_entity_creation_valid(self):
        """Test creating a valid entity."""
        entity = Entity(
            text="Ministry of Health",
            entity_type=EntityType.ORGANIZATION.value,
            relevance_score=0.9
        )
        assert entity.text == "Ministry of Health"
        assert entity.entity_type == "ORGANIZATION"
        assert entity.relevance_score == 0.9
    
    def test_entity_invalid_relevance_score_high(self):
        """Test entity creation fails with relevance score > 1.0."""
        with pytest.raises(ValueError) as exc_info:
            Entity(
                text="Test",
                entity_type="PERSON",
                relevance_score=1.5
            )
        assert "0.0 and 1.0" in str(exc_info.value)
    
    def test_entity_invalid_relevance_score_low(self):
        """Test entity creation fails with relevance score < 0.0."""
        with pytest.raises(ValueError) as exc_info:
            Entity(
                text="Test",
                entity_type="PERSON",
                relevance_score=-0.1
            )
        assert "0.0 and 1.0" in str(exc_info.value)


class TestSemanticMatchDataClass:
    """Test SemanticMatch data class."""
    
    def test_semantic_match_creation_valid(self):
        """Test creating a valid semantic match."""
        match = SemanticMatch(
            official_text="The policy was enacted in 2023",
            source_url="https://gov.example.com/policy",
            similarity_score=0.85,
            matching_context="Policy implementation details"
        )
        assert match.official_text == "The policy was enacted in 2023"
        assert match.similarity_score == 0.85
    
    def test_semantic_match_invalid_similarity_score(self):
        """Test semantic match creation fails with invalid similarity score."""
        with pytest.raises(ValueError) as exc_info:
            SemanticMatch(
                official_text="Test",
                source_url="https://example.com",
                similarity_score=1.2,
                matching_context="Context"
            )
        assert "0.0 and 1.0" in str(exc_info.value)


class TestSemanticAnalysisDataClass:
    """Test SemanticAnalysis data class."""
    
    def test_semantic_analysis_creation_valid(self):
        """Test creating a valid semantic analysis."""
        entities = [
            Entity("John Doe", EntityType.PERSON.value, 0.9),
            Entity("Ministry", EntityType.ORGANIZATION.value, 0.8)
        ]
        matches = [
            SemanticMatch("Official text", "https://gov.com", 0.7, "Context")
        ]
        
        analysis = SemanticAnalysis(
            claim="Test claim",
            entities=entities,
            policy_references=["Policy A", "Policy B"],
            key_dates=[datetime.now()],
            context="Test context",
            semantic_matches=matches,
            confidence=0.75
        )
        
        assert analysis.claim == "Test claim"
        assert len(analysis.entities) == 2
        assert len(analysis.policy_references) == 2
        assert analysis.confidence == 0.75
    
    def test_semantic_analysis_invalid_confidence(self):
        """Test semantic analysis creation fails with invalid confidence."""
        with pytest.raises(ValueError) as exc_info:
            SemanticAnalysis(
                claim="Test",
                entities=[],
                policy_references=[],
                key_dates=[],
                context="",
                semantic_matches=[],
                confidence=1.5
            )
        assert "0.0 and 1.0" in str(exc_info.value)


class TestComparisonResultDataClass:
    """Test ComparisonResult data class."""
    
    def test_comparison_result_creation_valid(self):
        """Test creating a valid comparison result."""
        result = ComparisonResult(
            claim="Test claim",
            official_statement="Official statement",
            similarity_score=0.8,
            differences=["Diff 1", "Diff 2"],
            matching_points=["Match 1"],
            analysis="Detailed analysis"
        )
        
        assert result.claim == "Test claim"
        assert result.similarity_score == 0.8
        assert len(result.differences) == 2
        assert len(result.matching_points) == 1
    
    def test_comparison_result_invalid_similarity_score(self):
        """Test comparison result creation fails with invalid similarity score."""
        with pytest.raises(ValueError) as exc_info:
            ComparisonResult(
                claim="Test",
                official_statement="Statement",
                similarity_score=-0.1,
                differences=[],
                matching_points=[],
                analysis=""
            )
        assert "0.0 and 1.0" in str(exc_info.value)


class TestAPIRequestRetryLogic:
    """Test API request retry logic with exponential backoff."""
    
    def test_make_api_request_success_first_try(self, intelligence_layer):
        """Test successful API request on first try."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
        
        with patch.object(intelligence_layer.session, 'post', return_value=mock_response):
            result = intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
            assert result == {"choices": [{"message": {"content": "test"}}]}
    
    def test_make_api_request_retry_on_timeout(self, intelligence_layer):
        """Test retry logic on timeout."""
        import requests
        
        # First two calls timeout, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "success"}}]}
        
        with patch.object(intelligence_layer.session, 'post') as mock_post:
            mock_post.side_effect = [
                requests.exceptions.Timeout(),
                requests.exceptions.Timeout(),
                mock_response
            ]
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
                assert result == {"choices": [{"message": {"content": "success"}}]}
                assert mock_post.call_count == 3
    
    def test_make_api_request_max_retries_exceeded(self, intelligence_layer):
        """Test that IntelligenceError is raised after max retries."""
        import requests
        
        with patch.object(intelligence_layer.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            
            with patch('time.sleep'):
                with pytest.raises(IntelligenceError) as exc_info:
                    intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
                
                assert "timeout after" in str(exc_info.value).lower()
                assert mock_post.call_count == 4  # Initial + 3 retries
    
    def test_make_api_request_rate_limit_retry(self, intelligence_layer):
        """Test retry on rate limit (429) response."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"choices": [{"message": {"content": "success"}}]}
        
        with patch.object(intelligence_layer.session, 'post') as mock_post:
            mock_post.side_effect = [mock_response_429, mock_response_200]
            
            with patch('time.sleep'):
                result = intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
                assert result == {"choices": [{"message": {"content": "success"}}]}
                assert mock_post.call_count == 2
    
    def test_make_api_request_rate_limit_max_retries(self, intelligence_layer):
        """Test RateLimitError after max retries on 429."""
        mock_response = Mock()
        mock_response.status_code = 429
        
        with patch.object(intelligence_layer.session, 'post', return_value=mock_response):
            with patch('time.sleep'):
                with pytest.raises(RateLimitError) as exc_info:
                    intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
                
                assert "rate limit exceeded" in str(exc_info.value).lower()
    
    def test_make_api_request_quota_exceeded(self, intelligence_layer):
        """Test APIQuotaExceededError on 403 with quota message."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "quota exceeded"}
        mock_response.content = b'{"error": "quota exceeded"}'
        
        with patch.object(intelligence_layer.session, 'post', return_value=mock_response):
            with pytest.raises(APIQuotaExceededError) as exc_info:
                intelligence_layer._make_api_request('test/endpoint', {'test': 'data'})
            
            assert "quota exceeded" in str(exc_info.value).lower()


class TestResponseValidation:
    """Test API response validation."""
    
    def test_validate_response_valid(self, intelligence_layer):
        """Test validation passes for valid response."""
        response = {"field1": "value1", "field2": "value2"}
        # Should not raise
        intelligence_layer._validate_response(response, ["field1", "field2"])
    
    def test_validate_response_missing_fields(self, intelligence_layer):
        """Test validation fails for missing fields."""
        response = {"field1": "value1"}
        
        with pytest.raises(IntelligenceError) as exc_info:
            intelligence_layer._validate_response(response, ["field1", "field2", "field3"])
        
        assert "missing fields" in str(exc_info.value).lower()
        assert "field2" in str(exc_info.value)
    
    def test_validate_response_not_dict(self, intelligence_layer):
        """Test validation fails for non-dict response."""
        response = "not a dict"
        
        with pytest.raises(IntelligenceError) as exc_info:
            intelligence_layer._validate_response(response, ["field1"])
        
        assert "invalid response format" in str(exc_info.value).lower()


class TestEntityParsing:
    """Test entity parsing from API responses."""
    
    def test_parse_entities_valid(self, intelligence_layer):
        """Test parsing valid entities."""
        entities_data = [
            {"text": "John Doe", "type": "PERSON", "relevance": 0.9},
            {"text": "Ministry", "type": "ORGANIZATION", "relevance": 0.8}
        ]
        
        entities = intelligence_layer._parse_entities(entities_data)
        
        assert len(entities) == 2
        assert entities[0].text == "John Doe"
        assert entities[0].entity_type == "PERSON"
        assert entities[0].relevance_score == 0.9
    
    def test_parse_entities_missing_fields(self, intelligence_layer):
        """Test parsing entities with missing fields uses defaults."""
        entities_data = [
            {"text": "Test Entity"}  # Missing type and relevance
        ]
        
        entities = intelligence_layer._parse_entities(entities_data)
        
        assert len(entities) == 1
        assert entities[0].text == "Test Entity"
        assert entities[0].entity_type == "UNKNOWN"
        assert entities[0].relevance_score == 0.5
    
    def test_parse_entities_invalid_data_skipped(self, intelligence_layer):
        """Test that invalid entities are skipped."""
        entities_data = [
            {"text": "Valid", "type": "PERSON", "relevance": 0.9},
            {"text": "Invalid", "type": "PERSON", "relevance": 2.0},  # Invalid score
            {"text": "Also Valid", "type": "ORGANIZATION", "relevance": 0.7}
        ]
        
        entities = intelligence_layer._parse_entities(entities_data)
        
        # Invalid entity should be skipped
        assert len(entities) == 2
        assert entities[0].text == "Valid"
        assert entities[1].text == "Also Valid"


class TestDateParsing:
    """Test date parsing from API responses."""
    
    def test_parse_dates_valid_iso_format(self, intelligence_layer):
        """Test parsing valid ISO format dates."""
        dates_data = [
            "2023-01-15T10:30:00Z",
            "2023-06-20T14:45:00+00:00"
        ]
        
        dates = intelligence_layer._parse_dates(dates_data)
        
        assert len(dates) == 2
        assert isinstance(dates[0], datetime)
        assert isinstance(dates[1], datetime)
    
    def test_parse_dates_invalid_format_skipped(self, intelligence_layer):
        """Test that invalid date formats are skipped."""
        dates_data = [
            "2023-01-15T10:30:00Z",
            "invalid date",
            "2023-06-20T14:45:00Z"
        ]
        
        dates = intelligence_layer._parse_dates(dates_data)
        
        # Invalid date should be skipped
        assert len(dates) == 2


class TestContextManager:
    """Test context manager functionality."""
    
    def test_context_manager_usage(self, mock_api_config):
        """Test using IntelligenceLayer as context manager."""
        with IntelligenceLayer(mock_api_config) as layer:
            assert layer is not None
            assert layer.session is not None
        
        # Session should be closed after context exit
        # (We can't easily test this without implementation details)
    
    def test_close_method(self, intelligence_layer):
        """Test close method closes session."""
        intelligence_layer.close()
        # Session should be closed (implementation detail)


class TestAnalyzeClaimBasic:
    """Test basic analyze_claim functionality."""
    
    def test_analyze_claim_minimal_response(self, intelligence_layer):
        """Test analyze_claim with minimal valid response."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "entities": [],
                        "policy_references": [],
                        "key_dates": [],
                        "context": "Test context",
                        "semantic_matches": [],
                        "confidence": 0.7
                    })
                }
            }]
        }
        
        with patch.object(intelligence_layer, '_make_api_request', return_value=mock_response):
            result = intelligence_layer.analyze_claim("Test claim")
            
            assert isinstance(result, SemanticAnalysis)
            assert result.claim == "Test claim"
            assert result.confidence == 0.7
            assert result.context == "Test context"
    
    def test_analyze_claim_with_entities(self, intelligence_layer):
        """Test analyze_claim extracts entities correctly."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "entities": [
                            {"text": "John Doe", "type": "PERSON", "relevance": 0.9}
                        ],
                        "policy_references": ["Policy A"],
                        "key_dates": ["2023-01-15T10:00:00Z"],
                        "context": "Context",
                        "semantic_matches": [],
                        "confidence": 0.8
                    })
                }
            }]
        }
        
        with patch.object(intelligence_layer, '_make_api_request', return_value=mock_response):
            result = intelligence_layer.analyze_claim("Test claim")
            
            assert len(result.entities) == 1
            assert result.entities[0].text == "John Doe"
            assert len(result.policy_references) == 1
            assert len(result.key_dates) == 1


class TestExtractEntities:
    """Test extract_entities functionality."""
    
    def test_extract_entities_success(self, intelligence_layer):
        """Test successful entity extraction."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "entities": [
                            {"text": "Ministry of Health", "type": "ORGANIZATION", "relevance": 0.9},
                            {"text": "2023", "type": "DATE", "relevance": 0.7}
                        ]
                    })
                }
            }]
        }
        
        with patch.object(intelligence_layer, '_make_api_request', return_value=mock_response):
            entities = intelligence_layer.extract_entities("Test text with entities")
            
            assert len(entities) == 2
            assert entities[0].text == "Ministry of Health"
            assert entities[0].entity_type == "ORGANIZATION"


class TestCompareStatements:
    """Test compare_statements functionality."""
    
    def test_compare_statements_success(self, intelligence_layer):
        """Test successful statement comparison."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "similarity_score": 0.85,
                        "differences": ["Difference 1"],
                        "matching_points": ["Match 1", "Match 2"],
                        "analysis": "Detailed comparison analysis"
                    })
                }
            }]
        }
        
        with patch.object(intelligence_layer, '_make_api_request', return_value=mock_response):
            result = intelligence_layer.compare_statements(
                "Test claim",
                "Official statement"
            )
            
            assert isinstance(result, ComparisonResult)
            assert result.similarity_score == 0.85
            assert len(result.differences) == 1
            assert len(result.matching_points) == 2
            assert result.analysis == "Detailed comparison analysis"
