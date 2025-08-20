from __future__ import annotations

from dataclasses import dataclass
import os


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
    testing_mode: bool = False

    def allows(self, feature: str) -> bool:
        # If testing mode is enabled, all features are allowed implicitly.
        if self.testing_mode or os.getenv("IOT_DISCOVERY_TESTING", "").lower() in ("1", "true", "yes"): 
            return True
        return bool(getattr(self, feature, False))

