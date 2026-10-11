# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Dependencies are pinned exactly so scores cannot drift with a library upgrade."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][^\s=;]*)$")
MODEL_RE = re.compile(
    r"^([a-z_]+) @ https://github\.com/explosion/spacy-models/releases/download/"
    r"\1-(\d+\.\d+\.\d+)/\1-\2-py3-none-any\.whl#sha256=[0-9a-f]{64}$"
)


def _lines(name: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _pins(name: str) -> dict[str, str]:
    pins = {}
    for line in _lines(name):
        match = PIN_RE.match(line)
        assert match, f"{name}: not an exact pin: {line!r}"
        pins[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pins


def test_requirements_are_pinned_with_exact_versions():
    runtime = _pins("requirements.txt")
    dev = _pins("requirements-dev.txt")
    lock = _pins("requirements.lock")
    assert {"fastmcp", "spacy", "sentence-transformers", "textstat"} <= set(runtime)
    assert {"pytest", "pytest-cov", "pip-audit", "pyyaml", "ruff", "mypy"} <= set(dev)
    for name, version in {**runtime, **dev}.items():
        assert lock.get(name) == version, f"{name}=={version} missing from lock"
    models = _lines("requirements-models.txt")
    assert len(models) == 2
    names = set()
    for line in models:
        match = MODEL_RE.match(line)
        assert match, f"model not pinned by version and sha256: {line!r}"
        names.add(match.group(1))
    assert names == {"en_core_web_sm", "xx_ent_wiki_sm"}
