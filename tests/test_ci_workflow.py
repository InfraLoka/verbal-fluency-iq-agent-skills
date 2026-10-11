# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""The CI workflow is parsed as YAML and checked against the hardening rules."""

import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
LINT_TARGETS = "mcp-server/ tests/ scripts/"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps(workflow: dict, job: str) -> list[dict]:
    return workflow["jobs"][job]["steps"]


def _runs(workflow: dict, job: str) -> str:
    return "\n".join(s.get("run", "") for s in _steps(workflow, job))


def test_ci_workflow_pins_tooling_and_lints_scripts(workflow):
    lint = _runs(workflow, "lint")
    assert f"ruff check {LINT_TARGETS}" in lint
    assert f"ruff format --check {LINT_TARGETS}" in lint
    for job in workflow["jobs"]:
        for run in _runs(workflow, job).splitlines():
            if "pip install" in run:
                assert "-c requirements.lock" in run, (job, run)
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    assert any(re.fullmatch(r"ruff==\d+\.\d+\.\d+", line) for line in dev)

    test_steps = _steps(workflow, "test")
    setup = next(s for s in test_steps if "setup-python" in s.get("uses", ""))
    assert setup["with"]["cache"] == "pip"
    assert "requirements-models.txt" in setup["with"]["cache-dependency-path"]
    assert "-r requirements-models.txt" in _runs(workflow, "test")
    assert "spacy download" not in WORKFLOW.read_text(encoding="utf-8")
    hf = next(s for s in test_steps if "actions/cache" in s.get("uses", ""))
    assert hf["with"]["path"] == "~/.cache/huggingface"
    assert "paraphrase-multilingual-MiniLM-L12-v2" in hf["with"]["key"]
    assert "e8f8c211226b894fcb81acc59f3b34ba3efd5f42" in hf["with"]["key"]


def test_ci_workflow_has_python_matrix_and_coverage_fail_under(workflow):
    test_job = workflow["jobs"]["test"]
    assert test_job["strategy"]["matrix"]["python-version"] == ["3.13", "3.14"]
    setup = next(s for s in test_job["steps"] if "setup-python" in s.get("uses", ""))
    assert setup["with"]["python-version"] == "${{ matrix.python-version }}"
    run = _runs(workflow, "test")
    for flag in ("--cov=mcp-server", "--cov=scripts", "--cov-fail-under=80"):
        assert flag in run, flag
    assert "python scripts/audit_status.py" in run


def test_ci_workflow_pins_actions_by_sha_and_runs_pip_audit(workflow):
    assert workflow["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text(encoding="utf-8")
    uses_lines = [ln.strip() for ln in text.splitlines() if "uses:" in ln]
    assert uses_lines
    for line in uses_lines:
        ref, _, comment = line.split("uses:", 1)[1].partition("#")
        assert SHA_PIN.match(ref.strip()), line
        assert re.fullmatch(r" v\d+\.\d+\.\d+", comment), line

    audit = _runs(workflow, "dependency-audit")
    assert "pip-audit -r requirements.lock --no-deps --disable-pip" in audit
    assert re.findall(r"--ignore-vuln (\S+)", audit) == ["PYSEC-2026-3740"]

    scan = workflow["jobs"]["secret-scan"]
    assert scan["env"]["GITLEAKS_VERSION"] == "8.30.1"
    assert re.fullmatch(r"[0-9a-f]{64}", scan["env"]["GITLEAKS_SHA256"])
    checkout = scan["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0
    scan_runs = _runs(workflow, "secret-scan")
    assert "sha256sum --check --strict" in scan_runs
    assert "gitleaks git --redact" in scan_runs
