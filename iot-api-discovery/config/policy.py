from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConsentPolicy:
    """Centralized consent gates for sensitive operations.

    All flags default to False. The core app should set these based on explicit
    user consent (ownership/authorization).
    """

    active_scan: bool = False
    sniffing: bool = False
    bluetooth: bool = False
    wifi: bool = False
    audio: bool = False
    image: bool = False

    def allows(self, feature: str) -> bool:
        return bool(getattr(self, feature, False))

