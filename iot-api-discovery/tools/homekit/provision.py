from __future__ import annotations

from typing import Any, Dict


def begin_pairing_stub() -> Dict[str, Any]:
    """Placeholder for HomeKit (HAP) pairing, handled natively on iOS.

    Returns a stub with guidance to mobile layer.
    """
    return {"status": "not_implemented", "hint": "Use native iOS HAP pairing APIs"}

