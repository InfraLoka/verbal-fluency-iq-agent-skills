# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Renumber curated findings by category and severity, then write the source of truth."""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_lib import PREFIX, ROOT, validate, verify_evidence

CURATED = ROOT / "docs" / "audit" / "curated.json"
OUT = ROOT / "docs" / "audit" / "2026-10-11-aegis-findings.json"
SEV = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
CAT_ORDER = {"fallacy": 0, "gap": 1, "feature": 2}


def renumber(findings: list[dict]) -> list[dict]:
    ordered = sorted(
        findings,
        key=lambda f: (CAT_ORDER[f["category"]], SEV[f["severity"]], f["phase"]),
    )
    counters = {k: 0 for k in PREFIX}
    old_to_new: dict[str, str] = {}
    out = []
    for f in ordered:
        counters[f["category"]] += 1
        new_id = f"{PREFIX[f['category']]}-{counters[f['category']]:03d}"
        old_to_new[f["id"]] = new_id
        out.append({**f, "id": new_id})
    for f in out:
        f["depends_on"] = [old_to_new.get(d, d) for d in f["depends_on"]]
    return out


def main() -> int:
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    final = renumber(curated)
    problems = validate(final) + verify_evidence(final, ROOT)
    for p in problems:
        print(f"ERROR {p}")
    if problems:
        return 1
    OUT.write_text(
        json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(final)} findings to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
