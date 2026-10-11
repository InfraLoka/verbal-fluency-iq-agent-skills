# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Prepend the InfraLoka proprietary copyright header to Python sources."""

import pathlib
import sys

HEADER = (
    "# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential."
)
PY_DIRS = ["mcp-server", "tests", "scripts"]


def add_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if any(line.rstrip("\n") == HEADER for line in lines[:2]):
        return text
    if lines and lines[0].startswith("#!"):
        return lines[0] + HEADER + "\n" + "".join(lines[1:])
    return HEADER + "\n" + text


def main(root: pathlib.Path) -> int:
    changed = 0
    for d in PY_DIRS:
        for path in (root / d).rglob("*.py"):
            original = path.read_text(encoding="utf-8")
            updated = add_header(original)
            if updated != original:
                path.write_text(updated, encoding="utf-8")
                changed += 1
    print(f"headers added: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(__file__).resolve().parent.parent))
