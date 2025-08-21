from __future__ import annotations

from typing import Dict, Type, Any

from .schemas import CapabilityType


class AdapterRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Dict[CapabilityType, Any]] = {}

    def register(self, provider: str, capability: CapabilityType, adapter: Any) -> None:
        p = provider.lower()
        self._registry.setdefault(p, {})[capability] = adapter

    def get(self, provider: str, capability: CapabilityType) -> Any | None:
        return self._registry.get(provider.lower(), {}).get(capability)

    def capabilities_for(self, provider: str) -> Dict[CapabilityType, Any]:
        return dict(self._registry.get(provider.lower(), {}))


registry = AdapterRegistry()

