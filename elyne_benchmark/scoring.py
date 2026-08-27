from __future__ import annotations

from typing import Any, Mapping

from elyne.contracts.hashing import InvalidInput, canonical_json_bytes, sha256_hex
from evals.harness.toolchain_matcher import DIMENSIONS, score_toolchain

from .common import SUBJECTS, match_satisfied


REPORT_KEYS = {"core-origin": "core_origin", "gemma-info": "gemma_info", "gemma-nu": "gemma_nu"}


def _scored_standard(family: str, case: Mapping[str, Any], observation: Mapping[str, Any]) -> dict[str, Any]:
    subject = observation["subject_id"]
    completed = observation["status"] == "completed"
    response = observation["response_text"]
    grounded = None
    expected_tool_called = None
    passed = None
    if case["case_type"] == "objective":
        rule = "expected-match"
        passed = match_satisfied(case["expected_match"], response) if completed else None
    elif case["case_type"] == "tool":
        grounded = match_satisfied(case["expected_match"], response) if completed else None
        if family == "justesse" and subject == "gemma-info":
            rule = "grounding-only"
            passed = grounded if completed else None
        elif family == "orchestration" and subject != "core-origin":
            rule = "action-unavailable"
            passed = False if completed else None
        else:
            rule = "tool-call-plus-grounding"
            expected_tool_called = case["expects_tool"] in observation["tool_calls"] if completed else None
            passed = bool(expected_tool_called and grounded) if completed else None
    elif case["case_type"] == "judge":
        rule = "judge-pending"
    else:
        raise InvalidInput("unsupported case_type")
    return {
        "subject_id": subject,
        "status": observation["status"],
        "reason_code": observation["reason_code"],
        "response_text": response,
        "response_sha256": sha256_hex(response.encode("utf-8")) if isinstance(response, str) else None,
        "tool_calls": observation["tool_calls"],
        "scoring_rule": rule,
        "expected_tool_called": expected_tool_called,
        "grounded": grounded,
        "passed": passed,
        "binding_sha256": observation["binding_sha256"],
        "sampling_sha256": observation["sampling_sha256"],
    }


def _scored_toolchain(case: Mapping[str, Any], observation: Mapping[str, Any]) -> dict[str, Any]:
    trace = observation["tool_trace"]
    tool_2_attested = len(trace) >= 2 and trace[1].get("target_line_attested") is True
    dimensions = score_toolchain(
        response_text=observation["response_text"],
        trace=trace,
        expected_calls=case["expected_calls"],
        final_token=case["final_token"],
        tool_2_contains_target=tool_2_attested,
    ) if observation["status"] == "completed" else {name: False for name in DIMENSIONS}
    response = observation["response_text"]
    return {
        "subject_id": observation["subject_id"],
        "status": observation["status"],
        "reason_code": observation["reason_code"],
        "response_text": response,
        "response_sha256": sha256_hex(response.encode("utf-8")) if isinstance(response, str) else None,
        "tool_trace": trace,
        "dimensions": dimensions,
        "passed": all(dimensions.values()),
        "binding_sha256": observation["binding_sha256"],
        "sampling_sha256": observation["sampling_sha256"],
        "context_mode": observation["context_mode"],
        "tools_declared": observation["tools_declared"],
    }


def _aggregate(items: list[dict[str, Any]], *, group: str, toolchain: bool) -> dict[str, Any]:
    scored = [item for item in items if item.get("scoring") != "judge" and all(item[REPORT_KEYS[s]]["status"] == "completed" for s in SUBJECTS)]
    counts = {REPORT_KEYS[s]: sum(item[REPORT_KEYS[s]]["passed"] is True for item in scored) for s in SUBJECTS}
    denominator = len(scored)
    rates = {key: (value / denominator if denominator else None) for key, value in counts.items()}
    result = {
        "group": group,
        "items": len(items),
        "scored_items": denominator,
        "noncomplete": sum(any(item[REPORT_KEYS[s]]["status"] != "completed" for s in SUBJECTS) for item in items),
        "successes": counts,
        "rates": rates,
        "deltas": {
            "substrate": rates["core_origin"] - rates["gemma_nu"] if denominator else None,
            "orchestration": rates["core_origin"] - rates["gemma_info"] if denominator else None,
            "access": rates["gemma_info"] - rates["gemma_nu"] if denominator else None,
        },
    }
    if toolchain:
        result["dimension_rates"] = {
            dimension: {
                REPORT_KEYS[s]: (
                    sum(item[REPORT_KEYS[s]]["dimensions"][dimension] for item in scored) / denominator
                    if denominator else None
                )
                for s in SUBJECTS
            }
            for dimension in DIMENSIONS
        }
    return result


def build_replication_report(
    *,
    family: str,
    campaign_id: str,
    battery: Mapping[str, Any],
    battery_sha256: str,
    observations: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    items = []
    bindings, samplings = set(), set()
    for case in battery["cases"]:
        arms = observations[case["id"]]
        if set(arms) != set(SUBJECTS):
            raise InvalidInput("incomplete arm triplet")
        for arm in arms.values():
            bindings.add(arm["binding_sha256"]); samplings.add(arm["sampling_sha256"])
        scored = {
            subject: (_scored_toolchain(case, arms[subject]) if family == "toolchain" else _scored_standard(family, case, arms[subject]))
            for subject in SUBJECTS
        }
        item = {
            "id": case["id"],
            "group": case.get("category") or case.get("property") or case.get("pattern"),
            "case_sha256": sha256_hex(canonical_json_bytes(case)),
            **{REPORT_KEYS[s]: scored[s] for s in SUBJECTS},
        }
        if family != "toolchain":
            item["scoring"] = case["case_type"]
        items.append(item)
    if len(bindings) != 1 or len(samplings) != 1:
        raise InvalidInput("fairness failure: all arms and cases must share one binding and sampling identity")
    groups = sorted({item["group"] for item in items})
    return {
        "schema": "elyne.benchmark.public-replication-report/v1",
        "status": "completed" if all(arm["status"] == "completed" for item in items for arm in (item["core_origin"], item["gemma_info"], item["gemma_nu"])) else "noncomplete",
        "family": family,
        "campaign_id": campaign_id,
        "seed": 0,
        "battery": {"id": battery["id"], "revision": battery["revision"], "sha256": battery_sha256, "source_sha256": battery["source"]["sha256"]},
        "subjects": list(SUBJECTS),
        "fairness": {"same_binding_identity": True, "same_sampling": True, "same_seed": True, "control_material_hash_echoed": True},
        "items": items,
        "groups": [_aggregate([item for item in items if item["group"] == group], group=group, toolchain=family == "toolchain") for group in groups],
        "overall": _aggregate(items, group="all", toolchain=family == "toolchain"),
    }

