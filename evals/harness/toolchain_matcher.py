"""Matcher gele du sous-banc tool-chain : JSON et trace stricts, aucun contains."""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from elyne.contracts.hashing import InvalidInput, canonical_json_bytes, sha256_hex


MATCHER_SCHEMA = "elyne.eval.toolchain-matcher/v1"
DIMENSIONS = (
    "tool_1_selection", "tool_2_selection", "causal_order",
    "result_integration", "final_accuracy", "no_parasitic_calls",
)


def _strict_object(raw: str) -> dict[str, Any] | None:
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
    except (json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def normalized_exact_target(response_text: object, expected: str) -> bool:
    if not isinstance(response_text, str) or not isinstance(expected, str):
        return False
    document = _strict_object(response_text)
    if document is None or set(document) != {"target"} or not isinstance(document["target"], str):
        return False
    observed = unicodedata.normalize("NFC", document["target"].strip())
    wanted = unicodedata.normalize("NFC", expected.strip())
    return observed == wanted and document["target"] == observed


def canonical_arguments(value: object) -> bytes:
    if type(value) is not dict:
        raise InvalidInput("toolchain matcher: arguments objet exact requis.")
    return canonical_json_bytes(value)


def call_matches(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return (
        isinstance(observed, Mapping)
        and observed.get("tool_id") == expected.get("tool_id")
        and canonical_arguments(observed.get("arguments")) == canonical_arguments(expected.get("arguments"))
        and observed.get("outcome") == "completed"
    )


def score_toolchain(
    *, response_text: object, trace: Sequence[Mapping[str, Any]],
    expected_calls: Sequence[Mapping[str, Any]], final_token: str,
    tool_2_contains_target: bool,
) -> dict[str, bool]:
    if len(expected_calls) != 2:
        raise InvalidInput("toolchain matcher: deux appels attendus requis.")
    first = len(trace) >= 1 and call_matches(trace[0], expected_calls[0])
    second = len(trace) >= 2 and call_matches(trace[1], expected_calls[1])
    exact_final = normalized_exact_target(response_text, final_token)
    scores = {
        "tool_1_selection": bool(first),
        "tool_2_selection": bool(second),
        "causal_order": bool(first and second),
        "result_integration": bool(second and tool_2_contains_target and exact_final),
        "final_accuracy": exact_final,
        "no_parasitic_calls": len(trace) == 2,
    }
    if tuple(scores) != DIMENSIONS:
        raise InvalidInput("toolchain matcher: dimensions divergentes.")
    return scores


def matcher_identity_sha256() -> str:
    return sha256_hex(canonical_json_bytes({"schema": MATCHER_SCHEMA, "dimensions": list(DIMENSIONS), "response": "strict-json-exact-nfc/v1", "arguments": "canonical-json-exact/v1"}))


__all__ = ["DIMENSIONS", "MATCHER_SCHEMA", "matcher_identity_sha256", "normalized_exact_target", "score_toolchain"]
