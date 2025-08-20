from __future__ import annotations

import base64
from typing import Optional

from cryptography.fernet import Fernet, MultiFernet


def _get_fernet(key_b64: str) -> Fernet:
    key = key_b64.encode("utf-8")
    return Fernet(key)


def encrypt(secret: str, key_b64: str) -> str:
    f = _get_fernet(key_b64)
    return f.encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt(token: str, key_b64: str) -> str:
    f = _get_fernet(key_b64)
    return f.decrypt(token.encode("utf-8")).decode("utf-8")


def generate_key() -> str:
    return Fernet.generate_key().decode("utf-8")

