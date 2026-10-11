# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Regenerate tests/fixtures/golden_scores.json. Run only when a score change is intended."""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pipeline import run_pipeline

GOLDEN_SOURCES = [
    "example/aqilah/source/1.md",
    "example/bimo/source/1.md",
    "example/fabhian/source/1.md",
]


def capture(root: pathlib.Path) -> dict[str, dict]:
    return {
        s: run_pipeline((root / s).read_text(encoding="utf-8")) for s in GOLDEN_SOURCES
    }


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parent.parent
    out = root / "tests" / "fixtures" / "golden_scores.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(capture(root), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
