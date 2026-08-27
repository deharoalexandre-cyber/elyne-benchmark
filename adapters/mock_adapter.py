"""Protocol smoke adapter. It is deliberately not a benchmark subject."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from elyne.contracts.hashing import canonical_json_bytes, sha256_hex  # noqa: E402

BINDING = hashlib.sha256(b"protocol-smoke-binding").hexdigest()
SAMPLING = hashlib.sha256(b"deterministic-greedy-seed-0").hexdigest()
MODES = {
    "justesse": {"core-origin": "substrate", "gemma-info": "information-only", "gemma-nu": "user-only"},
    "orchestration": {"core-origin": "substrate", "gemma-info": "raw-information-only", "gemma-nu": "user-only"},
    "toolchain": {"core-origin": "substrate", "gemma-info": "initial-information-only", "gemma-nu": "user-only"},
}


def main() -> int:
    request = json.load(sys.stdin)
    family, subject, case = request["family"], request["subject_id"], request["case"]
    response = "SMOKE-NO-MATCH"
    calls, trace = [], []
    if family == "toolchain" and subject == "core-origin":
        response = json.dumps({"target": case["final_token"]}, separators=(",", ":"))
        for ordinal, expected in enumerate(case["expected_calls"], 1):
            args = expected["arguments"]
            trace.append({
                "ordinal": ordinal,
                "tool_id": expected["tool_id"],
                "arguments": args,
                "outcome": "completed",
                "reason_code": None,
                "arguments_sha256": sha256_hex(canonical_json_bytes(args)),
                "result_sha256": hashlib.sha256(f"smoke-result-{ordinal}".encode()).hexdigest(),
                "target_line_attested": ordinal == 2,
            })
            calls.append(expected["tool_id"])
    elif family != "toolchain" and subject != "gemma-nu" and case["case_type"] != "judge":
        response = case["expected_match"]["value"]
        if case["case_type"] == "tool" and subject == "core-origin":
            calls.append(case["expects_tool"])
    elif case.get("case_type") == "judge":
        response = "Protocol smoke response; no research claim."
    observation = {
        "schema": "elyne.benchmark.adapter-observation/v1",
        "family": family,
        "item_id": request["item_id"],
        "subject_id": subject,
        "status": "completed",
        "reason_code": None,
        "response_text": response,
        "tool_calls": calls,
        "tool_trace": trace,
        "binding_sha256": BINDING,
        "sampling_sha256": SAMPLING,
        "context_mode": MODES[family][subject],
        "tools_declared": subject == "core-origin",
        "received_material_sha256": request["control_material_sha256"],
        "surfaced_information": case.get("substrate_setup", {}) if family == "justesse" and subject == "core-origin" else None,
    }
    json.dump(observation, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

