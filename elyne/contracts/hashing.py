"""Small public subset of Elyne's canonical hashing contract.

This module intentionally contains no runtime, memory, inference, or identity code.
It only keeps the copied benchmark sources and the frozen matcher executable.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


class InvalidInput(ValueError):
    """Closed-contract input error."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidInput("value is not canonical-JSON serializable") from exc
    return rendered.encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise InvalidInput("sha256_hex requires bytes")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["InvalidInput", "canonical_json_bytes", "sha256_hex"]

