"""
Database session management and CRUD helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterable, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Device, ApiEndpoint, ScanResult, AuthenticationMethod


def get_engine(database_url: str):
    # Pool tuning; avoid pooling for SQLite files
    if database_url.startswith("sqlite"):
        return create_engine(database_url, future=True)
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        future=True,
    )


def create_all(database_url: str) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def get_session_factory(database_url: str):
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(session_factory) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Basic CRUD examples
def create_device(session: Session, model: str, manufacturer: str, firmware_version: Optional[str] = None) -> Device:
    device = Device(model=model, manufacturer=manufacturer, firmware_version=firmware_version)
    session.add(device)
    session.flush()
    return device


def add_api_endpoint(
    session: Session,
    device_id: int,
    url: str,
    method: str = "GET",
    auth_required: bool = False,
    success_rate: float = 0.0,
) -> ApiEndpoint:
    endpoint = ApiEndpoint(
        device_id=device_id,
        url=url,
        method=method,
        auth_required=auth_required,
        success_rate=success_rate,
    )
    session.add(endpoint)
    session.flush()
    return endpoint

