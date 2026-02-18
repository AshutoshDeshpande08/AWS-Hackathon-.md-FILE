"""
Unit tests for Change Detector module.

Tests change detection, conflict detection, outdated flagging,
and version history tracking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.verigov.monitoring.change_detector import (
    ChangeDetector,
    DetectedChange,
    Conflict,
    OutdatedFlag,
    VersionHistory,
    ChangeType,
    ImpactLevel,
    ResolutionStatus
)
from src.verigov.collection.source_collector import CollectedData
from src.verigov.infrastructure.audit_log import AuditLog


@pytest.fixture
def mock_source_collector():
    """Create a mock source collector."""
    collector = Mock()
    collector.whitelist = Mock()
    return collector


@pytest.fixture
def audit_log():
    """Create an audit log instance."""
    return AuditLog()


@pytest.fixture
def change_detector(mock_source_collector, audit_log):
    """Create a change detector instance."""
    return ChangeDetector(
        source_collector=mock_source_collector,
        audit_log=audit_log,
        similarity_threshold=0.95
    )


@pytest.fixture
def sample_collected_data():
    """Create sample collected data."""
    return CollectedData(
        document_url="https://example.gov/policy",
        content="This is the policy content.",
        content_hash="abc123",
        collection_timestamp=datetime.now(timezone.utc),
        metadata={"title": "Sample Policy"},
        publication_date=datetime.now(timezone.utc) - timedelta(days=1),
        source_domain="example.gov"
    )


class TestChangeDetector:
    """Test suite for ChangeDetector class."""
    
    def test_initialization(self, change_detector, mock_source_collector, audit_log):
        """Test change detector initialization."""
        assert change_detector.source_collector == mock_source_collector
        assert change_detector.audit_log == audit_log
        assert change_detector.similarity_threshold == 0.95
        assert len(change_detector._version_history) == 0
        assert len(change_detector._content_cache) == 0
    
    def test_compute_similarity_identical(self, change_detector):
        """Test similarity computation for identical texts."""
        text = "This is a test document."
        similarity = change_detector._compute_similarity(text, text)
        assert similarity == 1.0
    
    def test_compute_similarity_different(self, change_detector):
        """Test similarity computation for different texts."""
        text1 = "This is a test document."
        text2 = "This is a completely different document."
        similarity = change_detector._compute_similarity(text1, text2)
        assert 0.0 < similarity < 1.0
    
    def test_generate_diff(self, change_detector):
        """Test diff generation."""
        old_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nLine 2 modified\nLine 3"
        
        diff = change_detector._generate_diff(old_content, new_content)
        
        assert "Line 2" in diff
        assert "Line 2 modified" in diff
    
    def test_classify_change_type_new_document(self, change_detector):
        """Test change type classification for new documents."""
        change_type = change_detector._classify_change_type(
            old_content=None,
            new_content="New content",
            diff=""
        )
        assert change_type == ChangeType.NEW_DOCUMENT
    
    def test_classify_change_type_amendment(self, change_detector):
        """Test change type classification for amendments."""
        diff = "This law has been amended to include new provisions."
        change_type = change_detector._classify_change_type(
            old_content="Old law",
            new_content="New law",
            diff=diff
        )
        assert change_type == ChangeType.LAW_AMENDMENT
    
    def test_classify_change_type_correction(self, change_detector):
        """Test change type classification for corrections."""
        diff = "Correction: The previous version contained an error."
        change_type = change_detector._classify_change_type(
            old_content="Old content",
            new_content="Corrected content",
            diff=diff
        )
        assert change_type == ChangeType.CORRECTION
    
    def test_classify_change_type_policy_update(self, change_detector):
        """Test change type classification for policy updates."""
        diff = "The policy has been updated with new guidelines."
        change_type = change_detector._classify_change_type(
            old_content="Old policy",
            new_content="Updated policy",
            diff=diff
        )
        assert change_type == ChangeType.POLICY_UPDATE
    
    def test_assess_impact_level_high(self, change_detector):
        """Test impact level assessment for high impact changes."""
        # Law amendments are high impact
        impact = change_detector._assess_impact_level(
            change_type=ChangeType.LAW_AMENDMENT,
            diff="Some diff"
        )
        assert impact == ImpactLevel.HIGH
        
        # Large diffs are high impact
        large_diff = "\n".join([f"Line {i}" for i in range(150)])
        impact = change_detector._assess_impact_level(
            change_type=ChangeType.POLICY_UPDATE,
            diff=large_diff
        )
        assert impact == ImpactLevel.HIGH
    
    def test_assess_impact_level_medium(self, change_detector):
        """Test impact level assessment for medium impact changes."""
        medium_diff = "\n".join([f"Line {i}" for i in range(50)])
        impact = change_detector._assess_impact_level(
            change_type=ChangeType.POLICY_UPDATE,
            diff=medium_diff
        )
        assert impact == ImpactLevel.MEDIUM
    
    def test_assess_impact_level_low(self, change_detector):
        """Test impact level assessment for low impact changes."""
        # Corrections are low impact
        impact = change_detector._assess_impact_level(
            change_type=ChangeType.CORRECTION,
            diff="Small correction"
        )
        assert impact == ImpactLevel.LOW
        
        # Small diffs are low impact
        small_diff = "Line 1\nLine 2"
        impact = change_detector._assess_impact_level(
            change_type=ChangeType.POLICY_UPDATE,
            diff=small_diff
        )
        assert impact == ImpactLevel.LOW
    
    def test_generate_change_summary(self, change_detector):
        """Test change summary generation."""
        diff = "+New line 1\n+New line 2\n-Old line 1"
        summary = change_detector._generate_change_summary(
            change_type=ChangeType.POLICY_UPDATE,
            diff=diff
        )
        
        assert "POLICY_UPDATE" in summary
        assert "added" in summary
        assert "removed" in summary


class TestDetectChanges:
    """Test suite for change detection functionality."""
    
    def test_detect_changes_first_collection(self, change_detector, sample_collected_data):
        """Test change detection on first collection (new document)."""
        source_url = sample_collected_data.document_url
        
        # Mock the source collector to return sample data
        change_detector.source_collector.collect_from_source = Mock(
            return_value=sample_collected_data
        )
        
        changes = change_detector.detect_changes(source_url)
        
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.NEW_DOCUMENT
        assert changes[0].source_url == source_url
        assert changes[0].old_content is None
        assert changes[0].new_content == sample_collected_data.content
        
        # Verify version history was created
        assert source_url in change_detector._version_history
        assert change_detector._version_history[source_url].get_version_count() == 1
        
        # Verify cache was updated
        assert source_url in change_detector._content_cache
    
    def test_detect_changes_no_change(self, change_detector, sample_collected_data):
        """Test change detection when content hasn't changed."""
        source_url = sample_collected_data.document_url
        
        # Pre-populate cache
        change_detector._content_cache[source_url] = sample_collected_data
        change_detector._version_history[source_url] = VersionHistory(source_url=source_url)
        
        # Mock the source collector to return same data
        change_detector.source_collector.collect_from_source = Mock(
            return_value=sample_collected_data
        )
        
        changes = change_detector.detect_changes(source_url)
        
        assert len(changes) == 0
    
    def test_detect_changes_content_changed(self, change_detector, sample_collected_data):
        """Test change detection when content has changed."""
        source_url = sample_collected_data.document_url
        
        # Pre-populate cache with old data
        old_data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="Old policy content that is different.",
            content_hash="old123",
            collection_timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
            metadata={"title": "Sample Policy"},
            publication_date=datetime.now(timezone.utc) - timedelta(days=2)
        )
        change_detector._content_cache[source_url] = old_data
        change_detector._version_history[source_url] = VersionHistory(source_url=source_url)
        
        # Mock the source collector to return new data
        new_data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="New policy content that is completely different from the old one.",
            content_hash="new456",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={"title": "Sample Policy"},
            publication_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        change_detector.source_collector.collect_from_source = Mock(return_value=new_data)
        
        changes = change_detector.detect_changes(source_url)
        
        assert len(changes) == 1
        assert changes[0].change_type in [ChangeType.POLICY_UPDATE, ChangeType.LAW_AMENDMENT, ChangeType.CORRECTION]
        assert changes[0].old_content == old_data.content
        assert changes[0].new_content == new_data.content
        assert changes[0].diff is not None
        
        # Verify version history was updated
        assert change_detector._version_history[source_url].get_version_count() == 1
        
        # Verify cache was updated
        assert change_detector._content_cache[source_url] == new_data
    
    def test_detect_changes_minor_change_below_threshold(self, change_detector):
        """Test that minor changes below similarity threshold are ignored."""
        source_url = "https://example.gov/policy"
        
        # Pre-populate cache
        old_data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="This is a policy document with some content.",
            content_hash="old123",
            collection_timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
            metadata={},
            publication_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        change_detector._content_cache[source_url] = old_data
        change_detector._version_history[source_url] = VersionHistory(source_url=source_url)
        
        # New data with minor change (just a period added)
        new_data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="This is a policy document with some content..",
            content_hash="new456",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        change_detector.source_collector.collect_from_source = Mock(return_value=new_data)
        
        changes = change_detector.detect_changes(source_url)
        
        # Should detect no significant change
        assert len(changes) == 0
    
    def test_detect_changes_error_handling(self, change_detector):
        """Test error handling in change detection."""
        source_url = "https://example.gov/policy"
        
        # Mock the source collector to raise an exception
        change_detector.source_collector.collect_from_source = Mock(
            side_effect=Exception("Network error")
        )
        
        changes = change_detector.detect_changes(source_url)
        
        # Should return empty list on error
        assert len(changes) == 0


class TestMonitorAllSources:
    """Test suite for monitoring all sources."""
    
    def test_monitor_all_sources(self, change_detector):
        """Test monitoring all whitelisted sources."""
        # Mock whitelist
        sources = [
            "https://example.gov/policy1",
            "https://example.gov/policy2"
        ]
        change_detector.source_collector.whitelist.get_all_sources = Mock(return_value=sources)
        
        # Mock detect_changes to return sample changes
        sample_change = DetectedChange(
            source_url="https://example.gov/policy1",
            change_type=ChangeType.NEW_DOCUMENT,
            old_content=None,
            new_content="Content",
            detected_timestamp=datetime.now(timezone.utc),
            impact_level=ImpactLevel.MEDIUM,
            summary="New document"
        )
        
        change_detector.detect_changes = Mock(return_value=[sample_change])
        
        # Collect all changes
        changes = list(change_detector.monitor_all_sources())
        
        # Should have called detect_changes for each source
        assert change_detector.detect_changes.call_count == 2
        assert len(changes) == 2
    
    def test_monitor_all_sources_with_errors(self, change_detector):
        """Test that monitoring continues even if some sources fail."""
        sources = [
            "https://example.gov/policy1",
            "https://example.gov/policy2",
            "https://example.gov/policy3"
        ]
        change_detector.source_collector.whitelist.get_all_sources = Mock(return_value=sources)
        
        # Mock detect_changes to fail for second source
        def detect_changes_side_effect(url):
            if url == sources[1]:
                raise Exception("Error")
            return []
        
        change_detector.detect_changes = Mock(side_effect=detect_changes_side_effect)
        
        # Should not raise exception
        changes = list(change_detector.monitor_all_sources())
        
        # Should have attempted all sources
        assert change_detector.detect_changes.call_count == 3


class TestDetectConflicts:
    """Test suite for conflict detection."""
    
    def test_detect_conflicts_no_sources(self, change_detector):
        """Test conflict detection with no sources."""
        conflicts = change_detector.detect_conflicts("healthcare")
        assert len(conflicts) == 0
    
    def test_detect_conflicts_single_source(self, change_detector):
        """Test conflict detection with only one source."""
        # Add one source to cache
        data = CollectedData(
            document_url="https://example.gov/policy",
            source_domain="example.gov",
            content="Healthcare policy states that coverage is mandatory.",
            content_hash="abc123",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc)
        )
        change_detector._content_cache["https://example.gov/policy"] = data
        
        conflicts = change_detector.detect_conflicts("healthcare")
        assert len(conflicts) == 0
    
    def test_detect_conflicts_multiple_sources_with_conflict(self, change_detector):
        """Test conflict detection with conflicting sources."""
        # Add multiple sources with conflicting information
        data1 = CollectedData(
            document_url="https://example.gov/policy1",
            source_domain="example.gov",
            content="Healthcare policy states that coverage is mandatory for all citizens.",
            content_hash="abc123",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc)
        )
        data2 = CollectedData(
            document_url="https://example.gov/policy2",
            source_domain="example.gov",
            content="Healthcare policy states that coverage is optional for citizens.",
            content_hash="def456",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc)
        )
        
        change_detector._content_cache["https://example.gov/policy1"] = data1
        change_detector._content_cache["https://example.gov/policy2"] = data2
        
        conflicts = change_detector.detect_conflicts("healthcare")
        
        assert len(conflicts) == 1
        assert conflicts[0].topic == "healthcare"
        assert len(conflicts[0].conflicting_sources) == 2
        assert conflicts[0].resolution_status == ResolutionStatus.UNRESOLVED
    
    def test_detect_conflicts_topic_not_found(self, change_detector):
        """Test conflict detection when topic is not in any source."""
        data = CollectedData(
            document_url="https://example.gov/policy",
            source_domain="example.gov",
            content="This is about education policy.",
            content_hash="abc123",
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc)
        )
        change_detector._content_cache["https://example.gov/policy"] = data
        
        conflicts = change_detector.detect_conflicts("healthcare")
        assert len(conflicts) == 0


class TestFlagOutdated:
    """Test suite for outdated content flagging."""
    
    def test_flag_outdated_no_history(self, change_detector, sample_collected_data):
        """Test flagging outdated content with no version history."""
        flag = change_detector.flag_outdated(sample_collected_data)
        assert flag is None
    
    def test_flag_outdated_current_version(self, change_detector):
        """Test flagging content that is the current version."""
        source_url = "https://example.gov/policy"
        content_hash = "abc123"
        
        # Create version history with current version
        version_history = VersionHistory(source_url=source_url)
        version_history.add_version(
            content_hash=content_hash,
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        change_detector._version_history[source_url] = version_history
        
        # Create data with same hash
        data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="Current content",
            content_hash=content_hash,
            collection_timestamp=datetime.now(timezone.utc),
            metadata={},
            publication_date=datetime.now(timezone.utc)
        )
        
        flag = change_detector.flag_outdated(data)
        assert flag is None
    
    def test_flag_outdated_old_version(self, change_detector):
        """Test flagging content that is an old version."""
        source_url = "https://example.gov/policy"
        old_hash = "old123"
        new_hash = "new456"
        
        # Create version history with newer version
        version_history = VersionHistory(source_url=source_url)
        version_history.add_version(
            content_hash=old_hash,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            metadata={}
        )
        version_history.add_version(
            content_hash=new_hash,
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        change_detector._version_history[source_url] = version_history
        
        # Create data with old hash
        old_data = CollectedData(
            document_url=source_url,
            source_domain="example.gov",
            content="Old content",
            content_hash=old_hash,
            collection_timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            metadata={},
            publication_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        flag = change_detector.flag_outdated(old_data)
        
        assert flag is not None
        assert flag.content_hash == old_hash
        assert flag.source_url == source_url
        assert flag.reason == "Superseded by newer version"
        assert flag.superseded_by == source_url


class TestVersionHistory:
    """Test suite for version history functionality."""
    
    def test_version_history_initialization(self):
        """Test version history initialization."""
        vh = VersionHistory(source_url="https://example.gov/policy")
        assert vh.source_url == "https://example.gov/policy"
        assert len(vh.versions) == 0
    
    def test_add_version(self):
        """Test adding versions to history."""
        vh = VersionHistory(source_url="https://example.gov/policy")
        
        timestamp = datetime.now(timezone.utc)
        vh.add_version(
            content_hash="abc123",
            timestamp=timestamp,
            metadata={"title": "Policy v1"}
        )
        
        assert vh.get_version_count() == 1
        assert vh.versions[0]['content_hash'] == "abc123"
        assert vh.versions[0]['metadata']['title'] == "Policy v1"
    
    def test_get_latest_version(self):
        """Test getting the latest version."""
        vh = VersionHistory(source_url="https://example.gov/policy")
        
        vh.add_version("hash1", datetime.now(timezone.utc) - timedelta(hours=2))
        vh.add_version("hash2", datetime.now(timezone.utc) - timedelta(hours=1))
        vh.add_version("hash3", datetime.now(timezone.utc))
        
        latest = vh.get_latest_version()
        assert latest['content_hash'] == "hash3"
    
    def test_get_latest_version_empty(self):
        """Test getting latest version from empty history."""
        vh = VersionHistory(source_url="https://example.gov/policy")
        assert vh.get_latest_version() is None


class TestHelperMethods:
    """Test suite for helper methods."""
    
    def test_get_version_history(self, change_detector):
        """Test getting version history for a source."""
        source_url = "https://example.gov/policy"
        vh = VersionHistory(source_url=source_url)
        change_detector._version_history[source_url] = vh
        
        retrieved = change_detector.get_version_history(source_url)
        assert retrieved == vh
    
    def test_get_version_history_not_found(self, change_detector):
        """Test getting version history for non-existent source."""
        retrieved = change_detector.get_version_history("https://example.gov/nonexistent")
        assert retrieved is None
    
    def test_get_all_conflicts(self, change_detector):
        """Test getting all conflicts."""
        conflict = Conflict(
            topic="healthcare",
            conflicting_sources=["url1", "url2"],
            statements=["statement1", "statement2"],
            detected_timestamp=datetime.now(timezone.utc),
            resolution_status=ResolutionStatus.UNRESOLVED
        )
        change_detector._conflicts.append(conflict)
        
        conflicts = change_detector.get_all_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0].topic == "healthcare"
    
    def test_get_all_outdated_flags(self, change_detector):
        """Test getting all outdated flags."""
        flag = OutdatedFlag(
            content_hash="abc123",
            source_url="https://example.gov/policy",
            reason="Superseded",
            superseded_by="https://example.gov/policy-v2",
            flagged_timestamp=datetime.now(timezone.utc)
        )
        change_detector._outdated_flags.append(flag)
        
        flags = change_detector.get_all_outdated_flags()
        assert len(flags) == 1
        assert flags[0].content_hash == "abc123"
    
    def test_resolve_conflict(self, change_detector):
        """Test resolving a conflict."""
        conflict = Conflict(
            topic="healthcare",
            conflicting_sources=["url1", "url2"],
            statements=["statement1", "statement2"],
            detected_timestamp=datetime.now(timezone.utc),
            resolution_status=ResolutionStatus.UNRESOLVED
        )
        change_detector._conflicts.append(conflict)
        
        change_detector.resolve_conflict(
            conflict,
            ResolutionStatus.RESOLVED,
            notes="Resolved by checking official source"
        )
        
        assert conflict.resolution_status == ResolutionStatus.RESOLVED
        assert conflict.notes == "Resolved by checking official source"


class TestDataStructures:
    """Test suite for data structure serialization."""
    
    def test_detected_change_to_dict(self):
        """Test DetectedChange serialization."""
        change = DetectedChange(
            source_url="https://example.gov/policy",
            change_type=ChangeType.POLICY_UPDATE,
            old_content="Old",
            new_content="New",
            detected_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            impact_level=ImpactLevel.HIGH,
            summary="Policy updated",
            diff="diff content"
        )
        
        data = change.to_dict()
        
        assert data['source_url'] == "https://example.gov/policy"
        assert data['change_type'] == "POLICY_UPDATE"
        assert data['impact_level'] == "HIGH"
        assert data['detected_timestamp'] == "2024-01-01T12:00:00+00:00"
    
    def test_conflict_to_dict(self):
        """Test Conflict serialization."""
        conflict = Conflict(
            topic="healthcare",
            conflicting_sources=["url1", "url2"],
            statements=["statement1", "statement2"],
            detected_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            resolution_status=ResolutionStatus.UNRESOLVED,
            notes="Test notes"
        )
        
        data = conflict.to_dict()
        
        assert data['topic'] == "healthcare"
        assert data['resolution_status'] == "UNRESOLVED"
        assert data['detected_timestamp'] == "2024-01-01T12:00:00+00:00"
    
    def test_outdated_flag_to_dict(self):
        """Test OutdatedFlag serialization."""
        flag = OutdatedFlag(
            content_hash="abc123",
            source_url="https://example.gov/policy",
            reason="Superseded",
            superseded_by="https://example.gov/policy-v2",
            flagged_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        data = flag.to_dict()
        
        assert data['content_hash'] == "abc123"
        assert data['flagged_timestamp'] == "2024-01-01T12:00:00+00:00"
