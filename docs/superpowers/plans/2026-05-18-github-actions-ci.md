# GitHub Actions CI Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-job parallel CI pipeline (lint, typecheck, test) that runs on every push and PR targeting main.

**Architecture:** A single `.github/workflows/ci.yml` defines three independent jobs — `lint`, `typecheck`, and `test` — that run concurrently on ubuntu-latest. Dev tools (ruff, mypy) live in a new `requirements-dev.txt` separate from production deps. Each job caches pip against its own requirements file hash so the lean lint/typecheck jobs don't pull ML dependencies. The test job additionally caches `~/.cache/huggingface` to avoid re-downloading the sentence-transformers model on every run.

**Tech Stack:** GitHub Actions (actions/checkout@v4, actions/setup-python@v5, actions/cache@v4), ruff, mypy, pytest, spaCy en_core_web_sm

---

### Task 1: Create requirements-dev.txt

**Files:**
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create the file**

  Create `requirements-dev.txt` at the project root with this exact content:

  ```
  ruff>=0.4.0
  mypy>=1.10.0
  ```

- [ ] **Step 2: Install dev tools locally and verify**

  ```bash
  pip install -r requirements-dev.txt
  ruff --version
  mypy --version
  ```

  Expected: both print version strings without errors.

- [ ] **Step 3: Run ruff check to establish baseline**

  ```bash
  ruff check mcp-server/ tests/
  ruff format --check mcp-server/ tests/
  ```

  If violations appear, fix them now (see Task 2) so the CI lint job passes on first push. If output is empty — all clean, proceed.

- [ ] **Step 4: Run mypy to establish baseline**

  ```bash
  mypy mcp-server/ --ignore-missing-imports
  ```

  Expected: `Success: no issues found` or only notes about missing stubs (suppressed by `--ignore-missing-imports`). If real type errors appear in project code, fix them before proceeding.

- [ ] **Step 5: Commit**

  ```bash
  git add requirements-dev.txt
  git commit -m "chore: add requirements-dev.txt with ruff and mypy"
  ```

---

### Task 2: Fix ruff violations (run only if Task 1 Step 3 reported issues)

**Files:**
- Modify: any files flagged by ruff in Task 1

- [ ] **Step 1: Auto-fix safe violations**

  ```bash
  ruff check mcp-server/ tests/ --fix
  ruff format mcp-server/ tests/
  ```

- [ ] **Step 2: Verify clean**

  ```bash
  ruff check mcp-server/ tests/
  ruff format --check mcp-server/ tests/
  ```

  Expected: no output (zero violations).

- [ ] **Step 3: Commit**

  ```bash
  git add mcp-server/ tests/
  git commit -m "style: apply ruff formatting and lint fixes"
  ```

---

### Task 3: Create the CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the directory**

  ```bash
  mkdir -p .github/workflows
  ```

- [ ] **Step 2: Write ci.yml**

  Create `.github/workflows/ci.yml` with this exact content:

  ```yaml
  name: CI

  on:
    push:
      branches: ["**"]
    pull_request:
      branches: [main]

  jobs:
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - uses: actions/setup-python@v5
          with:
            python-version: "3.14"

        - uses: actions/cache@v4
          with:
            path: ~/.cache/pip
            key: ${{ runner.os }}-pip-dev-${{ hashFiles('requirements-dev.txt') }}
            restore-keys: |
              ${{ runner.os }}-pip-dev-

        - name: Install dev dependencies
          run: pip install -r requirements-dev.txt

        - name: Lint
          run: ruff check mcp-server/ tests/

        - name: Format check
          run: ruff format --check mcp-server/ tests/

    typecheck:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - uses: actions/setup-python@v5
          with:
            python-version: "3.14"

        - uses: actions/cache@v4
          with:
            path: ~/.cache/pip
            key: ${{ runner.os }}-pip-dev-${{ hashFiles('requirements-dev.txt') }}
            restore-keys: |
              ${{ runner.os }}-pip-dev-

        - name: Install dev dependencies
          run: pip install -r requirements-dev.txt

        - name: Type-check
          run: mypy mcp-server/ --ignore-missing-imports

    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - uses: actions/setup-python@v5
          with:
            python-version: "3.14"

        - uses: actions/cache@v4
          with:
            path: ~/.cache/pip
            key: ${{ runner.os }}-pip-prod-${{ hashFiles('requirements.txt') }}
            restore-keys: |
              ${{ runner.os }}-pip-prod-

        - uses: actions/cache@v4
          with:
            path: ~/.cache/huggingface
            key: ${{ runner.os }}-hf-${{ hashFiles('requirements.txt') }}

        - name: Install dependencies
          run: pip install -r requirements.txt

        - name: Download spaCy model
          run: python -m spacy download en_core_web_sm

        - name: Run tests
          run: pytest tests/ -v
  ```

- [ ] **Step 3: Validate YAML syntax**

  ```bash
  python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML valid')"
  ```

  Expected: `YAML valid`

- [ ] **Step 4: Commit**

  ```bash
  git add .github/workflows/ci.yml
  git commit -m "ci: add parallel lint, typecheck, and test jobs"
  ```

---

### Task 4: Push and verify

- [ ] **Step 1: Push to remote**

  ```bash
  git push origin master
  ```

- [ ] **Step 2: Open GitHub Actions**

  Go to `https://github.com/<owner>/verbal-fluency-iq/actions`

  Expected: three jobs (`lint`, `typecheck`, `test`) appear and run in parallel.

- [ ] **Step 3: Confirm all three pass**

  All three jobs show green. First run of `test` takes 4–6 min (sentence-transformers downloads ~500 MB). Cached runs take ~90 s.

  If any job fails, read the step log and fix before marking this task done.
