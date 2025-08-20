from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


@dataclass
class DocumentationHunterConfig:
    github_token: Optional[str] = None
    request_timeout_seconds: int = 20
    max_concurrent_requests: int = 10
    max_retries: int = 3
    rate_limit_per_second: float = 2.0
    manufacturer_tlds: List[str] = None  # type: ignore[assignment]
    manufacturer_path_hints: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.manufacturer_tlds is None:
            self.manufacturer_tlds = [".com", ".io", ".net"]
        if self.manufacturer_path_hints is None:
            self.manufacturer_path_hints = [
                "/api",
                "/docs",
                "/developer",
                "/developers",
                "/support/api",
                "/support/developers",
            ]


class DocumentationHunter:
    def __init__(
        self,
        manufacturer: str,
        model: Optional[str] = None,
        config: Optional[DocumentationHunterConfig] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.manufacturer = manufacturer
        self.model = model
        self.config = config or DocumentationHunterConfig()
        self._session = session
        self._session_owner = session is None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

    async def __aenter__(self) -> "DocumentationHunter":
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_seconds)
            headers = {}
            if self.config.github_token:
                headers["Authorization"] = f"Bearer {self.config.github_token}"
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session and self._session_owner:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("ClientSession not initialized. Use 'async with DocumentationHunter(...)'.")
        return self._session

    async def discover(self) -> Dict[str, Any]:
        """
        Orchestrate discovery across sources and return structured results.

        Returns
        -------
        Dict[str, Any]
            Structured discovery data including endpoints, auth methods, and references.
        """
        logger.info("Starting documentation discovery for %s %s", self.manufacturer, self.model or "")
        results: Dict[str, Any] = {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "sources": {},
            "endpoints": [],
            "authentication_methods": [],
            "examples": [],
        }

        # Run discovery subtasks concurrently
        tasks = [self._search_github(), self._scrape_manufacturer_site(), self._search_forums()]

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for item in gathered:
            if isinstance(item, Exception):
                logger.warning("A discovery subtask failed: %s", item)
                continue
            # Merge partial results
            for key, value in item.items():
                if key in ("endpoints", "authentication_methods", "examples"):
                    results[key].extend(value)  # type: ignore[arg-type]
                elif key == "sources":
                    results["sources"].update(value)  # type: ignore[arg-type]
                else:
                    results[key] = value

        return results

    async def _rate_limited(self) -> None:
        await asyncio.sleep(1.0 / max(self.config.rate_limit_per_second, 0.1))

    async def _search_github(self) -> Dict[str, Any]:
        await self._rate_limited()
        logger.debug("Searching GitHub for %s %s", self.manufacturer, self.model or "")

        base_url = "https://api.github.com/search/repositories"
        query_terms: List[str] = [self.manufacturer]
        if self.model:
            query_terms.append(self.model)
        # Helpful qualifiers
        query_terms.extend(["integration OR plugin OR library", "(\"home assistant\" OR openhab OR iot)"])
        q = " ".join(query_terms)
        params = {"q": q, "per_page": 10, "sort": "stars", "order": "desc"}
        headers = {"Accept": "application/vnd.github+json"}

        repositories: List[Dict[str, Any]] = []
        try:
            data = await self._fetch_json("GET", base_url, params=params, headers=headers)
            for item in (data or {}).get("items", [])[:10]:
                repo = {
                    "name": item.get("full_name"),
                    "url": item.get("html_url"),
                    "stars": item.get("stargazers_count"),
                    "description": item.get("description"),
                    "updated_at": item.get("updated_at"),
                }
                repositories.append(repo)
        except Exception as exc:
            logger.warning("GitHub search failed: %s", exc)

        # Heuristic extraction of endpoints/auth from repository descriptions
        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []
        for repo in repositories:
            text = f"{repo.get('name','')} {repo.get('description','')}"
            extracted = self._extract_from_text(text, source=repo.get("url", "github"))
            endpoints.extend(extracted["endpoints"])  # type: ignore[index]
            auth_methods.extend(extracted["authentication_methods"])  # type: ignore[index]
            examples.extend(extracted["examples"])  # type: ignore[index]

        self._log_discoveries(endpoints, auth_methods, examples)

        return {
            "sources": {"github": repositories},
            "endpoints": endpoints,
            "authentication_methods": auth_methods,
            "examples": examples,
        }

    async def _scrape_manufacturer_site(self) -> Dict[str, Any]:
        await self._rate_limited()
        logger.debug("Scraping manufacturer site for %s %s", self.manufacturer, self.model or "")

        candidate_urls = self._build_candidate_manufacturer_urls()
        pages_scanned: List[Dict[str, Any]] = []
        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []

        async def scan_url(url: str) -> None:
            try:
                html = await self._fetch_text("GET", url)
            except Exception as exc:
                logger.debug("Manufacturer page fetch failed for %s: %s", url, exc)
                return
            soup = BeautifulSoup(html or "", "html.parser")
            text = soup.get_text("\n")
            extracted = self._extract_from_text(text, source=url)
            pages_scanned.append({"url": url, "found_endpoints": len(extracted["endpoints"])})
            endpoints.extend(extracted["endpoints"])  # type: ignore[index]
            auth_methods.extend(extracted["authentication_methods"])  # type: ignore[index]
            examples.extend(extracted["examples"])  # type: ignore[index]

        await asyncio.gather(*(scan_url(u) for u in candidate_urls))

        self._log_discoveries(endpoints, auth_methods, examples)

        return {
            "sources": {"manufacturer": pages_scanned},
            "endpoints": endpoints,
            "authentication_methods": auth_methods,
            "examples": examples,
        }

    async def _search_forums(self) -> Dict[str, Any]:
        await self._rate_limited()
        logger.debug("Searching forums for %s %s", self.manufacturer, self.model or "")

        query_terms: List[str] = [self.manufacturer]
        if self.model:
            query_terms.append(self.model)
        query = "+".join([t.strip().replace(" ", "+") for t in query_terms if t])

        forums = {
            "home-assistant": f"https://community.home-assistant.io/search.json?q={query}",
            "openhab": f"https://community.openhab.org/search.json?q={query}",
        }

        results: List[Dict[str, Any]] = []

        async def fetch_forum(name: str, url: str) -> None:
            try:
                data = await self._fetch_json("GET", url)
            except Exception as exc:
                logger.debug("Forum search failed for %s: %s", name, exc)
                return
            topics = (data or {}).get("topics", [])
            base = url.split("/search.json")[0]
            for t in topics[:10]:
                slug = t.get("slug")
                tid = t.get("id")
                created_at = t.get("created_at") or t.get("created_at_age")
                title = t.get("title")
                if not slug or not tid:
                    continue
                topic_url = f"{base}/t/{slug}/{tid}"
                results.append(
                    {
                        "platform": name,
                        "title": title,
                        "url": topic_url,
                        "created_at": created_at,
                    }
                )

        await asyncio.gather(*(fetch_forum(n, u) for n, u in forums.items()))

        # Extract endpoints/auth from titles as hints
        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []
        for item in results:
            text = f"{item.get('title','')}"
            extracted = self._extract_from_text(text, source=item.get("url", "forums"))
            endpoints.extend(extracted["endpoints"])  # type: ignore[index]
            auth_methods.extend(extracted["authentication_methods"])  # type: ignore[index]
            examples.extend(extracted["examples"])  # type: ignore[index]

        self._log_discoveries(endpoints, auth_methods, examples)

        return {
            "sources": {"forums": results},
            "endpoints": endpoints,
            "authentication_methods": auth_methods,
            "examples": examples,
        }

    # ---------------------- HTTP helpers with retry ----------------------
    async def _fetch_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        resp = await self._attempt_request(method, url, params=params, headers=headers)
        if resp is None:
            return {}
        try:
            return await resp.json()
        finally:
            await resp.release()

    async def _fetch_text(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        resp = await self._attempt_request(method, url, params=params, headers=headers)
        if resp is None:
            return ""
        try:
            return await resp.text()
        finally:
            await resp.release()

    async def _attempt_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[aiohttp.ClientResponse]:
        attempt = 0
        backoff_seconds = 1.0
        while attempt <= self.config.max_retries:
            async with self._semaphore:
                await self._rate_limited()
                try:
                    response = await self.session.request(method, url, params=params, headers=headers)
                except Exception as exc:
                    if attempt == self.config.max_retries:
                        logger.debug("Request failed for %s %s: %s", method, url, exc)
                        return None
                    await asyncio.sleep(backoff_seconds)
                    attempt += 1
                    backoff_seconds *= 2
                    continue

                if response.status in (429, 500, 502, 503, 504):
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds
                    await response.release()
                    if attempt == self.config.max_retries:
                        logger.debug("Non-200 status %s for %s, giving up", response.status, url)
                        return None
                    await asyncio.sleep(wait_seconds)
                    attempt += 1
                    backoff_seconds = min(backoff_seconds * 2, 30)
                    continue

                return response

        return None

    # ---------------------- Extraction helpers ----------------------
    def _extract_from_text(self, text: str, *, source: str) -> Dict[str, List[Dict[str, Any]]]:
        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []

        # Endpoint patterns: /api/... or /v1/... and full URLs with api segments
        path_pattern = re.compile(r"(?P<method>GET|POST|PUT|DELETE|PATCH|OPTIONS)?\s*(?P<path>/(?:api|v\d+)(?:/[A-Za-z0-9_\-\.]+)+)")
        url_pattern = re.compile(r"https?://[^\s\'\"]*(?:/api(?:/[^\s\'\"]*)*)")
        for match in path_pattern.finditer(text):
            path = match.group("path")
            method = match.group("method")
            endpoints.append(
                {
                    "path": path,
                    "method": method or None,
                    "source": source,
                    "discovered_at": datetime.utcnow().isoformat() + "Z",
                }
            )
        for match in url_pattern.finditer(text):
            endpoints.append(
                {
                    "path": match.group(0),
                    "method": None,
                    "source": source,
                    "discovered_at": datetime.utcnow().isoformat() + "Z",
                }
            )

        # Authentication hints
        auth_hints = {
            "oauth2": r"oauth\s*2(\.0)?|oauth2",
            "api_key": r"api\s*key|x-api-key|apikey",
            "basic": r"basic\s*auth",
            "bearer": r"bearer\s*token|authorization:\s*bearer",
            "jwt": r"jwt|json web token",
            "hmac": r"hmac|signature",
        }
        lowered = text.lower()
        for name, pattern in auth_hints.items():
            if re.search(pattern, lowered):
                auth_methods.append(
                    {
                        "type": name,
                        "details": None,
                        "source": source,
                        "discovered_at": datetime.utcnow().isoformat() + "Z",
                    }
                )

        # Example code snippets: detect curl or code fences
        code_snippets: List[str] = []
        for m in re.finditer(r"```[a-zA-Z0-9]*\n([\s\S]*?)```", text):
            snippet = m.group(1).strip()
            if snippet:
                code_snippets.append(snippet[:2000])
        for m in re.finditer(r"\bcurl\s+-[a-zA-Z]", text):
            # capture surrounding line
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 200)
            code_snippets.append(text[start:end])

        for snippet in code_snippets[:5]:
            examples.append(
                {
                    "language": "unknown",
                    "code": snippet,
                    "source": source,
                    "discovered_at": datetime.utcnow().isoformat() + "Z",
                }
            )

        return {
            "endpoints": endpoints,
            "authentication_methods": auth_methods,
            "examples": examples,
        }

    def _normalize_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
        return slug.strip("-")

    def _build_candidate_manufacturer_urls(self) -> List[str]:
        slug = self._normalize_slug(self.manufacturer)
        hosts = [f"{slug}{tld}" for tld in self.config.manufacturer_tlds]
        prefixes = ["www.", "docs.", "developer.", "developers.", "api.", "support."]
        urls: List[str] = []
        for host in hosts:
            for prefix in prefixes:
                base = f"https://{prefix}{host}"
                urls.append(base)
                for path in self.config.manufacturer_path_hints:
                    urls.append(base + path)
        # De-duplicate while preserving order
        seen: set[str] = set()
        ordered: List[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        # Limit to a reasonable number
        return ordered[:20]

    def _log_discoveries(
        self,
        endpoints: List[Dict[str, Any]],
        auth_methods: List[Dict[str, Any]],
        examples: List[Dict[str, Any]],
    ) -> None:
        timestamp = datetime.utcnow().isoformat() + "Z"
        for ep in endpoints:
            logger.info("[%s] endpoint: %s %s (source=%s)", timestamp, ep.get("method"), ep.get("path"), ep.get("source"))
        for am in auth_methods:
            logger.info("[%s] auth: %s (source=%s)", timestamp, am.get("type"), am.get("source"))
        for ex in examples[:5]:
            logger.info("[%s] example from %s", timestamp, ex.get("source"))