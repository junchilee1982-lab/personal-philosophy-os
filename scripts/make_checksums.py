#!/usr/bin/env python3
"""Create deterministic SHA-256 lines for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", default="SHA256SUMS")
    args = parser.parse_args()

    directory = args.directory.resolve(strict=True)
    output = directory / args.output
    artifacts = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.name != output.name and not path.name.startswith(".")
    )
    lines = [f"{_sha256(path)}  {path.name}" for path in artifacts]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {output.name} for {len(artifacts)} artifact(s)")
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
