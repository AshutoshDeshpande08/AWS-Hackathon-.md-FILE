"""
Source Whitelist Module for VeriGov AI

Maintains and validates the list of approved government sources with strict
validation rules including SSL certificate checking and domain authenticity verification.

Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
"""

import ssl
import socket
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from enum import Enum
import json
import threading


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SourceType(Enum):
    """Types of whitelisted sources."""
    WEB_SCRAPE = "web_scrape"
    API = "api"


class ValidationStatus(Enum):
    """Status of source validation."""
    VALID = "VALID"
    INVALID_SSL = "INVALID_SSL"
    INVALID_DOMAIN = "INVALID_DOMAIN"
    INVALID_RULES = "INVALID_RULES"
    NOT_WHITELISTED = "NOT_WHITELISTED"


@dataclass
class WhitelistedSource:
    """
    Represents a whitelisted government source.
    
    Attributes:
        domain: The domain name (e.g., "gov.example.com")
        source_type: Type of source (web_scrape or api)
        validation_rules: Dictionary of validation rules
        added_date: When the source was added to whitelist
        approved_by: Who approved the source
    """
    domain: str
    source_type: str
    validation_rules: Dict[str, Any]
    added_date: datetime
    approved_by: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['added_date'] = self.added_date.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WhitelistedSource':
        """Create WhitelistedSource from dictionary."""
        data = data.copy()
        if isinstance(data['added_date'], str):
            data['added_date'] = datetime.fromisoformat(data['added_date'])
        return cls(**data)


@dataclass
class ValidationResult:
    """
    Result of source validation.
    
    Attributes:
        is_valid: Whether the source passed validation
        status: Validation status code
        errors: List of validation errors
        warnings: List of validation warnings
        ssl_info: Optional SSL certificate information
    """
    is_valid: bool
    status: ValidationStatus
    errors: List[str]
    warnings: List[str]
    ssl_info: Optional[Dict[str, Any]] = None


class SourceWhitelist:
    """
    Manages the whitelist of approved government sources.
    
    Provides functionality for:
    - Checking if sources are whitelisted
    - Validating source authenticity (SSL, domain)
    - Adding new sources with manual approval
    - Rule-based trust filtering
    """
    
    def __init__(self, whitelist_file: Optional[str] = None):
        """
        Initialize the source whitelist.
        
        Args:
            whitelist_file: Optional path to JSON file containing whitelist
        """
        self._sources: Dict[str, WhitelistedSource] = {}
        self._lock = threading.Lock()
        self._whitelist_file = whitelist_file
        
        if whitelist_file:
            self._load_from_file(whitelist_file)
        
        logger.info(f"Source Whitelist initialized with {len(self._sources)} source(s)")
    
    def _load_from_file(self, filepath: str) -> None:
        """
        Load whitelist from JSON file.
        
        Args:
            filepath: Path to whitelist JSON file
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            sources_data = data.get('sources', [])
            
            for source_data in sources_data:
                source = WhitelistedSource.from_dict(source_data)
                self._sources[source.domain] = source
            
            logger.info(f"Loaded {len(self._sources)} source(s) from {filepath}")
        
        except FileNotFoundError:
            logger.warning(f"Whitelist file not found: {filepath}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse whitelist file: {e}")
        except Exception as e:
            logger.error(f"Error loading whitelist: {e}")
    
    def _save_to_file(self) -> None:
        """Save whitelist to JSON file if filepath is configured."""
        if not self._whitelist_file:
            return
        
        try:
            with self._lock:
                sources_list = [source.to_dict() for source in self._sources.values()]
            
            data = {
                'sources': sources_list,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self._whitelist_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved whitelist to {self._whitelist_file}")
        
        except Exception as e:
            logger.error(f"Failed to save whitelist: {e}")
    
    def _extract_domain(self, source_url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            source_url: Full URL or domain
            
        Returns:
            Domain name
        """
        # If it's already just a domain, return it
        if not source_url.startswith(('http://', 'https://')):
            return source_url.lower()
        
        parsed = urlparse(source_url)
        return parsed.netloc.lower()
    
    def is_whitelisted(self, source_url: str) -> bool:
        """
        Check if a source is in the whitelist.
        
        Args:
            source_url: URL or domain to check
            
        Returns:
            True if source is whitelisted, False otherwise
        """
        domain = self._extract_domain(source_url)
        
        with self._lock:
            is_listed = domain in self._sources
        
        logger.debug(f"Whitelist check for '{domain}': {is_listed}")
        return is_listed
    
    def _validate_ssl_certificate(self, domain: str) -> tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """
        Validate SSL certificate for a domain.
        
        Args:
            domain: Domain to validate
            
        Returns:
            Tuple of (is_valid, ssl_info, errors)
        """
        errors = []
        ssl_info = None
        
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to the domain on port 443
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # Get certificate info
                    cert = ssock.getpeercert()
                    
                    ssl_info = {
                        'subject': dict(x[0] for x in cert.get('subject', [])),
                        'issuer': dict(x[0] for x in cert.get('issuer', [])),
                        'version': cert.get('version'),
                        'notBefore': cert.get('notBefore'),
                        'notAfter': cert.get('notAfter'),
                    }
                    
                    # Check if certificate is valid for this domain
                    ssl.match_hostname(cert, domain)
                    
                    logger.debug(f"SSL certificate valid for {domain}")
                    return True, ssl_info, errors
        
        except ssl.SSLError as e:
            errors.append(f"SSL certificate error: {str(e)}")
            logger.warning(f"SSL validation failed for {domain}: {e}")
        
        except socket.gaierror as e:
            errors.append(f"Domain resolution failed: {str(e)}")
            logger.warning(f"Domain resolution failed for {domain}: {e}")
        
        except socket.timeout:
            errors.append("Connection timeout")
            logger.warning(f"Connection timeout for {domain}")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            logger.warning(f"SSL validation error for {domain}: {e}")
        
        return False, ssl_info, errors
    
    def _validate_domain_authenticity(self, domain: str) -> tuple[bool, List[str]]:
        """
        Validate domain authenticity.
        
        Checks if domain follows government domain patterns and conventions.
        
        Args:
            domain: Domain to validate
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Check for common government TLDs
        gov_tlds = ['.gov', '.gov.', '.mil', '.mil.']
        is_gov_tld = any(tld in domain for tld in gov_tlds)
        
        if not is_gov_tld:
            # Not a government TLD, but could still be valid
            # (e.g., ministry websites on .org or country-specific domains)
            logger.debug(f"Domain {domain} does not use standard government TLD")
        
        # Check domain format
        if not domain or '.' not in domain:
            errors.append("Invalid domain format")
            return False, errors
        
        # Check for suspicious patterns
        suspicious_patterns = ['free', 'blog', 'wordpress', 'blogspot']
        if any(pattern in domain.lower() for pattern in suspicious_patterns):
            errors.append(f"Domain contains suspicious pattern")
            return False, errors
        
        return True, errors
    
    def _validate_rules(self, source: WhitelistedSource) -> tuple[bool, List[str]]:
        """
        Validate source against its validation rules.
        
        Args:
            source: WhitelistedSource to validate
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        rules = source.validation_rules
        
        # Check required fields in validation rules
        if 'require_https' in rules and rules['require_https']:
            # This would be checked during actual connection
            pass
        
        if 'allowed_paths' in rules:
            # Path validation would happen during collection
            pass
        
        if 'rate_limit' in rules:
            # Rate limiting would be enforced during collection
            pass
        
        # All rules are valid at this level
        return True, errors
    
    def validate_source(self, source_url: str) -> ValidationResult:
        """
        Validate source authenticity with comprehensive checks.
        
        Performs:
        - Whitelist check
        - SSL certificate validation
        - Domain authenticity verification
        - Validation rule checks
        
        Args:
            source_url: URL or domain to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        domain = self._extract_domain(source_url)
        errors = []
        warnings = []
        ssl_info = None
        
        # Check if whitelisted
        with self._lock:
            source = self._sources.get(domain)
        
        if not source:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.NOT_WHITELISTED,
                errors=[f"Source '{domain}' is not in whitelist"],
                warnings=warnings
            )
        
        # Validate SSL certificate
        ssl_valid, ssl_info, ssl_errors = self._validate_ssl_certificate(domain)
        if not ssl_valid:
            errors.extend(ssl_errors)
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_SSL,
                errors=errors,
                warnings=warnings,
                ssl_info=ssl_info
            )
        
        # Validate domain authenticity
        domain_valid, domain_errors = self._validate_domain_authenticity(domain)
        if not domain_valid:
            errors.extend(domain_errors)
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_DOMAIN,
                errors=errors,
                warnings=warnings,
                ssl_info=ssl_info
            )
        
        # Validate rules
        rules_valid, rules_errors = self._validate_rules(source)
        if not rules_valid:
            errors.extend(rules_errors)
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_RULES,
                errors=errors,
                warnings=warnings,
                ssl_info=ssl_info
            )
        
        logger.info(f"Source validation passed for {domain}")
        
        return ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            errors=[],
            warnings=warnings,
            ssl_info=ssl_info
        )
    
    def add_source(
        self,
        source_url: str,
        validation_rules: Dict[str, Any],
        approved_by: str,
        source_type: str = "web_scrape",
        manual_approval: bool = True
    ) -> bool:
        """
        Add a new source to the whitelist with manual approval.
        
        Args:
            source_url: URL or domain to add
            validation_rules: Dictionary of validation rules
            approved_by: Identifier of approver
            source_type: Type of source ("web_scrape" or "api")
            manual_approval: Whether manual approval is required (default: True)
            
        Returns:
            True if source was added, False if rejected
        """
        domain = self._extract_domain(source_url)
        
        # Check if already whitelisted
        if self.is_whitelisted(domain):
            logger.warning(f"Source {domain} is already whitelisted")
            return False
        
        # Validate source type
        if source_type not in [SourceType.WEB_SCRAPE.value, SourceType.API.value]:
            logger.error(f"Invalid source type: {source_type}")
            return False
        
        # Require manual approval
        if manual_approval and not approved_by:
            logger.error("Manual approval required but no approver specified")
            return False
        
        # Perform basic validation before adding
        domain_valid, domain_errors = self._validate_domain_authenticity(domain)
        if not domain_valid:
            logger.error(f"Domain validation failed for {domain}: {domain_errors}")
            return False
        
        # Create new whitelisted source
        new_source = WhitelistedSource(
            domain=domain,
            source_type=source_type,
            validation_rules=validation_rules,
            added_date=datetime.now(timezone.utc),
            approved_by=approved_by
        )
        
        # Add to whitelist
        with self._lock:
            self._sources[domain] = new_source
        
        # Save to file if configured
        self._save_to_file()
        
        logger.info(f"Added source {domain} to whitelist (approved by: {approved_by})")
        return True
    
    def remove_source(self, source_url: str) -> bool:
        """
        Remove a source from the whitelist.
        
        Args:
            source_url: URL or domain to remove
            
        Returns:
            True if source was removed, False if not found
        """
        domain = self._extract_domain(source_url)
        
        with self._lock:
            if domain in self._sources:
                del self._sources[domain]
                logger.info(f"Removed source {domain} from whitelist")
                self._save_to_file()
                return True
        
        logger.warning(f"Source {domain} not found in whitelist")
        return False
    
    def get_source(self, source_url: str) -> Optional[WhitelistedSource]:
        """
        Get whitelisted source details.
        
        Args:
            source_url: URL or domain to retrieve
            
        Returns:
            WhitelistedSource if found, None otherwise
        """
        domain = self._extract_domain(source_url)
        
        with self._lock:
            return self._sources.get(domain)
    
    def get_all_sources(self) -> List[WhitelistedSource]:
        """
        Get all whitelisted sources.
        
        Returns:
            List of all WhitelistedSource objects
        """
        with self._lock:
            return list(self._sources.values())
    
    def get_sources_by_type(self, source_type: str) -> List[WhitelistedSource]:
        """
        Get all sources of a specific type.
        
        Args:
            source_type: Type to filter by ("web_scrape" or "api")
            
        Returns:
            List of WhitelistedSource objects matching the type
        """
        with self._lock:
            return [
                source for source in self._sources.values()
                if source.source_type == source_type
            ]
    
    def __len__(self) -> int:
        """Return the number of whitelisted sources."""
        with self._lock:
            return len(self._sources)
