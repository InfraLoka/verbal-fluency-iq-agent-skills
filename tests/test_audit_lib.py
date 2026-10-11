# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import copy
import json
import pathlib
import sys

sys.path.insert(0, "scripts")

from audit_lib import status_summary, validate, verify_evidence
from audit_status import main
from consolidate_findings import renumber

ROOT = pathlib.Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "docs" / "audit" / "2026-10-11-aegis-findings.json"


def _finding(i: int, **over) -> dict:
    f = {
        "id": f"G-{i:03d}",
        "category": "gap",
        "persona": "cto",
        "severity": "P2",
        "title": "Example gap",
        "claim": "Something important is missing here.",
        "evidence": [
            {"file": "mcp-server/server.py", "line": 1, "excerpt": "import json"}
        ],
        "impact_on_screened_person": "Could mis-score a candidate.",
        "fixability": "code",
        "fix": "Add the missing thing.",
        "acceptance_test": "test_g001_thing",
        "phase": 3,
        "status": "open",
        "depends_on": [],
    }
    f.update(over)
    return f


def _hundred() -> list[dict]:
    return [_finding(i) for i in range(1, 101)]


def test_validate_accepts_hundred_valid():
    assert validate(_hundred()) == []


def test_validate_rejects_wrong_count():
    errs = validate(_hundred()[:99])
    assert any("expected 100" in e for e in errs)


def test_validate_rejects_duplicate_ids():
    fs = _hundred()
    fs[1]["id"] = fs[0]["id"]
    assert any("duplicate id" in e for e in validate(fs))


def test_validate_rejects_bad_enum():
    fs = _hundred()
    fs[0]["severity"] = "P9"
    assert any("G-001" in e for e in validate(fs))


def test_validate_rejects_unknown_dependency():
    fs = _hundred()
    fs[0]["depends_on"] = ["F-999"]
    assert any("unknown dependency F-999" in e for e in validate(fs))


def test_validate_rejects_category_id_mismatch():
    fs = _hundred()
    fs[0]["category"] = "fallacy"
    assert any("prefix" in e for e in validate(fs))


def test_verify_evidence_flags_missing_file_and_bad_line():
    fs = [
        _finding(1, evidence=[{"file": "nope.py", "line": 1, "excerpt": "x"}]),
        _finding(
            2,
            evidence=[{"file": "mcp-server/server.py", "line": 99999, "excerpt": "x"}],
        ),
    ]
    errs = verify_evidence(fs, ROOT)
    assert any("G-001" in e and "missing file" in e for e in errs)
    assert any("G-002" in e and "out of range" in e for e in errs)


def test_verify_evidence_skips_done_findings():
    fs = [
        _finding(
            1, status="done", evidence=[{"file": "nope.py", "line": 5, "excerpt": "x"}]
        )
    ]
    assert verify_evidence(fs, ROOT) == []


def test_verify_evidence_allows_line_zero_absence():
    fs = [
        _finding(
            1,
            evidence=[
                {"file": "mcp-server/server.py", "line": 0, "excerpt": "no auth"}
            ],
        )
    ]
    assert verify_evidence(fs, ROOT) == []


def test_status_summary_counts_by_phase():
    fs = _hundred()
    fs[0]["status"] = "done"
    s = status_summary(fs)
    assert s[3] == {"open": 99, "done": 1}


def test_findings_file_valid_when_present():
    if not FINDINGS.exists():
        return
    fs = json.loads(FINDINGS.read_text(encoding="utf-8"))
    assert validate(fs) == []
    assert verify_evidence(fs, ROOT) == []


def test_findings_do_not_reference_personal_corpus():
    if not FINDINGS.exists():
        return
    text = FINDINGS.read_text(encoding="utf-8")
    assert "example/rahmat" not in text
    assert "legal.md" not in text


def test_validate_does_not_mutate_input():
    fs = _hundred()
    before = copy.deepcopy(fs)
    validate(fs)
    assert fs == before


def _write_findings(path: pathlib.Path, fs: list[dict]) -> pathlib.Path:
    path.write_text(json.dumps(fs), encoding="utf-8")
    return path


def test_verify_evidence_rejects_path_outside_repo():
    fs = [_finding(1, evidence=[{"file": "../x.py", "line": 1, "excerpt": "x"}])]
    errs = verify_evidence(fs, ROOT)
    assert any("G-001" in e and "evidence path outside repo ../x.py" in e for e in errs)


def test_verify_evidence_rejects_private_corpus_before_file_check():
    # The file deliberately does not exist: the privacy check must fire first.
    fs = [
        _finding(
            1, evidence=[{"file": "example/rahmat/a.md", "line": 1, "excerpt": "x"}]
        )
    ]
    errs = verify_evidence(fs, ROOT)
    assert any("G-001" in e and "evidence cites private corpus" in e for e in errs)
    assert not any("missing file" in e for e in errs)


def test_main_reports_validation_error_without_traceback(tmp_path, capsys):
    fs = _hundred()
    del fs[0]["phase"]
    path = _write_findings(tmp_path / "f.json", fs)
    assert main([], findings_path=path) == 1
    assert "ERROR" in capsys.readouterr().out


def test_main_missing_file_returns_one(tmp_path, capsys):
    path = tmp_path / "missing.json"
    assert main([], findings_path=path) == 1
    assert f"ERROR findings file not found: {path}" in capsys.readouterr().out


def test_main_require_complete_all_done_returns_zero(tmp_path):
    fs = _hundred()
    for f in fs:
        f["status"] = "done"
    path = _write_findings(tmp_path / "f.json", fs)
    assert main(["--require-complete"], findings_path=path) == 0


def test_main_require_complete_with_open_returns_one(tmp_path):
    fs = _hundred()
    for f in fs[1:]:
        f["status"] = "done"
    path = _write_findings(tmp_path / "f.json", fs)
    assert main(["--require-complete"], findings_path=path) == 1


def test_verify_evidence_rejects_private_corpus_case_variant():
    # macOS APFS is case-insensitive; the check must not depend on casing.
    # The file does not exist: the privacy check must fire before is_file().
    fs = [
        _finding(
            1, evidence=[{"file": "Example/Rahmat/a.md", "line": 1, "excerpt": "x"}]
        )
    ]
    errs = verify_evidence(fs, ROOT)
    assert any("G-001" in e and "evidence cites private corpus" in e for e in errs)
    assert not any("missing file" in e for e in errs)


def test_main_invalid_json_returns_one(tmp_path, capsys):
    path = tmp_path / "f.json"
    path.write_text("{not json", encoding="utf-8")
    assert main([], findings_path=path) == 1
    assert "ERROR findings file is not valid JSON:" in capsys.readouterr().out


def test_validate_non_dict_element_is_error_not_crash():
    fs = ["x"] + _hundred()[:99]
    errs = validate(fs)
    assert "0: finding is not an object" in errs


def test_renumber_orders_by_severity_and_prefixes_by_category():
    raw = [
        _finding(1, id="cto:X-001", category="feature", severity="P3", phase=5),
        _finding(2, id="cro:X-001", category="fallacy", severity="P0", phase=2),
        _finding(
            3,
            id="hacker:X-001",
            category="gap",
            severity="P1",
            phase=3,
            depends_on=["cro:X-001"],
        ),
    ]
    out = renumber(raw)
    assert [f["id"] for f in out] == ["F-001", "G-001", "N-001"]
    assert out[1]["depends_on"] == ["F-001"]
