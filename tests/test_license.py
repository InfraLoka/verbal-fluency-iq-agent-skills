# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import pathlib
import sys

sys.path.insert(0, "scripts")

from add_license_header import HEADER, add_header

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY_DIRS = ["mcp-server", "tests", "scripts"]


def _py_files():
    for d in PY_DIRS:
        yield from (ROOT / d).rglob("*.py")


def test_license_is_proprietary():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" not in text
    assert "All rights reserved" in text
    assert "InfraLoka" in text


def test_readme_states_proprietary_license():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## License" in text
    assert "proprietary" in text.lower()


def test_every_source_file_has_header():
    missing = [
        str(p.relative_to(ROOT))
        for p in _py_files()
        if HEADER not in p.read_text(encoding="utf-8").splitlines()[:2]
    ]
    assert missing == []


def test_add_header_is_idempotent():
    once = add_header("import os\n")
    assert add_header(once) == once


def test_add_header_preserves_shebang():
    out = add_header("#!/usr/bin/env python3\nimport os\n")
    lines = out.splitlines()
    assert lines[0] == "#!/usr/bin/env python3"
    assert lines[1] == HEADER


def test_add_header_on_empty_file():
    assert add_header("") == HEADER + "\n"
