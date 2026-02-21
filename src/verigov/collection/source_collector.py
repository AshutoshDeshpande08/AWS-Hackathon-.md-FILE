"""
Source Collector Module for VeriGov AI

Collects data exclusively from whitelisted government sources with continuous monitoring.
Implements web scraping, API integration, metadata extraction, and comprehensive error handling.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

import hashlib
import logging
import time
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Iterator
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .source_whitelist import SourceWhitelist, SourceType
from ..infrastructure.audit_log import AuditLog


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class UnauthorizedSourceError(Exception):
    """Raised when attempting to collect from non-whitelisted source."""
    pass


class CollectionError(Exception):
    """Raised when data collection fails."""
    pass


@dataclass
class CollectedData:
    """
    Represents data collected from a government source.
    
    Attributes:
        content: The collected content/text
        source_domain: Domain of the source
        document_url: Full URL of the document
        publication_date: When the content was published
        collection_timestamp: When the content was collected
        content_hash: SHA-256 hash of the content
        metadata: Additional metadata (title, author, etc.)
    """
    content: str
    source_domain: str
    document_url: str
    publication_date: Optional[datetime]
    collection_timestamp: datetime
    content_hash: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if self.publication_date:
            data['publication_date'] = self.publication_date.isoformat()
        data['collection_timestamp'] = self.collection_timestamp.isoformat()
        return data


class SourceCollector:
    """
    Collects data exclusively from whitelisted government sources.
    
    Provides functionality for:
    - Whitelist validation before collection
    - Web scraping from government domains
    - Government API integration
    - Metadata extraction
    - Error handling and logging
    - Continuous monitoring
    """
    
    def __init__(
        self,
        whitelist: SourceWhitelist,
        audit_log: AuditLog,
        timeout: int = 30,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the Source Collector.
        
        Args:
            whitelist: SourceWhitelist instance for validation
            audit_log: AuditLog instance for logging operations
            timeout: Request timeout in seconds (default: 30)
            user_agent: Custom user agent string (optional)
        """
        self.whitelist = whitelist
        self.audit_log = audit_log
        self.timeout = timeout
        self.user_agent = user_agent or "VeriGov-AI/1.0 (Official Source Collector)"
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        
        logger.info("Source Collector initialized")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _validate_source(self, source_url: str) -> None:
        """
        Validate source against whitelist.
        
        Args:
            source_url: URL to validate
            
        Raises:
            UnauthorizedSourceError: If source is not whitelisted
        """
        if not self.whitelist.is_whitelisted(source_url):
            domain = self._extract_domain(source_url)
            
            # Log unauthorized attempt
            self.audit_log.log_unauthorized_attempt(
                source=source_url,
                reason="Source not in whitelist"
            )
            
            logger.warning(f"Rejected collection attempt from non-whitelisted source: {domain}")
            
            raise UnauthorizedSourceError(
                f"Source '{domain}' is not in whitelist. "
                "All sources must be whitelisted before collection."
            )
    
    def _scrape_web_content(self, url: str) -> tuple[str, Dict[str, Any]]:
        """
        Scrape content from a web page.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (content, metadata)
            
        Raises:
            CollectionError: If scraping fails
        """
        try:
            # Add custom headers for specific domains
            headers = {}
            if "www.congress.gov" in url:
                headers.update({
                    "Referer": "https://www.google.com",
                    "Accept-Language": "en-US,en;q=0.9"
                })

            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract metadata
            metadata = {
                'title': None,
                'description': None,
                'author': None,
                'content_type': 'web_page'
            }
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                metadata['description'] = meta_desc['content'].strip()
            
            # Extract author
            meta_author = soup.find('meta', attrs={'name': 'author'})
            if meta_author and meta_author.get('content'):
                metadata['author'] = meta_author['content'].strip()
            
            # Extract main content (remove scripts, styles, nav, footer)
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Get text content
            content = soup.get_text(separator='\n', strip=True)
            
            logger.debug(f"Successfully scraped content from {url}")
            
            return content, metadata
            
        except requests.exceptions.Timeout:
            raise CollectionError(f"Request timeout while accessing {url}")
        
        except requests.exceptions.HTTPError as e:
            raise CollectionError(f"HTTP error {e.response.status_code} while accessing {url}")
        
        except requests.exceptions.RequestException as e:
            raise CollectionError(f"Request failed for {url}: {str(e)}")
        
        except Exception as e:
            raise CollectionError(f"Failed to scrape {url}: {str(e)}")
    
    def _collect_from_api(self, url: str, api_config: Optional[Dict[str, Any]] = None) -> tuple[str, Dict[str, Any]]:
        """
        Collect data from a government API.
        
        Args:
            url: API endpoint URL
            api_config: Optional API configuration (headers, auth, etc.)
            
        Returns:
            Tuple of (content, metadata)
            
        Raises:
            CollectionError: If API call fails
        """
        try:
            headers = {}
            auth = None
            
            if api_config:
                if 'headers' in api_config:
                    headers.update(api_config['headers'])
                if 'api_key' in api_config:
                    headers['Authorization'] = f"Bearer {api_config['api_key']}"
                if 'auth' in api_config:
                    auth = api_config['auth']
            
            response = self.session.get(
                url,
                headers=headers,
                auth=auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                data = response.json()
                content = str(data)
                metadata = {
                    'content_type': 'api_response',
                    'format': 'json',
                    'response_size': len(response.content)
                }
            except ValueError:
                # Not JSON, treat as text
                content = response.text
                metadata = {
                    'content_type': 'api_response',
                    'format': 'text',
                    'response_size': len(response.content)
                }
            
            logger.debug(f"Successfully collected data from API: {url}")
            
            return content, metadata
            
        except requests.exceptions.Timeout:
            raise CollectionError(f"API request timeout for {url}")
        
        except requests.exceptions.HTTPError as e:
            raise CollectionError(f"API HTTP error {e.response.status_code} for {url}")
        
        except requests.exceptions.RequestException as e:
            raise CollectionError(f"API request failed for {url}: {str(e)}")
        
        except Exception as e:
            raise CollectionError(f"Failed to collect from API {url}: {str(e)}")
    
    def _extract_publication_date(self, url: str, metadata: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract publication date from metadata or content.
        
        Args:
            url: Source URL
            metadata: Extracted metadata
            
        Returns:
            Publication date if found, None otherwise
        """
        # This is a simplified implementation
        # In production, you'd use more sophisticated date extraction
        
        # Check if metadata contains date information
        if 'publication_date' in metadata:
            return metadata['publication_date']
        
        # Could implement more sophisticated date extraction here
        # For now, return None if not found
        return None
    
    def collect_from_source(
        self,
        source_url: str,
        api_config: Optional[Dict[str, Any]] = None
    ) -> CollectedData:
        """
        Collect data from a single source with whitelist validation.
        
        Validates source against whitelist, collects content based on source type,
        extracts metadata, and logs the operation.
        
        Args:
            source_url: URL to collect from
            api_config: Optional API configuration for API sources
            
        Returns:
            CollectedData object with content and metadata
            
        Raises:
            UnauthorizedSourceError: If source not in whitelist
            CollectionError: If collection fails
        """
        # Validate source
        self._validate_source(source_url)
        
        domain = self._extract_domain(source_url)
        collection_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting collection from {domain}")
        
        try:
            # Get source details from whitelist
            source = self.whitelist.get_source(source_url)
            
            if not source:
                raise CollectionError(f"Source {domain} not found in whitelist")
            
            # Collect based on source type
            if source.source_type == SourceType.WEB_SCRAPE.value:
                content, metadata = self._scrape_web_content(source_url)
            elif source.source_type == SourceType.API.value:
                content, metadata = self._collect_from_api(source_url, api_config)
            else:
                raise CollectionError(f"Unknown source type: {source.source_type}")
            
            # Extract publication date
            publication_date = self._extract_publication_date(source_url, metadata)
            
            # Compute content hash
            content_hash = self._compute_content_hash(content)
            
            # Create CollectedData object
            collected_data = CollectedData(
                content=content,
                source_domain=domain,
                document_url=source_url,
                publication_date=publication_date,
                collection_timestamp=collection_time,
                content_hash=content_hash,
                metadata=metadata
            )
            
            # Log successful collection
            self.audit_log.log_collection(
                source=source_url,
                content_hash=content_hash,
                timestamp=collection_time,
                metadata={
                    'source_type': source.source_type,
                    'content_length': len(content),
                    'has_publication_date': publication_date is not None
                }
            )
            
            logger.info(f"Successfully collected data from {domain} (hash: {content_hash[:8]}...)")
            
            return collected_data
            
        except UnauthorizedSourceError:
            # Re-raise unauthorized errors (already logged in _validate_source)
            raise
        
        except CollectionError as e:
            # Log collection errors with error at top level
            error_metadata = {
                'error': str(e),
                'success': False,
                'error_type': 'CollectionError'
            }
            self.audit_log.log_collection(
                source=source_url,
                content_hash="",
                timestamp=collection_time,
                metadata=error_metadata
            )
            # Re-raise the error
            raise
        
        except Exception as e:
            # Log and wrap unexpected errors
            error_msg = f"Unexpected error collecting from {source_url}: {str(e)}"
            logger.error(error_msg)
            
            error_metadata = {
                'error': error_msg,
                'success': False,
                'error_type': 'UnexpectedException'
            }
            self.audit_log.log_collection(
                source=source_url,
                content_hash="",
                timestamp=collection_time,
                metadata=error_metadata
            )
            
            raise CollectionError(error_msg) from e
    
    def collect_all(self, api_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> List[CollectedData]:
        """
        Collect from all whitelisted sources.
        
        Continues collection even if individual sources fail.
        Logs all failures for review.
        
        Args:
            api_configs: Optional dictionary mapping domains to API configurations
            
        Returns:
            List of successfully collected data
        """
        api_configs = api_configs or {}
        sources = self.whitelist.get_all_sources()
        collected = []
        failures = []
        
        logger.info(f"Starting collection from {len(sources)} whitelisted source(s)")
        
        for source in sources:
            # Construct URL from domain
            url = f"https://{source.domain}"
            
            try:
                api_config = api_configs.get(source.domain)
                data = self.collect_from_source(url, api_config)
                collected.append(data)
                
            except (UnauthorizedSourceError, CollectionError) as e:
                failures.append({
                    'source': source.domain,
                    'error': str(e)
                })
                logger.warning(f"Failed to collect from {source.domain}: {e}")
                continue
        
        logger.info(
            f"Collection complete: {len(collected)} successful, "
            f"{len(failures)} failed"
        )
        
        if failures:
            logger.warning(f"Failed sources: {[f['source'] for f in failures]}")
        
        return collected
    
    def monitor_sources(
        self,
        interval: int = 300,
        api_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Iterator[CollectedData]:
        """
        Continuously monitor sources for new content.
        
        Polls whitelisted sources at regular intervals and yields
        new data as it becomes available.
        
        Args:
            interval: Polling interval in seconds (default: 300 = 5 minutes)
            api_configs: Optional dictionary mapping domains to API configurations
            
        Yields:
            CollectedData objects as new content is discovered
        """
        api_configs = api_configs or {}
        seen_hashes: Dict[str, set] = {}  # domain -> set of content hashes
        
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        while True:
            sources = self.whitelist.get_all_sources()
            
            for source in sources:
                url = f"https://{source.domain}"
                
                try:
                    api_config = api_configs.get(source.domain)
                    data = self.collect_from_source(url, api_config)
                    
                    # Check if this is new content
                    if source.domain not in seen_hashes:
                        seen_hashes[source.domain] = set()
                    
                    if data.content_hash not in seen_hashes[source.domain]:
                        seen_hashes[source.domain].add(data.content_hash)
                        logger.info(f"New content detected from {source.domain}")
                        yield data
                    
                except (UnauthorizedSourceError, CollectionError) as e:
                    logger.warning(f"Monitoring error for {source.domain}: {e}")
                    continue
            
            # Wait before next poll
            time.sleep(interval)
    
    def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        self.session.close()
        logger.info("Source Collector closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
