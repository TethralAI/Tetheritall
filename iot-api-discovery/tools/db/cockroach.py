from __future__ import annotations

from typing import Any
from sqlalchemy import create_engine


def make_cockroach_engine(url: str):
    """Create a CockroachDB engine via SQLAlchemy.

    Example URL: postgresql+psycopg2://user:pass@host:26257/db?sslmode=require
    """
    return create_engine(url, pool_pre_ping=True, future=True)

