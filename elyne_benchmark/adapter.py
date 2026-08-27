from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from elyne.contracts.hashing import InvalidInput

from .common import ROOT, SUBJECTS, hash_document


CONTEXT_MODES = {
    "justesse": {
        "core-origin": "substrate",
        "gemma-info": "information-only",
        "gemma-nu": "user-only",
    },
    "orchestration": {
        "core-origin": "substrate",
        "gemma-info": "raw-information-only",
        "gemma-nu": "user-only",
    },
    "toolchain": {
        "core-origin": "substrate",
        "gemma-info": "initial-information-only",
        "gemma-nu": "user-only",
    },
}


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise InvalidInput(f"{label} must be a lowercase sha256")
    return value


def validate_observation(
    value: object,
    *,
    family: str,
    item_id: str,
    subject_id: str,
    material: object | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput("adapter observation must be an object")
    required = {
        "schema", "family", "item_id", "subject_id", "status", "reason_code",
        "response_text", "tool_calls", "tool_trace", "binding_sha256",
        "sampling_sha256", "context_mode", "tools_declared",
        "received_material_sha256", "surfaced_information",
    }
    if set(value) != required:
        raise InvalidInput("adapter observation has an open or incomplete shape")
    if value["schema"] != "elyne.benchmark.adapter-observation/v1":
        raise InvalidInput("adapter observation schema mismatch")
    if (value["family"], value["item_id"], value["subject_id"]) != (family, item_id, subject_id):
        raise InvalidInput("adapter observation identity mismatch")
    if subject_id not in SUBJECTS:
        raise InvalidInput("unknown subject arm")
    if value["context_mode"] != CONTEXT_MODES[family][subject_id]:
        raise InvalidInput("adapter context mode mismatch")
    _sha(value["binding_sha256"], "binding_sha256")
    _sha(value["sampling_sha256"], "sampling_sha256")
    if value["status"] not in {"completed", "failed"}:
        raise InvalidInput("adapter status mismatch")
    if value["status"] == "completed":
        if value["reason_code"] is not None or not isinstance(value["response_text"], str):
            raise InvalidInput("completed adapter observation is malformed")
    elif not isinstance(value["reason_code"], str) or value["response_text"] is not None:
        raise InvalidInput("failed adapter observation is malformed")
    if not isinstance(value["tool_calls"], list) or any(not isinstance(x, str) for x in value["tool_calls"]):
        raise InvalidInput("tool_calls must be a string list")
    if not isinstance(value["tool_trace"], list) or not isinstance(value["tools_declared"], bool):
        raise InvalidInput("tool trace/declaration mismatch")
    if subject_id != "core-origin" and (value["tools_declared"] or value["tool_calls"] or value["tool_trace"]):
        raise InvalidInput("direct control arms cannot expose tools")
    expected_material = None if material is None else hash_document(material)
    if value["received_material_sha256"] != expected_material:
        raise InvalidInput("control material hash was not echoed exactly")
    if subject_id == "core-origin" and family == "justesse":
        if not isinstance(value["surfaced_information"], dict):
            raise InvalidInput("justesse core must expose the exact information replayed to gemma-info")
    elif value["surfaced_information"] is not None:
        raise InvalidInput("surfaced_information attached to an unsupported arm")
    return value


def invoke_adapter(command: Sequence[str], request: Mapping[str, Any], *, timeout_seconds: int) -> dict[str, Any]:
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise InvalidInput("adapter command must be a non-empty argv array")
    try:
        completed = subprocess.run(
            list(command),
            input=json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
            shell=False,
            cwd=ROOT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidInput(f"adapter process failed: {type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise InvalidInput(f"adapter returned {completed.returncode}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InvalidInput("adapter stdout is not one strict JSON document") from exc
    if not isinstance(value, dict):
        raise InvalidInput("adapter stdout JSON root must be an object")
    return value


def load_adapter_config(path: Path) -> dict[str, Sequence[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidInput("cannot load adapter config") from exc
    if not isinstance(value, dict) or value.get("schema") != "elyne.benchmark.adapter-config/v1":
        raise InvalidInput("adapter config schema mismatch")
    commands = value.get("commands")
    if not isinstance(commands, dict) or set(commands) != set(SUBJECTS):
        raise InvalidInput("adapter config must define the exact three arms")
    for subject, command in commands.items():
        if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
            raise InvalidInput(f"invalid adapter command for {subject}")
    return commands
