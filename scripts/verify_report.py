from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from elyne.contracts.hashing import InvalidInput  # noqa: E402
from elyne_benchmark.verify import verify_all, verify_reference_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify frozen batteries, evidence and reports.")
    parser.add_argument("--family", choices=("justesse", "orchestration", "toolchain"))
    args = parser.parse_args()
    try:
        result = verify_reference_run(args.family) if args.family else verify_all()
    except InvalidInput as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

