"""
Fact Verification Engine Module for VeriGov AI

Core verification component that validates claims against official documents.
Implements claim matching, timeline validation, multi-authority cross-verification,
confidence scoring, and result categorization.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from .intelligence_layer import IntelligenceLayer, IntelligenceError, SemanticAnalysis
from ..infrastructure.audit_log import AuditLog
from ..collection.source_collector import CollectedData


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class VerificationStatus(Enum):
    """Status of claim verification."""
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    INCORRECT = "INCORRECT"
    UNVERIFIED = "UNVERIFIED"


class VerificationError(Exception):
    """Raised when verification operations fail."""
    pass


@dataclass
class TimelineValidation:
    """
    Timeline-based validation result.
    
    Attributes:
        claim_date: Date mentioned in the claim (if any)
        source_dates: Dates from supporting sources
        is_current: Whether the information is current
        superseded_by: URL of superseding document (if any)
    """
    claim_date: Optional[datetime]
    source_dates: List[datetime]
    is_current: bool
    superseded_by: Optional[str] = None


@dataclass
class VerificationResult:
    """
    Result of claim verification.
    
    Attributes:
        claim: The original claim
        status: Verification status (VERIFIED, PARTIALLY_VERIFIED, INCORRECT, UNVERIFIED)
        confidence_score: Confidence score (0-100)
        supporting_sources: List of source URLs that support the claim
        conflicting_sources: List of source URLs that conflict with the claim
        timeline_validation: Timeline validation result (if applicable)
        reasoning: Human-readable explanation of the verification
        verification_timestamp: When verification was performed
    """
    claim: str
    status: VerificationStatus
    confidence_score: float
    supporting_sources: List[str]
    conflicting_sources: List[str]
    timeline_validation: Optional[TimelineValidation]
    reasoning: str
    verification_timestamp: datetime
    
    def __post_init__(self):
        """Validate verification result data."""
        if not 0.0 <= self.confidence_score <= 100.0:
            raise ValueError(
                f"Confidence score must be between 0 and 100, got {self.confidence_score}"
            )


@dataclass
class CrossVerificationResult:
    """
    Result of cross-verification across multiple sources.
    
    Attributes:
        claim: The original claim
        sources_checked: Number of sources checked
        sources_supporting: Number of sources supporting the claim
        sources_conflicting: Number of sources conflicting with the claim
        aggregated_confidence: Aggregated confidence score (0-100)
        verification_details: List of individual verification results
    """
    claim: str
    sources_checked: int
    sources_supporting: int
    sources_conflicting: int
    aggregated_confidence: float
    verification_details: List[Dict[str, Any]]


class FactVerificationEngine:
    """
    Core verification component for validating claims against official documents.
    
    Provides functionality for:
    - Claim matching against official documents
    - Timeline-based validation
    - Multi-authority cross-verification
    - Confidence score calculation (0-100)
    - Result categorization (Verified, Partially Verified, Incorrect, Unverified)
    - Instant flagging for unverified claims
    """
    
    def __init__(
        self,
        intelligence_layer: IntelligenceLayer,
        audit_log: AuditLog,
        min_confidence_verified: float = 80.0,
        min_confidence_partial: float = 50.0
    ):
        """
        Initialize the Fact Verification Engine.
        
        Args:
            intelligence_layer: IntelligenceLayer instance for semantic analysis
            audit_log: AuditLog instance for logging verification activities
            min_confidence_verified: Minimum confidence for VERIFIED status (default: 80.0)
            min_confidence_partial: Minimum confidence for PARTIALLY_VERIFIED status (default: 50.0)
        """
        self.intelligence_layer = intelligence_layer
        self.audit_log = audit_log
        self.min_confidence_verified = min_confidence_verified
        self.min_confidence_partial = min_confidence_partial
        
        logger.info("Fact Verification Engine initialized")

    def _calculate_confidence_score(
        self,
        semantic_analysis: SemanticAnalysis,
        supporting_sources: List[CollectedData],
        conflicting_sources: List[CollectedData],
        timeline_valid: bool
    ) -> float:
        """
        Calculate confidence score based on multiple factors.
        
        Factors considered:
        - Semantic analysis confidence
        - Number of supporting sources
        - Number of conflicting sources
        - Timeline validity
        - Source quality (publication dates, metadata)
        
        Args:
            semantic_analysis: Semantic analysis result
            supporting_sources: List of supporting sources
            conflicting_sources: List of conflicting sources
            timeline_valid: Whether timeline validation passed
            
        Returns:
            Confidence score (0-100)
        """
        # Start with semantic analysis confidence (0-1 scale)
        base_confidence = semantic_analysis.confidence
        
        # Factor 1: Number of supporting sources (up to +30 points)
        support_factor = min(len(supporting_sources) * 10, 30)
        
        # Factor 2: Conflicting sources penalty (up to -40 points)
        conflict_penalty = min(len(conflicting_sources) * 15, 40)
        
        # Factor 3: Timeline validity bonus (+10 points if valid)
        timeline_bonus = 10 if timeline_valid else 0
        
        # Factor 4: Source quality bonus (up to +10 points)
        quality_bonus = 0
        for source in supporting_sources:
            if source.publication_date:
                quality_bonus += 2
            if source.metadata.get('title'):
                quality_bonus += 1
        quality_bonus = min(quality_bonus, 10)
        
        # Calculate final confidence (0-100 scale)
        confidence = (base_confidence * 50) + support_factor - conflict_penalty + timeline_bonus + quality_bonus
        
        # Ensure within bounds
        confidence = max(0.0, min(100.0, confidence))
        
        logger.debug(
            f"Confidence calculation: base={base_confidence:.2f}, "
            f"support={support_factor}, conflict_penalty={conflict_penalty}, "
            f"timeline={timeline_bonus}, quality={quality_bonus}, "
            f"final={confidence:.2f}"
        )
        
        return confidence
    
    def _categorize_result(
        self,
        confidence_score: float,
        supporting_sources: List[CollectedData],
        conflicting_sources: List[CollectedData]
    ) -> VerificationStatus:
        """
        Categorize verification result based on confidence and sources.
        
        Rules:
        - VERIFIED: High confidence (>= min_confidence_verified) and supporting sources
        - PARTIALLY_VERIFIED: Medium confidence (>= min_confidence_partial) or mixed sources
        - INCORRECT: Conflicting sources with no support
        - UNVERIFIED: Low confidence or no sources
        
        Args:
            confidence_score: Calculated confidence score (0-100)
            supporting_sources: List of supporting sources
            conflicting_sources: List of conflicting sources
            
        Returns:
            VerificationStatus
        """
        # INCORRECT: Strong evidence against the claim
        if conflicting_sources and not supporting_sources:
            return VerificationStatus.INCORRECT
        
        # VERIFIED: High confidence with supporting sources
        if confidence_score >= self.min_confidence_verified and supporting_sources:
            return VerificationStatus.VERIFIED
        
        # PARTIALLY_VERIFIED: Medium confidence or mixed evidence
        if confidence_score >= self.min_confidence_partial:
            if supporting_sources:
                return VerificationStatus.PARTIALLY_VERIFIED
        
        # UNVERIFIED: Low confidence or insufficient evidence
        return VerificationStatus.UNVERIFIED
    
    def _validate_timeline(
        self,
        semantic_analysis: SemanticAnalysis,
        sources: List[CollectedData]
    ) -> TimelineValidation:
        """
        Perform timeline-based validation.
        
        Checks if dates mentioned in the claim align with source dates
        and whether information is current or superseded.
        
        Args:
            semantic_analysis: Semantic analysis with extracted dates
            sources: List of source documents
            
        Returns:
            TimelineValidation result
        """
        # Extract claim date (use first key date if available)
        claim_date = semantic_analysis.key_dates[0] if semantic_analysis.key_dates else None
        
        # Extract source dates
        source_dates = [
            source.publication_date
            for source in sources
            if source.publication_date
        ]
        
        # Check if information is current
        is_current = True
        superseded_by = None
        
        if claim_date and source_dates:
            # Check if any source is significantly newer than the claim date
            newest_source = max(source_dates)
            if (newest_source - claim_date).days > 365:  # More than 1 year difference
                is_current = False
                # Find the superseding document
                for source in sources:
                    if source.publication_date == newest_source:
                        superseded_by = source.document_url
                        break
        
        return TimelineValidation(
            claim_date=claim_date,
            source_dates=source_dates,
            is_current=is_current,
            superseded_by=superseded_by
        )
    
    def _match_claim_to_sources(
        self,
        semantic_analysis: SemanticAnalysis,
        sources: List[CollectedData]
    ) -> tuple[List[CollectedData], List[CollectedData]]:
        """
        Match claim against sources to identify supporting and conflicting sources.
        
        Uses semantic matches from the analysis to categorize sources.
        
        Args:
            semantic_analysis: Semantic analysis result
            sources: List of source documents
            
        Returns:
            Tuple of (supporting_sources, conflicting_sources)
        """
        supporting_sources = []
        conflicting_sources = []
        
        # Create a mapping of source URLs to CollectedData
        source_map = {source.document_url: source for source in sources}
        
        # Categorize based on semantic matches
        for match in semantic_analysis.semantic_matches:
            source = source_map.get(match.source_url)
            if not source:
                continue
            
            # High similarity = supporting
            if match.similarity_score >= 0.7:
                if source not in supporting_sources:
                    supporting_sources.append(source)
            # Low similarity = potentially conflicting
            elif match.similarity_score < 0.3:
                if source not in conflicting_sources:
                    conflicting_sources.append(source)
        
        return supporting_sources, conflicting_sources
    
    def _generate_reasoning(
        self,
        status: VerificationStatus,
        confidence_score: float,
        supporting_sources: List[CollectedData],
        conflicting_sources: List[CollectedData],
        timeline_validation: TimelineValidation
    ) -> str:
        """
        Generate human-readable reasoning for the verification result.
        
        Args:
            status: Verification status
            confidence_score: Confidence score
            supporting_sources: Supporting sources
            conflicting_sources: Conflicting sources
            timeline_validation: Timeline validation result
            
        Returns:
            Reasoning string
        """
        reasoning_parts = []
        
        # Status explanation
        if status == VerificationStatus.VERIFIED:
            reasoning_parts.append(
                f"Claim is VERIFIED with {confidence_score:.1f}% confidence."
            )
        elif status == VerificationStatus.PARTIALLY_VERIFIED:
            reasoning_parts.append(
                f"Claim is PARTIALLY VERIFIED with {confidence_score:.1f}% confidence."
            )
        elif status == VerificationStatus.INCORRECT:
            reasoning_parts.append(
                f"Claim appears INCORRECT based on available evidence."
            )
        else:
            reasoning_parts.append(
                f"Claim is UNVERIFIED - insufficient evidence to confirm or deny."
            )
        
        # Source information
        if supporting_sources:
            reasoning_parts.append(
                f"Found {len(supporting_sources)} supporting source(s)."
            )
        
        if conflicting_sources:
            reasoning_parts.append(
                f"Found {len(conflicting_sources)} conflicting source(s)."
            )
        
        if not supporting_sources and not conflicting_sources:
            reasoning_parts.append(
                "No matching sources found in official documents."
            )
        
        # Timeline information
        if not timeline_validation.is_current and timeline_validation.superseded_by:
            reasoning_parts.append(
                f"Information may be outdated. See: {timeline_validation.superseded_by}"
            )
        
        return " ".join(reasoning_parts)
    
    def verify_claim(
        self,
        claim: str,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Verify a single claim against official sources.
        
        Performs semantic matching, timeline validation, and
        multi-authority cross-verification.
        
        Args:
            claim: The claim to verify
            context: Optional context with 'sources' (List[CollectedData])
            
        Returns:
            VerificationResult with verification details
            
        Raises:
            VerificationError: If verification fails
        """
        logger.info(f"Verifying claim: {claim[:100]}...")
        
        verification_time = datetime.now(timezone.utc)
        
        try:
            # Extract sources from context
            sources = context.get('sources', []) if context else []
            
            if not sources:
                logger.warning("No sources provided for verification")
                # Return unverified result
                result = VerificationResult(
                    claim=claim,
                    status=VerificationStatus.UNVERIFIED,
                    confidence_score=0.0,
                    supporting_sources=[],
                    conflicting_sources=[],
                    timeline_validation=None,
                    reasoning="No official sources available for verification.",
                    verification_timestamp=verification_time
                )
                
                # Log verification
                self._log_verification(result)
                
                return result
            
            # Step 1: Semantic analysis using Intelligence Layer
            logger.debug("Performing semantic analysis...")
            semantic_analysis = self.intelligence_layer.analyze_claim(claim, sources)
            
            # Step 2: Match claim to sources
            logger.debug("Matching claim to sources...")
            supporting_sources, conflicting_sources = self._match_claim_to_sources(
                semantic_analysis, sources
            )
            
            # Step 3: Timeline validation
            logger.debug("Performing timeline validation...")
            timeline_validation = self._validate_timeline(semantic_analysis, sources)
            
            # Step 4: Calculate confidence score
            logger.debug("Calculating confidence score...")
            confidence_score = self._calculate_confidence_score(
                semantic_analysis,
                supporting_sources,
                conflicting_sources,
                timeline_validation.is_current
            )
            
            # Step 5: Categorize result
            status = self._categorize_result(
                confidence_score,
                supporting_sources,
                conflicting_sources
            )
            
            # Step 6: Generate reasoning
            reasoning = self._generate_reasoning(
                status,
                confidence_score,
                supporting_sources,
                conflicting_sources,
                timeline_validation
            )
            
            # Create verification result
            result = VerificationResult(
                claim=claim,
                status=status,
                confidence_score=confidence_score,
                supporting_sources=[s.document_url for s in supporting_sources],
                conflicting_sources=[s.document_url for s in conflicting_sources],
                timeline_validation=timeline_validation,
                reasoning=reasoning,
                verification_timestamp=verification_time
            )
            
            # Log verification
            self._log_verification(result)
            
            logger.info(
                f"Verification complete: {status.value}, "
                f"confidence={confidence_score:.1f}%"
            )
            
            return result
            
        except IntelligenceError as e:
            logger.error(f"Intelligence Layer error during verification: {e}")
            # Return unverified result on Intelligence Layer failure
            result = VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIED,
                confidence_score=0.0,
                supporting_sources=[],
                conflicting_sources=[],
                timeline_validation=None,
                reasoning=f"Verification failed due to analysis error: {str(e)}",
                verification_timestamp=verification_time
            )
            
            # Log verification failure
            self._log_verification(result)
            
            return result
        
        except Exception as e:
            logger.error(f"Unexpected error during verification: {e}")
            raise VerificationError(f"Failed to verify claim: {str(e)}") from e

    def verify_batch(self, claims: List[str], context: Optional[Dict[str, Any]] = None) -> List[VerificationResult]:
        """
        Verify multiple claims efficiently.
        
        Processes claims sequentially, reusing sources from context.
        
        Args:
            claims: List of claims to verify
            context: Optional context with 'sources' (List[CollectedData])
            
        Returns:
            List of VerificationResult objects
        """
        logger.info(f"Starting batch verification of {len(claims)} claim(s)")
        
        results = []
        
        for i, claim in enumerate(claims, 1):
            logger.debug(f"Verifying claim {i}/{len(claims)}")
            
            try:
                result = self.verify_claim(claim, context)
                results.append(result)
            except VerificationError as e:
                logger.error(f"Failed to verify claim {i}: {e}")
                # Create unverified result for failed claim
                result = VerificationResult(
                    claim=claim,
                    status=VerificationStatus.UNVERIFIED,
                    confidence_score=0.0,
                    supporting_sources=[],
                    conflicting_sources=[],
                    timeline_validation=None,
                    reasoning=f"Verification failed: {str(e)}",
                    verification_timestamp=datetime.now(timezone.utc)
                )
                results.append(result)
        
        logger.info(
            f"Batch verification complete: {len(results)} result(s), "
            f"{sum(1 for r in results if r.status == VerificationStatus.VERIFIED)} verified"
        )
        
        return results
    
    def cross_verify(
        self,
        claim: str,
        sources: List[CollectedData]
    ) -> CrossVerificationResult:
        """
        Verify claim across multiple government sources.
        
        Returns aggregated verification with confidence score.
        
        Args:
            claim: The claim to verify
            sources: List of CollectedData from different government sources
            
        Returns:
            CrossVerificationResult with aggregated verification details
        """
        logger.info(f"Starting cross-verification across {len(sources)} source(s)")
        
        verification_details = []
        supporting_count = 0
        conflicting_count = 0
        total_confidence = 0.0
        
        # Group sources by domain for multi-authority verification
        sources_by_domain: Dict[str, List[CollectedData]] = {}
        for source in sources:
            domain = source.source_domain
            if domain not in sources_by_domain:
                sources_by_domain[domain] = []
            sources_by_domain[domain].append(source)
        
        logger.debug(f"Cross-verifying across {len(sources_by_domain)} domain(s)")
        
        # Verify against each authority
        for domain, domain_sources in sources_by_domain.items():
            try:
                # Verify claim against this authority's sources
                context = {'sources': domain_sources}
                result = self.verify_claim(claim, context)
                
                # Track results
                if result.supporting_sources:
                    supporting_count += 1
                if result.conflicting_sources:
                    conflicting_count += 1
                
                total_confidence += result.confidence_score
                
                verification_details.append({
                    'authority': domain,
                    'status': result.status.value,
                    'confidence': result.confidence_score,
                    'supporting_sources': result.supporting_sources,
                    'conflicting_sources': result.conflicting_sources
                })
                
            except VerificationError as e:
                logger.warning(f"Failed to verify against {domain}: {e}")
                verification_details.append({
                    'authority': domain,
                    'status': 'ERROR',
                    'confidence': 0.0,
                    'error': str(e)
                })
        
        # Calculate aggregated confidence
        if verification_details:
            aggregated_confidence = total_confidence / len(verification_details)
        else:
            aggregated_confidence = 0.0
        
        # Create cross-verification result
        cross_result = CrossVerificationResult(
            claim=claim,
            sources_checked=len(sources_by_domain),
            sources_supporting=supporting_count,
            sources_conflicting=conflicting_count,
            aggregated_confidence=aggregated_confidence,
            verification_details=verification_details
        )
        
        logger.info(
            f"Cross-verification complete: {supporting_count} supporting, "
            f"{conflicting_count} conflicting, "
            f"aggregated confidence={aggregated_confidence:.1f}%"
        )
        
        return cross_result
    
    def _log_verification(self, result: VerificationResult) -> None:
        """
        Log verification result to audit log.
        
        Args:
            result: VerificationResult to log
        """
        result_dict = {
            'status': result.status.value,
            'confidence_score': result.confidence_score,
            'supporting_sources': result.supporting_sources,
            'conflicting_sources': result.conflicting_sources,
            'reasoning': result.reasoning,
            'has_timeline_validation': result.timeline_validation is not None
        }
        
        if result.timeline_validation:
            result_dict['timeline_validation'] = {
                'is_current': result.timeline_validation.is_current,
                'superseded_by': result.timeline_validation.superseded_by
            }
        
        self.audit_log.log_verification(
            claim=result.claim,
            result=result_dict,
            timestamp=result.verification_timestamp
        )
