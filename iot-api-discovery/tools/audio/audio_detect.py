from __future__ import annotations

from typing import Any, Dict, List


def list_audio_devices() -> List[Dict[str, Any]]:
    """List audio input devices (best-effort), without recording.

    Requires sounddevice/pyaudio depending on platform; returns [] if unavailable.
    """
    try:
        import sounddevice as sd  # type: ignore
    except Exception:
        return []
    devices = []
    try:
        for d in sd.query_devices():
            if d.get("max_input_channels", 0) > 0:
                devices.append({"name": d.get("name"), "hostapi": d.get("hostapi"), "channels": d.get("max_input_channels")})
    except Exception:
        return []
    return devices

