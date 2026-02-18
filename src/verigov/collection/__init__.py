"""Data collection module for VeriGov AI."""

from verigov.collection.source_whitelist import (
    SourceWhitelist,
    WhitelistedSource,
    ValidationResult,
    SourceType,
    ValidationStatus
)

from verigov.collection.source_collector import (
    SourceCollector,
    CollectedData,
    UnauthorizedSourceError,
    CollectionError
)

__all__ = [
    'SourceWhitelist',
    'WhitelistedSource',
    'ValidationResult',
    'SourceType',
    'ValidationStatus',
    'SourceCollector',
    'CollectedData',
    'UnauthorizedSourceError',
    'CollectionError'
]
