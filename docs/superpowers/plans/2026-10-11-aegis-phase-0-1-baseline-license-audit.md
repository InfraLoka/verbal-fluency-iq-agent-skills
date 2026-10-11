# AEGIS Phase 0–1: Baseline, Proprietary License, 100-Finding Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the in-flight Indonesian-bias fix on a working test environment, convert the project to proprietary licensing, and produce exactly 100 verified, schema-valid AEGIS findings with tooling that tracks their completion.

**Architecture:** Three stacked local branches (`fix/indonesian-syntactic-bias` → `chore/proprietary-license` → `aegis/audit`). A small Python audit library (`scripts/audit_lib.py`) validates the findings file and reports progress; a shared pipeline runner (`scripts/pipeline.py`) captures golden scores so later phases make score changes explicit. The audit itself is produced by seven persona subagents writing raw JSON, then consolidated and verified by the controller.

**Tech Stack:** Python 3.14 (matches CI), pytest, jsonschema, spaCy (`en_core_web_sm`, `xx_ent_wiki_sm`), ruff, existing `mcp-server/tools/*`.

**Spec:** `docs/superpowers/specs/2026-10-11-aegis-100-findings-remediation-design.md`

## Global Constraints

- Threat model: **screening people (hiring, admissions)**; severity judged against that.
- Exactly **100** findings; IDs `F-###` (fallacy), `G-###` (gap), `N-###` (feature); no padding; every finding cites `file:line` or an explicit absence (`line: 0`).
- Severity enum `P0 | P1 | P2 | P3`; fixability enum `code | guardrail | process`; phase integer `2..5`; status `open | done`.
- Deterministic tools stay deterministic; the AI never estimates scores.
- `mcp-server/config/iq_norms.json` and mapper weights are **unchanged** in Phase 0–1.
- License: InfraLoka proprietary, "All rights reserved"; previously published GPL-3.0 versions remain GPL for existing recipients.
- No `git push`, PR creation, or repo-visibility change without explicit owner confirmation at that moment (GitHub account currently returns HTTP 403 suspended).
- `example/rahmat/`, `.agent/skills/`, `.claude/` stay **untracked**; their contents are never copied into committed files.
- New Python files pass `ruff check` and `ruff format --check` (CI enforces).

## Review Focus

1. **Personal corpus leakage** — `example/rahmat/source/` contains personal documents. Expect: never committed, never quoted in findings/report/golden fixtures. Pinned by `test_golden_sources_exclude_untracked_personal_corpus` (Task 4) and `test_findings_do_not_reference_personal_corpus` (Task 5).
2. **Evidence line drift** — later phases edit code, so cited line numbers go stale. Expect: validator checks line ranges only for `status: open` findings and reports drift instead of crashing. Pinned by `test_verify_evidence_skips_done_findings` (Task 5).
3. **Wrong count / duplicate IDs** — a consolidated file with 99, 101, or duplicated IDs. Expect: validator rejects with a message naming the problem. Pinned by `test_validate_rejects_wrong_count` and `test_validate_rejects_duplicate_ids` (Task 5).
4. **Re-running the license header script** — expect idempotence: second run changes nothing; shebang lines stay first. Pinned by `test_add_header_is_idempotent` and `test_add_header_preserves_shebang` (Task 3).
5. **Golden scores flaking across machines** — embedding floats differ slightly per BLAS build. Expect: comparison tolerant (VFS ±0.5, IQ ±1) yet still catching real score changes. Pinned by `test_golden_scores_match` tolerances (Task 4).

---

### Task 1: Working local test environment + CI installs the Indonesian model

Local `pytest` currently dies at collection: `ValueError: numpy.dtype size changed` (anaconda Python 3.12 with mismatched numpy). CI downloads only `en_core_web_sm`, but `preprocess.py:15` and `syntactic.py:33` load `xx_ent_wiki_sm` for Indonesian.

**Files:**
- Modify: `.github/workflows/ci.yml` (step "Download spaCy model", ~line 80)
- Create: `.venv/` (gitignored, not committed)

**Interfaces:**
- Produces: `.venv/bin/python` with all deps; every later task runs tests as `.venv/bin/python -m pytest`.

- [ ] **Step 1: Create venv with the CI Python version**

```bash
/opt/homebrew/bin/python3.14 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m spacy download en_core_web_sm
.venv/bin/python -m spacy download xx_ent_wiki_sm
```

If any wheel is unavailable for 3.14, fall back to `/opt/homebrew/bin/python3.13` and record that in the commit message.

- [ ] **Step 2: Run the suite to get the real baseline**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: collection succeeds (no numpy dtype error). Record pass/fail counts; failures here belong to the bias branch and are handled in Task 2.

- [ ] **Step 3: Make CI install the Indonesian model**

In `.github/workflows/ci.yml` replace:

```yaml
      - name: Download spaCy model
        run: python -m spacy download en_core_web_sm
```

with:

```yaml
      - name: Download spaCy models
        run: |
          python -m spacy download en_core_web_sm
          python -m spacy download xx_ent_wiki_sm
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: install xx_ent_wiki_sm so Indonesian paths are tested"
```

---

### Task 2: Finish and commit the Indonesian-bias fix

Plan: `docs/plans/2026-06-15-001-fix-indonesian-syntactic-analysis-bias-plan.md` (acceptance criteria lines 247–262). Uncommitted diff already touches `syntactic.py`, `semantic.py`, `reporter.py`, `server.py`, `.agent/SKILL.md`, and three test files.

**Files:**
- Modify (as needed to satisfy criteria): `mcp-server/tools/syntactic.py`, `mcp-server/tools/semantic.py`, `mcp-server/tools/reporter.py`, `mcp-server/server.py`, `.agent/SKILL.md`
- Test: `tests/test_syntactic.py`, `tests/test_semantic.py`, `tests/test_reporter.py`

**Interfaces:**
- Produces: `analyze_syntactic(sentences, "id")` returns `dependency_depth: None`; `analyze_semantic(text, sentences, lang, segment_boundaries=None)`.

- [ ] **Step 1: Run the bias-related tests**

Run: `.venv/bin/python -m pytest tests/test_syntactic.py tests/test_semantic.py tests/test_reporter.py -v`
Expected: all PASS. For each FAIL, use superpowers:systematic-debugging, fix the implementation (not the test), re-run.

- [ ] **Step 2: Verify each acceptance criterion has a passing test**

For each unchecked criterion at plan lines 249–261, grep for its test:

```bash
grep -n "dependency_depth\|subordination_index\|passive_ratio\|segment_boundaries\|N/A (no parser" tests/test_syntactic.py tests/test_semantic.py tests/test_reporter.py
```

Any criterion without a test: write the test first (specified in that plan's "Test Plan (files)" section, line 264+), run it, then implement until it passes.

- [ ] **Step 3: Verify norms and weights unchanged**

Run: `git diff --stat main -- mcp-server/config/iq_norms.json && git diff main -- mcp-server/tools/mapper.py | grep -n "0.35\|0.25\|0.15"`
Expected: no output from either command.

- [ ] **Step 4: Full suite + lint**

Run: `.venv/bin/python -m pytest tests/ -q && .venv/bin/ruff check mcp-server/ tests/ && .venv/bin/ruff format --check mcp-server/ tests/`
Expected: all pass. If format check fails, run `.venv/bin/ruff format mcp-server/ tests/` and re-run.

- [ ] **Step 5: Tick the plan checkboxes and commit (exclude personal corpus and untracked skills)**

Edit the plan file, changing each satisfied `- [ ]` at lines 249–261 to `- [x]`.

```bash
git add mcp-server/ tests/ .agent/SKILL.md docs/plans/2026-06-15-001-fix-indonesian-syntactic-analysis-bias-plan.md
git status --short   # confirm example/rahmat/, .agent/skills/, .claude/ remain untracked
git commit -m "fix: remove Indonesian syntactic-analysis bias (parser-free heuristic, N/A depth, segment-aware coherence)"
```

---

### Task 3: Convert to proprietary license

**Files:**
- Create branch: `chore/proprietary-license` from `fix/indonesian-syntactic-bias`
- Replace: `LICENSE`
- Create: `scripts/add_license_header.py`
- Modify: every `*.py` under `mcp-server/`, `tests/`, `scripts/` (header line), `README.md` (append License section)
- Test: `tests/test_license.py`

**Interfaces:**
- Produces: `HEADER: str` and `add_header(text: str) -> str` in `scripts/add_license_header.py`.

- [ ] **Step 1: Branch**

```bash
git checkout -b chore/proprietary-license
```

- [ ] **Step 2: Write the failing tests**

`tests/test_license.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_license.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'add_license_header'`.

- [ ] **Step 4: Implement the header script**

`scripts/add_license_header.py`:

```python
"""Prepend the InfraLoka proprietary copyright header to Python sources."""

import pathlib
import sys

HEADER = "# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential."
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
```

- [ ] **Step 5: Replace LICENSE**

Overwrite `LICENSE` with:

```text
InfraLoka Proprietary License

Copyright (c) 2026 InfraLoka. All rights reserved.

This software and its source code, documentation, configuration, models,
norms tables and associated files (the "Software") are the confidential and
proprietary property of InfraLoka.

No license, express or implied, is granted to any person to use, copy,
modify, merge, publish, distribute, sublicense, sell, or create derivative
works of the Software, in whole or in part, except under a separate written
agreement signed by an authorized representative of InfraLoka.

Unauthorized use, reproduction, or disclosure is strictly prohibited.

Versions of this Software previously published under the GNU General Public
License v3.0 remain available under that license solely to persons who
received them under it. All versions from the date of this notice onward are
proprietary.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED. IN NO EVENT SHALL INFRALOKA BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY ARISING FROM THE USE OF THE SOFTWARE.

Contact: contact@infraloka.com
```

- [ ] **Step 6: Append README License section**

Append to the end of `README.md`:

```markdown

---

## License

Proprietary. Copyright (c) 2026 InfraLoka. All rights reserved. See [LICENSE](LICENSE).
Use, copying, or distribution requires a written agreement with InfraLoka.
Versions previously published under GPL-3.0 remain GPL only for those who received them.
```

- [ ] **Step 7: Apply headers and run tests**

```bash
.venv/bin/python scripts/add_license_header.py
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check mcp-server/ tests/ scripts/ && .venv/bin/ruff format --check mcp-server/ tests/ scripts/
```

Expected: `headers added: N` (N = number of .py files), all tests PASS, lint clean.

- [ ] **Step 8: Commit**

```bash
git add LICENSE README.md scripts/add_license_header.py tests/test_license.py mcp-server/ tests/
git commit -m "chore: relicense as InfraLoka proprietary (closed source)"
```

---

### Task 4: Shared pipeline runner + golden-score baseline

Later phases change scoring; golden fixtures make every shift explicit. Only tracked examples (`aqilah`, `bimo`, `fabhian`) are used.

**Files:**
- Create branch: `aegis/audit` from `chore/proprietary-license`
- Create: `scripts/pipeline.py`, `scripts/capture_golden.py`, `tests/fixtures/golden_scores.json`
- Test: `tests/test_golden.py`

**Interfaces:**
- Produces: `run_pipeline(text: str) -> dict` returning `{"lang": str, "vfs": float, "iq": int, "ci": [int, int], "edu": str, "word_count": int}`; `GOLDEN_SOURCES: list[str]` (repo-relative paths); `capture(root: pathlib.Path) -> dict[str, dict]`.

- [ ] **Step 1: Branch**

```bash
git checkout -b aegis/audit
```

- [ ] **Step 2: Write the failing tests**

`tests/test_golden.py`:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from capture_golden import GOLDEN_SOURCES
from pipeline import run_pipeline

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "golden_scores.json"


def test_golden_sources_exclude_untracked_personal_corpus():
    assert GOLDEN_SOURCES
    assert all("example/rahmat" not in s for s in GOLDEN_SOURCES)


def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert set(out) == {"lang", "vfs", "iq", "ci", "edu", "word_count"}
    assert len(out["ci"]) == 2


@pytest.mark.parametrize("source", GOLDEN_SOURCES)
def test_golden_scores_match(source):
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))[source]
    text = (ROOT / source).read_text(encoding="utf-8")
    actual = run_pipeline(text)
    assert actual["lang"] == expected["lang"]
    assert actual["vfs"] == pytest.approx(expected["vfs"], abs=0.5)
    assert abs(actual["iq"] - expected["iq"]) <= 1
    assert actual["edu"] == expected["edu"]
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_golden.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'capture_golden'`.

- [ ] **Step 4: Implement the runner**

Before writing, open `mcp-server/tools/mapper.py` lines 66–146 and confirm the return keys of `predict_iq` (`point_estimate`, CI key) and `estimate_education_level` (level key). The code below assumes `ci_95` and `level`; change those two key names to match the file exactly.

`scripts/pipeline.py`:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical  # noqa: E402
from tools.mapper import (  # noqa: E402
    compute_verbal_fluency_score,
    estimate_education_level,
    predict_iq,
)
from tools.preprocess import detect_language, preprocess_text  # noqa: E402
from tools.readability import analyze_readability  # noqa: E402
from tools.semantic import analyze_semantic  # noqa: E402
from tools.syntactic import analyze_syntactic  # noqa: E402


def run_pipeline(text: str) -> dict:
    lang = detect_language(text)["lang"]
    prep = preprocess_text(text, lang)
    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["vfs"], vfs["confidence"])
    edu = estimate_education_level(
        read["gunning_fog"], read["ari"], lex["lexical_density"], syn["clause_density"]
    )
    return {
        "lang": lang,
        "vfs": vfs["vfs"],
        "iq": iq["point_estimate"],
        "ci": list(iq["ci_95"]),
        "edu": edu["level"],
        "word_count": prep["word_count"],
    }
```

`scripts/capture_golden.py`:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Regenerate tests/fixtures/golden_scores.json. Run only when a score change is intended."""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pipeline import run_pipeline  # noqa: E402

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
```

- [ ] **Step 5: Capture baseline and run tests**

```bash
.venv/bin/python scripts/capture_golden.py
.venv/bin/python -m pytest tests/test_golden.py -v
```

Expected: fixture written; all PASS. Run the golden test a second time to confirm stability.

- [ ] **Step 6: Commit**

```bash
git add scripts/pipeline.py scripts/capture_golden.py tests/test_golden.py tests/fixtures/golden_scores.json
git commit -m "test: golden-score baseline over tracked examples"
```

---

### Task 5: Findings schema, validator, and status gate

**Files:**
- Create: `docs/audit/findings.schema.json`, `scripts/audit_lib.py`, `scripts/audit_status.py`
- Modify: `requirements.txt` (add `jsonschema>=4.21.0`)
- Test: `tests/test_audit_lib.py`

**Interfaces:**
- Produces:
  - `ROOT: pathlib.Path`, `PREFIX: dict[str, str]`
  - `load_findings(path: pathlib.Path) -> list[dict]`
  - `validate(findings: list[dict], expected_count: int = 100) -> list[str]` (error strings; empty = valid)
  - `verify_evidence(findings: list[dict], root: pathlib.Path) -> list[str]`
  - `status_summary(findings: list[dict]) -> dict[int, dict[str, int]]` (phase → {"open": n, "done": n})
  - CLI: `python scripts/audit_status.py [--require-complete]` exit 0/1.

- [ ] **Step 1: Write the schema**

`docs/audit/findings.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AEGIS finding",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "category", "persona", "severity", "title", "claim", "evidence",
               "impact_on_screened_person", "fixability", "fix", "acceptance_test",
               "phase", "status", "depends_on"],
  "properties": {
    "id": {"type": "string", "pattern": "^[FGN]-[0-9]{3}$"},
    "category": {"enum": ["fallacy", "gap", "feature"]},
    "persona": {"enum": ["data-detective", "skeptical-economist", "pragmatist",
                         "cto", "cro", "hacker", "ceo"]},
    "severity": {"enum": ["P0", "P1", "P2", "P3"]},
    "title": {"type": "string", "minLength": 5},
    "claim": {"type": "string", "minLength": 20},
    "evidence": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["file", "line", "excerpt"],
        "properties": {
          "file": {"type": "string"},
          "line": {"type": "integer", "minimum": 0},
          "excerpt": {"type": "string"}
        }
      }
    },
    "impact_on_screened_person": {"type": "string", "minLength": 10},
    "fixability": {"enum": ["code", "guardrail", "process"]},
    "fix": {"type": "string", "minLength": 10},
    "acceptance_test": {"type": "string", "minLength": 5},
    "phase": {"type": "integer", "minimum": 2, "maximum": 5},
    "status": {"enum": ["open", "done"]},
    "depends_on": {"type": "array", "items": {"type": "string", "pattern": "^[FGN]-[0-9]{3}$"}}
  }
}
```

`line: 0` means "explicit absence" (the thing is missing from that file); `excerpt` then describes what is absent.

- [ ] **Step 2: Write the failing tests**

`tests/test_audit_lib.py`:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import copy
import json
import pathlib
import sys

sys.path.insert(0, "scripts")

from audit_lib import status_summary, validate, verify_evidence

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
        "evidence": [{"file": "mcp-server/server.py", "line": 1, "excerpt": "import json"}],
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
        _finding(2, evidence=[{"file": "mcp-server/server.py", "line": 99999, "excerpt": "x"}]),
    ]
    errs = verify_evidence(fs, ROOT)
    assert any("G-001" in e and "missing file" in e for e in errs)
    assert any("G-002" in e and "out of range" in e for e in errs)


def test_verify_evidence_skips_done_findings():
    fs = [_finding(1, status="done", evidence=[{"file": "nope.py", "line": 5, "excerpt": "x"}])]
    assert verify_evidence(fs, ROOT) == []


def test_verify_evidence_allows_line_zero_absence():
    fs = [_finding(1, evidence=[{"file": "mcp-server/server.py", "line": 0, "excerpt": "no auth"}])]
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
```

- [ ] **Step 3: Install dependency and run to verify failure**

Add `jsonschema>=4.21.0` to `requirements.txt`, then:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/test_audit_lib.py -v
```

Expected: ERROR `ModuleNotFoundError: No module named 'audit_lib'`.

- [ ] **Step 4: Implement `scripts/audit_lib.py` and `scripts/audit_status.py`**

`scripts/audit_lib.py`:

```python
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
    ids = [f.get("id", "?") for f in findings]
    for dup, n in Counter(ids).items():
        if n > 1:
            errors.append(f"duplicate id {dup} ({n}x)")
    known = set(ids)
    for f in findings:
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
    for f in findings:
        if f.get("status") == "done":
            continue
        for ev in f.get("evidence", []):
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
```

`scripts/audit_status.py`:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Print AEGIS remediation progress. --require-complete exits 1 unless 100/100 done."""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_lib import ROOT, load_findings, status_summary, validate, verify_evidence  # noqa: E402

FINDINGS = ROOT / "docs" / "audit" / "2026-10-11-aegis-findings.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-complete", action="store_true")
    args = ap.parse_args()
    findings = load_findings(FINDINGS)
    problems = validate(findings) + verify_evidence(findings, ROOT)
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
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_audit_lib.py -v && .venv/bin/ruff check scripts/ tests/ && .venv/bin/ruff format --check scripts/ tests/`
Expected: all PASS (file-dependent tests return early because the findings file does not exist yet).

- [ ] **Step 6: Commit**

```bash
git add docs/audit/findings.schema.json scripts/audit_lib.py scripts/audit_status.py tests/test_audit_lib.py requirements.txt
git commit -m "feat(audit): findings schema, validator, and status gate"
```

---

### Task 6: Run the seven-persona AEGIS audit (raw findings)

The controller dispatches seven subagents **in parallel**, each read-only on code, each writing one file `docs/audit/raw/<persona>.json` (a JSON array in the schema shape, IDs temporarily `X-001…`).

**Files:**
- Create: `docs/audit/raw/{data-detective,skeptical-economist,pragmatist,cto,cro,hacker,ceo}.json`

**Interfaces:**
- Consumes: `docs/audit/findings.schema.json` (Task 5).
- Produces: seven raw arrays consumed by Task 7.

- [ ] **Step 1: Dispatch the seven persona agents in one message**

Common prompt prefix for every agent:

```text
You are a member of an AEGIS adversarial review panel auditing the repository at
/Users/rahmatwibowo/infraloka/verbal-fluency-iq-agent-skills. The tool estimates IQ, mental
age and education level from text (English + Indonesian) and is intended to SCREEN PEOPLE
for hiring and admissions. Judge severity against harm to a screened person:
P0 = can cause an unfair/unaccountable decision about a person, or a security/legal breach;
P1 = materially wrong score or missing core control; P2 = quality/robustness; P3 = polish.

Read first: .agent/skills/aegis/SKILL.md, .agent/skills/aegis/module-f.md,
.agent/skills/aegis/module-h-devil-advocate-engine.md, README.md, .agent/SKILL.md,
mcp-server/server.py, mcp-server/tools/*.py, mcp-server/config/*.json, tests/*.py,
.github/workflows/ci.yml, scripts/*.py.

Rules:
- Every finding must cite real evidence: file path + 1-based line + verbatim excerpt you read,
  or line 0 with an excerpt describing an explicit absence. Never invent line numbers.
- NEVER read or cite anything under example/rahmat/ (private personal data).
- No padding. Fewer real findings beat more weak ones. No duplicates within your list.
- For each finding pick fixability: code (behaviour change + test), guardrail (code cannot make
  the claim true, so the system must refuse/warn/degrade honestly), or process (needs a written
  artefact such as a validation-study protocol, DPIA, consent text).
- phase: 2 = validity/fairness fallacies; 3 = engineering gaps; 4 = screening compliance; 5 = new features.
- acceptance_test: a concrete pytest name (test_<topic>_<behaviour>) or, for process items,
  "doc: docs/<path>.md exists and <check>".
- Output: write ONLY a JSON array to docs/audit/raw/<persona>.json matching
  docs/audit/findings.schema.json, with id "X-001", "X-002", ... (renumbered later), status "open",
  depends_on []. Then reply with the count and your top 3 P0/P1 titles.
```

Note: raw IDs `X-###` intentionally fail the final schema's `^[FGN]-` pattern; they are only valid after Task 7 renumbering.

Persona-specific suffixes (target counts):

| persona | suffix |
|---|---|
| `data-detective` (category fallacy, ~14) | "Hunt statistical and data fallacies: false precision (e.g. mapper.py `ci_half = 15 - confidence*10`), arbitrary thresholds, hand-set weights (0.35/0.25/0.25/0.15), norms tables without provenance (config/iq_norms.json, edu_norms.json), ecological fallacy, small-sample metrics (MATTR/VOCD on short text), range restriction, regression to the mean ignored." |
| `skeptical-economist` (category fallacy, ~14; act as a psychometrician) | "Hunt construct-validity and causal fallacies: verbal fluency treated as IQ, mental age from a ratio-IQ concept, education inferred from readability, confounds (topic, genre, editing tools, AI-assisted writing, translation, dictation), circular reasoning in band mapping, reification of the VFS." |
| `pragmatist` (category fallacy, ~12) | "Hunt fairness and decision-use fallacies: cross-language comparability (en vs id norms), dialect/register penalties (Javanese-influenced Indonesian, code-switching, non-native English), disability (dyslexia), adverse impact, base-rate neglect in screening, automation bias, single-number decisions." |
| `cto` (category gap, ~20) | "Hunt engineering gaps: error handling, input limits, model loading/caching, determinism, test coverage holes, typing, config validation, performance on long texts, observability/logging, versioning of scores/norms, MCP tool contract consistency, packaging, CI gaps." |
| `cro` (category gap, ~12) | "Hunt compliance/risk gaps for screening in Indonesia and globally: UU PDP No. 27/2022 (consent, purpose limitation, automated-decision rights, retention, cross-border transfer), EU AI Act high-risk (employment/education), EEOC four-fifths rule, audit trail, human-in-the-loop, explainability, model/norm change control, data minimisation in reports." |
| `hacker` (category gap, ~8) | "Hunt security gaps: oversized/malicious input DoS, prompt injection carried in analysed text into the orchestrating agent, adversarial gaming of scores (vocabulary stuffing, sentence padding), dependency/supply-chain risk (unpinned requirements, model downloads), path handling, report injection (markdown/HTML)." |
| `ceo` (category feature, ~25) | "Propose new features that make this a responsible screening product: per-metric explanations, writing-improvement feedback, calibration/validation harness, fairness dashboard, batch scoring, consent capture, audit export, versioned norms, AI-written-text detection flag, language expansion, API auth, rate limiting, human-review workflow, score appeal path. Evidence = line 0 absence or the code a feature extends. Rank by value to a responsible screening customer." |

- [ ] **Step 2: Validate each raw file parses**

```bash
for f in docs/audit/raw/*.json; do .venv/bin/python -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[1], len(d))" "$f"; done
```

Expected: seven files, each a non-empty array. Re-dispatch any agent whose file is missing or unparseable.

- [ ] **Step 3: Commit raw findings**

```bash
git add docs/audit/raw/
git commit -m "docs(audit): raw AEGIS persona findings"
```

---

### Task 7: Consolidate to exactly 100 verified findings

**Files:**
- Create: `scripts/consolidate_findings.py`, `docs/audit/curated.json`, `docs/audit/2026-10-11-aegis-findings.json`
- Modify: `tests/test_audit_lib.py` (append renumber test)

**Interfaces:**
- Consumes: raw arrays (Task 6); `PREFIX`, `ROOT`, `validate`, `verify_evidence` (Task 5).
- Produces: `docs/audit/2026-10-11-aegis-findings.json` (100 items) and `renumber(findings: list[dict]) -> list[dict]`.

- [ ] **Step 1: Write the renumber test** (append to `tests/test_audit_lib.py`)

```python
from consolidate_findings import renumber


def test_renumber_orders_by_severity_and_prefixes_by_category():
    raw = [
        _finding(1, id="cto:X-001", category="feature", severity="P3", phase=5),
        _finding(2, id="cro:X-001", category="fallacy", severity="P0", phase=2),
        _finding(3, id="hacker:X-001", category="gap", severity="P1", phase=3,
                 depends_on=["cro:X-001"]),
    ]
    out = renumber(raw)
    assert [f["id"] for f in out] == ["F-001", "G-001", "N-001"]
    assert out[1]["depends_on"] == ["F-001"]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_audit_lib.py::test_renumber_orders_by_severity_and_prefixes_by_category -v`
Expected: ERROR `No module named 'consolidate_findings'`.

- [ ] **Step 3: Implement `scripts/consolidate_findings.py`**

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Renumber curated findings by category and severity, then write the source of truth."""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_lib import PREFIX, ROOT, validate, verify_evidence  # noqa: E402

CURATED = ROOT / "docs" / "audit" / "curated.json"
OUT = ROOT / "docs" / "audit" / "2026-10-11-aegis-findings.json"
SEV = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
CAT_ORDER = {"fallacy": 0, "gap": 1, "feature": 2}


def renumber(findings: list[dict]) -> list[dict]:
    ordered = sorted(
        findings, key=lambda f: (CAT_ORDER[f["category"]], SEV[f["severity"]], f["phase"])
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
    OUT.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(final)} findings to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the renumber test**

Run: `.venv/bin/python -m pytest tests/test_audit_lib.py -v`
Expected: all PASS.

- [ ] **Step 5: Curate (controller judgement, not automation)**

1. Load all raw arrays; prefix each ID with its persona (`cto:X-001`) so IDs are unique across files.
2. Merge duplicates across personas (union evidence lists, keep the higher severity, keep the clearer claim).
3. For every finding, open each cited `file:line` and confirm the excerpt is there; correct or drop any that are not.
4. Drop restatements, unfalsifiable claims, and non-actionable items.
5. If more than 100 remain: cut lowest-value P3 items first. If fewer than 100: re-dispatch the persona(s) with the thinnest coverage (same prompt + "Do not repeat: <titles>"), then repeat 2–4.
6. Set `depends_on` (using prefixed raw IDs) where one fix must precede another.
7. Write `docs/audit/curated.json` with exactly 100.

- [ ] **Step 6: Produce the source of truth and run the gate**

```bash
.venv/bin/python scripts/consolidate_findings.py
.venv/bin/python scripts/audit_status.py
.venv/bin/python -m pytest tests/test_audit_lib.py -v
```

Expected: `wrote 100 findings`; status prints `total: 0/100 done` and exits 0; all tests PASS including `test_findings_file_valid_when_present` and `test_findings_do_not_reference_personal_corpus`.

- [ ] **Step 7: Commit**

```bash
git add scripts/consolidate_findings.py docs/audit/curated.json docs/audit/2026-10-11-aegis-findings.json tests/test_audit_lib.py
git commit -m "docs(audit): consolidate 100 verified AEGIS findings"
```

---

### Task 8: Audit report + CI gate

**Files:**
- Create: `docs/audit/2026-10-11-aegis-report.md`
- Modify: `.github/workflows/ci.yml` (test job, after "Run tests")

**Interfaces:**
- Consumes: findings JSON (Task 7), `scripts/audit_status.py` (Task 5).

- [ ] **Step 1: Compute report numbers from the JSON (never hand-tally)**

```bash
.venv/bin/python -c "import json,collections;d=json.load(open('docs/audit/2026-10-11-aegis-findings.json'));print(collections.Counter((f['category'],f['severity']) for f in d));print(collections.Counter((f['phase'],f['fixability']) for f in d));print(collections.Counter(f['persona'] for f in d))"
```

- [ ] **Step 2: Write the report**

`docs/audit/2026-10-11-aegis-report.md`, conclusion first (internal document, so AEGIS may be named):

1. **Verdict** — panel composite using module [H] weights (CTO 25%, CEO 30%, CRO 30%, Hacker 15%; [F] persona findings inform the CRO and CTO scores), each persona score 1–10 with one-line justification, verdict band (≥8 PASS, 6–8 CONDITIONAL MINOR, 4–6 CONDITIONAL MAJOR, <4 FAIL), and a one-paragraph answer to "is this fit to screen people today?"
2. **Top 10 P0/P1 findings** — id, title, impact on the screened person, fix.
3. **Counts** — category × severity table and phase × fixability table (from Step 1 output).
4. **Full ranked table** — all 100: id | severity | title | fixability | phase.
5. **What code cannot fix** — every `process`/`guardrail` item stated plainly (e.g. "scores remain unvalidated against standardised IQ tests until the validation protocol is executed").
6. **Remediation roadmap** — phases 2–5 with item counts and key dependencies.

- [ ] **Step 3: Add CI step**

In `.github/workflows/ci.yml` test job, after `Run tests`:

```yaml
      - name: AEGIS findings integrity
        run: python scripts/audit_status.py
```

(`--require-complete` is added only at the end of Phase 5.)

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check mcp-server/ tests/ scripts/ && .venv/bin/ruff format --check mcp-server/ tests/ scripts/
.venv/bin/python scripts/audit_status.py
```

Expected: all green; `total: 0/100 done`.

- [ ] **Step 5: Commit report, CI, spec, and plan**

```bash
git add docs/audit/2026-10-11-aegis-report.md .github/workflows/ci.yml docs/superpowers/specs/2026-10-11-aegis-100-findings-remediation-design.md docs/superpowers/plans/2026-10-11-aegis-phase-0-1-baseline-license-audit.md
git commit -m "docs(audit): AEGIS panel report and CI integrity gate"
```

- [ ] **Step 6: Hand back to owner**

Report: branches created, test counts, panel verdict, P0 count. Ask before any push/PR (GitHub account suspended; repo visibility change is manual). Next: brainstorm → spec → plan for Phase 2 from the `phase: 2` findings.
