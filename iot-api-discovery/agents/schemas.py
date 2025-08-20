from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    platform: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None


class Endpoint(BaseModel):
    path: str
    method: Optional[str] = None
    source: Optional[str] = None
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    description: Optional[str] = None
    confidence: Optional[float] = None


class AuthenticationMethod(BaseModel):
    type: str
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    confidence: Optional[float] = None


class Example(BaseModel):
    language: Optional[str] = None
    code: str
    source: Optional[str] = None
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class DiscoveryResult(BaseModel):
    manufacturer: str
    model: Optional[str]
    sources: Dict[str, List[Dict[str, Any]]]
    endpoints: List[Endpoint]
    authentication_methods: List[AuthenticationMethod]
    examples: List[Example]

