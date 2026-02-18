"""
Unit tests for Fact Verification Engine module.

Tests claim verification, timeline validation, confidence scoring,
result categorization, and cross-verification.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.verigov.verification.fact_verification_engine import (
    FactVerificationEngine,
    VerificationStatus,
    VerificationResult,
    TimelineValidation,
    CrossVerificationResult,
    VerificationError
)
from src.verigov.verification.intelligence_layer import (
    IntelligenceLayer,
    SemanticAnalysis,
    SemanticMatch,
    Entity,
    IntelligenceError
)
from src.verigov.infrastructure.audit_log import AuditLog
from src.verigov.collection.source_collector import CollectedData


@pytest.fixture
def mock_intelligence_layer():
    """Create a mock Intelligence Layer."""
    return Mock(spec=IntelligenceLayer)


@pytest.fixture
def audit_log():
    """Create an AuditLog instance."""
    return AuditLog()


@pytest.fixture
def verification_engine(mock_intelligence_layer, audit_log):
    """Create a FactVerificationEngine instance."""
    return FactVerificationEngine(
        intelligence_layer=mock_intelligence_layer,
        audit_log=audit_log
    )


@pytest.fixture
def sample_collected_data():
    """Create sample CollectedData for testing."""
    return CollectedData(
        content="The Ministry of Health announced new policy on healthcare.",
        source_domain="health.gov.example",
        document_url="https://health.gov.example/policy",
        publication_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        collection_timestamp=datetime.now(timezone.utc),
        content_hash="abc123",
        metadata={'title': 'Healthcare Policy Update'}
    )


@pytest.fixture
def sample_semantic_analysis():
    """Create sample SemanticAnalysis for testing."""
    return SemanticAnalysis(
        claim="Ministry of Health announced new policy",
        entities=[
            Entity(text="Ministry of Health", entity_type="ORGANIZATION", relevance_score=0.9)
        ],
        policy_references=["Healthcare Policy 2024"],
        key_dates=[datetime(2024, 1, 15, tzinfo=timezone.utc)],
        context="Government healthcare policy announcement",
        semantic_matches=[
            SemanticMatch(
                official_text="Ministry of Health announced new policy",
                source_url="https://health.gov.example/policy",
                similarity_score=0.95,
                matching_context="Policy announcement"
            )
        ],
        confidence=0.9
    )


class TestFactVerificationEngineInitialization:
    """Test Fact Verification Engine initialization."""
    
    def test_initialization_success(self, mock_intelligence_layer, audit_log):
        """Test successful initialization."""
        engine = FactVerificationEngine(
            intelligence_layer=mock_intelligence_layer,
            audit_log=audit_log
        )
        assert engine.intelligence_layer == mock_intelligence_layer
        assert engine.audit_log == audit_log
        assert engine.min_confidence_verified == 80.0
        assert engine.min_confidence_partial == 50.0
    
    def test_initialization_custom_thresholds(self, mock_intelligence_layer, audit_log):
        """Test initialization with custom confidence thresholds."""
        engine = FactVerificationEngine(
            intelligence_layer=mock_intelligence_layer,
            audit_log=audit_log,
            min_confidence_verified=85.0,
            min_confidence_partial=60.0
        )
        assert engine.min_confidence_verified == 85.0
        assert engine.min_confidence_partial == 60.0


class TestVerificationStatusEnum:
    """Test VerificationStatus enum."""
    
    def test_verification_status_values(self):
        """Test all verification status values exist."""
        assert VerificationStatus.VERIFIED.value == "VERIFIED"
        assert VerificationStatus.PARTIALLY_VERIFIED.value == "PARTIALLY_VERIFIED"
        assert VerificationStatus.INCORRECT.value == "INCORRECT"
        assert VerificationStatus.UNVERIFIED.value == "UNVERIFIED"


class TestVerificationResultDataClass:
    """Test VerificationResult data class."""
    
    def test_verification_result_creation_valid(self):
        """Test creating a valid verification result."""
        result = VerificationResult(
            claim="Test claim",
            status=VerificationStatus.VERIFIED,
            confidence_score=85.0,
            supporting_sources=["https://example.gov/doc1"],
            conflicting_sources=[],
            timeline_validation=None,
            reasoning="Claim verified with high confidence",
            verification_timestamp=datetime.now(timezone.utc)
        )
        assert result.claim == "Test claim"
        assert result.status == VerificationStatus.VERIFIED
        assert result.confidence_score == 85.0
    
    def test_verification_result_invalid_confidence_high(self):
        """Test verification result fails with confidence > 100."""
        with pytest.raises(ValueError) as exc_info:
            VerificationResult(
                claim="Test",
                status=VerificationStatus.VERIFIED,
                confidence_score=150.0,
                supporting_sources=[],
                conflicting_sources=[],
                timeline_validation=None,
                reasoning="Test",
                verification_timestamp=datetime.now(timezone.utc)
            )
        assert "0 and 100" in str(exc_info.value)
    
    def test_verification_result_invalid_confidence_low(self):
        """Test verification result fails with confidence < 0."""
        with pytest.raises(ValueError) as exc_info:
            VerificationResult(
                claim="Test",
                status=VerificationStatus.VERIFIED,
                confidence_score=-10.0,
                supporting_sources=[],
                conflicting_sources=[],
                timeline_validation=None,
                reasoning="Test",
                verification_timestamp=datetime.now(timezone.utc)
            )
        assert "0 and 100" in str(exc_info.value)


class TestConfidenceScoreCalculation:
    """Test confidence score calculation."""
    
    def test_calculate_confidence_high_support(
        self,
        verification_engine,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test confidence calculation with strong supporting evidence."""
        supporting = [sample_collected_data] * 3  # 3 supporting sources
        conflicting = []
        
        confidence = verification_engine._calculate_confidence_score(
            sample_semantic_analysis,
            supporting,
            conflicting,
            timeline_valid=True
        )
        
        # Should be high confidence
        assert confidence >= 70.0
        assert confidence <= 100.0
    
    def test_calculate_confidence_with_conflicts(
        self,
        verification_engine,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test confidence calculation with conflicting sources."""
        supporting = [sample_collected_data]
        conflicting = [sample_collected_data] * 2  # 2 conflicting sources
        
        confidence = verification_engine._calculate_confidence_score(
            sample_semantic_analysis,
            supporting,
            conflicting,
            timeline_valid=True
        )
        
        # Should be lower due to conflicts
        assert confidence < 70.0
    
    def test_calculate_confidence_no_sources(
        self,
        verification_engine,
        sample_semantic_analysis
    ):
        """Test confidence calculation with no sources."""
        confidence = verification_engine._calculate_confidence_score(
            sample_semantic_analysis,
            [],
            [],
            timeline_valid=False
        )
        
        # Should be low confidence
        assert confidence < 60.0
    
    def test_calculate_confidence_bounds(
        self,
        verification_engine,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test confidence score stays within 0-100 bounds."""
        # Test with extreme values
        supporting = [sample_collected_data] * 10
        conflicting = []
        
        confidence = verification_engine._calculate_confidence_score(
            sample_semantic_analysis,
            supporting,
            conflicting,
            timeline_valid=True
        )
        
        assert 0.0 <= confidence <= 100.0


class TestResultCategorization:
    """Test result categorization logic."""
    
    def test_categorize_verified(self, verification_engine, sample_collected_data):
        """Test categorization as VERIFIED."""
        status = verification_engine._categorize_result(
            confidence_score=85.0,
            supporting_sources=[sample_collected_data],
            conflicting_sources=[]
        )
        assert status == VerificationStatus.VERIFIED
    
    def test_categorize_partially_verified(self, verification_engine, sample_collected_data):
        """Test categorization as PARTIALLY_VERIFIED."""
        status = verification_engine._categorize_result(
            confidence_score=65.0,
            supporting_sources=[sample_collected_data],
            conflicting_sources=[]
        )
        assert status == VerificationStatus.PARTIALLY_VERIFIED
    
    def test_categorize_incorrect(self, verification_engine, sample_collected_data):
        """Test categorization as INCORRECT."""
        status = verification_engine._categorize_result(
            confidence_score=30.0,
            supporting_sources=[],
            conflicting_sources=[sample_collected_data]
        )
        assert status == VerificationStatus.INCORRECT
    
    def test_categorize_unverified(self, verification_engine):
        """Test categorization as UNVERIFIED."""
        status = verification_engine._categorize_result(
            confidence_score=20.0,
            supporting_sources=[],
            conflicting_sources=[]
        )
        assert status == VerificationStatus.UNVERIFIED


class TestTimelineValidation:
    """Test timeline validation logic."""
    
    def test_validate_timeline_current(
        self,
        verification_engine,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test timeline validation for current information."""
        timeline = verification_engine._validate_timeline(
            sample_semantic_analysis,
            [sample_collected_data]
        )
        
        assert isinstance(timeline, TimelineValidation)
        assert timeline.is_current is True
        assert timeline.superseded_by is None
    
    def test_validate_timeline_outdated(
        self,
        verification_engine,
        sample_collected_data
    ):
        """Test timeline validation for outdated information."""
        # Create analysis with old date
        old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        analysis = SemanticAnalysis(
            claim="Old policy",
            entities=[],
            policy_references=[],
            key_dates=[old_date],
            context="",
            semantic_matches=[],
            confidence=0.8
        )
        
        # Create newer source
        new_source = CollectedData(
            content="Updated policy",
            source_domain="gov.example",
            document_url="https://gov.example/new",
            publication_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            collection_timestamp=datetime.now(timezone.utc),
            content_hash="xyz789",
            metadata={}
        )
        
        timeline = verification_engine._validate_timeline(analysis, [new_source])
        
        assert timeline.is_current is False
        assert timeline.superseded_by == "https://gov.example/new"


class TestClaimVerification:
    """Test claim verification functionality."""
    
    def test_verify_claim_success(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_semantic_analysis,
        sample_collected_data,
        audit_log
    ):
        """Test successful claim verification."""
        # Mock intelligence layer response
        mock_intelligence_layer.analyze_claim.return_value = sample_semantic_analysis
        
        # Verify claim
        result = verification_engine.verify_claim(
            claim="Ministry of Health announced new policy",
            context={'sources': [sample_collected_data]}
        )
        
        assert isinstance(result, VerificationResult)
        assert result.claim == "Ministry of Health announced new policy"
        assert result.status in [
            VerificationStatus.VERIFIED,
            VerificationStatus.PARTIALLY_VERIFIED,
            VerificationStatus.UNVERIFIED
        ]
        assert 0.0 <= result.confidence_score <= 100.0
        assert result.reasoning != ""
        
        # Verify audit log was called
        assert len(audit_log.get_all_entries()) > 0
    
    def test_verify_claim_no_sources(
        self,
        verification_engine,
        audit_log
    ):
        """Test claim verification with no sources."""
        result = verification_engine.verify_claim(
            claim="Test claim",
            context={'sources': []}
        )
        
        assert result.status == VerificationStatus.UNVERIFIED
        assert result.confidence_score == 0.0
        assert "No official sources" in result.reasoning
    
    def test_verify_claim_intelligence_error(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_collected_data
    ):
        """Test claim verification handles Intelligence Layer errors."""
        # Mock intelligence layer to raise error
        mock_intelligence_layer.analyze_claim.side_effect = IntelligenceError("API error")
        
        result = verification_engine.verify_claim(
            claim="Test claim",
            context={'sources': [sample_collected_data]}
        )
        
        assert result.status == VerificationStatus.UNVERIFIED
        assert result.confidence_score == 0.0
        assert "analysis error" in result.reasoning.lower()


class TestBatchVerification:
    """Test batch verification functionality."""
    
    def test_verify_batch_success(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test successful batch verification."""
        # Mock intelligence layer
        mock_intelligence_layer.analyze_claim.return_value = sample_semantic_analysis
        
        claims = [
            "Claim 1",
            "Claim 2",
            "Claim 3"
        ]
        
        results = verification_engine.verify_batch(
            claims,
            context={'sources': [sample_collected_data]}
        )
        
        assert len(results) == 3
        assert all(isinstance(r, VerificationResult) for r in results)
        assert results[0].claim == "Claim 1"
        assert results[1].claim == "Claim 2"
        assert results[2].claim == "Claim 3"
    
    def test_verify_batch_with_failures(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_collected_data
    ):
        """Test batch verification handles individual failures."""
        # Mock to fail on second claim
        mock_intelligence_layer.analyze_claim.side_effect = [
            SemanticAnalysis(
                claim="Claim 1",
                entities=[],
                policy_references=[],
                key_dates=[],
                context="",
                semantic_matches=[],
                confidence=0.8
            ),
            IntelligenceError("API error"),
            SemanticAnalysis(
                claim="Claim 3",
                entities=[],
                policy_references=[],
                key_dates=[],
                context="",
                semantic_matches=[],
                confidence=0.8
            )
        ]
        
        claims = ["Claim 1", "Claim 2", "Claim 3"]
        results = verification_engine.verify_batch(
            claims,
            context={'sources': [sample_collected_data]}
        )
        
        assert len(results) == 3
        assert results[1].status == VerificationStatus.UNVERIFIED


class TestCrossVerification:
    """Test cross-verification functionality."""
    
    def test_cross_verify_multiple_sources(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_semantic_analysis
    ):
        """Test cross-verification across multiple sources."""
        # Create sources from different domains
        source1 = CollectedData(
            content="Policy announcement",
            source_domain="health.gov.example",
            document_url="https://health.gov.example/policy",
            publication_date=datetime.now(timezone.utc),
            collection_timestamp=datetime.now(timezone.utc),
            content_hash="hash1",
            metadata={}
        )
        
        source2 = CollectedData(
            content="Policy confirmation",
            source_domain="cabinet.gov.example",
            document_url="https://cabinet.gov.example/policy",
            publication_date=datetime.now(timezone.utc),
            collection_timestamp=datetime.now(timezone.utc),
            content_hash="hash2",
            metadata={}
        )
        
        # Mock intelligence layer
        mock_intelligence_layer.analyze_claim.return_value = sample_semantic_analysis
        
        result = verification_engine.cross_verify(
            claim="Test policy claim",
            sources=[source1, source2]
        )
        
        assert isinstance(result, CrossVerificationResult)
        assert result.sources_checked == 2
        assert 0.0 <= result.aggregated_confidence <= 100.0
        assert len(result.verification_details) == 2
    
    def test_cross_verify_single_source(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_semantic_analysis,
        sample_collected_data
    ):
        """Test cross-verification with single source."""
        mock_intelligence_layer.analyze_claim.return_value = sample_semantic_analysis
        
        result = verification_engine.cross_verify(
            claim="Test claim",
            sources=[sample_collected_data]
        )
        
        assert result.sources_checked == 1
        assert len(result.verification_details) == 1


class TestAuditLogging:
    """Test audit logging integration."""
    
    def test_verification_logged(
        self,
        verification_engine,
        mock_intelligence_layer,
        sample_semantic_analysis,
        sample_collected_data,
        audit_log
    ):
        """Test that verification results are logged."""
        mock_intelligence_layer.analyze_claim.return_value = sample_semantic_analysis
        
        verification_engine.verify_claim(
            claim="Test claim",
            context={'sources': [sample_collected_data]}
        )
        
        # Check audit log
        entries = audit_log.get_all_entries()
        assert len(entries) > 0
        
        # Find verification entry
        verification_entries = [
            e for e in entries
            if e.event_type == "VERIFICATION"
        ]
        assert len(verification_entries) > 0
        
        entry = verification_entries[0]
        assert 'result' in entry.details
        result_data = entry.details['result']
        assert result_data['status'] in [
            "VERIFIED", "PARTIALLY_VERIFIED", "INCORRECT", "UNVERIFIED"
        ]
        assert 'confidence_score' in result_data
