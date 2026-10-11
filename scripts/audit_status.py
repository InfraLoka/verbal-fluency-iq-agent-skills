# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Print AEGIS remediation progress. --require-complete exits 1 unless 100/100 done."""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_lib import ROOT, load_findings, status_summary, validate, verify_evidence

FINDINGS = ROOT / "docs" / "audit" / "2026-10-11-aegis-findings.json"


def main(argv: list[str] | None = None, findings_path: pathlib.Path = FINDINGS) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-complete", action="store_true")
    args = ap.parse_args(argv)
    if not findings_path.is_file():
        print(f"ERROR findings file not found: {findings_path}")
        return 1
    try:
        findings = load_findings(findings_path)
    except json.JSONDecodeError as e:
        print(f"ERROR findings file is not valid JSON: {e}")
        return 1
    problems = validate(findings)
    if problems:
        for p in problems:
            print(f"ERROR {p}")
        return 1
    problems = verify_evidence(findings, ROOT)
    for p in problems:
        print(f"ERROR {p}")
    done = 0
    for phase, c in sorted(status_summary(findings).items()):
        print(f"phase {phase}: {c['done']} done / {c['open']} open")
        done += c["done"]
    print(f"total: {done}/{len(findings)} done")
    if problems:
        return 1
    if args.require_complete and done != len(findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
