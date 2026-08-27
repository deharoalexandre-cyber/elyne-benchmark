from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from elyne.contracts.hashing import InvalidInput, canonical_json_bytes, sha256_hex


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("justesse", "orchestration", "toolchain")
SUBJECTS = ("core-origin", "gemma-info", "gemma-nu")


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise InvalidInput(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidInput(f"cannot read strict JSON: {path}") from exc
    if not isinstance(value, dict):
        raise InvalidInput(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
    except OSError as exc:
        raise InvalidInput(f"cannot hash file: {path}") from exc
    return digest.hexdigest()


def safe_relative(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise InvalidInput("relative POSIX path required")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise InvalidInput("path escapes its declared root") from exc
    return candidate


def load_battery(family: str) -> tuple[dict[str, Any], Path]:
    if family not in FAMILIES:
        raise InvalidInput(f"unknown benchmark family: {family}")
    path = ROOT / "evals" / "fixtures" / f"{family}.battery.json"
    battery = load_json(path)
    if battery.get("id") != family or not isinstance(battery.get("cases"), list):
        raise InvalidInput(f"invalid {family} battery envelope")
    return battery, path


def match_satisfied(rule: Mapping[str, Any] | None, response: object) -> bool:
    if rule is None or not isinstance(response, str):
        return False
    if rule.get("normalization") != "unicode-nfc-trim/v1":
        raise InvalidInput("unsupported normalization")
    expected = unicodedata.normalize("NFC", str(rule.get("value", "")).strip())
    observed = unicodedata.normalize("NFC", response.strip())
    if rule.get("case_sensitive") is False:
        expected, observed = expected.casefold(), observed.casefold()
    mode = rule.get("mode")
    if mode == "contains":
        return expected in observed
    if mode == "exact":
        return expected == observed
    raise InvalidInput(f"unsupported match mode: {mode}")


def hash_document(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def write_canonical_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(value))
    except FileExistsError as exc:
        raise InvalidInput(f"refusing to overwrite: {path}") from exc

