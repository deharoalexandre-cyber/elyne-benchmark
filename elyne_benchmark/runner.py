from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from elyne.contracts.hashing import InvalidInput

from .adapter import invoke_adapter, load_adapter_config, validate_observation
from .common import SUBJECTS, hash_document, load_battery, sha256_file, write_canonical_exclusive
from .scoring import build_replication_report


def _material(family: str, subject: str, case: dict[str, Any], core: dict[str, Any] | None) -> object | None:
    if subject == "core-origin" or subject == "gemma-nu":
        return None
    if family == "justesse":
        if core is None:
            raise InvalidInput("core arm must run before information control")
        return core["surfaced_information"]
    return case["info_material"]


def run_campaign(
    *,
    family: str,
    adapter_config: Path,
    output_root: Path,
    campaign_id: str | None = None,
    timeout_cap_seconds: int = 3600,
) -> Path:
    battery, battery_path = load_battery(family)
    commands = load_adapter_config(adapter_config)
    campaign_id = campaign_id or secrets.token_hex(16)
    if len(campaign_id) != 32 or any(c not in "0123456789abcdef" for c in campaign_id):
        raise InvalidInput("campaign_id must be 32 lowercase hexadecimal characters")
    directory = output_root.resolve() / family / campaign_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise InvalidInput(f"refusing to overwrite campaign: {directory}") from exc
    observations: dict[str, dict[str, dict[str, Any]]] = {}
    for case in battery["cases"]:
        item_id = case["id"]
        case_dir = directory / "cases" / item_id
        case_dir.mkdir(parents=True)
        arms: dict[str, dict[str, Any]] = {}
        core = None
        for subject in SUBJECTS:
            material = _material(family, subject, case, core)
            request = {
                "schema": "elyne.benchmark.adapter-request/v1",
                "family": family,
                "campaign_id": campaign_id,
                "item_id": item_id,
                "subject_id": subject,
                "seed": 0,
                "case": case,
                "control_material": material,
                "control_material_sha256": None if material is None else hash_document(material),
            }
            write_canonical_exclusive(case_dir / f"request.{subject}.json", request)
            raw = invoke_adapter(
                commands[subject],
                request,
                timeout_seconds=min(int(case["timeout_seconds"]), timeout_cap_seconds),
            )
            observation = validate_observation(raw, family=family, item_id=item_id, subject_id=subject, material=material)
            write_canonical_exclusive(case_dir / f"observation.{subject}.json", observation)
            arms[subject] = observation
            if subject == "core-origin":
                core = observation
        observations[item_id] = arms
    report = build_replication_report(
        family=family,
        campaign_id=campaign_id,
        battery=battery,
        battery_sha256=sha256_file(battery_path),
        observations=observations,
    )
    report_path = directory / "report.json"
    write_canonical_exclusive(report_path, report)
    manifest = {
        "schema": "elyne.benchmark.public-campaign-manifest/v1",
        "campaign_id": campaign_id,
        "family": family,
        "battery_sha256": sha256_file(battery_path),
        "report": {"relative_path": "report.json", "sha256": sha256_file(report_path), "size_bytes": report_path.stat().st_size},
        "status": report["status"],
    }
    write_canonical_exclusive(directory / "campaign-manifest.json", manifest)
    return report_path
