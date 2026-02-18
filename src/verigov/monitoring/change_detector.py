"""
Change Detector Module for VeriGov AI

Monitors government sources for policy updates and changes, detects conflicts across sources,
flags outdated information, and generates real-time alerts with version history tracking.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
"""

import difflib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Iterator
from enum import Enum
import hashlib
import threading

from ..collection.source_collector import SourceCollector, CollectedData
from ..infrastructure.audit_log import AuditLog


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ChangeType(Enum):
    """Types of changes that can be detected."""
    POLICY_UPDATE = "POLICY_UPDATE"
    LAW_AMENDMENT = "LAW_AMENDMENT"
    CORRECTION = "CORRECTION"
    NEW_DOCUMENT = "NEW_DOCUMENT"


class ImpactLevel(Enum):
    """Impact level of detected changes."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResolutionStatus(Enum):
    """Status of conflict resolution."""
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"
    INVESTIGATING = "INVESTIGATING"


@dataclass
class DetectedChange:
    """
    Represents a detected change in a government source.
    
    Attributes:
        source_url: URL of the source where change was detected
        change_type: Type of change detected
        old_content: Previous content (None for new documents)
        new_content: Current content
        detected_timestamp: When the change was detected
        impact_level: Assessed impact level of the change
        summary: Human-readable summary of the change
        diff: Optional detailed diff of changes
    """
    source_url: str
    change_type: ChangeType
    old_content: Optional[str]
    new_content: str
    detected_timestamp: datetime
    impact_level: ImpactLevel
    summary: str
    diff: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['change_type'] = self.change_type.value
        data['impact_level'] = self.impact_level.value
        data['detected_timestamp'] = self.detected_timestamp.isoformat()
        return data


@dataclass
class Conflict:
    """
    Represents conflicting statements across sources.
    
    Attributes:
        topic: Topic or subject of the conflict
        conflicting_sources: List of source URLs with conflicts
        statements: List of conflicting statements
        detected_timestamp: When the conflict was detected
        resolution_status: Current status of conflict resolution
        notes: Optional notes about the conflict
    """
    topic: str
    conflicting_sources: List[str]
    statements: List[str]
    detected_timestamp: datetime
    resolution_status: ResolutionStatus
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['resolution_status'] = self.resolution_status.value
        data['detected_timestamp'] = self.detected_timestamp.isoformat()
        return data


@dataclass
class OutdatedFlag:
    """
    Represents outdated information flagged by the system.
    
    Attributes:
        content_hash: Hash of the outdated content
        source_url: URL of the source
        reason: Reason why content is outdated
        superseded_by: URL of the superseding document
        flagged_timestamp: When the content was flagged
    """
    content_hash: str
    source_url: str
    reason: str
    superseded_by: Optional[str]
    flagged_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['flagged_timestamp'] = self.flagged_timestamp.isoformat()
        return data


@dataclass
class VersionHistory:
    """
    Represents version history for a source.
    
    Attributes:
        source_url: URL of the source
        versions: List of content versions with timestamps
    """
    source_url: str
    versions: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_version(self, content_hash: str, timestamp: datetime, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a new version to history."""
        version = {
            'content_hash': content_hash,
            'timestamp': timestamp.isoformat(),
            'metadata': metadata or {}
        }
        self.versions.append(version)
    
    def get_latest_version(self) -> Optional[Dict[str, Any]]:
        """Get the most recent version."""
        return self.versions[-1] if self.versions else None
    
    def get_version_count(self) -> int:
        """Get the number of versions."""
        return len(self.versions)


class ChangeDetector:
    """
    Monitors government sources for policy updates and changes.
    
    Provides functionality for:
    - Continuous source monitoring
    - Policy modification detection with diff analysis
    - Conflict detection across sources
    - Outdated information flagging
    - Real-time alert generation
    - Version history tracking
    """
    
    def __init__(
        self,
        source_collector: SourceCollector,
        audit_log: AuditLog,
        similarity_threshold: float = 0.95
    ):
        """
        Initialize the Change Detector.
        
        Args:
            source_collector: SourceCollector instance for retrieving content
            audit_log: AuditLog instance for logging operations
            similarity_threshold: Threshold for considering content as unchanged (0-1)
        """
        self.source_collector = source_collector
        self.audit_log = audit_log
        self.similarity_threshold = similarity_threshold
        
        # Version history storage: source_url -> VersionHistory
        self._version_history: Dict[str, VersionHistory] = {}
        
        # Content cache: source_url -> CollectedData
        self._content_cache: Dict[str, CollectedData] = {}
        
        # Detected conflicts storage
        self._conflicts: List[Conflict] = []
        
        # Outdated flags storage
        self._outdated_flags: List[OutdatedFlag] = []
        
        self._lock = threading.Lock()
        
        logger.info("Change Detector initialized")
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity ratio between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity ratio between 0 and 1
        """
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _generate_diff(self, old_content: str, new_content: str) -> str:
        """
        Generate a unified diff between old and new content.
        
        Args:
            old_content: Previous content
            new_content: Current content
            
        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='old',
            tofile='new',
            lineterm=''
        )
        
        return ''.join(diff)
    
    def _classify_change_type(self, old_content: Optional[str], new_content: str, diff: str) -> ChangeType:
        """
        Classify the type of change based on content analysis.
        
        Args:
            old_content: Previous content (None for new documents)
            new_content: Current content
            diff: Diff between old and new content
            
        Returns:
            ChangeType classification
        """
        if old_content is None:
            return ChangeType.NEW_DOCUMENT
        
        # Simple heuristics for classification
        # In production, this would use more sophisticated NLP analysis
        
        diff_lower = diff.lower()
        
        # Check for amendment keywords
        amendment_keywords = ['amend', 'amendment', 'revised', 'modified', 'updated law']
        if any(keyword in diff_lower for keyword in amendment_keywords):
            return ChangeType.LAW_AMENDMENT
        
        # Check for correction keywords
        correction_keywords = ['correction', 'erratum', 'corrected', 'error']
        if any(keyword in diff_lower for keyword in correction_keywords):
            return ChangeType.CORRECTION
        
        # Default to policy update
        return ChangeType.POLICY_UPDATE
    
    def _assess_impact_level(self, change_type: ChangeType, diff: str) -> ImpactLevel:
        """
        Assess the impact level of a change.
        
        Args:
            change_type: Type of change
            diff: Diff between old and new content
            
        Returns:
            ImpactLevel assessment
        """
        # Law amendments are typically high impact
        if change_type == ChangeType.LAW_AMENDMENT:
            return ImpactLevel.HIGH
        
        # Corrections are typically low impact
        if change_type == ChangeType.CORRECTION:
            return ImpactLevel.LOW
        
        # Assess based on size of change
        diff_lines = diff.count('\n')
        
        if diff_lines > 100:
            return ImpactLevel.HIGH
        elif diff_lines > 20:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW
    
    def _generate_change_summary(self, change_type: ChangeType, diff: str) -> str:
        """
        Generate a human-readable summary of the change.
        
        Args:
            change_type: Type of change
            diff: Diff between old and new content
            
        Returns:
            Summary string
        """
        # Count additions and deletions
        additions = diff.count('\n+')
        deletions = diff.count('\n-')
        
        summary = f"{change_type.value}: "
        
        if additions > 0 and deletions > 0:
            summary += f"{additions} line(s) added, {deletions} line(s) removed"
        elif additions > 0:
            summary += f"{additions} line(s) added"
        elif deletions > 0:
            summary += f"{deletions} line(s) removed"
        else:
            summary += "Content modified"
        
        return summary
