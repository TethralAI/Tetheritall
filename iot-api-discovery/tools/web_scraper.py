from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import aiohttp
from bs4 import BeautifulSoup


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def parse_html_for_endpoints(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    return {"endpoints": [], "text_sample": text[:1000]}

