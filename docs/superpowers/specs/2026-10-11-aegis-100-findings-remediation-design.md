---
title: AEGIS 100-finding audit and full remediation of verbal-fluency-iq
status: draft — awaiting review
date: 2026-10-11
path: architectural
---

# AEGIS 100-finding audit and full remediation

## 1. Intent (agreed)

| Item | Decision |
|---|---|
| Goal | Run AEGIS against this project, produce exactly 100 verified findings (logical fallacies, engineering gaps, new features), and complete **all 100**. |
| Use case / threat model | **Screening people (hiring, admissions).** Every output may influence a decision about a third party. Severity is judged against that. |
| Baseline | Finish and commit `fix/indonesian-syntactic-bias` first; audit the resulting code. |
| Licensing | Project becomes **proprietary / closed source** (InfraLoka). |
| Method | Audit-first, then risk-ordered phased remediation (Approach A). |

### Definition of "complete" per finding

Not every finding is fixable by code. Each finding carries a `fixability` and is complete when its acceptance check passes:

- `code` — behaviour change + automated test that fails before and passes after.
- `guardrail` — the code cannot make the claim true (e.g. "scores are not validated against real IQ tests"), so completion = the system refuses, warns, or degrades honestly, enforced by a test.
- `process` — requires a human/organisational artefact (validation study protocol, DPIA, consent text, legal opinion). Completion = the artefact is written in `docs/` and the code references or enforces it (e.g. a config gate). Results that require real-world data collection are scoped as a protocol, not fabricated data.

## 2. Phase 0 — Baseline and closed-source conversion

1. Run `pytest`; finish `docs/plans/2026-06-15-001-…` on `fix/indonesian-syntactic-bias`; commit.
2. New branch `chore/proprietary-license`:
   - Replace `LICENSE` (GPL-3.0) with an InfraLoka proprietary "All rights reserved" license.
   - Add copyright header to every source file; update README license/ethics sections; remove open-source contribution language.
   - Note in README that versions previously published under GPL-3.0 remain GPL for existing recipients.
3. Repo visibility → private: **manual by owner** (GitHub account currently returns 403 suspended). Not automated.

All git pushes/PRs require explicit owner confirmation at that moment.

## 3. Phase 1 — AEGIS audit

### Panel

| Engine | Persona | Target category | Approx. count |
|---|---|---|---|
| Module [F] | Data Detective | statistical / data fallacies | 12 |
| Module [F] | Skeptical Economist (→ psychometrician) | causal & construct-validity fallacies | 12 |
| Module [F] | Pragmatist | fairness, distributional, decision-use fallacies | 11 |
| Module [H] | CTO | engineering gaps (architecture, tests, perf, observability) | 20 |
| Module [H] | CRO | compliance / risk gaps (UU PDP, consent, audit, adverse impact) | 12 |
| Module [H] | Advanced Hacker | security gaps (input, MCP surface, deps, prompt injection via text) | 8 |
| Module [H] | CEO | new features | 25 |

Counts are targets; after de-duplication the total is trimmed or topped up to **exactly 100 verified** findings. No padding: every finding cites `file:line` or an explicit absence.

### Finding schema (`docs/audit/findings.schema.json`)

```json
{
  "id": "F-001 | G-001 | N-001",
  "category": "fallacy | gap | feature",
  "persona": "string",
  "severity": "P0 | P1 | P2 | P3",
  "title": "string",
  "claim": "what is wrong / missing",
  "evidence": [{"file": "path", "line": 0, "excerpt": "string"}],
  "impact_on_screened_person": "string",
  "fixability": "code | guardrail | process",
  "fix": "intended change",
  "acceptance_test": "test name or check that proves completion",
  "phase": 2,
  "status": "open | done",
  "depends_on": ["id"]
}
```

Severity: **P0** = can cause an unfair or unaccountable decision about a person, or a security/legal breach; **P1** = materially wrong score or missing core control; **P2** = quality/robustness; **P3** = polish/feature nicety.

### Outputs

- `docs/audit/2026-10-11-aegis-findings.json` — source of truth, validated against the schema.
- `docs/audit/2026-10-11-aegis-report.md` — conclusion-first, panel composite score and verdict (module [H] weights), ranked findings table.
- `scripts/audit_status.py` — prints done/open counts by phase; used as the completion gate (`100/100 done`).

Seed findings already observed (to be verified in the audit):
- `mcp-server/tools/mapper.py` VFS weights 0.35/0.25/0.25/0.15 are hand-set, never fitted.
- IQ band mapping in `config/iq_norms.json` has no validation provenance.
- `ci_half = 15 - confidence*10` shrinks the CI with text length — false precision on an unvalidated proxy.

## 4. Phases 2–5 — Remediation

Phases run in order; within a phase, findings are grouped into batches of ~5–10 by touched module to avoid conflicts in `mapper.py` / `reporter.py`.

| Phase | Scope | Exit gate |
|---|---|---|
| 2 | Validity & fairness fallacies (scoring honesty, CI, cross-language normalisation, decision guards) | all `phase=2` done; golden-score diff reviewed |
| 3 | Engineering gaps (tests, config, errors, input limits, security, observability) | all `phase=3` done; coverage ≥ 80% |
| 4 | Screening compliance (consent, audit log, human-in-the-loop, adverse-impact report, data retention, DPIA docs) | all `phase=4` done |
| 5 | New features | all `phase=5` done; `audit_status.py` reports 100/100 |

Each phase gets its own implementation plan (`docs/superpowers/plans/`) via writing-plans, executed with TDD; one branch + PR per phase.

### Design principles for fixes

- Deterministic tools stay deterministic; the AI never estimates scores.
- Any change to scoring output is accompanied by a **golden-score regression fixture** over `example/*/source`, so score shifts are explicit and reviewed, never accidental.
- Screening outputs must never present a bare IQ number as a decision: reports carry uncertainty, validity status, and a mandatory human-review flag (exact form decided by Phase 2/4 findings).
- New features follow existing module boundaries (`mcp-server/tools/*.py`, one `@mcp.tool()` per capability); large files are split if a phase grows them past ~300 lines.

## 5. Testing

- Existing suite must stay green at every commit.
- New: golden-score fixtures, per-finding tests named `test_<finding_id>_*`, schema validation of the findings JSON in CI, `audit_status.py` gate in CI.
- `.github/` workflow updated to run all of the above.

## 6. Risks

- **Score churn**: Phase 2 will change IQ outputs for every example; mitigated by golden fixtures and explicit review.
- **Scale**: 100 items is multi-week; phased PRs keep each review tractable.
- **Process items cannot produce real validation data**; they deliver protocols and enforcement gates, and the report states the system remains unvalidated until that study is run.
- **Verdict honesty**: the audit may conclude the tool is unfit for screening; that verdict is reported as found, not softened.
