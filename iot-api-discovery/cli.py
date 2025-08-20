from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Optional

from agents.documentation_hunter import DocumentationHunter, DocumentationHunterConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IoT API Documentation Hunter CLI")
    parser.add_argument("manufacturer", help="Device manufacturer name")
    parser.add_argument("--model", default=None, help="Device model name")
    parser.add_argument("--github-token", default=None, help="GitHub token for higher rate limits")
    parser.add_argument("--rate", type=float, default=2.0, help="Rate limit requests per second")
    parser.add_argument("--max-requests", type=int, default=10, help="Max concurrent requests")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING)")
    return parser


async def run(manufacturer: str, model: Optional[str], token: Optional[str], rate: float, max_requests: int) -> dict:
    logging.basicConfig(level=logging.getLevelName(logging.getLogger().level))
    config = DocumentationHunterConfig(
        github_token=token,
        rate_limit_per_second=rate,
        max_concurrent_requests=max_requests,
    )
    async with DocumentationHunter(manufacturer=manufacturer, model=model, config=config) as hunter:
        return await hunter.discover()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))
    result = asyncio.run(
        run(
            manufacturer=args.manufacturer,
            model=args.model,
            token=args.github_token,
            rate=args.rate,
            max_requests=args.max_requests,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

