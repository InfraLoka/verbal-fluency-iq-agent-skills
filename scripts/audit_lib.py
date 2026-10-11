# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Validation and progress tracking for the AEGIS findings file."""

import json
import pathlib
from collections import Counter

from jsonschema import Draft7Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "docs" / "audit" / "findings.schema.json"
PREFIX = {"fallacy": "F", "gap": "G", "feature": "N"}


def load_findings(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(findings: list[dict], expected_count: int = 100) -> list[str]:
    errors: list[str] = []
    if len(findings) != expected_count:
        errors.append(f"expected {expected_count} findings, got {len(findings)}")
    validator = Draft7Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    objs: list[dict] = []
    for i, f in enumerate(findings):
        if isinstance(f, dict):
            objs.append(f)
        else:
            errors.append(f"{i}: finding is not an object")
    ids = [f.get("id", "?") for f in objs]
    for dup, n in Counter(ids).items():
        if n > 1:
            errors.append(f"duplicate id {dup} ({n}x)")
    known = set(ids)
    for f in objs:
        fid = f.get("id", "?")
        for err in validator.iter_errors(f):
            path = "/".join(str(p) for p in err.absolute_path)
            errors.append(f"{fid}: {path or '<root>'}: {err.message}")
        cat = f.get("category")
        if cat in PREFIX and not fid.startswith(PREFIX[cat] + "-"):
            errors.append(f"{fid}: id prefix does not match category {cat}")
        for dep in f.get("depends_on", []):
            if dep not in known:
                errors.append(f"{fid}: unknown dependency {dep}")
    return errors


def verify_evidence(findings: list[dict], root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    base = root.resolve()
    for f in findings:
        fid = f.get("id", "?")
        done = f.get("status") == "done"
        for ev in f.get("evidence", []):
            resolved = (root / ev["file"]).resolve()
            try:
                rel = resolved.relative_to(base)
            except ValueError:
                errors.append(f"{fid}: evidence path outside repo {ev['file']}")
                continue
            if tuple(p.casefold() for p in rel.parts[:2]) == ("example", "rahmat"):
                errors.append(f"{fid}: evidence cites private corpus {ev['file']}")
                continue
            if done:
                continue
            path = root / ev["file"]
            if not path.is_file():
                errors.append(f"{f['id']}: missing file {ev['file']}")
                continue
            if ev["line"] == 0:
                continue
            n_lines = len(path.read_text(encoding="utf-8").splitlines())
            if ev["line"] > n_lines:
                errors.append(
                    f"{f['id']}: line {ev['line']} out of range for {ev['file']} ({n_lines})"
                )
    return errors


def status_summary(findings: list[dict]) -> dict[int, dict[str, int]]:
    summary: dict[int, dict[str, int]] = {}
    for f in findings:
        bucket = summary.setdefault(f["phase"], {"open": 0, "done": 0})
        bucket[f["status"]] += 1
    return summary
