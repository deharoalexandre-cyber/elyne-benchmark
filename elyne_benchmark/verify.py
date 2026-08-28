from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from elyne.contracts.hashing import InvalidInput, sha256_hex
from evals.harness.toolchain_matcher import DIMENSIONS, score_toolchain

from .common import FAMILIES, ROOT, load_battery, load_json, match_satisfied, safe_relative, sha256_file
from .schemas import schema_path, validate_json_schema


REFERENCE_RUNS = {
    "justesse": "9177fc4da44232f91e71eccf3e4e84e0",
    "orchestration": "57ac0b2c3de9a18f0bdfaf9d22254eaa",
    "toolchain": "4fdfa915f8ff6ec20b688ac3b298e5cf",
}
REPORT_SCHEMAS = {
    "justesse": "justesse-report.schema.json",
    "orchestration": "orchestration-report.schema.json",
    "toolchain": "toolchain-report.schema.json",
}
ARM_KEYS = ("core_origin", "gemma_info", "gemma_nu")


def _verify_fixture(family: str) -> tuple[dict[str, Any], Path]:
    battery, battery_path = load_battery(family)
    catalog_path = ROOT / "evals" / "catalogs" / f"{family}.json"
    catalog = load_json(catalog_path)
    validate_json_schema(catalog, schema_path("probe-catalog.schema.json"))
    validate_json_schema(battery, schema_path(f"fixture-{family}.schema.json"))
    linkage = battery.get("catalog", {})
    if linkage.get("id") != catalog.get("id") or linkage.get("revision") != catalog.get("revision"):
        raise InvalidInput(f"{family}: catalog identity mismatch")
    if linkage.get("sha256") != sha256_file(catalog_path):
        raise InvalidInput(f"{family}: catalog hash mismatch")
    source = safe_relative(ROOT, battery["source"]["module"])
    if sha256_file(source) != battery["source"]["sha256"]:
        raise InvalidInput(f"{family}: source hash mismatch")
    if family == "toolchain":
        matcher = safe_relative(ROOT, battery["matcher"]["module"])
        if sha256_file(matcher) != battery["matcher"]["sha256"]:
            raise InvalidInput("toolchain: frozen matcher hash mismatch")
    return battery, battery_path


def _verify_response_hashes(report: Mapping[str, Any]) -> None:
    for item in report["items"]:
        for key in ARM_KEYS:
            arm = item[key]
            response = arm["response_text"]
            expected = sha256_hex(response.encode("utf-8")) if isinstance(response, str) else None
            if arm["response_sha256"] != expected:
                raise InvalidInput(f"{item['id']}/{key}: response hash mismatch")


def _verify_evidence(run_dir: Path, report: Mapping[str, Any]) -> None:
    for item in report["items"]:
        for reference in item["evidence"].values():
            path = safe_relative(run_dir, reference["relative_path"])
            if not path.is_file():
                raise InvalidInput(f"missing public evidence: {reference['relative_path']}")
            if path.stat().st_size != reference["size_bytes"] or sha256_file(path) != reference["sha256"]:
                raise InvalidInput(f"evidence commitment mismatch: {reference['relative_path']}")


def _rescore_standard(family: str, battery: Mapping[str, Any], report: Mapping[str, Any]) -> None:
    cases = {case["id"]: case for case in battery["cases"]}
    for item in report["items"]:
        case = cases[item["id"]]
        for key in ARM_KEYS:
            arm = item[key]
            if arm["status"] != "completed" or case["case_type"] == "judge":
                expected = None
            elif case["case_type"] == "objective":
                expected = match_satisfied(case["expected_match"], arm["response_text"])
            elif family == "justesse" and key == "gemma_info":
                expected = match_satisfied(case["expected_match"], arm["response_text"])
            elif family == "orchestration":
                trace = arm["tool_trace"]
                chain = case["toolchain"]
                dimensions = score_toolchain(
                    response_text=arm["response_text"],
                    trace=trace,
                    expected_calls=chain["expected_calls"],
                    final_token=chain["final_token"],
                    tool_2_contains_target=(
                        len(trace) >= 2
                        and trace[1]["target_line_attested"] is True
                    ),
                )
                if arm["dimensions"] != dimensions:
                    raise InvalidInput(
                        f"orchestration/{item['id']}/{key}: causal dimensions mismatch"
                    )
                expected = all(dimensions.values())
            else:
                expected = (
                    case["expects_tool"] in arm["tool_calls"]
                    and match_satisfied(case["expected_match"], arm["response_text"])
                )
            if arm["passed"] != expected:
                raise InvalidInput(f"{family}/{item['id']}/{key}: published score mismatch")


def _rescore_toolchain(battery: Mapping[str, Any], report: Mapping[str, Any]) -> None:
    cases = {case["id"]: case for case in battery["cases"]}
    for item in report["items"]:
        case = cases[item["id"]]
        for key in ARM_KEYS:
            arm = item[key]
            trace = arm["tool_trace"]
            dimensions = score_toolchain(
                response_text=arm["response_text"],
                trace=trace,
                expected_calls=case["expected_calls"],
                final_token=case["final_token"],
                tool_2_contains_target=len(trace) >= 2 and trace[1]["target_line_attested"] is True,
            )
            if dimensions != arm["dimensions"] or arm["passed"] != all(dimensions.values()):
                raise InvalidInput(f"toolchain/{item['id']}/{key}: frozen matcher mismatch")


def _verify_overall(report: Mapping[str, Any]) -> None:
    scored = [
        item for item in report["items"]
        if item.get("scoring") != "judge" and all(item[key]["status"] == "completed" for key in ARM_KEYS)
    ]
    expected_counts = {key: sum(item[key]["passed"] is True for item in scored) for key in ARM_KEYS}
    overall = report["overall"]
    if overall["scored_items"] != len(scored) or overall["successes"] != expected_counts:
        raise InvalidInput("published aggregate counts mismatch")
    for key, count in expected_counts.items():
        expected_rate = count / len(scored) if scored else None
        if overall["rates"][key] != expected_rate:
            raise InvalidInput("published aggregate rate mismatch")


def verify_reference_run(family: str) -> dict[str, Any]:
    battery, battery_path = _verify_fixture(family)
    run_dir = ROOT / "runs" / "reference" / family / REFERENCE_RUNS[family]
    report_path = run_dir / "report.json"
    report = load_json(report_path)
    validate_json_schema(report, schema_path(REPORT_SCHEMAS[family]))
    if report["battery"]["sha256"] != sha256_file(battery_path):
        raise InvalidInput(f"{family}: report/battery hash mismatch")
    if report["battery"]["source_sha256"] != battery["source"]["sha256"]:
        raise InvalidInput(f"{family}: report/source hash mismatch")
    if len(report["items"]) != len(battery["cases"]):
        raise InvalidInput(f"{family}: report item count mismatch")
    _verify_response_hashes(report)
    _verify_evidence(run_dir, report)
    if family == "toolchain":
        _rescore_toolchain(battery, report)
        manifest = load_json(run_dir / "campaign-manifest.json")
        if manifest["report"]["sha256"] != sha256_file(report_path):
            raise InvalidInput("toolchain campaign manifest mismatch")
    else:
        if family == "orchestration":
            matcher_path = ROOT / "evals" / "harness" / "toolchain_matcher.py"
            if report["matcher"]["source_sha256"] != sha256_file(matcher_path):
                raise InvalidInput("orchestration matcher commitment mismatch")
        _rescore_standard(family, battery, report)
        key_path = run_dir / "judge-key.json"
        load_json(key_path)
        if sha256_file(key_path) != report["judge_key_sha256"]:
            raise InvalidInput(f"{family}: judge-key commitment mismatch")
    _verify_overall(report)
    return {
        "family": family,
        "campaign_id": report["campaign_id"],
        "items": len(report["items"]),
        "report_sha256": sha256_file(report_path),
        "status": report["status"],
    }


def _ignored(relative: str) -> bool:
    parts = relative.split("/")
    return (
        relative == "release-manifest.json"
        or ".git" in parts
        or "__pycache__" in parts
        or ".pytest_cache" in parts
        or relative.startswith("runs/local/")
        or relative.endswith(".pyc")
    )


def verify_release_manifest() -> dict[str, Any]:
    manifest_path = ROOT / "release-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "elyne.benchmark.release-manifest/v1":
        raise InvalidInput("release manifest schema mismatch")
    expected = {entry["path"]: entry for entry in manifest.get("files", [])}
    actual = {
        path.relative_to(ROOT).as_posix(): path
        for path in ROOT.rglob("*")
        if path.is_file() and not _ignored(path.relative_to(ROOT).as_posix())
    }
    if set(expected) != set(actual):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise InvalidInput(f"release file set mismatch missing={missing[:3]} extra={extra[:3]}")
    for relative, path in actual.items():
        entry = expected[relative]
        if path.stat().st_size != entry["size_bytes"] or sha256_file(path) != entry["sha256"]:
            raise InvalidInput(f"release file commitment mismatch: {relative}")
    return {"files": len(actual), "manifest_sha256": sha256_file(manifest_path)}


def verify_all() -> dict[str, Any]:
    references = [verify_reference_run(family) for family in FAMILIES]
    release = verify_release_manifest()
    return {"status": "verified", "references": references, "release": release}
