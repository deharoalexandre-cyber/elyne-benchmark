from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from elyne.contracts.hashing import InvalidInput  # noqa: E402
from elyne_benchmark.runner import run_campaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one public Elyne three-arm benchmark family.")
    parser.add_argument("--family", required=True, choices=("justesse", "orchestration", "toolchain"))
    parser.add_argument("--adapter-config", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "local")
    parser.add_argument("--campaign-id")
    parser.add_argument("--timeout-cap", type=int, default=3600)
    args = parser.parse_args()
    try:
        report = run_campaign(
            family=args.family,
            adapter_config=args.adapter_config.resolve(),
            output_root=args.output.resolve(),
            campaign_id=args.campaign_id,
            timeout_cap_seconds=args.timeout_cap,
        )
    except (InvalidInput, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "completed", "report": str(report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

