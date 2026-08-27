from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from elyne_benchmark.freeze import freeze_release  # noqa: E402
from elyne_benchmark.common import sha256_file  # noqa: E402


if __name__ == "__main__":
    path = freeze_release()
    print(json.dumps({"manifest": str(path), "sha256": sha256_file(path)}, sort_keys=True))

