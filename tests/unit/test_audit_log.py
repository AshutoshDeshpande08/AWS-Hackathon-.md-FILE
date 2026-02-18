"""
Unit tests for Audit Log module.

Tests immutable logging, query functionality, and audit trail retrieval.
Requirements: 2.3, 2.7, 8.4
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import threading
import time

from src.verigov.infrastructure.audit_log import (
    AuditLog,
    AuditEntry,
    EventType
)


class TestAuditLogInitialization:
    """Test Audit Log initialization."""
    
    def test_initialization(self):
        """Test successful initialization of audit log."""
        audit_log = AuditLog()
        assert len(audit_log) == 0
        assert audit_log.get_all_entries() == []


class TestCollectionLogging:
    """Test logging of data collection events."""
    
    def test_log_collection_basic(self):
        """Test basic collection event logging."""
        audit_log = AuditLog()
        
        audit_log.log_collection(
            source="https://ministry.gov",
            content_hash="abc123def456"
        )
        
        assert len(audit_log) == 1
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.event_type == EventType.COLLECTION.value
        assert entry.details["source"] == "https://ministry.gov"
        assert entry.details["content_hash"] == "abc123def456"
        assert entry.source == "https://ministry.gov"
        assert entry.entry_id is not None
        assert entry.timestamp is not None
    
    def test_log_collection_with_metadata(self):
        """Test collection logging with additional metadata."""
        audit_log = AuditLog()
        metadata = {
            "document_url": "https://ministry.gov/policy.pdf",
            "publication_date": "2024-01-15"
        }
        
        audit_log.log_collection(
            source="https://ministry.gov",
            content_hash="xyz789",
            metadata=metadata
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.details["metadata"] == metadata
        assert entry.details["metadata"]["document_url"] == "https://ministry.gov/policy.pdf"
    
    def test_log_collection_with_custom_timestamp(self):
        """Test collection logging with custom timestamp."""
        audit_log = AuditLog()
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        audit_log.log_collection(
            source="https://judiciary.gov",
            content_hash="hash123",
            timestamp=custom_time
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert custom_time.isoformat() in entry.details["collection_timestamp"]
    
    def test_log_collection_unique_entry_ids(self):
        """Test that each collection log has a unique entry ID."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_collection("source2", "hash2")
        audit_log.log_collection("source3", "hash3")
        
        entries = audit_log.get_all_entries()
        entry_ids = [e.entry_id for e in entries]
        
        assert len(entry_ids) == len(set(entry_ids))  # All unique


class TestVerificationLogging:
    """Test logging of verification activities."""
    
    def test_log_verification_basic(self):
        """Test basic verification event logging."""
        audit_log = AuditLog()
        
        result = {
            "status": "VERIFIED",
            "confidence_score": 95.5,
            "sources": ["https://ministry.gov/doc1"]
        }
        
        audit_log.log_verification(
            claim="Policy X was enacted in 2024",
            result=result
        )
        
        assert len(audit_log) == 1
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.event_type == EventType.VERIFICATION.value
        assert entry.details["claim"] == "Policy X was enacted in 2024"
        assert entry.details["result"] == result
        assert entry.entry_id is not None
    
    def test_log_verification_with_user(self):
        """Test verification logging with user identifier."""
        audit_log = AuditLog()
        
        result = {"status": "UNVERIFIED"}
        
        audit_log.log_verification(
            claim="Test claim",
            result=result,
            user="admin@verigov.ai"
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.user == "admin@verigov.ai"
    
    def test_log_verification_with_custom_timestamp(self):
        """Test verification logging with custom timestamp."""
        audit_log = AuditLog()
        custom_time = datetime(2024, 2, 20, 14, 45, 0, tzinfo=timezone.utc)
        
        audit_log.log_verification(
            claim="Test claim",
            result={"status": "VERIFIED"},
            timestamp=custom_time
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert custom_time.isoformat() in entry.details["verification_timestamp"]


class TestUnauthorizedAttemptLogging:
    """Test logging of unauthorized access attempts."""
    
    def test_log_unauthorized_attempt_basic(self):
        """Test basic unauthorized attempt logging."""
        audit_log = AuditLog()
        
        audit_log.log_unauthorized_attempt(
            source="https://untrusted-site.com"
        )
        
        assert len(audit_log) == 1
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.event_type == EventType.UNAUTHORIZED_ATTEMPT.value
        assert entry.details["source"] == "https://untrusted-site.com"
        assert entry.source == "https://untrusted-site.com"
    
    def test_log_unauthorized_attempt_with_reason(self):
        """Test unauthorized attempt logging with reason."""
        audit_log = AuditLog()
        
        audit_log.log_unauthorized_attempt(
            source="https://fake-gov.com",
            reason="Source not in whitelist"
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.details["reason"] == "Source not in whitelist"
    
    def test_log_unauthorized_attempt_with_metadata(self):
        """Test unauthorized attempt logging with metadata."""
        audit_log = AuditLog()
        metadata = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        }
        
        audit_log.log_unauthorized_attempt(
            source="https://malicious.com",
            metadata=metadata
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.details["metadata"] == metadata


class TestConfigChangeLogging:
    """Test logging of configuration changes."""
    
    def test_log_config_change_basic(self):
        """Test basic configuration change logging."""
        audit_log = AuditLog()
        
        details = {
            "setting": "whitelist",
            "action": "add_source",
            "value": "https://new-ministry.gov"
        }
        
        audit_log.log_config_change(
            change_type="whitelist_update",
            details=details
        )
        
        assert len(audit_log) == 1
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.event_type == EventType.CONFIG_CHANGE.value
        assert entry.details["change_type"] == "whitelist_update"
        assert entry.details["setting"] == "whitelist"
    
    def test_log_config_change_with_user(self):
        """Test configuration change logging with user."""
        audit_log = AuditLog()
        
        audit_log.log_config_change(
            change_type="api_key_rotation",
            details={"api": "grok"},
            user="admin@verigov.ai"
        )
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.user == "admin@verigov.ai"


class TestQueryLogs:
    """Test audit log query functionality."""
    
    def test_query_logs_no_filters(self):
        """Test querying logs without filters returns all entries."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_verification("claim1", {"status": "VERIFIED"})
        audit_log.log_unauthorized_attempt("bad_source")
        
        results = audit_log.query_logs()
        assert len(results) == 3
    
    def test_query_logs_by_event_type_string(self):
        """Test querying logs by event type (string)."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_collection("source2", "hash2")
        audit_log.log_verification("claim1", {"status": "VERIFIED"})
        
        results = audit_log.query_logs({"event_type": "COLLECTION"})
        assert len(results) == 2
        assert all(e.event_type == EventType.COLLECTION.value for e in results)
    
    def test_query_logs_by_event_type_enum(self):
        """Test querying logs by event type (EventType enum)."""
        audit_log = AuditLog()
        
        audit_log.log_verification("claim1", {"status": "VERIFIED"})
        audit_log.log_verification("claim2", {"status": "UNVERIFIED"})
        audit_log.log_collection("source1", "hash1")
        
        results = audit_log.query_logs({"event_type": EventType.VERIFICATION})
        assert len(results) == 2
        assert all(e.event_type == EventType.VERIFICATION.value for e in results)
    
    def test_query_logs_by_source(self):
        """Test querying logs by source."""
        audit_log = AuditLog()
        
        audit_log.log_collection("https://ministry.gov", "hash1")
        audit_log.log_collection("https://judiciary.gov", "hash2")
        audit_log.log_unauthorized_attempt("https://ministry.gov")
        
        results = audit_log.query_logs({"source": "https://ministry.gov"})
        assert len(results) == 2
        assert all(e.source == "https://ministry.gov" for e in results)
    
    def test_query_logs_by_user(self):
        """Test querying logs by user."""
        audit_log = AuditLog()
        
        audit_log.log_verification("claim1", {"status": "VERIFIED"}, user="user1")
        audit_log.log_verification("claim2", {"status": "VERIFIED"}, user="user2")
        audit_log.log_verification("claim3", {"status": "VERIFIED"}, user="user1")
        
        results = audit_log.query_logs({"user": "user1"})
        assert len(results) == 2
        assert all(e.user == "user1" for e in results)
    
    def test_query_logs_by_time_range(self):
        """Test querying logs by time range."""
        audit_log = AuditLog()
        
        # Create entries with different timestamps
        time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        time3 = datetime(2024, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        audit_log.log_collection("source1", "hash1", timestamp=time1)
        audit_log.log_collection("source2", "hash2", timestamp=time2)
        audit_log.log_collection("source3", "hash3", timestamp=time3)
        
        # Query for entries in January
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        results = audit_log.query_logs({"start_time": start, "end_time": end})
        assert len(results) == 2
    
    def test_query_logs_by_claim(self):
        """Test querying logs by claim text."""
        audit_log = AuditLog()
        
        audit_log.log_verification("Policy X enacted", {"status": "VERIFIED"})
        audit_log.log_verification("Policy Y rejected", {"status": "UNVERIFIED"})
        audit_log.log_verification("Policy X enacted", {"status": "VERIFIED"})
        
        results = audit_log.query_logs({"claim": "Policy X enacted"})
        assert len(results) == 2
        assert all(e.details["claim"] == "Policy X enacted" for e in results)
    
    def test_query_logs_multiple_filters(self):
        """Test querying logs with multiple filters."""
        audit_log = AuditLog()
        
        time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        
        audit_log.log_collection("https://ministry.gov", "hash1", timestamp=time1)
        audit_log.log_collection("https://ministry.gov", "hash2", timestamp=time2)
        audit_log.log_collection("https://judiciary.gov", "hash3", timestamp=time1)
        
        # Query for ministry.gov entries in early January
        filters = {
            "event_type": EventType.COLLECTION,
            "source": "https://ministry.gov",
            "start_time": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "end_time": datetime(2024, 1, 10, 23, 59, 59, tzinfo=timezone.utc)
        }
        
        results = audit_log.query_logs(filters)
        assert len(results) == 1
        assert results[0].source == "https://ministry.gov"


class TestAuditTrail:
    """Test audit trail retrieval for specific claims."""
    
    def test_get_audit_trail_single_claim(self):
        """Test retrieving audit trail for a single claim."""
        audit_log = AuditLog()
        
        claim = "Policy X was enacted in 2024"
        
        audit_log.log_verification(claim, {"status": "VERIFIED"})
        audit_log.log_verification("Other claim", {"status": "UNVERIFIED"})
        audit_log.log_verification(claim, {"status": "VERIFIED", "confidence": 98})
        
        trail = audit_log.get_audit_trail(claim)
        assert len(trail) == 2
        assert all(e.details["claim"] == claim for e in trail)
    
    def test_get_audit_trail_no_matches(self):
        """Test retrieving audit trail for non-existent claim."""
        audit_log = AuditLog()
        
        audit_log.log_verification("Claim A", {"status": "VERIFIED"})
        audit_log.log_verification("Claim B", {"status": "UNVERIFIED"})
        
        trail = audit_log.get_audit_trail("Non-existent claim")
        assert len(trail) == 0
    
    def test_get_audit_trail_chronological_order(self):
        """Test that audit trail maintains chronological order."""
        audit_log = AuditLog()
        
        claim = "Test claim"
        
        time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        time3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)
        
        audit_log.log_verification(claim, {"status": "UNVERIFIED"}, timestamp=time1)
        audit_log.log_verification(claim, {"status": "PARTIALLY_VERIFIED"}, timestamp=time2)
        audit_log.log_verification(claim, {"status": "VERIFIED"}, timestamp=time3)
        
        trail = audit_log.get_audit_trail(claim)
        assert len(trail) == 3
        
        # Verify chronological order
        timestamps = [e.timestamp for e in trail]
        assert timestamps == sorted(timestamps)


class TestImmutability:
    """Test immutability of audit log entries."""
    
    def test_entries_are_immutable_copies(self):
        """Test that returned entries are copies and cannot modify internal state."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        
        # Get entries and try to modify
        entries = audit_log.get_all_entries()
        original_count = len(entries)
        
        # Modify the returned list
        entries.append(None)
        
        # Original audit log should be unchanged
        assert len(audit_log.get_all_entries()) == original_count
    
    def test_query_results_are_copies(self):
        """Test that query results are copies."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_collection("source2", "hash2")
        
        results = audit_log.query_logs({"event_type": EventType.COLLECTION})
        original_count = len(results)
        
        # Modify results
        results.clear()
        
        # Original audit log should be unchanged
        assert len(audit_log.query_logs({"event_type": EventType.COLLECTION})) == original_count


class TestThreadSafety:
    """Test thread safety of audit log operations."""
    
    def test_concurrent_logging(self):
        """Test that concurrent logging operations are thread-safe."""
        audit_log = AuditLog()
        num_threads = 10
        logs_per_thread = 100
        
        def log_entries(thread_id):
            for i in range(logs_per_thread):
                audit_log.log_collection(f"source_{thread_id}", f"hash_{thread_id}_{i}")
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=log_entries, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have exactly num_threads * logs_per_thread entries
        assert len(audit_log) == num_threads * logs_per_thread
    
    def test_concurrent_read_write(self):
        """Test concurrent read and write operations."""
        audit_log = AuditLog()
        stop_flag = threading.Event()
        
        def writer():
            count = 0
            while not stop_flag.is_set() and count < 100:
                audit_log.log_collection(f"source_{count}", f"hash_{count}")
                count += 1
                time.sleep(0.001)
        
        def reader():
            while not stop_flag.is_set():
                _ = audit_log.get_all_entries()
                _ = audit_log.query_logs({"event_type": EventType.COLLECTION})
                time.sleep(0.001)
        
        writer_thread = threading.Thread(target=writer)
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]
        
        writer_thread.start()
        for thread in reader_threads:
            thread.start()
        
        time.sleep(0.2)
        stop_flag.set()
        
        writer_thread.join()
        for thread in reader_threads:
            thread.join()
        
        # Should complete without errors
        assert len(audit_log) > 0


class TestExportFunctionality:
    """Test audit log export functionality."""
    
    def test_export_to_json_string(self):
        """Test exporting audit log to JSON string."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_verification("claim1", {"status": "VERIFIED"})
        
        json_str = audit_log.export_to_json()
        
        assert isinstance(json_str, str)
        assert "source1" in json_str
        assert "hash1" in json_str
        assert "claim1" in json_str
        assert "COLLECTION" in json_str
        assert "VERIFICATION" in json_str
    
    def test_export_to_json_file(self, tmp_path):
        """Test exporting audit log to JSON file."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        audit_log.log_unauthorized_attempt("bad_source")
        
        filepath = tmp_path / "audit_log.json"
        json_str = audit_log.export_to_json(str(filepath))
        
        # File should be created
        assert filepath.exists()
        
        # Content should match
        with open(filepath, 'r') as f:
            file_content = f.read()
        
        assert file_content == json_str
    
    def test_export_empty_log(self):
        """Test exporting empty audit log."""
        audit_log = AuditLog()
        
        json_str = audit_log.export_to_json()
        
        assert json_str == "[]"


class TestAuditEntryDataClass:
    """Test AuditEntry data class functionality."""
    
    def test_audit_entry_creation(self):
        """Test creating an AuditEntry."""
        timestamp = datetime.now(timezone.utc)
        entry = AuditEntry(
            entry_id="test-123",
            timestamp=timestamp,
            event_type=EventType.COLLECTION.value,
            details={"key": "value"},
            user="test_user",
            source="test_source"
        )
        
        assert entry.entry_id == "test-123"
        assert entry.timestamp == timestamp
        assert entry.event_type == EventType.COLLECTION.value
        assert entry.details == {"key": "value"}
        assert entry.user == "test_user"
        assert entry.source == "test_source"
    
    def test_audit_entry_to_dict(self):
        """Test converting AuditEntry to dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        entry = AuditEntry(
            entry_id="test-456",
            timestamp=timestamp,
            event_type=EventType.VERIFICATION.value,
            details={"claim": "test"},
            user="user1"
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["entry_id"] == "test-456"
        assert entry_dict["timestamp"] == timestamp.isoformat()
        assert entry_dict["event_type"] == EventType.VERIFICATION.value
        assert entry_dict["details"] == {"claim": "test"}
        assert entry_dict["user"] == "user1"
    
    def test_audit_entry_optional_fields(self):
        """Test AuditEntry with optional fields as None."""
        entry = AuditEntry(
            entry_id="test-789",
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.CONFIG_CHANGE.value,
            details={}
        )
        
        assert entry.user is None
        assert entry.source is None


class TestTimestampHandling:
    """Test UTC timestamp handling."""
    
    def test_timestamps_are_utc(self):
        """Test that all timestamps are in UTC."""
        audit_log = AuditLog()
        
        audit_log.log_collection("source1", "hash1")
        
        entries = audit_log.get_all_entries()
        entry = entries[0]
        
        assert entry.timestamp.tzinfo == timezone.utc
    
    def test_custom_timestamp_preserved(self):
        """Test that custom timestamps are preserved."""
        audit_log = AuditLog()
        custom_time = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        
        audit_log.log_collection("source1", "hash1", timestamp=custom_time)
        
        entries = audit_log.get_all_entries()
        # The entry timestamp is when the entry was created (now)
        # But the collection_timestamp in details should match custom_time
        assert custom_time.isoformat() in entries[0].details["collection_timestamp"]
