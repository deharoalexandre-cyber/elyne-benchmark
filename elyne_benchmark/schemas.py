from __future__ import annotations

from pathlib import Path
from typing import Any

from elyne.contracts.hashing import InvalidInput

from .common import ROOT, load_json


def validate_json_schema(document: Any, schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise InvalidInput("jsonschema is required; install requirements.lock") from exc
    schema = load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda e: list(e.path))
    except Exception as exc:
        raise InvalidInput(f"invalid JSON Schema: {schema_path.name}") from exc
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        raise InvalidInput(f"schema failure {schema_path.name} at {location}: {first.message}")


def schema_path(filename: str) -> Path:
    return ROOT / "evals" / "schemas" / filename

