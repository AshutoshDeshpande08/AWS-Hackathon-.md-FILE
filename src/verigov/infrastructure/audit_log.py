"""
Audit Log Module for VeriGov AI

Provides immutable, append-only logging for complete traceability of all system operations.
Logs data collection events, verification activities, unauthorized access attempts, and
configuration changes.

Requirements: 2.3, 2.7, 8.4
"""

import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import json
import threading

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be logged."""
    COLLECTION = "COLLECTION"
    VERIFICATION = "VERIFICATION"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    UNAUTHORIZED_ATTEMPT = "UNAUTHORIZED_ATTEMPT"


@dataclass
class AuditEntry:
    """
    Immutable audit log entry.
    
    Attributes:
        entry_id: Unique identifier for the entry
        timestamp: UTC timestamp when event occurred
        event_type: Type of event (COLLECTION, VERIFICATION, etc.)
        details: Event-specific details
        user: Optional user identifier
        source: Optional source identifier
    """
    entry_id: str
    timestamp: datetime
    event_type: str
    details: Dict[str, Any]
    user: Optional[str] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO format string
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AuditLog:
    """
    Immutable append-only audit log for complete system traceability.
    
    Provides logging for:
    - Data collection events
    - Verification activities
    - Configuration changes
    - Unauthorized access attempts
    
    All entries are immutable and timestamped in UTC.
    """
    
    def __init__(self):
        """Initialize the audit log with empty entries list."""
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()  # Thread-safe operations
    
    def _create_entry(
        self,
        event_type: Union[EventType, str],
        details: Dict[str, Any],
        user: Optional[str] = None,
        source: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> AuditEntry:
        """
        Create a new audit entry with unique ID and UTC timestamp.
        
        Args:
            event_type: Type of event being logged (EventType enum or string)
            details: Event-specific details
            user: Optional user identifier
            source: Optional source identifier
            timestamp: Optional custom timestamp (defaults to now)
            
        Returns:
            Immutable AuditEntry
        """
        # Handle both EventType enum and string
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
        
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=timestamp or datetime.now(timezone.utc),
            event_type=event_type_str,
            details=details,
            user=user,
            source=source
        )
        return entry
    
    def log_collection(
        self,
        source: str,
        content_hash: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a data collection event.
        
        Args:
            source: Source domain or URL
            content_hash: Hash of collected content
            timestamp: Optional collection timestamp (defaults to now)
            metadata: Optional additional metadata
        """
        collection_time = timestamp or datetime.now(timezone.utc)
        
        details = {
            "source": source,
            "content_hash": content_hash,
            "collection_timestamp": collection_time.isoformat()
        }
        
        if metadata:
            details["metadata"] = metadata
        
        entry = self._create_entry(
            event_type=EventType.COLLECTION,
            details=details,
            source=source,
            timestamp=collection_time
        )
        
        with self._lock:
            self._entries.append(entry)
    
    def log_verification(
        self,
        claim: str,
        result: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        user: Optional[str] = None
    ) -> None:
        """
        Log a verification activity.
        
        Args:
            claim: The claim that was verified
            result: Verification result details (status, confidence, sources, etc.)
            timestamp: Optional verification timestamp (defaults to now)
            user: Optional user who initiated verification
        """
        verification_time = timestamp or datetime.now(timezone.utc)
        
        details = {
            "claim": claim,
            "result": result,
            "verification_timestamp": verification_time.isoformat()
        }
        
        entry = self._create_entry(
            event_type=EventType.VERIFICATION,
            details=details,
            user=user,
            timestamp=verification_time
        )
        
        with self._lock:
            self._entries.append(entry)
    
    def log_unauthorized_attempt(
        self,
        source: str,
        timestamp: Optional[datetime] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an unauthorized access attempt.
        
        Args:
            source: Source that was attempted to be accessed
            timestamp: Optional attempt timestamp (defaults to now)
            reason: Optional reason for rejection
            metadata: Optional additional metadata
        """
        attempt_time = timestamp or datetime.now(timezone.utc)
        
        details = {
            "source": source,
            "attempt_timestamp": attempt_time.isoformat()
        }
        
        if reason:
            details["reason"] = reason
        
        if metadata:
            details["metadata"] = metadata
        
        entry = self._create_entry(
            event_type=EventType.UNAUTHORIZED_ATTEMPT,
            details=details,
            source=source,
            timestamp=attempt_time
        )
        
        with self._lock:
            self._entries.append(entry)
    
    def log_config_change(
        self,
        change_type: str,
        details: Dict[str, Any],
        user: Optional[str] = None
    ) -> None:
        """
        Log a configuration change.
        
        Args:
            change_type: Type of configuration change
            details: Change details
            user: Optional user who made the change
        """
        change_details = {
            "change_type": change_type,
            **details
        }
        
        entry = self._create_entry(
            event_type=EventType.CONFIG_CHANGE,
            details=change_details,
            user=user
        )
        
        with self._lock:
            self._entries.append(entry)
    def log_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        user: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Log a generic event to the audit log.

        Args:
            event_type: Type of event being logged
            details: Additional details about the event
            source: Source related to the event
            user: User who triggered the event
            timestamp: Custom timestamp (defaults to current UTC time)
        """
        entry = self._create_entry(
            event_type=event_type,
            details=details or {},
            source=source,
            user=user,
            timestamp=timestamp
        )

        with self._lock:
            self._entries.append(entry)

        logger.info(f"Event logged: {event_type}")
    
    def query_logs(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[AuditEntry]:
        """
        Query audit logs with optional filters.
        
        Supported filters:
        - event_type: Filter by event type (str or EventType)
        - source: Filter by source
        - user: Filter by user
        - start_time: Filter entries after this time (datetime)
        - end_time: Filter entries before this time (datetime)
        - claim: Filter verification logs by claim text
        
        Args:
            filters: Optional dictionary of filter criteria
            
        Returns:
            List of matching AuditEntry objects
        """
        with self._lock:
            results = list(self._entries)  # Create a copy
        
        if not filters:
            return results
        
        # Apply filters
        if "event_type" in filters:
            event_type_filter = filters["event_type"]
            if isinstance(event_type_filter, EventType):
                event_type_filter = event_type_filter.value
            results = [e for e in results if e.event_type == event_type_filter]
        
        if "source" in filters:
            results = [e for e in results if e.source == filters["source"]]
        
        if "user" in filters:
            results = [e for e in results if e.user == filters["user"]]
        
        if "start_time" in filters:
            start_time = filters["start_time"]
            results = [e for e in results if e.timestamp >= start_time]
        
        if "end_time" in filters:
            end_time = filters["end_time"]
            results = [e for e in results if e.timestamp <= end_time]
        
        if "claim" in filters:
            claim_filter = filters["claim"]
            results = [
                e for e in results
                if e.event_type == EventType.VERIFICATION.value
                and e.details.get("claim") == claim_filter
            ]
        
        return results
    
    def get_audit_trail(self, claim: str) -> List[AuditEntry]:
        """
        Get complete audit trail for a specific claim.
        
        Returns all verification events related to the claim,
        ordered chronologically.
        
        Args:
            claim: The claim to retrieve audit trail for
            
        Returns:
            List of AuditEntry objects related to the claim
        """
        return self.query_logs({"claim": claim})
    
    def get_all_entries(self) -> List[AuditEntry]:
        """
        Get all audit log entries.
        
        Returns:
            List of all AuditEntry objects
        """
        with self._lock:
            return list(self._entries)  # Return a copy
    
    def export_to_json(self, filepath: Optional[str] = None) -> str:
        """
        Export audit log to JSON format.
        
        Args:
            filepath: Optional file path to write JSON to
            
        Returns:
            JSON string representation of audit log
        """
        with self._lock:
            entries_dict = [entry.to_dict() for entry in self._entries]
        
        json_str = json.dumps(entries_dict, indent=2)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def __len__(self) -> int:
        """Return the number of entries in the audit log."""
        with self._lock:
            return len(self._entries)
