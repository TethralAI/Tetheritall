from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple
import time
from urllib.parse import urlparse, urljoin
import urllib.robotparser as robotparser

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel

from .schemas import DiscoveryResult, Endpoint, AuthenticationMethod, Example


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
    serpapi_key: Optional[str] = None
    per_domain_rate_limit_per_second: float = 1.0
    respect_robots_txt: bool = True
    user_agent: str = "IoT-API-Discovery/1.0 (+github.com/example)"

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
        self._domain_last_request_time: Dict[str, float] = {}
        self._robots_parsers: Dict[str, robotparser.RobotFileParser] = {}
        self._cache_text: Dict[str, Dict[str, Any]] = {}
        self._cache_json: Dict[str, Dict[str, Any]] = {}

    async def __aenter__(self) -> "DocumentationHunter":
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_seconds)
            headers = {"User-Agent": self.config.user_agent}
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

        tasks = [self._search_github(), self._scrape_manufacturer_site(), self._search_forums()]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for item in gathered:
            if isinstance(item, Exception):
                logger.warning("A discovery subtask failed: %s", item)
                continue
            for key, value in item.items():
                if key in ("endpoints", "authentication_methods", "examples"):
                    results[key].extend(value)  # type: ignore[arg-type]
                elif key == "sources":
                    results["sources"].update(value)  # type: ignore[arg-type]
                else:
                    results[key] = value

        dr = DiscoveryResult(
            manufacturer=results["manufacturer"],
            model=results["model"],
            sources=results["sources"],
            endpoints=[Endpoint(**e) for e in results["endpoints"]],
            authentication_methods=[AuthenticationMethod(**a) for a in results["authentication_methods"]],
            examples=[Example(**ex) for ex in results["examples"]],
        )
        return dr.model_dump()

    async def _rate_limited(self) -> None:
        await asyncio.sleep(1.0 / max(self.config.rate_limit_per_second, 0.1))

    async def _domain_rate_limit(self, url: str) -> None:
        if self.config.per_domain_rate_limit_per_second <= 0:
            return
        domain = urlparse(url).netloc
        now = time.monotonic()
        min_interval = 1.0 / self.config.per_domain_rate_limit_per_second
        last = self._domain_last_request_time.get(domain)
        if last is not None:
            elapsed = now - last
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        self._domain_last_request_time[domain] = time.monotonic()

    async def _search_github(self) -> Dict[str, Any]:
        await self._rate_limited()
        logger.debug("Searching GitHub for %s %s", self.manufacturer, self.model or "")

        base_url = "https://api.github.com/search/repositories"
        query_terms: List[str] = [self.manufacturer]
        if self.model:
            query_terms.append(self.model)
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
            if self.config.respect_robots_txt and not await self._is_allowed_by_robots(url):
                pages_scanned.append({"url": url, "skipped": "robots_txt"})
                return
            try:
                html = await self._fetch_text("GET", url)
            except Exception as exc:
                logger.debug("Manufacturer page fetch failed for %s: %s", url, exc)
                return
            soup = BeautifulSoup(html or "", "html.parser")
            text = soup.get_text("\n")
            extracted = self._extract_from_text(text, source=url)

            api_links = self._find_api_spec_links(soup, base_url=url)
            for link in api_links:
                spec_endpoints, spec_auth = await self._fetch_and_parse_api_spec(link)
                for ep in spec_endpoints:
                    endpoints.append(ep)
                for am in spec_auth:
                    auth_methods.append(am)

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

        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []
        for item in results:
            text = f"{item.get('title','')}"
            extracted = self._extract_from_text(text, source=item.get("url", "forums"))
            endpoints.extend(extracted["endpoints"])  # type: ignore[index]
            auth_methods.extend(extracted["authentication_methods"])  # type: ignore[index]
            examples.extend(extracted["examples"])  # type: ignore[index]

        async def enrich_forum_items(items: List[Dict[str, Any]]) -> None:
            async def fetch_body(item: Dict[str, Any]) -> None:
                try:
                    url = item.get("url", "")
                    if not url:
                        return
                    parts = url.rstrip("/").split("/")
                    tid = parts[-1]
                    topic_json_url = "/".join(parts[:-2]) + f"/t/{tid}.json"
                    data = await self._fetch_json("GET", topic_json_url)
                    if not data:
                        return
                    posts = data.get("post_stream", {}).get("posts", [])
                    if posts:
                        cooked = posts[0].get("cooked") or ""
                        text = BeautifulSoup(cooked, "html.parser").get_text("\n")
                        extracted = self._extract_from_text(text, source=item.get("url", "forums"))
                        endpoints.extend(extracted["endpoints"])  # type: ignore[index]
                        auth_methods.extend(extracted["authentication_methods"])  # type: ignore[index]
                        examples.extend(extracted["examples"])  # type: ignore[index]
                except Exception:
                    return

            await asyncio.gather(*(fetch_body(it) for it in items[:5]))

        await enrich_forum_items(results)

        self._log_discoveries(endpoints, auth_methods, examples)

        return {
            "sources": {"forums": results},
            "endpoints": endpoints,
            "authentication_methods": auth_methods,
            "examples": examples,
        }

    async def _fetch_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        effective_headers = dict(headers or {})
        cache_entry = self._cache_json.get(url)
        if cache_entry:
            if etag := cache_entry.get("etag"):
                effective_headers["If-None-Match"] = etag
            if last_mod := cache_entry.get("last_modified"):
                effective_headers["If-Modified-Since"] = last_mod
        await self._domain_rate_limit(url)
        resp = await self._attempt_request(method, url, params=params, headers=effective_headers)
        if resp is None:
            return cache_entry.get("data", {}) if cache_entry else {}
        try:
            if resp.status == 304 and cache_entry:
                return cache_entry.get("data", {})
            data = await resp.json()
            self._cache_json[url] = {
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "data": data,
            }
            return data
        finally:
            await resp.release()

    async def _fetch_text(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        skip_robots: bool = False,
    ) -> str:
        if self.config.respect_robots_txt and not skip_robots:
            allowed = await self._is_allowed_by_robots(url)
            if not allowed:
                raise PermissionError(f"robots.txt disallows fetching {url}")
        effective_headers = dict(headers or {})
        cache_entry = self._cache_text.get(url)
        if cache_entry:
            if etag := cache_entry.get("etag"):
                effective_headers["If-None-Match"] = etag
            if last_mod := cache_entry.get("last_modified"):
                effective_headers["If-Modified-Since"] = last_mod
        await self._domain_rate_limit(url)
        resp = await self._attempt_request(method, url, params=params, headers=effective_headers)
        if resp is None:
            return cache_entry.get("text", "") if cache_entry else ""
        try:
            if resp.status == 304 and cache_entry:
                return cache_entry.get("text", "")
            text = await resp.text()
            self._cache_text[url] = {
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "text": text,
            }
            return text
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

    async def _is_allowed_by_robots(self, url: str) -> bool:
        if not self.config.respect_robots_txt:
            return True
        parsed = urlparse(url)
        domain = parsed.netloc
        rp = self._robots_parsers.get(domain)
        if rp is None:
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            try:
                content = await self._fetch_text("GET", robots_url, skip_robots=True)
            except Exception:
                self._robots_parsers[domain] = robotparser.RobotFileParser()
                self._robots_parsers[domain].parse("")
                return True
            rp = robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.parse(content.splitlines())
            self._robots_parsers[domain] = rp
        return rp.can_fetch(self.config.user_agent, url)

    def _extract_from_text(self, text: str, *, source: str) -> Dict[str, List[Dict[str, Any]]]:
        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []
        examples: List[Dict[str, Any]] = []

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

        code_snippets: List[str] = []
        for m in re.finditer(r"```[a-zA-Z0-9]*\n([\s\S]*?)```", text):
            snippet = m.group(1).strip()
            if snippet:
                code_snippets.append(snippet[:2000])
        for m in re.finditer(r"\bcurl\s+-[a-zA-Z]", text):
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
        seen: set[str] = set()
        ordered: List[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
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

    def _find_api_spec_links(self, soup: BeautifulSoup, *, base_url: str) -> List[str]:
        patterns = [
            re.compile(r"openapi\.(json|yaml|yml)$", re.I),
            re.compile(r"swagger\.(json|yaml|yml)$", re.I),
            re.compile(r"postman(_collection)?\.(json)$", re.I),
            re.compile(r"/openapi\.json$", re.I),
            re.compile(r"/swagger\.json$", re.I),
        ]
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            for pat in patterns:
                if pat.search(href):
                    if href.startswith("http"):
                        links.append(href)
                    else:
                        try:
                            links.append(urljoin(base_url, href))
                        except Exception:
                            continue
                    break
        return links[:10]

    async def _fetch_and_parse_api_spec(self, url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        try:
            text = await self._fetch_text("GET", url)
        except Exception as exc:
            logger.debug("Failed to fetch API spec %s: %s", url, exc)
            return [], []

        try:
            import json as _json
            import yaml as _yaml

            data: Dict[str, Any]
            if url.endswith((".yaml", ".yml")):
                data = _yaml.safe_load(text)  # type: ignore[assignment]
            else:
                data = _json.loads(text)
        except Exception as exc:
            logger.debug("Failed to parse API spec %s: %s", url, exc)
            return [], []

        endpoints: List[Dict[str, Any]] = []
        auth_methods: List[Dict[str, Any]] = []

        if "paths" in data:
            for path, methods in data.get("paths", {}).items():
                if not isinstance(methods, dict):
                    continue
                for method, op in methods.items():
                    if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                        continue
                    endpoints.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "source": url,
                            "discovered_at": datetime.utcnow().isoformat() + "Z",
                            "description": (op or {}).get("summary"),
                        }
                    )

        components = data.get("components", {}) if isinstance(data, dict) else {}
        security_schemes = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
        for name, scheme in security_schemes.items() if isinstance(security_schemes, dict) else []:
            t = (scheme or {}).get("type")
            details = {k: v for k, v in (scheme or {}).items() if k != "type"}
            auth_methods.append(
                {
                    "type": str(t) if t else name,
                    "details": details,
                    "source": url,
                    "discovered_at": datetime.utcnow().isoformat() + "Z",
                }
            )

        return endpoints, auth_methods