from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Generator, List
import hashlib
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


class UnauthorizedSourceError(Exception):
    pass


class CollectionError(Exception):
    pass


@dataclass
class CollectedData:
    content: str
    source_domain: str
    document_url: str
    publication_date: Optional[datetime]
    collection_timestamp: datetime
    content_hash: str
    metadata: Dict

    def to_dict(self):
        return {
            "content": self.content,
            "source_domain": self.source_domain,
            "document_url": self.document_url,
            "publication_date": (
                self.publication_date.isoformat()
                if self.publication_date else None
            ),
            "collection_timestamp": self.collection_timestamp.isoformat(),
            "content_hash": self.content_hash,
            "metadata": self.metadata
        }


class SourceCollector:

    def __init__(
        self,
        whitelist,
        audit_log,
        timeout: int = 30,
        user_agent: str = "VeriGov-AI/1.0"
    ):
        self.whitelist = whitelist
        self.audit_log = audit_log
        self.timeout = timeout
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    # ------------------------------
    # Core Helpers
    # ------------------------------

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc

    def _compute_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _scrape_html(self, html: str) -> (str, Dict):
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        content = soup.get_text(separator=" ", strip=True)

        metadata = {
            "title": soup.title.string if soup.title else None,
            "description": (
                soup.find("meta", attrs={"name": "description"}) or {}
            ).get("content"),
            "author": (
                soup.find("meta", attrs={"name": "author"}) or {}
            ).get("content"),
            "content_type": "web_page",
        }

        return content, metadata

    # ------------------------------
    # Collection Logic
    # ------------------------------

    def collect_from_source(self, url: str, api_config: Dict = None) -> CollectedData:
        domain = self._extract_domain(url)

        if not self.whitelist.is_allowed(domain):
            self.audit_log.log(
                event_type="UNAUTHORIZED_ATTEMPT",
                details={"source": url}
            )
            raise UnauthorizedSourceError(f"{domain} not in whitelist")

        try:
            headers = {}
            if api_config and "api_key" in api_config:
                headers["Authorization"] = f"Bearer {api_config['api_key']}"
                headers.update(api_config.get("headers", {}))

            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")

            if "application/json" in content_type:
                data = response.json()
                content = str(data)
                metadata = {
                    "content_type": "api_response",
                    "format": "json"
                }
            else:
                try:
                    data = response.json()
                    content = str(data)
                    metadata = {
                        "content_type": "api_response",
                        "format": "json"
                    }
                except Exception:
                    content, metadata = self._scrape_html(response.text)
                    metadata["format"] = "text"

            content_hash = self._compute_content_hash(content)

            collected = CollectedData(
                content=content,
                source_domain=domain,
                document_url=url,
                publication_date=None,
                collection_timestamp=datetime.now(timezone.utc),
                content_hash=content_hash,
                metadata=metadata
            )

            self.audit_log.log(
                event_type="COLLECTION",
                details={
                    "source": url,
                    "content_hash": content_hash,
                    "metadata": {"success": True}
                }
            )

            return collected

        except requests.exceptions.Timeout:
            raise CollectionError("Request timeout")

        except Exception as e:
            self.audit_log.log(
                event_type="COLLECTION",
                details={
                    "source": url,
                    "metadata": {"success": False, "error": str(e)}
                }
            )
            raise CollectionError(f"Failed to scrape: {str(e)}")

    # ------------------------------
    # Bulk Collection
    # ------------------------------

    def collect_all(self) -> List[CollectedData]:
        results = []

        for source in self.whitelist.get_all_sources():
            try:
                results.append(
                    self.collect_from_source(source)
                )
            except Exception:
                continue

        return results

    # ------------------------------
    # Monitoring (Test-Safe Design)
    # ------------------------------

    def monitor_sources(
        self,
        interval: int = 60,
        max_cycles: Optional[int] = None
    ) -> Generator[CollectedData, None, None]:

        seen_hashes = set()
        cycles = 0

        while max_cycles is None or cycles < max_cycles:
            results = self.collect_all()

            for result in results:
                if result.content_hash not in seen_hashes:
                    seen_hashes.add(result.content_hash)
                    yield result

            cycles += 1
            time.sleep(interval)

    # ------------------------------
    # Context Management
    # ------------------------------

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()