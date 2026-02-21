"""
Intelligence Layer Module for VeriGov AI

Provides AI-powered semantic analysis using Groq AI for claim verification.
Implements entity extraction, context-aware analysis, retry logic, and rate limiting.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

import time
import logging
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from ..config.api_configuration import APIConfiguration, ConfigurationError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EntityType(Enum):
    """Types of entities that can be extracted."""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    POLICY = "POLICY"
    DATE = "DATE"
    LOCATION = "LOCATION"


class IntelligenceError(Exception):
    """Raised when intelligence layer operations fail."""
    pass


class RateLimitError(IntelligenceError):
    """Raised when API rate limit is exceeded."""
    pass


class APIQuotaExceededError(IntelligenceError):
    """Raised when API quota is exceeded."""
    pass


@dataclass
class Entity:
    """
    Represents an extracted entity from text.
    
    Attributes:
        text: The entity text
        entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
        relevance_score: Relevance score (0.0-1.0)
    """
    text: str
    entity_type: str
    relevance_score: float
    
    def __post_init__(self):
        """Validate entity data."""
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(f"Relevance score must be between 0.0 and 1.0, got {self.relevance_score}")


@dataclass
class SemanticMatch:
    """
    Represents a semantic match between claim and official text.
    
    Attributes:
        official_text: The matching official text
        source_url: URL of the source document
        similarity_score: Similarity score (0.0-1.0)
        matching_context: Context around the match
    """
    official_text: str
    source_url: str
    similarity_score: float
    matching_context: str
    
    def __post_init__(self):
        """Validate semantic match data."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {self.similarity_score}")


@dataclass
class SemanticAnalysis:
    """
    Result of semantic analysis of a claim.
    
    Attributes:
        claim: The original claim
        entities: List of extracted entities
        policy_references: List of policy references found
        key_dates: List of key dates mentioned
        context: Contextual understanding of the claim
        semantic_matches: List of semantic matches with official documents
        confidence: Overall confidence in the analysis (0.0-1.0)
    """
    claim: str
    entities: List[Entity]
    policy_references: List[str]
    key_dates: List[datetime]
    context: str
    semantic_matches: List[SemanticMatch]
    confidence: float
    
    def __post_init__(self):
        """Validate semantic analysis data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class ComparisonResult:
    """
    Result of comparing a claim against an official statement.
    
    Attributes:
        claim: The claim being compared
        official_statement: The official statement
        similarity_score: Similarity score (0.0-1.0)
        differences: List of identified differences
        matching_points: List of matching points
        analysis: Detailed analysis of the comparison
    """
    claim: str
    official_statement: str
    similarity_score: float
    differences: List[str]
    matching_points: List[str]
    analysis: str
    
    def __post_init__(self):
        """Validate comparison result data."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {self.similarity_score}")


class IntelligenceLayer:
    """
    AI-powered semantic analysis using Groq AI.
    
    Provides functionality for:
    - Semantic analysis of claims against official documents
    - Entity extraction (people, organizations, dates, policies)
    - Context-aware analysis of government terminology
    - Retry logic with exponential backoff
    - Rate limiting handling
    - Response validation
    """
    
    def __init__(
        self,
        api_config: APIConfiguration,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        timeout: int = 30
    ):
        """
        Initialize the Intelligence Layer.
        
        Args:
            api_config: APIConfiguration instance
            max_retries: Maximum number of retries (default: 3)
            initial_retry_delay: Initial retry delay in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 30)
            
        Raises:
            ConfigurationError: If API configuration is invalid
        """
        self.api_config = api_config
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.timeout = timeout
        
        # Validate configuration
        try:
            self.api_key = api_config.get_groq_api_key()
            self.api_url = api_config.get_groq_api_url()
        except ConfigurationError as e:
            logger.error(f"Failed to initialize Intelligence Layer: {e}")
            raise
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info("Intelligence Layer initialized with Groq AI")

    def _make_api_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic and exponential backoff.
        
        Args:
            endpoint: API endpoint path
            payload: Request payload
            retry_count: Current retry attempt (internal use)
            
        Returns:
            API response as dictionary
            
        Raises:
            RateLimitError: If rate limit is exceeded
            APIQuotaExceededError: If API quota is exceeded
            IntelligenceError: If request fails after retries
        """
        url = f"{self.api_url}/{endpoint}"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    delay = self.initial_retry_delay * (2 ** retry_count)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s "
                        f"(attempt {retry_count + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    return self._make_api_request(endpoint, payload, retry_count + 1)
                else:
                    raise RateLimitError(
                        "API rate limit exceeded. Please try again later."
                    )
            
            # Handle quota exceeded (403)
            if response.status_code == 403:
                error_data = response.json() if response.content else {}
                if 'quota' in str(error_data).lower():
                    raise APIQuotaExceededError(
                        "API quota exceeded. Please check your API plan."
                    )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Parse and return response
            return response.json()
            
        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                delay = self.initial_retry_delay * (2 ** retry_count)
                logger.warning(
                    f"Request timeout, retrying in {delay}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(delay)
                return self._make_api_request(endpoint, payload, retry_count + 1)
            else:
                raise IntelligenceError(
                    f"Request timeout after {self.max_retries} retries"
                )
        
        except requests.exceptions.RequestException as e:
            if retry_count < self.max_retries:
                delay = self.initial_retry_delay * (2 ** retry_count)
                logger.warning(
                    f"Request failed: {e}, retrying in {delay}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(delay)
                return self._make_api_request(endpoint, payload, retry_count + 1)
            else:
                raise IntelligenceError(
                    f"Request failed after {self.max_retries} retries: {str(e)}"
                )
        
        except (RateLimitError, APIQuotaExceededError):
            # Re-raise these specific errors
            raise
        
        except Exception as e:
            raise IntelligenceError(f"Unexpected error during API request: {str(e)}")
    
    def _validate_response(self, response: Dict[str, Any], expected_fields: List[str]) -> None:
        """
        Validate API response structure.
        
        Args:
            response: API response dictionary
            expected_fields: List of expected field names
            
        Raises:
            IntelligenceError: If response is invalid
        """
        if not isinstance(response, dict):
            raise IntelligenceError(
                f"Invalid response format: expected dict, got {type(response)}"
            )
        
        missing_fields = [field for field in expected_fields if field not in response]
        
        if missing_fields:
            raise IntelligenceError(
                f"Invalid response: missing fields {missing_fields}"
            )
    
    def _parse_entities(self, entities_data: List[Dict[str, Any]]) -> List[Entity]:
        """
        Parse entities from API response.
        
        Args:
            entities_data: List of entity dictionaries from API
            
        Returns:
            List of Entity objects
        """
        entities = []
        
        for entity_data in entities_data:
            try:
                entity = Entity(
                    text=entity_data.get('text', ''),
                    entity_type=entity_data.get('type', 'UNKNOWN'),
                    relevance_score=float(entity_data.get('relevance', 0.5))
                )
                entities.append(entity)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse entity: {e}")
                continue
        
        return entities
    
    def _parse_dates(self, dates_data: List[str]) -> List[datetime]:
        """
        Parse dates from API response.
        
        Args:
            dates_data: List of date strings from API
            
        Returns:
            List of datetime objects
        """
        dates = []
        
        for date_str in dates_data:
            try:
                # Try ISO format first
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                dates.append(date)
            except (ValueError, AttributeError):
                logger.warning(f"Failed to parse date: {date_str}")
                continue
        
        return dates
    
    def analyze_claim(
        self,
        claim: str,
        official_docs: Optional[List[Any]] = None
    ) -> SemanticAnalysis:
        """
        Analyze claim semantically against official documents.
        
        Uses Groq AI to understand context, extract entities,
        and identify relevant policy references.
        
        Args:
            claim: The claim to analyze
            official_docs: Optional list of CollectedData objects
            
        Returns:
            SemanticAnalysis object with analysis results
            
        Raises:
            IntelligenceError: If analysis fails
            RateLimitError: If rate limit is exceeded
            APIQuotaExceededError: If API quota is exceeded
        """
        logger.info(f"Analyzing claim: {claim[:100]}...")
        
        # Prepare official documents context
        docs_context = []
        if official_docs:
            for doc in official_docs[:5]:  # Limit to 5 docs to avoid token limits
                docs_context.append({
                    'content': doc.content[:1000],  # Limit content length
                    'source': doc.document_url
                })
        
        # Prepare API payload
        payload = {
            'model': 'grok-beta',
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are an expert in analyzing government policy claims. '
                        'Extract entities (people, organizations, policies, dates, locations), '
                        'identify policy references, and provide semantic matches with official documents. '
                        'Respond in JSON format with: entities (list of {text, type, relevance}), '
                        'policy_references (list of strings), key_dates (list of ISO dates), '
                        'context (string), semantic_matches (list of {official_text, source_url, '
                        'similarity_score, matching_context}), and confidence (0.0-1.0).'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Claim: {claim}\n\n'
                        f'Official Documents: {docs_context if docs_context else "None provided"}\n\n'
                        'Analyze this claim and provide structured output.'
                    )
                }
            ],
            'temperature': 0.3,  # Lower temperature for more consistent analysis
            'max_tokens': 2000
        }
        
        try:
            # Make API request
            response = self._make_api_request('chat/completions', payload)
            
            # Validate response structure
            self._validate_response(response, ['choices'])
            
            if not response['choices'] or len(response['choices']) == 0:
                raise IntelligenceError("Empty response from API")
            
            # Extract content
            content = response['choices'][0].get('message', {}).get('content', '')
            
            if not content:
                raise IntelligenceError("No content in API response")
            
            # Parse JSON response
            import json
            try:
                # Try to extract JSON from markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                analysis_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API response as JSON: {e}")
                # Fallback: create minimal analysis
                analysis_data = {
                    'entities': [],
                    'policy_references': [],
                    'key_dates': [],
                    'context': content[:500],
                    'semantic_matches': [],
                    'confidence': 0.5
                }
            
            # Parse entities
            entities = self._parse_entities(analysis_data.get('entities', []))
            
            # Parse dates
            key_dates = self._parse_dates(analysis_data.get('key_dates', []))
            
            # Parse semantic matches
            semantic_matches = []
            for match_data in analysis_data.get('semantic_matches', []):
                try:
                    match = SemanticMatch(
                        official_text=match_data.get('official_text', ''),
                        source_url=match_data.get('source_url', ''),
                        similarity_score=float(match_data.get('similarity_score', 0.5)),
                        matching_context=match_data.get('matching_context', '')
                    )
                    semantic_matches.append(match)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse semantic match: {e}")
                    continue
            
            # Create SemanticAnalysis object
            analysis = SemanticAnalysis(
                claim=claim,
                entities=entities,
                policy_references=analysis_data.get('policy_references', []),
                key_dates=key_dates,
                context=analysis_data.get('context', ''),
                semantic_matches=semantic_matches,
                confidence=float(analysis_data.get('confidence', 0.5))
            )
            
            logger.info(
                f"Analysis complete: {len(entities)} entities, "
                f"{len(semantic_matches)} matches, confidence: {analysis.confidence:.2f}"
            )
            
            return analysis
            
        except (RateLimitError, APIQuotaExceededError, IntelligenceError):
            # Re-raise known errors
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error during claim analysis: {e}")
            raise IntelligenceError(f"Failed to analyze claim: {str(e)}")
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract key entities from text.
        
        Extracts people, organizations, dates, policies, and locations.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of Entity objects
            
        Raises:
            IntelligenceError: If extraction fails
        """
        logger.info(f"Extracting entities from text ({len(text)} chars)")
        
        # Prepare API payload
        payload = {
            'model': 'grok-beta',
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are an expert in named entity recognition for government documents. '
                        'Extract entities and classify them as PERSON, ORGANIZATION, POLICY, DATE, or LOCATION. '
                        'Respond in JSON format with: entities (list of {text, type, relevance}).'
                    )
                },
                {
                    'role': 'user',
                    'content': f'Extract entities from this text:\n\n{text[:2000]}'
                }
            ],
            'temperature': 0.2,
            'max_tokens': 1000
        }
        
        try:
            # Make API request
            response = self._make_api_request('chat/completions', payload)
            
            # Validate response
            self._validate_response(response, ['choices'])
            
            content = response['choices'][0].get('message', {}).get('content', '')
            
            # Parse JSON response
            import json
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse entity extraction response")
                return []
            
            # Parse entities
            entities = self._parse_entities(data.get('entities', []))
            
            logger.info(f"Extracted {len(entities)} entities")
            
            return entities
            
        except (RateLimitError, APIQuotaExceededError, IntelligenceError):
            raise
        
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            raise IntelligenceError(f"Entity extraction failed: {str(e)}")
    
    def compare_statements(
        self,
        claim: str,
        official_statement: str
    ) -> ComparisonResult:
        """
        Compare claim against official statement semantically.
        
        Returns similarity score and identified differences.
        
        Args:
            claim: The claim to compare
            official_statement: The official statement to compare against
            
        Returns:
            ComparisonResult with comparison details
            
        Raises:
            IntelligenceError: If comparison fails
        """
        logger.info("Comparing claim against official statement")
        
        # Prepare API payload
        payload = {
            'model': 'grok-beta',
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are an expert in comparing government policy statements. '
                        'Compare the claim against the official statement and identify similarities and differences. '
                        'Respond in JSON format with: similarity_score (0.0-1.0), differences (list of strings), '
                        'matching_points (list of strings), and analysis (string).'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Claim: {claim}\n\n'
                        f'Official Statement: {official_statement}\n\n'
                        'Compare these statements.'
                    )
                }
            ],
            'temperature': 0.3,
            'max_tokens': 1500
        }
        
        try:
            # Make API request
            response = self._make_api_request('chat/completions', payload)
            
            # Validate response
            self._validate_response(response, ['choices'])
            
            content = response['choices'][0].get('message', {}).get('content', '')
            
            # Parse JSON response
            import json
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse comparison response")
                data = {
                    'similarity_score': 0.5,
                    'differences': [],
                    'matching_points': [],
                    'analysis': content[:500]
                }
            
            # Create ComparisonResult
            result = ComparisonResult(
                claim=claim,
                official_statement=official_statement,
                similarity_score=float(data.get('similarity_score', 0.5)),
                differences=data.get('differences', []),
                matching_points=data.get('matching_points', []),
                analysis=data.get('analysis', '')
            )
            
            logger.info(f"Comparison complete: similarity={result.similarity_score:.2f}")
            
            return result
            
        except (RateLimitError, APIQuotaExceededError, IntelligenceError):
            raise
        
        except Exception as e:
            logger.error(f"Failed to compare statements: {e}")
            raise IntelligenceError(f"Statement comparison failed: {str(e)}")
    
    def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        self.session.close()
        logger.info("Intelligence Layer closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
