from __future__ import annotations

from typing import Any, Dict, List


def decode_barcodes(image_path: str) -> List[Dict[str, Any]]:
    """Decode QR codes and barcodes from an image file.

    Returns a list of {type, data, rect} entries. Best-effort if deps missing.
    """
    try:
        from PIL import Image  # type: ignore
        from pyzbar.pyzbar import decode  # type: ignore
    except Exception:
        return []

    try:
        img = Image.open(image_path)
        results = []
        for obj in decode(img):
            results.append(
                {
                    "type": getattr(obj, "type", None),
                    "data": getattr(obj, "data", b"").decode(errors="ignore"),
                    "rect": getattr(obj, "rect", None),
                }
            )
        return results
    except Exception:
        return []

