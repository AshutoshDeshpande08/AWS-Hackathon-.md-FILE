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

    
    def detect_changes(self, source_url: str) -> List[DetectedChange]:
        """
        Detect changes in a specific source by comparing with historical versions.
        
        Compares current content with the most recent cached version and
        identifies modifications.
        
        Args:
            source_url: URL of the source to check
            
        Returns:
            List of DetectedChange objects (empty if no changes)
        """
        logger.info(f"Detecting changes for {source_url}")
        
        try:
            # Collect current content
            current_data = self.source_collector.collect_from_source(source_url)
            
            with self._lock:
                # Get cached content
                cached_data = self._content_cache.get(source_url)
                
                # Initialize version history if needed
                if source_url not in self._version_history:
                    self._version_history[source_url] = VersionHistory(source_url=source_url)
                
                version_history = self._version_history[source_url]
                
                # If no cached content, this is the first collection
                if cached_data is None:
                    logger.info(f"First collection for {source_url}, no changes to detect")
                    
                    # Add to version history
                    version_history.add_version(
                        content_hash=current_data.content_hash,
                        timestamp=current_data.collection_timestamp,
                        metadata={'publication_date': current_data.publication_date}
                    )
                    
                    # Update cache
                    self._content_cache[source_url] = current_data
                    
                    # Create NEW_DOCUMENT change
                    change = DetectedChange(
                        source_url=source_url,
                        change_type=ChangeType.NEW_DOCUMENT,
                        old_content=None,
                        new_content=current_data.content,
                        detected_timestamp=current_data.collection_timestamp,
                        impact_level=ImpactLevel.MEDIUM,
                        summary="New document added to monitoring",
                        diff=None
                    )
                    
                    return [change]
                
                # Check if content has changed
                if current_data.content_hash == cached_data.content_hash:
                    logger.debug(f"No changes detected for {source_url}")
                    return []
                
                # Content has changed - perform diff analysis
                similarity = self._compute_similarity(cached_data.content, current_data.content)
                
                # If similarity is above threshold, consider it unchanged
                if similarity >= self.similarity_threshold:
                    logger.debug(f"Content similarity {similarity:.2f} above threshold, no significant change")
                    return []
                
                # Generate diff
                diff = self._generate_diff(cached_data.content, current_data.content)
                
                # Classify change type
                change_type = self._classify_change_type(cached_data.content, current_data.content, diff)
                
                # Assess impact level
                impact_level = self._assess_impact_level(change_type, diff)
                
                # Generate summary
                summary = self._generate_change_summary(change_type, diff)
                
                # Create change object
                change = DetectedChange(
                    source_url=source_url,
                    change_type=change_type,
                    old_content=cached_data.content,
                    new_content=current_data.content,
                    detected_timestamp=current_data.collection_timestamp,
                    impact_level=impact_level,
                    summary=summary,
                    diff=diff
                )
                
                # Update version history
                version_history.add_version(
                    content_hash=current_data.content_hash,
                    timestamp=current_data.collection_timestamp,
                    metadata={
                        'publication_date': current_data.publication_date,
                        'change_type': change_type.value,
                        'impact_level': impact_level.value
                    }
                )
                
                # Update cache
                self._content_cache[source_url] = current_data
                
                # Log the change
                self.audit_log.log_event(
                    event_type="change_detected",
                    details={
                        'source_url': source_url,
                        'change_type': change_type.value,
                        'impact_level': impact_level.value,
                        'summary': summary
                    }
                )
                
                logger.info(f"Change detected: {summary}")
                
                return [change]
                
        except Exception as e:
            logger.error(f"Error detecting changes for {source_url}: {e}")
            self.audit_log.log_event(
                event_type="change_detection_error",
                details={
                    'source_url': source_url,
                    'error': str(e)
                }
            )
            return []
    
    def monitor_all_sources(self) -> Iterator[DetectedChange]:
        """
        Continuously monitor all sources for changes.
        
        Yields changes as they are detected.
        
        Yields:
            DetectedChange objects as changes are found
        """
        logger.info("Starting continuous monitoring of all sources")
        
        # Get all sources from the source collector's whitelist
        whitelisted_sources = self.source_collector.whitelist.get_all_sources()
        
        for source_url in whitelisted_sources:
            try:
                changes = self.detect_changes(source_url)
                for change in changes:
                    yield change
            except Exception as e:
                logger.error(f"Error monitoring {source_url}: {e}")
                continue
    
    def detect_conflicts(self, topic: str) -> List[Conflict]:
        """
        Detect conflicting statements across sources on a topic.
        
        Analyzes cached content from multiple sources to identify
        contradictory information about the same topic.
        
        Args:
            topic: Topic to check for conflicts
            
        Returns:
            List of Conflict objects
        """
        logger.info(f"Detecting conflicts for topic: {topic}")
        
        conflicts = []
        
        with self._lock:
            # Get all cached content
            sources_with_topic = []
            
            for source_url, data in self._content_cache.items():
                # Simple keyword matching - in production would use NLP
                if topic.lower() in data.content.lower():
                    sources_with_topic.append((source_url, data))
            
            if len(sources_with_topic) < 2:
                logger.debug(f"Not enough sources found for topic '{topic}' to detect conflicts")
                return []
            
            # Compare statements across sources
            # This is a simplified implementation - production would use semantic analysis
            statements = {}
            for source_url, data in sources_with_topic:
                # Extract sentences containing the topic
                sentences = [s.strip() for s in data.content.split('.') if topic.lower() in s.lower()]
                if sentences:
                    statements[source_url] = sentences
            
            # Check for conflicts (simplified - just checks if statements differ significantly)
            if len(statements) >= 2:
                source_urls = list(statements.keys())
                all_statements = []
                
                for url in source_urls:
                    all_statements.extend(statements[url])
                
                # If we have different statements, flag as potential conflict
                # In production, this would use semantic similarity analysis
                if len(set(all_statements)) > 1:
                    conflict = Conflict(
                        topic=topic,
                        conflicting_sources=source_urls,
                        statements=all_statements,
                        detected_timestamp=datetime.now(timezone.utc),
                        resolution_status=ResolutionStatus.UNRESOLVED,
                        notes=f"Potential conflict detected across {len(source_urls)} sources"
                    )
                    
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)
                    
                    # Log the conflict
                    self.audit_log.log_event(
                        event_type="conflict_detected",
                        details={
                            'topic': topic,
                            'sources': source_urls,
                            'statement_count': len(all_statements)
                        }
                    )
                    
                    logger.warning(f"Conflict detected for topic '{topic}' across {len(source_urls)} sources")
        
        return conflicts
    
    def flag_outdated(self, content: CollectedData) -> Optional[OutdatedFlag]:
        """
        Check if content is outdated based on superseding documents.
        
        Analyzes content metadata and version history to determine
        if the information has been superseded by newer documents.
        
        Args:
            content: CollectedData to check
            
        Returns:
            OutdatedFlag if content is outdated, None otherwise
        """
        logger.debug(f"Checking if content from {content.document_url} is outdated")
        
        with self._lock:
            # Get version history for this source
            version_history = self._version_history.get(content.document_url)
            
            if not version_history:
                logger.debug("No version history available, cannot determine if outdated")
                return None
            
            # Check if there's a newer version
            latest_version = version_history.get_latest_version()
            
            if not latest_version:
                return None
            
            # If the content hash doesn't match the latest version, it's outdated
            if content.content_hash != latest_version['content_hash']:
                flag = OutdatedFlag(
                    content_hash=content.content_hash,
                    source_url=content.document_url,
                    reason="Superseded by newer version",
                    superseded_by=content.document_url,  # Same URL, newer version
                    flagged_timestamp=datetime.now(timezone.utc)
                )
                
                self._outdated_flags.append(flag)
                
                # Log the flag
                self.audit_log.log_event(
                    event_type="outdated_content_flagged",
                    details={
                        'source_url': content.document_url,
                        'content_hash': content.content_hash,
                        'reason': flag.reason
                    }
                )
                
                logger.info(f"Content from {content.document_url} flagged as outdated")
                
                return flag
        
        return None
    
    def get_version_history(self, source_url: str) -> Optional[VersionHistory]:
        """
        Get version history for a source.
        
        Args:
            source_url: URL of the source
            
        Returns:
            VersionHistory object or None if not found
        """
        with self._lock:
            return self._version_history.get(source_url)
    
    def get_all_conflicts(self) -> List[Conflict]:
        """
        Get all detected conflicts.
        
        Returns:
            List of all Conflict objects
        """
        with self._lock:
            return self._conflicts.copy()
    
    def get_all_outdated_flags(self) -> List[OutdatedFlag]:
        """
        Get all outdated flags.
        
        Returns:
            List of all OutdatedFlag objects
        """
        with self._lock:
            return self._outdated_flags.copy()
    
    def resolve_conflict(self, conflict: Conflict, resolution_status: ResolutionStatus, notes: Optional[str] = None) -> None:
        """
        Update the resolution status of a conflict.
        
        Args:
            conflict: Conflict to resolve
            resolution_status: New resolution status
            notes: Optional notes about the resolution
        """
        with self._lock:
            conflict.resolution_status = resolution_status
            if notes:
                conflict.notes = notes
            
            self.audit_log.log_event(
                event_type="conflict_resolved",
                details={
                    'topic': conflict.topic,
                    'resolution_status': resolution_status.value,
                    'notes': notes
                }
            )
            
            logger.info(f"Conflict for topic '{conflict.topic}' updated to {resolution_status.value}")

    def detect_changes(self, source_url: str) -> List[DetectedChange]:
        """
        Detect changes in a specific source by comparing with historical versions.
        
        Compares current content with the most recent cached version and
        identifies modifications.
        
        Args:
            source_url: URL of the source to check
            
        Returns:
            List of DetectedChange objects (empty if no changes)
        """
        logger.info(f"Detecting changes for {source_url}")
        
        try:
            # Collect current content
            current_data = self.source_collector.collect_from_source(source_url)
            
            with self._lock:
                # Get cached content
                cached_data = self._content_cache.get(source_url)
                
                # Initialize version history if needed
                if source_url not in self._version_history:
                    self._version_history[source_url] = VersionHistory(source_url=source_url)
                
                version_history = self._version_history[source_url]
                
                # If no cached content, this is the first collection
                if cached_data is None:
                    logger.info(f"First collection for {source_url}, no changes to detect")
                    
                    # Add to version history
                    version_history.add_version(
                        content_hash=current_data.content_hash,
                        timestamp=current_data.collection_timestamp,
                        metadata={'publication_date': current_data.publication_date}
                    )
                    
                    # Update cache
                    self._content_cache[source_url] = current_data
                    
                    # Create NEW_DOCUMENT change
                    change = DetectedChange(
                        source_url=source_url,
                        change_type=ChangeType.NEW_DOCUMENT,
                        old_content=None,
                        new_content=current_data.content,
                        detected_timestamp=current_data.collection_timestamp,
                        impact_level=ImpactLevel.MEDIUM,
                        summary="New document added to monitoring",
                        diff=None
                    )
                    
                    return [change]
                
                # Check if content has changed
                if current_data.content_hash == cached_data.content_hash:
                    logger.debug(f"No changes detected for {source_url}")
                    return []
                
                # Content has changed - perform diff analysis
                similarity = self._compute_similarity(cached_data.content, current_data.content)
                
                # If similarity is above threshold, consider it unchanged
                if similarity >= self.similarity_threshold:
                    logger.debug(f"Content similarity {similarity:.2f} above threshold, no significant change")
                    return []
                
                # Generate diff
                diff = self._generate_diff(cached_data.content, current_data.content)
                
                # Classify change type
                change_type = self._classify_change_type(cached_data.content, current_data.content, diff)
                
                # Assess impact level
                impact_level = self._assess_impact_level(change_type, diff)
                
                # Generate summary
                summary = self._generate_change_summary(change_type, diff)
                
                # Create change object
                change = DetectedChange(
                    source_url=source_url,
                    change_type=change_type,
                    old_content=cached_data.content,
                    new_content=current_data.content,
                    detected_timestamp=current_data.collection_timestamp,
                    impact_level=impact_level,
                    summary=summary,
                    diff=diff
                )
                
                # Update version history
                version_history.add_version(
                    content_hash=current_data.content_hash,
                    timestamp=current_data.collection_timestamp,
                    metadata={
                        'publication_date': current_data.publication_date,
                        'change_type': change_type.value,
                        'impact_level': impact_level.value
                    }
                )
                
                # Update cache
                self._content_cache[source_url] = current_data
                
                # Log the change
                self.audit_log.log_event(
                    event_type="change_detected",
                    details={
                        'source_url': source_url,
                        'change_type': change_type.value,
                        'impact_level': impact_level.value,
                        'summary': summary
                    }
                )
                
                logger.info(f"Change detected: {summary}")
                
                return [change]
                
        except Exception as e:
            logger.error(f"Error detecting changes for {source_url}: {e}")
            self.audit_log.log_event(
                event_type="change_detection_error",
                details={
                    'source_url': source_url,
                    'error': str(e)
                }
            )
            return []
    
    def monitor_all_sources(self) -> Iterator[DetectedChange]:
        """
        Continuously monitor all sources for changes.
        
        Yields changes as they are detected.
        
        Yields:
            DetectedChange objects as changes are found
        """
        logger.info("Starting continuous monitoring of all sources")
        
        # Get all sources from the source collector's whitelist
        whitelisted_sources = self.source_collector.whitelist.get_all_sources()
        
        for source_url in whitelisted_sources:
            try:
                changes = self.detect_changes(source_url)
                for change in changes:
                    yield change
            except Exception as e:
                logger.error(f"Error monitoring {source_url}: {e}")
                continue
    
    def detect_conflicts(self, topic: str) -> List[Conflict]:
        """
        Detect conflicting statements across sources on a topic.
        
        Analyzes cached content from multiple sources to identify
        contradictory information about the same topic.
        
        Args:
            topic: Topic to check for conflicts
            
        Returns:
            List of Conflict objects
        """
        logger.info(f"Detecting conflicts for topic: {topic}")
        
        conflicts = []
        
        with self._lock:
            # Get all cached content
            sources_with_topic = []
            
            for source_url, data in self._content_cache.items():
                # Simple keyword matching - in production would use NLP
                if topic.lower() in data.content.lower():
                    sources_with_topic.append((source_url, data))
            
            if len(sources_with_topic) < 2:
                logger.debug(f"Not enough sources found for topic '{topic}' to detect conflicts")
                return []
            
            # Compare statements across sources
            # This is a simplified implementation - production would use semantic analysis
            statements = {}
            for source_url, data in sources_with_topic:
                # Extract sentences containing the topic
                sentences = [s.strip() for s in data.content.split('.') if topic.lower() in s.lower()]
                if sentences:
                    statements[source_url] = sentences
            
            # Check for conflicts (simplified - just checks if statements differ significantly)
            if len(statements) >= 2:
                source_urls = list(statements.keys())
                all_statements = []
                
                for url in source_urls:
                    all_statements.extend(statements[url])
                
                # If we have different statements, flag as potential conflict
                # In production, this would use semantic similarity analysis
                if len(set(all_statements)) > 1:
                    conflict = Conflict(
                        topic=topic,
                        conflicting_sources=source_urls,
                        statements=all_statements,
                        detected_timestamp=datetime.now(timezone.utc),
                        resolution_status=ResolutionStatus.UNRESOLVED,
                        notes=f"Potential conflict detected across {len(source_urls)} sources"
                    )
                    
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)
                    
                    # Log the conflict
                    self.audit_log.log_event(
                        event_type="conflict_detected",
                        details={
                            'topic': topic,
                            'sources': source_urls,
                            'statement_count': len(all_statements)
                        }
                    )
                    
                    logger.warning(f"Conflict detected for topic '{topic}' across {len(source_urls)} sources")
        
        return conflicts
    
    def flag_outdated(self, content: CollectedData) -> Optional[OutdatedFlag]:
        """
        Check if content is outdated based on superseding documents.
        
        Analyzes content metadata and version history to determine
        if the information has been superseded by newer documents.
        
        Args:
            content: CollectedData to check
            
        Returns:
            OutdatedFlag if content is outdated, None otherwise
        """
        logger.debug(f"Checking if content from {content.document_url} is outdated")
        
        with self._lock:
            # Get version history for this source
            version_history = self._version_history.get(content.document_url)
            
            if not version_history:
                logger.debug("No version history available, cannot determine if outdated")
                return None
            
            # Check if there's a newer version
            latest_version = version_history.get_latest_version()
            
            if not latest_version:
                return None
            
            # If the content hash doesn't match the latest version, it's outdated
            if content.content_hash != latest_version['content_hash']:
                flag = OutdatedFlag(
                    content_hash=content.content_hash,
                    source_url=content.document_url,
                    reason="Superseded by newer version",
                    superseded_by=content.document_url,  # Same URL, newer version
                    flagged_timestamp=datetime.now(timezone.utc)
                )
                
                self._outdated_flags.append(flag)
                
                # Log the flag
                self.audit_log.log_event(
                    event_type="outdated_content_flagged",
                    details={
                        'source_url': content.document_url,
                        'content_hash': content.content_hash,
                        'reason': flag.reason
                    }
                )
                
                logger.info(f"Content from {content.document_url} flagged as outdated")
                
                return flag
        
        return None
    
    def get_version_history(self, source_url: str) -> Optional[VersionHistory]:
        """
        Get version history for a source.
        
        Args:
            source_url: URL of the source
            
        Returns:
            VersionHistory object or None if not found
        """
        with self._lock:
            return self._version_history.get(source_url)
    
    def get_all_conflicts(self) -> List[Conflict]:
        """
        Get all detected conflicts.
        
        Returns:
            List of all Conflict objects
        """
        with self._lock:
            return self._conflicts.copy()
    
    def get_all_outdated_flags(self) -> List[OutdatedFlag]:
        """
        Get all outdated flags.
        
        Returns:
            List of all OutdatedFlag objects
        """
        with self._lock:
            return self._outdated_flags.copy()
    
    def resolve_conflict(self, conflict: Conflict, resolution_status: ResolutionStatus, notes: Optional[str] = None) -> None:
        """
        Update the resolution status of a conflict.
        
        Args:
            conflict: Conflict to resolve
            resolution_status: New resolution status
            notes: Optional notes about the resolution
        """
        with self._lock:
            conflict.resolution_status = resolution_status
            if notes:
                conflict.notes = notes
            
            self.audit_log.log_event(
                event_type="conflict_resolved",
                details={
                    'topic': conflict.topic,
                    'resolution_status': resolution_status.value,
                    'notes': notes
                }
            )
            
            logger.info(f"Conflict for topic '{conflict.topic}' updated to {resolution_status.value}")
