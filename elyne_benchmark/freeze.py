from __future__ import annotations

from pathlib import Path

from .common import ROOT, sha256_file, write_canonical_exclusive


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


def freeze_release(root: Path = ROOT) -> Path:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _ignored(relative):
            continue
        files.append({"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    target = root / "release-manifest.json"
    if target.exists():
        target.unlink()
    write_canonical_exclusive(target, {"schema": "elyne.benchmark.release-manifest/v1", "files": files})
    return target

