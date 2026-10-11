# AEGIS Phase 2 — Validity & Fairness Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all 33 phase-2 findings (F-001 to F-033) so that no output presents an unvalidated text statistic as a measurement of a person: IQ, percentile and mental age are withheld unless a documented validation passes, inputs that cannot support the measurement are refused with a status and reasons, and the component metrics stop rewarding length, typos, register and missing punctuation.

**Architecture:** A new policy layer (`mcp-server/tools/policy.py` + `mcp-server/config/validation.json`) evaluates every input gate once and returns a *gate* dict (`status`, `reasons`, permissions). `predict_iq`, the text complexity band and the reporter consume that gate, so nothing can emit IQ without passing it; the only switch is the config file. The lexical, semantic and Indonesian syntactic analysers are corrected in place, the mapper renormalises unavailable components and derives percentile from the normal CDF, and `scripts/pipeline.run_pipeline`, `mcp-server/server.py` and `.agent/` expose the new keys. A synthetic reference corpus drives the length-invariance test and a published component-correlation report.

**Tech Stack:** Python 3.14 (`.venv`), spaCy 3 (`en_core_web_sm`, `xx_ent_wiki_sm`), sentence-transformers, lexicalrichness (MTLD), wordfreq (new, bundled en/id data), PySastrawi, langid + langdetect, textstat, numpy, pytest, ruff, mypy.

**Spec:** docs/superpowers/specs/2026-10-11-aegis-100-findings-remediation-design.md

## Global Constraints

- Run everything through the repo venv: `.venv/bin/python`, `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/pip`. Run commands from the repository root.
- Every new `.py` file starts with exactly this first line: `# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.` (`tests/test_license.py` enforces it).
- `ruff check` and `ruff format` must be clean on every file a task touches (each task has a lint step).
- Never read `example/rahmat/` and never open `example/*/source` files. The only code that reads `example/{aqilah,bimo,fabhian}/source/1.md` is `scripts/capture_golden.py`, run once in Task 12.
- `git add` only the paths listed in the task (never `git add -A` / `git add .`). Never push. Every commit message ends with the trailer line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `mcp-server/config/validation.json` is exactly: `{"version": "2026-10-11", "languages": {"en": {"iq_validated": false, "education_validated": false}, "id": {"iq_validated": false, "education_validated": false}}, "min_words": 250, "min_lang_confidence": 0.80, "max_mixed_language_share": 0.20, "max_words_per_terminal_mark": 40, "uncalibrated_range_half_width": 25, "min_drift_transitions": 5}`.
- Statuses, highest precedence first: `UNSUPPORTED_LANGUAGE`, `MIXED_LANGUAGE`, `INSUFFICIENT_TEXT`, `INSUFFICIENT_STRUCTURE`, `UNVERIFIED_PROVENANCE`, `UNVALIDATED`; `OK` when none triggers. Every pipeline result carries `status` and `reasons: list[str]` (each reason is prefixed `"<STATUS>: "`).
- `provenance` ∈ `supervised_unaided | unsupervised | unknown`; `text_type` ∈ `formal_prose | informal | unknown`; any other value raises `ValueError`.
- No per-call override can enable IQ. Functions accept an injected `policy` dict so tests can mark a language validated; production code only reads the config.
- Nothing is ever labelled "95% CI". Heuristic confidences are never formatted as percentages.
- One new dependency only: `wordfreq>=3.1.1` (Task 6). No new model downloads.
- Test names: each finding's `acceptance_test` from `docs/audit/2026-10-11-aegis-findings.json` is the test function name (see the map below). An existing test that asserts old behaviour is updated in the same task that changes the behaviour.
- After every task the full suite is green and `scripts/audit_status.py` exits 0. From Task 2 to Task 12 the golden comparison `test_golden_scores_match` is marked `xfail(strict=False)`; Task 12 recaptures the fixture once and removes the marker.
- `scripts/audit_status.py` fails if an open finding cites a line beyond the end of a file. Until Task 12 these files must keep at least this many lines: `README.md` 904, `mcp-server/tools/reporter.py` 286, `mcp-server/tools/syntactic.py` 240, `mcp-server/server.py` 156, `mcp-server/tools/semantic.py` 143, `mcp-server/tools/mapper.py` 134, `mcp-server/tools/preprocess.py` 93, `mcp-server/tools/lexical.py` 84, `mcp-server/tools/readability.py` 62, `.agent/SKILL.md` 53, `mcp-server/config/iq_norms.json` 34, `scripts/pipeline.py` 33, `tests/test_golden.py` 36; after Task 12 the phase 3–5 floors still apply (`README.md` 904, `reporter.py` 277, `syntactic.py` 200, `server.py` 156, `semantic.py` 143, `mapper.py` 98, `preprocess.py` 85, `lexical.py` 84, `iq_norms.json` 34, `.agent/SKILL.md` 53). `mcp-server/config/edu_norms.json` must keep existing (G-017 cites it), which is why it is rewritten rather than renamed. The code in this plan satisfies every floor; do not shorten these files beyond it.
- `mcp-server/server.py` and `.agent/` change only in Task 12 (binding decision D10). Between Task 3 and Task 12 `server.py` calls superseded signatures; no test imports it, and Task 12 runs `mypy`. The installed `mcp` 2.x has no `mcp.server.fastmcp`, so the pre-existing mypy error `Module "mcp.server.fastmcp" has no attribute "FastMCP"` remains (out of scope); no other mypy error is acceptable.
- `syntactic.py` and `reporter.py` end above the ~300-line split guideline. They are not split in this phase because the line floors above would break `audit_status.py`; most of the growth in `syntactic.py` is word lists.

## Review Focus

1. **Malay or regional-language text that looks Indonesian** (Malay "bahawa/kerajaan", Javanese, Sundanese): a person expects it to be refused, not scored as Indonesian. Pinned by `test_malay_is_not_scored_as_indonesian` and the Javanese case of `test_pipeline_refuses_scoring_for_unsupported_or_low_confidence_language` (Task 5).
2. **Text with no alphabetic words** (empty string, whitespace, emoji, a column of numbers): expected to return no style index and no screening field, without an exception. Pinned by `test_pipeline_returns_no_style_index_for_text_without_words` (Task 5).
3. **Informal Indonesian that writes locative "di" solid** ("dirumah", "dikantor"): expected not to count as passive, while suffixed passives ("dijalankan", "dirumahkan") still do. Pinned by `test_id_locative_written_solid_is_not_passive_but_suffixed_form_is` (Task 8).
4. **Callers that skip the gate** (`predict_iq(..., gate=None)` with a validated config, or `tool_predict_iq` without `gate_json`): expected to withhold IQ. Pinned by `test_predict_iq_without_gate_is_withheld_even_when_validated` (Task 3) and `test_server_chain_without_gate_refuses_iq` (Task 12).
5. **Mistyped provenance or text type** (`"self-reported"`, `"essay"`): expected to be rejected loudly, not silently treated as `unknown`. Pinned by `test_invalid_enum_values_are_rejected` (Task 2) and the `ValueError` case in `test_pipeline_withholds_iq_without_supervised_unaided_provenance` (Task 5).

---

## Decisions this plan records

Binding decisions D1–D12 are implemented as given, with these refinements and the two acceptance-test changes D7/D8 allowed. Each was found while prototyping the plan's code against the repository:

1. **F-023 acceptance test changed** to `test_syntactic_scores_flagged_not_comparable_across_languages` (Task 8). English syntax is scored from spaCy dependency labels and Indonesian from a conjunction lexicon; no equating study exists. A parallel-text tolerance test would either be tuned to one hand-picked pair (a fudged tolerance) or fail. The honest completion is the guardrail: every syntactic result carries `comparable_across_languages: False` and cross-language ranking raises. The equating study belongs to `docs/validation/norming-plan.md`.
2. **F-022 acceptance test changed** to `test_cross_component_effective_weights_and_length_share_reported` (Task 10). On the 12-passage reference corpus the measured `length_share` (R² of the style index on mean sentence length and mean word length) is about 0.87, so "below cap" could only pass with a cap so loose it means nothing. The report publishes the matrix, the effective weights and the share; re-weighting needs the calibration sample.
3. **Language-detection confidence is redefined** (Task 5) as the lower of langid's normalised probability and langdetect's probability for the detected language (0 when they disagree). The old sigmoid of the log-probability margin gave 0.77 for a correct 275-word Indonesian news passage (Malay is always the runner-up), so with `min_lang_confidence` 0.80 it would have refused correct Indonesian far more often than English. The new value is still labelled a heuristic agreement index and never shown as a percent.
4. **Text complexity band availability** (Task 4): available when the text gates pass and the language's readability formulas are native (`READABILITY_NATIVE_LANGUAGES = {"en"}`) or `education_validated` is true. So it is shown for English and unavailable for Indonesian (F-013). It describes the text, so provenance and text type do not gate it; IQ, percentile and mental age are the screening fields those gates govern.
5. **Non-formal `text_type`** has no dedicated status in D1, so it is reported as `UNVALIDATED` with reason `text_type '<value>' is outside the formal-prose scope; IQ is refused`.
6. **Passive rule (F-010)** adds one refinement to D7: a bare `di-` + common place noun (`dirumah`, `dikantor`, …) is the locative written solid, not passive; the same root with `-kan`/`-i` (`dirumahkan`, `dijalankan`) still is. Roots must have at least 4 letters (stops `dinas` → `nas`).
7. **Clause joiners (F-011)**: `dan`/`atau`/`serta` count only when the following segment starts with an overt subject followed by a predicate (shared-subject predicate coordination such as "makan nasi dan minum teh" stays one clause); temporal words count when any predicate follows. This makes the finding's sentence score `clause_density` 1.0. `maka` is added to the clause coordinators so `makanya → maka` normalisation (F-018) is counted like its formal paraphrase.
8. **No style index for unanalysable text** (Task 5): "style outputs always present" applies to analysable text. When the language is unsupported, detection confidence is below the floor, or there are zero alphabetic words, `style_index` is `None` (reporting a number for an empty or Javanese text would be a fabricated measurement).
9. **Golden fixture interim** (Task 2): marked `xfail(strict=False)` because scores change in Tasks 2, 3, 5, 6, 7 and 8; recaptured once in Task 12 with the before/after table in the commit message.

## Finding → task → test

| Finding | Task | Test (acceptance) |
|---|---|---|
| F-001 | 3 | `test_iq_output_requires_validation_flag_and_style_index_label` |
| F-002 | 11 | `test_validation_protocol_names_criterion_sample_subgroups_and_thresholds` (doc check) |
| F-003 | 3 | `test_predict_iq_interval_not_labelled_95ci_without_validation` |
| F-004 | 3 | `test_predict_iq_percentile_consistent_with_normal_cdf` |
| F-005 | 3 | `test_scores_flag_cross_language_norms_unvalidated_and_block_cross_language_ranking` |
| F-006 | 5 | `test_pipeline_refuses_scoring_for_unsupported_or_low_confidence_language` |
| F-007 | 5 | `test_punctuation_only_change_moves_iq_by_less_than_5_points_or_is_refused` |
| F-008 | 5 | `test_pipeline_refuses_iq_for_informal_or_unknown_genre` |
| F-009 | 3 | `test_predict_iq_refused_below_min_word_count` |
| F-010 | 8 | `test_id_passive_not_triggered_by_terjadi_terkait_terbaik_dimana_diantara` |
| F-011 | 8 | `test_id_clause_density_ignores_nominal_coordination_and_temporal_prepositions` |
| F-012 | 7 | `test_semantic_entity_score_independent_of_ner_label_set` |
| F-013 | 4 | `test_estimate_education_unavailable_for_indonesian_without_calibrated_norms` |
| F-014 | 4 | `test_estimate_education_does_not_report_high_confidence_for_conflicting_metrics` |
| F-015 | 6 | `test_lexical_density_uses_content_words_not_length_threshold` |
| F-016 | 3 | `test_compute_vfs_renormalises_weights_when_semantic_unavailable` |
| F-017 | 3 | `test_predict_mental_age_not_reported_for_adults_or_assumed_age` |
| F-018 | 8 | `test_id_syntactic_score_equal_for_formal_and_colloquial_paraphrase` |
| F-019 | 4 | `test_education_output_is_text_complexity_not_degree` |
| F-020 | 9 (gate in 5) | `test_report_includes_provenance_caveat_and_requires_attestation` |
| F-021 | 6 | `test_vfs_stable_across_truncation_lengths_within_tolerance` |
| F-022 | 10 | `test_cross_component_effective_weights_and_length_share_reported` (changed, decision 2) |
| F-023 | 8 | `test_syntactic_scores_flagged_not_comparable_across_languages` (changed, decision 1) |
| F-024 | 6 | `test_misspelled_text_not_scored_higher_than_clean_text_and_flagged_low_reliability` |
| F-025 | 9 | `test_report_and_readme_name_construct_lexical_syntactic_complexity_not_fluency` |
| F-026 | 9 | `test_report_research_section_states_no_individual_validation` |
| F-027 | 11 | `test_norming_plan_defines_population_age_bands_and_language_strata` (doc check) |
| F-028 | 7 | `test_topic_drift_none_when_fewer_than_min_transitions` |
| F-029 | 6 | `test_lexical_diversity_metrics_use_same_token_unit_per_language` |
| F-030 | 7 | `test_semantic_metric_renamed_and_scaling_loaded_per_language` |
| F-031 | 2 | `test_word_count_excludes_numeric_and_symbol_tokens` |
| F-032 | 9 | `test_report_does_not_format_heuristic_confidence_as_percent` |
| F-033 | 3 | `test_band_labels_contain_no_psychometric_terms` |

## File Structure

| Path | Change | Responsibility |
|---|---|---|
| `mcp-server/config/validation.json` | create (T2) | Validity policy: per-language flags and every gate threshold |
| `mcp-server/tools/policy.py` | create (T2) | Statuses, `evaluate_gates`, withholding reason, cross-language guard, shared notice strings |
| `mcp-server/tools/preprocess.py` | modify (T2, T5) | Alphabetic word count, terminal marks; language support + code-switching detection |
| `mcp-server/tools/mapper.py` | modify (T3, T4) | Style index with renormalisation, gated IQ, normal-CDF percentile, mental-age guard, text complexity band |
| `mcp-server/config/iq_norms.json` | rewrite (T3) | Neutral style bands, N(100,15), mental-age ceiling |
| `mcp-server/config/edu_norms.json` | rewrite (T4) | Text complexity band thresholds (file name kept) |
| `mcp-server/tools/lexical.py` | rewrite (T6) | MATTR + MTLD + content-word density on dictionary words; OOV reliability flag |
| `mcp-server/tools/semantic.py` | rewrite (T7) | Adjacent-sentence similarity with per-language scaling; drift gated by transitions; entities informational |
| `mcp-server/config/semantic_scaling.json` | create (T7) | Per-language similarity scaling, marked uncalibrated |
| `mcp-server/tools/syntactic.py` | rewrite (T8) | Indonesian passive/clause heuristics, colloquial normalisation, non-comparability flag |
| `mcp-server/tools/reporter.py` | modify (T3, T4, T6, T7), rewrite (T9) | Report and JSON with status, notice, provenance caveat, Inspired By |
| `mcp-server/server.py` | rewrite (T12) | MCP tools wired to the new signatures, new `tool_evaluate_gates` |
| `.agent/SKILL.md`, `.agent/tools.json` | rewrite (T12) | Vendor-neutral tool sequence and schemas |
| `scripts/pipeline.py` | modify (T2–T7) | `run_pipeline` with gates, status and new keys |
| `scripts/component_correlation.py` | create (T10) | Correlation matrix, effective weights, length share → `docs/validation/effective-weights.md` |
| `docs/validation/validation-protocol.md`, `docs/validation/norming-plan.md` | create (T11) | Process artefacts for F-002 / F-027 |
| `docs/validation/effective-weights.md` | generated (T10) | Published component diagnostics |
| `tests/fixtures/reference_corpus/` | create (T1) | 12 synthetic en/id passages + manifest |
| `tests/helpers.py` | create (T1), extend (T2) | Corpus loader, validated-policy and OK-gate fixtures |
| `tests/test_reference_corpus.py`, `tests/test_policy.py`, `tests/test_gates.py`, `tests/test_component_correlation.py`, `tests/test_validation_docs.py`, `tests/test_server_wiring.py` | create | New test modules |
| `tests/test_{mapper,preprocess,lexical,semantic,syntactic,reporter,pipeline,golden}.py` | modify | Updated with the behaviour they test |
| `requirements.txt` | modify (T6) | `wordfreq>=3.1.1` |
| `README.md` | modify (T9, T12) | Construct naming, limitations, statuses, tool reference |
| `docs/audit/curated.json`, `docs/audit/2026-10-11-aegis-findings.json` | modify (T8, T10, T12) | Two acceptance-test changes; phase 2 marked done |
| `tests/fixtures/golden_scores.json` | recapture (T12) | New pipeline output for the three tracked examples |

---

### Task 1: Synthetic reference corpus and test helpers

Infrastructure for F-007, F-021 and F-022: twelve passages written for this repository (no real person's text), six English and six Indonesian, across academic, news, narrative, instructional, opinion and informal genres.

**Files:**
- Create: `tests/fixtures/reference_corpus/manifest.json` and the 12 `.txt` files listed in it
- Create: `tests/helpers.py`
- Test: `tests/test_reference_corpus.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `tests/helpers.py` with `ROOT: pathlib.Path`, `CORPUS_DIR: pathlib.Path`, `corpus_manifest() -> list[dict]` (each dict has `name`, `lang`, `genre`, `text_type`), `corpus_text(name: str) -> str`. Importing `tests.helpers` also puts `mcp-server` on `sys.path`. Passage names: `en_academic_essay`, `en_news_report`, `en_personal_narrative`, `en_technical_instructions`, `en_opinion`, `en_informal_email`, `id_academic_essay`, `id_news_report`, `id_personal_narrative`, `id_technical_instructions`, `id_opinion`, `id_informal_chat`. `en_academic_essay` has ≥ 600 alphabetic words; every `formal_prose` passage has ≥ 260.

- [ ] **Step 1: Write the failing test**


Create `tests/test_reference_corpus.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re

from tests.helpers import CORPUS_DIR, corpus_manifest, corpus_text

WORD_RE = re.compile(r"[^\W\d_]+")


def test_manifest_lists_twelve_synthetic_passages_in_both_languages():
    passages = corpus_manifest()
    assert len(passages) == 12
    assert {p["lang"] for p in passages} == {"en", "id"}
    assert sum(p["lang"] == "en" for p in passages) == 6
    assert len({p["genre"] for p in passages}) >= 6


def test_every_manifest_entry_has_a_file_and_every_file_is_listed():
    names = {p["name"] for p in corpus_manifest()}
    files = {p.stem for p in CORPUS_DIR.glob("*.txt")}
    assert names == files


def test_formal_passages_meet_minimum_length_for_scoring():
    for p in corpus_manifest():
        n_words = len(WORD_RE.findall(corpus_text(p["name"])))
        if p["text_type"] == "formal_prose":
            assert n_words >= 260, p["name"]
        assert n_words >= 200, p["name"]


def test_long_passage_supports_truncation_to_600_words():
    assert len(WORD_RE.findall(corpus_text("en_academic_essay"))) >= 600
```


Create `tests/helpers.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Shared test helpers: synthetic reference corpus and policy fixtures."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "tests" / "fixtures" / "reference_corpus"

sys.path.insert(0, str(ROOT / "mcp-server"))


def corpus_manifest() -> list[dict]:
    data = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    return data["passages"]


def corpus_text(name: str) -> str:
    return (CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")
```


- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_reference_corpus.py -v
```

Expected: FAIL with `FileNotFoundError` for `tests/fixtures/reference_corpus/manifest.json`.

- [ ] **Step 3: Add the corpus**


Create `tests/fixtures/reference_corpus/manifest.json` with exactly this content:

```json
{
  "description": "Synthetic reference passages written for this repository. No real person's text. Used for length-invariance tests and the component correlation report (F-021, F-022).",
  "passages": [
    {"name": "en_academic_essay", "lang": "en", "genre": "academic_essay", "text_type": "formal_prose"},
    {"name": "en_news_report", "lang": "en", "genre": "news_report", "text_type": "formal_prose"},
    {"name": "en_personal_narrative", "lang": "en", "genre": "personal_narrative", "text_type": "formal_prose"},
    {"name": "en_technical_instructions", "lang": "en", "genre": "technical_instructions", "text_type": "formal_prose"},
    {"name": "en_opinion", "lang": "en", "genre": "opinion", "text_type": "formal_prose"},
    {"name": "en_informal_email", "lang": "en", "genre": "informal_email", "text_type": "informal"},
    {"name": "id_academic_essay", "lang": "id", "genre": "academic_essay", "text_type": "formal_prose"},
    {"name": "id_news_report", "lang": "id", "genre": "news_report", "text_type": "formal_prose"},
    {"name": "id_personal_narrative", "lang": "id", "genre": "personal_narrative", "text_type": "formal_prose"},
    {"name": "id_technical_instructions", "lang": "id", "genre": "technical_instructions", "text_type": "formal_prose"},
    {"name": "id_opinion", "lang": "id", "genre": "opinion", "text_type": "formal_prose"},
    {"name": "id_informal_chat", "lang": "id", "genre": "informal_chat", "text_type": "informal"}
  ]
}
```


Create `tests/fixtures/reference_corpus/en_academic_essay.txt` with exactly this content:

```text
Urban water systems are usually described as engineering problems, but their history suggests that they are equally problems of institutions and trust. When a city builds a reservoir, it is not only moving water from one place to another. It is also making a promise about who will receive that water, at what price, and with what guarantee of safety. The physical network of pipes therefore sits on top of a second network of rules, budgets and expectations, and the two rarely change at the same speed.

Consider the expansion of piped supply in rapidly growing coastal cities. Engineers can estimate future demand from population projections, and they can design treatment plants with a comfortable margin of capacity. What they cannot easily predict is how households will respond when the service is unreliable. If water arrives only a few hours each day, families install storage tanks and private pumps. These devices lower the pressure in the network, which makes the supply even less reliable for neighbours who did not invest. A technical shortfall becomes a social one, because the households with the most money are able to protect themselves while others absorb the cost.

This pattern has encouraged some researchers to argue that reliability matters more than coverage. A network that reaches every street but delivers water irregularly may produce worse outcomes than a smaller network that works continuously. The argument is persuasive, although it is difficult to test. Cities rarely run controlled experiments on their infrastructure, and the data that utilities publish tend to report connections rather than hours of service. As a result, the most important variable is often the one that is least measured.

There is also a financial dimension that is easy to overlook. Utilities that cannot collect enough revenue postpone maintenance, and leaking pipes then waste a large share of the treated water. Losses of thirty or forty percent are common in older systems. Raising tariffs could fund repairs, but political leaders are reluctant to increase prices for a service that residents already consider poor. The utility is caught in a cycle in which low quality justifies low prices and low prices guarantee low quality.

Breaking that cycle usually requires more than a single reform. Some cities have succeeded by dividing the network into districts with separate meters, which allows managers to locate leaks and to show residents that improvements are real. Others have introduced lifeline tariffs, in which the first few cubic metres each month are cheap and larger volumes cost more. These measures do not remove the underlying tension between affordability and cost recovery, yet they make the trade-off visible and therefore open to public debate.

The lesson for planners is that infrastructure should be evaluated as a relationship rather than as an object. A treatment plant can be technically excellent and still fail if the people it serves do not believe that the system will treat them fairly. Conversely, modest technical improvements can produce large benefits when they are accompanied by transparent reporting and predictable rules. Trust, in this sense, is not a soft addition to engineering but one of its operating conditions.

None of this means that technical expertise is unimportant. Hydraulic modelling, materials science and water chemistry remain essential, and poor design can waste resources for decades. The point is rather that technical choices always carry social consequences, and those consequences feed back into the performance of the system. A pipe that is never repaired because nobody trusts the utility enough to pay for it is, in the end, a pipe that does not work.

Future research could make this argument more precise by measuring service hours, household coping costs and public confidence together over several years. Such studies are expensive, but they would allow cities to compare reforms on the outcomes that residents actually experience, instead of on the number of new connections that appear in annual reports.
```


Create `tests/fixtures/reference_corpus/en_news_report.txt` with exactly this content:

```text
The regional transport authority announced on Tuesday that the new light rail line between the harbour district and the northern suburbs will open three months later than planned. Officials blamed delays in the delivery of signalling equipment and a shortage of trained drivers.

The line was originally scheduled to begin passenger service in March. Construction of the twelve stations is almost complete, and test trains have been running on the eastern section since the start of the year. However, the authority said that the signalling system, which allows trains to run safely at short intervals, had arrived from the manufacturer with software faults that must be corrected before the line can carry the public.

The director of the authority told reporters that safety would not be compromised to meet a deadline. She said that engineers were working with the supplier every day and that the revised opening date was realistic. She also confirmed that the project remains within its approved budget, although the cost of the delay is still being calculated.

Local business owners reacted with frustration. A café owner near the planned harbour station said that customers had been avoiding the area because of construction noise and closed roads. He had hoped that the opening of the line would bring new visitors before the summer season. Several shopkeepers said they would ask the city council for temporary support.

Commuter groups were more cautious in their criticism. A spokesperson for a passenger association said that a late opening was better than an unreliable service, but she urged the authority to publish regular progress reports. She noted that residents of the northern suburbs currently spend more than an hour travelling to the city centre by bus during peak times.

The authority has begun recruiting additional drivers and expects the first group of trainees to complete their course in early summer. Free trial rides for residents will be offered on two weekends before the official opening. Further details will be published on the authority's website next month.
```


Create `tests/fixtures/reference_corpus/en_personal_narrative.txt` with exactly this content:

```text
The summer I turned fourteen, my grandmother decided that I should learn to bake bread. She did not ask whether I wanted to learn. She simply woke me at six one morning, handed me an apron that was far too large, and pointed at a bag of flour on the kitchen table.

I remember being annoyed at first. My friends were going to the lake that day, and I could not understand why bread was more important than swimming. My grandmother ignored my complaints. She showed me how to warm the water until it felt like nothing on my wrist, how to wake the yeast with a spoon of sugar, and how to wait. Waiting, she said, was the part that most people got wrong.

The first loaf was a disaster. I had kneaded it too little and baked it too soon, and it came out of the oven as heavy as a stone. I expected her to laugh, but she cut a thick slice, spread butter on it, and ate the whole thing without a word. Then she told me to start again.

By the end of that summer I could make a loaf that rose properly and had a crust that cracked when you pressed it. More importantly, I had learned to pay attention to small signs: the smell of the dough when it was ready, the way it sprang back under a finger, the hollow sound of a finished loaf when you tapped the bottom.

My grandmother died many years ago, but I still bake on Sunday mornings. When my own children complain that they would rather be somewhere else, I hand them an apron that is far too large and tell them that waiting is the part that most people get wrong. They roll their eyes, exactly as I did, and then they stay.
```


Create `tests/fixtures/reference_corpus/en_technical_instructions.txt` with exactly this content:

```text
Before you install the backup agent, make sure that the server has at least two gigabytes of free disk space and that the system clock is synchronised with a reliable time source. Backups that are created with an incorrect clock can be difficult to restore in the right order.

First, download the installation package from the internal software portal. Choose the version that matches the operating system of the server. Do not use packages that were sent by email or copied from another machine, because they may be outdated or modified.

Second, open a terminal with administrator rights and run the installer. The installer will ask for the address of the backup controller and for a registration token. You can find the token in the controller dashboard under the section for new devices. Each token can be used only once and expires after twenty four hours.

Third, select the folders that should be protected. By default the agent includes the system configuration and the user home directories. If the server hosts a database, add the database export folder and schedule the export to run at least thirty minutes before the backup window starts. Copying live database files directly is not supported and may produce corrupted backups.

Fourth, run a test backup. The first backup may take several hours because every file must be copied. Later backups are faster because only changed blocks are transferred. When the test has finished, open the controller dashboard and confirm that the job status is green and that the reported size is reasonable.

Finally, perform a test restore of a single file to a temporary location. A backup that has never been restored should not be trusted. Record the date of the test in the maintenance log and repeat the restore test every three months. If any step fails, collect the agent log file and contact the infrastructure team before making further changes.
```


Create `tests/fixtures/reference_corpus/en_opinion.txt` with exactly this content:

```text
Every few years someone proposes that schools should stop assigning homework, and every few years the proposal is rejected with the same arguments. Homework, we are told, builds discipline, reinforces what was learned in class, and prepares students for the demands of adult life. These claims sound reasonable, but they deserve more scrutiny than they usually receive.

The strongest argument for homework is practice. Skills such as reading fluently or solving equations improve with repetition, and the school day is short. Yet practice is only useful when students know how to do the task correctly. A child who misunderstood the lesson will simply repeat the mistake at home, often without anyone noticing until the next test. In that case homework does not reinforce learning; it reinforces errors.

The discipline argument is weaker still. Students from calm homes with a quiet desk and an available parent can complete assignments easily. Students who share a small room with siblings, or who care for younger children after school, cannot. When teachers grade homework, they are partly grading the home environment. What looks like a lesson in responsibility may in fact be a lesson in inequality.

None of this means that all homework should disappear. Reading for pleasure, short review exercises and projects that students choose themselves can be valuable. The problem is not homework as such but homework that is assigned out of habit, without a clear purpose and without attention to the conditions in which it will be done.

A better policy would ask teachers to justify each assignment in a single sentence: what will the student be able to do afterwards that they could not do before? If the answer is unclear, the assignment should be dropped. Schools could also offer supervised study time at the end of the day, so that every student has a quiet place and an adult to ask.

We rarely question routines that we experienced ourselves as children. That is precisely why this one deserves a fresh look.
```


Create `tests/fixtures/reference_corpus/en_informal_email.txt` with exactly this content:

```text
Hi Sam,

Thanks so much for sending the photos from the weekend, they made me laugh all over again. I still can't believe the tent collapsed twice in one night. Next time we're definitely checking the weather before we leave, and maybe we should practise putting the thing up in the garden first.

Anyway, I wanted to ask about the plan for next month. Are we still going to your cousin's place by the coast? I've told my boss I need the Friday off, so I'm free from Thursday evening. If it's easier, I can drive and pick up Jo on the way, since she lives pretty close to me. Let me know what works for you.

Also, do you still have my blue jacket? I think I left it in your car after we stopped for food on the way home. No rush at all, just bring it next time we meet up.

Oh, and before I forget, my sister is having a small party for her birthday on the twentieth. Nothing fancy, just food and music in her flat. She said you're very welcome to come, and she'd love to meet you properly after hearing all our camping stories. Bring someone if you like.

Work has been a bit crazy this week. We're moving offices, so everything is in boxes and nobody can find anything. I spent half of yesterday looking for a cable that turned out to be in my own bag the whole time. Classic.

Anyway, write back when you have a minute and tell me how the new job is going. I want to hear everything, especially about that manager you mentioned who sends emails at midnight.

Talk soon,
Alex
```


Create `tests/fixtures/reference_corpus/id_academic_essay.txt` with exactly this content:

```text
Pengelolaan sampah di kota besar sering dipahami sebagai persoalan teknis, padahal pengalaman banyak daerah menunjukkan bahwa masalah utamanya terletak pada kelembagaan dan kebiasaan warga. Ketika pemerintah kota membangun tempat pembuangan akhir yang baru, kapasitasnya biasanya dihitung berdasarkan jumlah penduduk dan perkiraan volume sampah. Perhitungan tersebut penting, tetapi tidak cukup untuk menjamin bahwa sistem akan berjalan dengan baik.

Sebagian besar sampah rumah tangga di Indonesia terdiri atas sisa makanan dan bahan organik lain. Jika sampah organik dipisahkan sejak dari rumah, bahan tersebut dapat diolah menjadi kompos atau gas biologis, sehingga beban tempat pembuangan akhir berkurang secara signifikan. Namun, pemilahan di sumber membutuhkan perubahan perilaku yang konsisten. Warga harus menyediakan wadah terpisah, petugas harus mengangkut sampah yang sudah dipilah tanpa mencampurnya kembali, dan pemerintah harus memastikan bahwa hasil pemilahan benar benar dimanfaatkan.

Di banyak kota, salah satu mata rantai itu sering terputus. Warga yang sudah memilah sampah kecewa ketika melihat truk pengangkut mencampur semua kantong menjadi satu. Kekecewaan tersebut membuat mereka berhenti memilah, dan program yang awalnya menjanjikan akhirnya dianggap gagal. Kegagalan seperti ini bukan disebabkan oleh kurangnya teknologi, melainkan oleh lemahnya koordinasi antarlembaga dan rendahnya kepercayaan masyarakat.

Beberapa daerah berhasil memperbaiki keadaan dengan pendekatan bertahap. Program dimulai di satu kelurahan, hasilnya diukur secara terbuka, lalu diperluas ke wilayah lain setelah masalah praktis diselesaikan. Bank sampah yang dikelola oleh warga juga terbukti membantu, karena memberikan imbalan nyata bagi rumah tangga yang menyetorkan bahan daur ulang. Pendekatan ini memperlihatkan bahwa insentif kecil yang dapat dipercaya sering lebih efektif daripada kampanye besar yang tidak diikuti tindakan.

Pelajaran yang dapat diambil adalah bahwa infrastruktur sampah perlu dinilai sebagai hubungan antara pemerintah dan warga, bukan sekadar sebagai bangunan fisik. Teknologi pengolahan tetap diperlukan, tetapi keberhasilannya bergantung pada aturan yang jelas, pelayanan yang dapat diandalkan, serta laporan yang transparan. Penelitian selanjutnya sebaiknya mengukur tingkat pemilahan, biaya pengangkutan, dan kepuasan warga secara bersamaan selama beberapa tahun agar pemerintah daerah dapat membandingkan kebijakan berdasarkan dampak yang benar benar dirasakan masyarakat.
```


Create `tests/fixtures/reference_corpus/id_news_report.txt` with exactly this content:

```text
Pemerintah provinsi mengumumkan pada hari Selasa bahwa pembangunan jalan tol yang menghubungkan kawasan pelabuhan dengan wilayah selatan akan selesai tiga bulan lebih lambat dari jadwal. Keterlambatan tersebut disebabkan oleh proses pembebasan lahan yang belum tuntas dan curah hujan yang tinggi selama awal tahun.

Kepala dinas pekerjaan umum mengatakan bahwa sebagian besar konstruksi sudah mencapai tahap akhir. Jembatan utama telah tersambung, dan pengaspalan di ruas timur sedang dikerjakan. Namun, masih ada beberapa bidang tanah di ruas barat yang belum dibebaskan karena pemiliknya mengajukan keberatan atas nilai ganti rugi.

Menurut kepala dinas, pemerintah tidak akan memaksakan penyelesaian proyek dengan mengorbankan keselamatan atau hak warga. Ia menjelaskan bahwa tim penilai independen telah diminta untuk meninjau kembali harga tanah di lokasi tersebut. Ia juga menegaskan bahwa anggaran proyek masih berada dalam batas yang telah disetujui oleh dewan perwakilan rakyat daerah.

Para pengusaha di sekitar pelabuhan menyatakan kekecewaan mereka. Seorang pemilik usaha angkutan barang mengatakan bahwa kemacetan di jalan lama membuat biaya pengiriman meningkat setiap bulan. Ia berharap jalan tol dapat segera digunakan sehingga waktu tempuh truk dari pelabuhan ke kawasan industri bisa dipersingkat.

Sementara itu, warga yang tanahnya terdampak meminta agar proses musyawarah dilakukan secara terbuka. Mereka menginginkan penjelasan yang rinci mengenai cara perhitungan nilai ganti rugi. Pemerintah provinsi berjanji akan menggelar pertemuan dengan warga pada bulan depan dan mengumumkan perkembangan proyek secara berkala melalui situs resmi.

Pengamat transportasi dari sebuah universitas negeri menilai bahwa keterlambatan ini seharusnya dapat diperkirakan sejak awal. Menurutnya, persoalan pembebasan lahan hampir selalu muncul dalam proyek infrastruktur besar, sehingga jadwal pembangunan perlu memasukkan cadangan waktu yang memadai. Ia menyarankan agar pemerintah menerbitkan peta kemajuan proyek setiap bulan supaya masyarakat dapat mengikuti perkembangan secara langsung.
```


Create `tests/fixtures/reference_corpus/id_personal_narrative.txt` with exactly this content:

```text
Waktu saya berumur dua belas tahun, ayah mengajak saya memancing di sungai dekat desa kakek. Saya tidak terlalu tertarik, karena saya lebih suka bermain sepak bola dengan teman teman. Akan tetapi, ayah sudah menyiapkan dua joran dan sekotak umpan, jadi saya tidak punya alasan untuk menolak.

Kami berangkat sebelum matahari terbit. Udara masih dingin dan jalan setapak menuju sungai licin karena embun. Ayah berjalan di depan sambil membawa senter, sementara saya mengikuti dari belakang dengan perasaan mengantuk. Sesampainya di tepi sungai, ayah menunjukkan cara memasang umpan dan melempar kail ke tengah arus.

Selama hampir dua jam tidak ada satu ikan pun yang memakan umpan kami. Saya mulai bosan dan beberapa kali mengeluh. Ayah hanya tersenyum dan berkata bahwa memancing bukan tentang ikan, melainkan tentang belajar menunggu. Waktu itu saya tidak mengerti maksudnya.

Menjelang siang, joran saya tiba tiba melengkung. Saya menarik dengan panik sampai hampir terjatuh ke air. Ayah membantu saya menahan joran, dan akhirnya seekor ikan nila sebesar telapak tangan berhasil kami angkat. Ikan itu kecil, tetapi saya merasa seperti baru saja menang lomba.

Sekarang ayah sudah tua dan tidak bisa lagi berjalan jauh. Kadang kadang saya mengajak anak saya ke sungai yang sama. Ketika dia mengeluh karena ikan tidak kunjung datang, saya tersenyum dan mengulang kata kata ayah. Dia pasti belum mengerti, sama seperti saya dulu, tetapi saya yakin suatu hari dia akan mengerti.

Kenangan pagi itu masih sering muncul ketika saya merasa tidak sabar di tempat kerja. Banyak hal penting dalam hidup ternyata membutuhkan waktu, dan hasilnya tidak selalu besar. Namun, seperti ikan kecil yang kami tangkap hari itu, hasil yang sederhana pun bisa terasa sangat berharga jika kita bersedia menunggu dengan sabar.
```


Create `tests/fixtures/reference_corpus/id_technical_instructions.txt` with exactly this content:

```text
Sebelum memasang aplikasi kasir di komputer toko, pastikan komputer tersebut memiliki ruang penyimpanan kosong minimal dua gigabita dan tersambung ke jaringan internet yang stabil. Periksa juga tanggal dan jam pada komputer, karena transaksi yang tercatat dengan waktu yang salah akan menyulitkan proses pembukuan.

Langkah pertama adalah mengunduh berkas pemasangan dari portal resmi perusahaan. Pilih versi yang sesuai dengan sistem operasi komputer Anda. Jangan menggunakan berkas yang dikirim melalui pesan pribadi atau disalin dari komputer lain, karena berkas tersebut mungkin sudah usang atau telah diubah.

Langkah kedua adalah menjalankan berkas pemasangan dengan hak akses administrator. Aplikasi akan meminta kode toko dan kata sandi awal. Kode toko dapat dilihat pada halaman pengaturan di dasbor pusat. Setiap kode hanya dapat digunakan satu kali dan akan kedaluwarsa dalam waktu dua puluh empat jam.

Langkah ketiga adalah menghubungkan printer struk dan laci uang. Sambungkan kabel printer ke komputer, kemudian pilih jenis printer pada menu perangkat. Lakukan cetak percobaan untuk memastikan bahwa ukuran kertas dan posisi tulisan sudah benar. Jika hasil cetakan terpotong, ubah pengaturan lebar kertas sebelum mencoba lagi.

Langkah keempat adalah memasukkan daftar barang. Anda dapat mengetik data satu per satu atau mengimpor berkas lembar kerja yang disediakan oleh kantor pusat. Setelah data dimasukkan, periksa kembali harga dan stok beberapa barang secara acak.

Terakhir, lakukan transaksi percobaan dan batalkan transaksi tersebut. Catat tanggal percobaan di buku pemeliharaan. Apabila salah satu langkah gagal, simpan berkas catatan aplikasi dan hubungi tim dukungan teknis sebelum melakukan perubahan lain.

Sebagai tambahan, buatlah salinan cadangan data penjualan setiap akhir pekan. Simpan salinan tersebut di media penyimpanan terpisah yang tidak selalu tersambung ke komputer kasir. Dengan cara ini, data toko tetap aman apabila komputer rusak atau terserang perangkat lunak berbahaya.
```


Create `tests/fixtures/reference_corpus/id_opinion.txt` with exactly this content:

```text
Setiap kali musim penerimaan siswa baru tiba, perdebatan tentang sistem zonasi kembali muncul. Sebagian orang tua merasa dirugikan karena anak mereka tidak dapat bersekolah di sekolah favorit yang letaknya jauh dari rumah. Sebagian lain menganggap zonasi sebagai langkah penting untuk mengurangi kesenjangan antar sekolah. Kedua pandangan ini memiliki alasan yang masuk akal, tetapi perdebatan sering berhenti pada keluhan tanpa melihat persoalan yang lebih mendasar.

Alasan terkuat untuk mendukung zonasi adalah pemerataan. Selama bertahun tahun, siswa dengan nilai tinggi berkumpul di sekolah tertentu, sementara sekolah lain kekurangan siswa berprestasi dan kehilangan semangat untuk berkembang. Dengan zonasi, setiap sekolah menerima siswa dengan latar belakang yang lebih beragam. Namun, pemerataan siswa tidak otomatis menghasilkan pemerataan mutu.

Masalahnya, kualitas guru dan fasilitas belum merata. Sekolah di pusat kota umumnya memiliki laboratorium yang lengkap dan guru yang berpengalaman, sedangkan sekolah di pinggiran masih kekurangan buku dan ruang kelas. Jika siswa diwajibkan bersekolah di dekat rumah tanpa perbaikan pada sekolah itu sendiri, kebijakan zonasi justru dapat memindahkan ketidakadilan dari satu kelompok ke kelompok lain.

Oleh karena itu, zonasi sebaiknya tidak diperlakukan sebagai tujuan, melainkan sebagai bagian dari rangkaian kebijakan. Pemerintah perlu menetapkan standar minimum yang jelas untuk setiap sekolah, lalu mengalokasikan anggaran tambahan bagi sekolah yang belum memenuhinya. Rotasi guru yang adil dan pelatihan yang berkelanjutan juga dapat membantu mempersempit jarak mutu.

Orang tua wajar menginginkan pendidikan terbaik bagi anaknya. Tugas kebijakan publik adalah memastikan bahwa sekolah terbaik itu tidak hanya ada di beberapa tempat, tetapi dapat ditemukan di setiap lingkungan.

Pada akhirnya, keberhasilan zonasi tidak dapat diukur hanya dari jumlah siswa yang diterima di sekolah terdekat. Ukuran yang lebih penting adalah apakah kemampuan membaca, menulis, dan berhitung siswa di sekolah pinggiran meningkat dari tahun ke tahun. Data seperti itu seharusnya dikumpulkan dan diumumkan secara rutin, sehingga perdebatan publik dapat berpijak pada bukti, bukan hanya pada kekhawatiran.
```


Create `tests/fixtures/reference_corpus/id_informal_chat.txt` with exactly this content:

```text
Halo Rina, makasih ya udah kirim foto foto dari acara kemarin. Aku ketawa terus liat foto pas tendanya roboh dua kali. Lain kali kita harus cek cuaca dulu sebelum berangkat, biar nggak kehujanan lagi kayak kemarin.

Eh iya, gimana rencana bulan depan? Jadi nggak kita ke rumah sepupumu yang di pantai? Aku udah izin sama bos buat libur hari Jumat, jadi aku bisa berangkat dari Kamis sore. Kalo kamu mau, aku yang nyetir aja, sekalian jemput Dewi soalnya rumahnya deket sama rumahku. Kabarin aja ya enaknya gimana.

Terus jaket biruku masih di kamu nggak? Kayaknya ketinggalan di mobilmu pas kita mampir makan waktu pulang. Santai aja kok, bawa pas kita ketemu lagi aja.

Oh iya, hampir lupa, kakakku mau bikin acara kecil buat ulang tahunnya tanggal dua puluh. Nggak rame kok, cuma makan makan sama dengerin musik di rumahnya. Dia bilang kamu boleh banget dateng, soalnya dia penasaran pengen kenalan setelah denger cerita kemah kita. Kalo mau ajak temen juga boleh.

Kerjaan minggu ini lagi kacau banget. Kantor kita lagi pindahan, jadi semua barang masih di dalam kardus dan nggak ada yang bisa nemu apa apa. Kemarin aku setengah hari nyari kabel, ternyata kabelnya ada di tasku sendiri dari tadi. Parah banget kan.

Udah dulu ya, nanti kalo sempet bales dan ceritain gimana kerjaan barumu. Aku pengen denger semuanya, apalagi soal atasan yang suka kirim pesan tengah malam itu.

Dah,
Mira
```


- [ ] **Step 4: Run the test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_reference_corpus.py -v
```

Expected: 4 passed.


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix tests/helpers.py tests/test_reference_corpus.py
.venv/bin/ruff format tests/helpers.py tests/test_reference_corpus.py
.venv/bin/ruff check tests/helpers.py tests/test_reference_corpus.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_reference_corpus.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: 4 passed in the focused run. The full suite passes; the three `test_golden_scores_match` cases still pass, since no score changed. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/reference_corpus \
  tests/helpers.py \
  tests/test_reference_corpus.py
git commit -m "test(aegis): synthetic en/id reference corpus for phase 2" -m "Twelve synthetic passages (no real person's text) used by the length-invariance, punctuation and component-correlation work in AEGIS phase 2." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 2: Policy module, validation config and status plumbing (F-031)

**Files:**
- Create: `mcp-server/config/validation.json`, `mcp-server/tools/policy.py`
- Modify: `mcp-server/tools/preprocess.py` (word counts, terminal marks), `scripts/pipeline.py` (gates + status), `tests/helpers.py` (policy fixtures)
- Test: `tests/test_policy.py` (new), `tests/test_preprocess.py`, `tests/test_golden.py`

Behaviour changes that break existing tests in this task: `word_count` now counts alphabetic words only, so the golden fixture no longer matches; `run_pipeline` gains keys. Both are updated here (`test_golden.py`).

**Interfaces:**
- Consumes: `tests.helpers` from Task 1.
- Produces (`tools.policy`):
  - constants `OK`, `UNSUPPORTED_LANGUAGE`, `MIXED_LANGUAGE`, `INSUFFICIENT_TEXT`, `INSUFFICIENT_STRUCTURE`, `UNVERIFIED_PROVENANCE`, `UNVALIDATED`, `STATUS_PRECEDENCE: tuple[str, ...]`, `TEXT_STATUSES: frozenset`, `PROVENANCE_VALUES`, `TEXT_TYPE_VALUES`, `READABILITY_NATIVE_LANGUAGES = frozenset({"en"})`, `STYLE_INDEX_LABEL`, `PROVENANCE_CAVEAT`, `NO_INDIVIDUAL_DECISION_NOTICE` (strings), `CrossLanguageComparisonError(ValueError)`.
  - `load_policy(path: str | None = None) -> dict` (fresh deep copy), `iq_validated(lang, policy=None) -> bool`, `education_validated(lang, policy=None) -> bool`, `count_terminal_marks(text: str) -> int`.
  - `evaluate_gates(lang_result: dict, alpha_word_count: int, terminal_mark_count: int, provenance: str = "unknown", text_type: str = "unknown", policy: dict | None = None) -> dict` with keys `status`, `statuses` (list, precedence order), `reasons` (list of `"<STATUS>: message"`), `iq_allowed` (= status is OK), `text_ok`, `education_allowed`, `language_norm_unvalidated`, `lang`, `provenance`, `text_type`, `policy_version`. `lang_result` keys read: `lang`, `confidence`, optional `mixed_language_share`.
  - `withheld_reason(gate: dict | None) -> str | None`, `assert_same_language(results: list[dict]) -> str`, `rank_by_style_index(results: list[dict]) -> list[dict]`.
- Produces (`tools.preprocess.preprocess_text`): result keys `word_count` (alphabetic tokens), `token_count` (old count), `terminal_mark_count`.
- Produces (`tests.helpers`): `validated_policy() -> dict` (shipped policy with every language `iq_validated`/`education_validated` true), `ok_gate(lang: str = "en", policy: dict | None = None) -> dict` (status `OK` under `validated_policy()`).
- Produces (`scripts.pipeline.run_pipeline(text, *, provenance="unknown", text_type="unknown", policy=None)`): adds `status`, `statuses`, `reasons`, `token_count`.

- [ ] **Step 1: Write the failing tests**


Create `tests/test_policy.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.policy import (
    INSUFFICIENT_STRUCTURE,
    INSUFFICIENT_TEXT,
    MIXED_LANGUAGE,
    OK,
    UNSUPPORTED_LANGUAGE,
    UNVALIDATED,
    UNVERIFIED_PROVENANCE,
    CrossLanguageComparisonError,
    assert_same_language,
    count_terminal_marks,
    evaluate_gates,
    load_policy,
    rank_by_style_index,
    withheld_reason,
)

from tests.helpers import ok_gate, validated_policy

CONFIG = pathlib.Path("mcp-server/config/validation.json")
EN_GOOD = {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0}


def _gate(
    lang_result=None,
    words=400,
    marks=20,
    prov="supervised_unaided",
    text_type="formal_prose",
    policy=None,
):
    return evaluate_gates(
        lang_result or EN_GOOD,
        words,
        marks,
        prov,
        text_type,
        policy if policy is not None else validated_policy(),
    )


def test_validation_config_ships_with_every_language_unvalidated():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["version"] == "2026-10-11"
    for lang in ("en", "id"):
        assert cfg["languages"][lang] == {
            "iq_validated": False,
            "education_validated": False,
        }
    assert cfg["min_words"] == 250
    assert cfg["min_lang_confidence"] == 0.80
    assert cfg["max_mixed_language_share"] == 0.20
    assert cfg["max_words_per_terminal_mark"] == 40
    assert cfg["uncalibrated_range_half_width"] == 25
    assert cfg["min_drift_transitions"] == 5


def test_load_policy_returns_independent_copies():
    a = load_policy()
    a["languages"]["en"]["iq_validated"] = True
    assert load_policy()["languages"]["en"]["iq_validated"] is False


def test_default_policy_is_unvalidated_even_when_every_input_is_good():
    gate = evaluate_gates(EN_GOOD, 400, 20, "supervised_unaided", "formal_prose")
    assert gate["status"] == UNVALIDATED
    assert gate["iq_allowed"] is False
    assert gate["language_norm_unvalidated"] is True
    assert any("not validated" in r for r in gate["reasons"])


def test_validated_policy_with_good_inputs_is_ok():
    gate = ok_gate()
    assert gate["status"] == OK
    assert gate["reasons"] == []
    assert gate["iq_allowed"] is True
    assert withheld_reason(gate) is None


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"lang_result": {"lang": "jv", "confidence": 0.99}}, UNSUPPORTED_LANGUAGE),
        ({"lang_result": {"lang": "en", "confidence": 0.6}}, UNSUPPORTED_LANGUAGE),
        (
            {
                "lang_result": {
                    "lang": "en",
                    "confidence": 0.9,
                    "mixed_language_share": 0.4,
                }
            },
            MIXED_LANGUAGE,
        ),
        ({"words": 120}, INSUFFICIENT_TEXT),
        ({"marks": 2}, INSUFFICIENT_STRUCTURE),
        ({"prov": "unknown"}, UNVERIFIED_PROVENANCE),
        ({"prov": "unsupervised"}, UNVERIFIED_PROVENANCE),
        ({"text_type": "informal"}, UNVALIDATED),
        ({"text_type": "unknown"}, UNVALIDATED),
    ],
)
def test_each_gate_sets_its_status_and_blocks_iq(kwargs, expected):
    gate = _gate(**kwargs)
    assert gate["status"] == expected
    assert expected in gate["statuses"]
    assert gate["iq_allowed"] is False
    assert any(r.startswith(expected + ":") for r in gate["reasons"])


def test_status_precedence_and_all_reasons_kept():
    gate = _gate(words=100, marks=1, prov="unknown")
    assert gate["status"] == INSUFFICIENT_TEXT
    assert gate["statuses"] == [
        INSUFFICIENT_TEXT,
        INSUFFICIENT_STRUCTURE,
        UNVERIFIED_PROVENANCE,
    ]
    assert len(gate["reasons"]) == 3


def test_invalid_enum_values_are_rejected():
    with pytest.raises(ValueError):
        _gate(prov="self-reported")
    with pytest.raises(ValueError):
        _gate(text_type="essay")


def test_education_allowed_only_for_calibrated_languages_and_good_text():
    assert _gate()["education_allowed"] is True
    id_gate = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        load_policy(),
    )
    assert id_gate["education_allowed"] is False
    assert _gate(words=100)["education_allowed"] is False
    # Provenance and text type govern IQ, not the descriptive text band.
    assert _gate(prov="unknown")["education_allowed"] is True


def test_withheld_reason_without_gate_refuses():
    assert "no gate" in withheld_reason(None)


def test_count_terminal_marks():
    assert count_terminal_marks("One. Two! Three? Four...") == 4
    assert count_terminal_marks("no punctuation at all") == 0
    assert count_terminal_marks("") == 0


def test_rank_refuses_mixed_languages_and_sorts_same_language():
    en = [{"lang": "en", "style_index": 40.0}, {"lang": "en", "style_index": 60.0}]
    assert [r["style_index"] for r in rank_by_style_index(en)] == [60.0, 40.0]
    assert assert_same_language(en) == "en"
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(en + [{"lang": "id", "style_index": 50.0}])
```


Replace `tests/helpers.py` (adds the policy fixtures):

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Shared test helpers: synthetic reference corpus and policy fixtures."""

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "tests" / "fixtures" / "reference_corpus"

sys.path.insert(0, str(ROOT / "mcp-server"))


def corpus_manifest() -> list[dict]:
    data = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    return data["passages"]


def corpus_text(name: str) -> str:
    return (CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def validated_policy() -> dict:
    """The shipped policy with every language marked validated.

    Only for unit tests of the computed (non-withheld) paths. Production code has
    no per-call override; validation is a config change backed by a study.
    """
    from tools.policy import load_policy

    pol = copy.deepcopy(load_policy())
    for flags in pol["languages"].values():
        flags["iq_validated"] = True
        flags["education_validated"] = True
    return pol


def ok_gate(lang: str = "en", policy: dict | None = None) -> dict:
    """A gate that passes every input check (status OK under validated_policy)."""
    from tools.policy import evaluate_gates

    return evaluate_gates(
        {"lang": lang, "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=400,
        terminal_mark_count=20,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=policy if policy is not None else validated_policy(),
    )
```


Append to the end of `tests/test_preprocess.py`:

```python
def test_word_count_excludes_numeric_and_symbol_tokens():
    result = preprocess_text(
        "Total 12345 67890 2024 100 200 300 400 500 is fine.", "en"
    )
    assert result["word_count"] == 3
    assert result["token_count"] == 11


def test_preprocess_counts_terminal_marks():
    result = preprocess_text("One two. Three four! Five six? Seven", "en")
    assert result["terminal_mark_count"] == 3
```


In `tests/test_golden.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert set(out) == {"lang", "vfs", "iq", "ci", "edu", "word_count"}
    assert len(out["ci"]) == 2
```

   with:

```python
def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert {
        "status",
        "statuses",
        "reasons",
        "lang",
        "word_count",
        "token_count",
    } <= set(out)
    assert out["status"] == "INSUFFICIENT_TEXT"
    assert any(r.startswith("INSUFFICIENT_TEXT:") for r in out["reasons"])
```

2. Replace:

```python
@pytest.mark.parametrize("source", GOLDEN_SOURCES)
```

   with:

```python
# Phase 2 changes scoring in several tasks; the fixture is recaptured once, with a
# reviewed before/after diff, in the final task. Until then a mismatch is expected.
@pytest.mark.xfail(
    reason="AEGIS phase 2 score churn; golden fixture recaptured in Task 12",
    strict=False,
)
@pytest.mark.parametrize("source", GOLDEN_SOURCES)
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_policy.py tests/test_preprocess.py tests/test_golden.py -v
```

Expected: collection ERROR in `tests/test_policy.py` with `ModuleNotFoundError: No module named 'tools.policy'`; `test_word_count_excludes_numeric_and_symbol_tokens` FAILS (`assert 11 == 3`).

- [ ] **Step 3: Implement the policy layer**


Create `mcp-server/config/validation.json` with exactly this content:

```json
{
  "version": "2026-10-11",
  "languages": {
    "en": {"iq_validated": false, "education_validated": false},
    "id": {"iq_validated": false, "education_validated": false}
  },
  "min_words": 250,
  "min_lang_confidence": 0.80,
  "max_mixed_language_share": 0.20,
  "max_words_per_terminal_mark": 40,
  "uncalibrated_range_half_width": 25,
  "min_drift_transitions": 5
}
```


Create `mcp-server/tools/policy.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Validity policy: decides which outputs may be emitted and why others are withheld.

All thresholds come from ``config/validation.json`` (or an injected dict of the same
shape, for unit tests). There is deliberately no per-call override: IQ output for a
language is enabled only by setting ``iq_validated`` in the config after the study in
``docs/validation/validation-protocol.md`` has passed.
"""

import copy
import json
import os
import re

OK = "OK"
UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
MIXED_LANGUAGE = "MIXED_LANGUAGE"
INSUFFICIENT_TEXT = "INSUFFICIENT_TEXT"
INSUFFICIENT_STRUCTURE = "INSUFFICIENT_STRUCTURE"
UNVERIFIED_PROVENANCE = "UNVERIFIED_PROVENANCE"
UNVALIDATED = "UNVALIDATED"

# Highest precedence first. ``status`` is the first triggered entry; every triggered
# status is listed in ``statuses`` and explained in ``reasons``.
STATUS_PRECEDENCE = (
    UNSUPPORTED_LANGUAGE,
    MIXED_LANGUAGE,
    INSUFFICIENT_TEXT,
    INSUFFICIENT_STRUCTURE,
    UNVERIFIED_PROVENANCE,
    UNVALIDATED,
)
# Statuses meaning the text itself cannot support the measurement.
TEXT_STATUSES = frozenset(
    {UNSUPPORTED_LANGUAGE, MIXED_LANGUAGE, INSUFFICIENT_TEXT, INSUFFICIENT_STRUCTURE}
)

PROVENANCE_VALUES = ("supervised_unaided", "unsupervised", "unknown")
TEXT_TYPE_VALUES = ("formal_prose", "informal", "unknown")

# Gunning Fog, ARI and Coleman-Liau were built for English. Other languages need
# ``education_validated`` before a text complexity band is shown (F-013).
READABILITY_NATIVE_LANGUAGES = frozenset({"en"})

STYLE_INDEX_LABEL = (
    "Writing-style index (lexical-syntactic complexity). Not an intelligence measure."
)
PROVENANCE_CAVEAT = (
    "Valid only for supervised, unaided writing produced for the same prompt. "
    "AI assistance, translation, dictation or editing change every score."
)
NO_INDIVIDUAL_DECISION_NOTICE = (
    "Not validated for decisions about individuals (hiring, admissions, "
    "clinical, legal). Human review is mandatory."
)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "validation.json"
)
_TERMINAL_MARK_RE = re.compile(r"[.!?…]+")
_cached: dict | None = None


class CrossLanguageComparisonError(ValueError):
    """Raised when results from different languages are compared or ranked."""


def load_policy(path: str | None = None) -> dict:
    """Return a fresh copy of the validation policy."""
    global _cached
    if path is not None:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    if _cached is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _cached = json.load(f)
    return copy.deepcopy(_cached)


def _resolve(policy: dict | None) -> dict:
    return policy if policy is not None else load_policy()


def iq_validated(lang: str | None, policy: dict | None = None) -> bool:
    flags = _resolve(policy)["languages"].get(lang or "", {})
    return bool(flags.get("iq_validated", False))


def education_validated(lang: str | None, policy: dict | None = None) -> bool:
    flags = _resolve(policy)["languages"].get(lang or "", {})
    return bool(flags.get("education_validated", False))


def count_terminal_marks(text: str) -> int:
    """Count runs of sentence-ending punctuation ('...' counts once)."""
    return len(_TERMINAL_MARK_RE.findall(text or ""))


def _require(value: str, allowed: tuple[str, ...], name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")


def evaluate_gates(
    lang_result: dict,
    alpha_word_count: int,
    terminal_mark_count: int,
    provenance: str = "unknown",
    text_type: str = "unknown",
    policy: dict | None = None,
) -> dict:
    """Apply every input gate and return the status that governs all outputs."""
    pol = _resolve(policy)
    _require(provenance, PROVENANCE_VALUES, "provenance")
    _require(text_type, TEXT_TYPE_VALUES, "text_type")

    lang = lang_result.get("lang")
    confidence = float(lang_result.get("confidence", 0.0))
    mixed = lang_result.get("mixed_language_share")
    issues: list[tuple[str, str]] = []

    if lang not in pol["languages"]:
        supported = ", ".join(sorted(pol["languages"]))
        issues.append(
            (UNSUPPORTED_LANGUAGE, f"language {lang!r} is not supported ({supported})")
        )
    elif mixed is not None and mixed > pol["max_mixed_language_share"]:
        issues.append(
            (
                MIXED_LANGUAGE,
                (
                    f"{mixed:.2f} of words are in a second language "
                    f"(max {pol['max_mixed_language_share']:.2f})"
                ),
            )
        )
    elif confidence < pol["min_lang_confidence"]:
        issues.append(
            (
                UNSUPPORTED_LANGUAGE,
                (
                    f"language detection confidence {confidence:.2f} is below "
                    f"{pol['min_lang_confidence']:.2f}"
                ),
            )
        )

    if alpha_word_count < pol["min_words"]:
        issues.append(
            (
                INSUFFICIENT_TEXT,
                f"{alpha_word_count} words; at least {pol['min_words']} are required",
            )
        )

    words_per_mark = alpha_word_count / max(1, terminal_mark_count)
    if alpha_word_count > 0 and words_per_mark > pol["max_words_per_terminal_mark"]:
        issues.append(
            (
                INSUFFICIENT_STRUCTURE,
                (
                    f"{words_per_mark:.1f} words per sentence-ending mark "
                    f"(max {pol['max_words_per_terminal_mark']}); punctuation is too "
                    "sparse for sentence-length metrics"
                ),
            )
        )

    if provenance != "supervised_unaided":
        issues.append(
            (
                UNVERIFIED_PROVENANCE,
                (
                    f"provenance {provenance!r}: authorship is not attested as "
                    "supervised and unaided"
                ),
            )
        )

    if text_type != "formal_prose":
        issues.append(
            (
                UNVALIDATED,
                (
                    f"text_type {text_type!r} is outside the formal-prose scope; "
                    "IQ is refused"
                ),
            )
        )

    if lang in pol["languages"] and not iq_validated(lang, pol):
        issues.append(
            (
                UNVALIDATED,
                (
                    f"IQ mapping is not validated for language {lang!r} "
                    "(config/validation.json)"
                ),
            )
        )

    triggered = {status for status, _ in issues}
    statuses = [s for s in STATUS_PRECEDENCE if s in triggered]
    status = statuses[0] if statuses else OK
    text_ok = not (triggered & TEXT_STATUSES)
    band_calibrated = lang in READABILITY_NATIVE_LANGUAGES or education_validated(
        lang, pol
    )
    return {
        "status": status,
        "statuses": statuses,
        "reasons": [f"{s}: {msg}" for s, msg in issues],
        "iq_allowed": status == OK,
        "text_ok": text_ok,
        "education_allowed": text_ok and band_calibrated,
        "language_norm_unvalidated": not iq_validated(lang, pol),
        "lang": lang,
        "provenance": provenance,
        "text_type": text_type,
        "policy_version": pol["version"],
    }


def withheld_reason(gate: dict | None) -> str | None:
    """Why screening outputs are withheld, or None when they may be emitted."""
    if gate is None:
        return "no gate evaluation supplied (tools.policy.evaluate_gates)"
    if gate["iq_allowed"]:
        return None
    return "; ".join(gate["reasons"])


def assert_same_language(results: list[dict]) -> str:
    """Return the shared language, or refuse a cross-language comparison (F-005)."""
    langs = {r.get("lang") for r in results}
    if len(langs) != 1 or None in langs:
        shown = sorted(repr(lang) for lang in langs)
        raise CrossLanguageComparisonError(
            f"refusing to compare results across languages {shown}: "
            "per-language norms are not equated"
        )
    return str(langs.pop())


def rank_by_style_index(results: list[dict]) -> list[dict]:
    """Order same-language results by style index (highest first)."""
    assert_same_language(results)
    scored = [r for r in results if r.get("style_index") is not None]
    return sorted(scored, key=lambda r: r["style_index"], reverse=True)
```


Replace `mcp-server/tools/preprocess.py` with (language detection is unchanged in this task; only the counts are new):

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import math
import re

import langid
import spacy
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

from tools.policy import count_terminal_marks

DetectorFactory.seed = 42

_nlp_cache: dict = {}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        nlp = spacy.load(model)
        # xx_ent_wiki_sm has no dependency parser or sentencizer; add one so
        # doc.sents is available for non-English languages.
        if (
            "sentencizer" not in nlp.pipe_names
            and "parser" not in nlp.pipe_names
            and "senter" not in nlp.pipe_names
        ):
            nlp.add_pipe("sentencizer", first=True)
        _nlp_cache[lang] = nlp
    return _nlp_cache[lang]


def _langid_confidence(text: str) -> tuple[str, float]:
    """Return (lang, confidence) from langid using log-prob margin."""
    ranked = langid.rank(text)
    top_lang, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else top_score - 1.0
    margin = top_score - second_score  # always >= 0
    # sigmoid(margin/30): margin ~30 -> 0.73, margin ~5 -> 0.54, large -> ~1.0
    confidence = round(1.0 / (1.0 + math.exp(-margin / 30)), 2)
    return top_lang, confidence


def detect_language(text: str) -> dict:
    if not text or not text.strip():
        return {"lang": "en", "confidence": 0.0}

    ld_failed = False
    try:
        ld_lang = detect(text)
    except LangDetectException:
        ld_lang = None
        ld_failed = True

    li_lang, li_conf = _langid_confidence(text)

    if not ld_failed and ld_lang == li_lang:
        lang = ld_lang
        confidence = round(min(0.95, li_conf + 0.05), 2)
    else:
        lang = li_lang
        confidence = li_conf

    if lang not in ("en", "id"):
        lang = "en"
        confidence = 0.50

    return {"lang": lang, "confidence": confidence}


def preprocess_text(text: str, lang: str) -> dict:
    if lang not in ("en", "id"):
        raise ValueError(f"Unsupported language: {lang!r}. Must be 'en' or 'id'.")
    if not text or not text.strip():
        return {
            "tokens": [],
            "sentences": [],
            "word_count": 0,
            "token_count": 0,
            "terminal_mark_count": 0,
            "sentence_count": 0,
            "text_clean": "",
        }

    cleaned = re.sub(r"http\S+|www\S+", "", text)
    cleaned = re.sub(r"@\w+|#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    nlp = _get_nlp(lang)
    doc = nlp(cleaned)

    sentences = [
        {"idx": i, "text": sent.text.strip()}
        for i, sent in enumerate(doc.sents)
        if sent.text.strip()
    ]
    tokens = [t.text for t in doc if not t.is_space]
    # word_count: alphabetic words only, so numbers, emoji and symbols cannot
    # inflate length-based reliability (F-031). token_count keeps the old count.
    word_count = len([t for t in doc if t.is_alpha])
    token_count = len([t for t in doc if not t.is_space and not t.is_punct])

    return {
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "token_count": token_count,
        "terminal_mark_count": count_terminal_marks(cleaned),
        "sentence_count": len(sentences),
        "text_clean": cleaned,
    }
```


Replace `scripts/pipeline.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_education_level,
    predict_iq,
)
from tools.policy import evaluate_gates, load_policy
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def run_pipeline(
    text: str,
    *,
    provenance: str = "unknown",
    text_type: str = "unknown",
    policy: dict | None = None,
) -> dict:
    pol = policy if policy is not None else load_policy()
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep = preprocess_text(text, lang)
    gate = evaluate_gates(
        lang_r,
        prep["word_count"],
        prep["terminal_mark_count"],
        provenance,
        text_type,
        pol,
    )
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
        "status": gate["status"],
        "statuses": gate["statuses"],
        "reasons": gate["reasons"],
        "lang": lang,
        "vfs": vfs["vfs"],
        "iq": iq["point_estimate"],
        "ci": [iq["ci_low"], iq["ci_high"]],
        "edu": edu["level_code"],
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
    }
```


- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_policy.py tests/test_preprocess.py tests/test_golden.py -v
```

Expected: all pass except `test_golden_scores_match[...]` ×3, which report XFAIL (word counts changed).


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/policy.py mcp-server/tools/preprocess.py scripts/pipeline.py tests/helpers.py tests/test_policy.py tests/test_preprocess.py tests/test_golden.py
.venv/bin/ruff format mcp-server/tools/policy.py mcp-server/tools/preprocess.py scripts/pipeline.py tests/helpers.py tests/test_policy.py tests/test_preprocess.py tests/test_golden.py
.venv/bin/ruff check mcp-server/tools/policy.py mcp-server/tools/preprocess.py scripts/pipeline.py tests/helpers.py tests/test_policy.py tests/test_preprocess.py tests/test_golden.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_policy.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: all `test_policy.py` tests pass. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add mcp-server/config/validation.json \
  mcp-server/tools/policy.py \
  mcp-server/tools/preprocess.py \
  scripts/pipeline.py \
  tests/helpers.py \
  tests/test_policy.py \
  tests/test_preprocess.py \
  tests/test_golden.py
git commit -m "feat(policy): validity gates, statuses and alphabetic word count (AEGIS F-031)" -m "Adds tools/policy.py and config/validation.json (no language validated). run_pipeline now returns status and reasons. word_count counts alphabetic words only; token_count keeps the old count. Golden comparison is xfail until the Task 12 recapture." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 3: Style index, gated IQ, percentile, mental age, neutral bands (F-001, F-003, F-004, F-005, F-009, F-016, F-017, F-033)

**Files:**
- Modify: `mcp-server/tools/mapper.py` (full replacement below; `estimate_education_level` is kept unchanged until Task 4), `mcp-server/config/iq_norms.json`, `mcp-server/tools/reporter.py` (compatibility edits), `scripts/pipeline.py`
- Test: `tests/test_mapper.py` (replaced), `tests/test_reporter.py`, `tests/test_pipeline.py`

Behaviour changes that break existing tests in this task: `predict_iq` signature and keys (`ci_low`/`ci_high` → `range_low`/`range_high`), IQ withheld by default, numeric `confidence` removed from the style-index result, mental age withheld for adults and unknown ages. `test_mapper.py`, `test_reporter.py` and `test_pipeline.py` are updated here.

**Interfaces:**
- Consumes: `tools.policy.STYLE_INDEX_LABEL`, `iq_validated`, `load_policy`, `withheld_reason`, `evaluate_gates`; `tests.helpers.ok_gate`, `validated_policy`.
- Produces (`tools.mapper`):
  - `NOMINAL_WEIGHTS = {"lexical": 0.35, "syntactic": 0.25, "semantic": 0.25, "readability": 0.15}`, `RANGE_LABEL = "uncalibrated heuristic range"`, `MIN_RANGE_HALF_WIDTH = 25`.
  - `compute_verbal_fluency_score(lexical, syntactic, semantic, readability, word_count, lang) -> dict` with keys `vfs`, `style_index` (same value; `None` when every component is `None`), `style_index_label`, `lexical`, `syntactic`, `semantic`, `readability` (each `float | None`), `weights_used`, `unavailable_components`, `confidence_label` (ordinal length tier), `lang`, `text_length_words`. No numeric `confidence`.
  - `iq_percentile(iq: float) -> int` (normal CDF, clamped 1..99).
  - `predict_iq(style_index: float | None, lang: str, gate: dict | None = None, policy: dict | None = None) -> dict` with keys `style_index`, `style_index_label`, `style_band`, `point_estimate`, `range_low`, `range_high`, `range_label`, `classification`, `percentile`, `withheld_reason`, `language_norm_unvalidated`. IQ fields are `None` unless `gate["iq_allowed"]` and the language is `iq_validated`.
  - `predict_mental_age(iq_estimate: float | None, chronological_age: int | None = None) -> dict` with keys `mental_age`, `based_on_chronological_age`, `age_assumed` (always `False`), `withheld_reason`, `formula`.
- Produces (`iq_norms.json`): bands labelled `Style band 1`..`Style band 5`, keys `iq_mean`, `iq_sd`, `max_ratio_mental_age_years`; no `percentile_min`, no `default_chronological_age`.
- Produces (`run_pipeline`): adds keyword `chronological_age: int | None = None` and keys `lang_confidence`, `language_norm_unvalidated`, `provenance`, `text_type`, `policy_version`, `style_index`, `style_index_label`, `style_band`, `components`, `iq`, `percentile`, `classification`, `range`, `range_label`, `withheld_reason`, `mental_age` (`edu` stays until Task 4).

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_mapper.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import math
import pathlib
import re
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_education_level,
    iq_percentile,
    predict_iq,
    predict_mental_age,
)
from tools.policy import (
    CrossLanguageComparisonError,
    evaluate_gates,
    rank_by_style_index,
)

from tests.helpers import ok_gate, validated_policy

MOCK_LEXICAL = {"score": 80.0, "mattr": 0.78, "lexical_density": 0.53, "evidence": []}
MOCK_SYNTACTIC = {"score": 70.0, "clause_density": 2.1, "evidence": []}
MOCK_SEMANTIC = {"score": 72.0, "evidence": []}
MOCK_READABILITY = {"score": 65.0, "gunning_fog": 12.4, "ari": 11.8, "evidence": []}
IQ_NORMS = pathlib.Path("mcp-server/config/iq_norms.json")


def _vfs(word_count=412, **override):
    parts = {
        "lexical": MOCK_LEXICAL,
        "syntactic": MOCK_SYNTACTIC,
        "semantic": MOCK_SEMANTIC,
        "readability": MOCK_READABILITY,
    }
    parts.update(override)
    return compute_verbal_fluency_score(
        parts["lexical"],
        parts["syntactic"],
        parts["semantic"],
        parts["readability"],
        word_count,
        "en",
    )


def test_vfs_returns_required_keys():
    result = _vfs()
    for key in (
        "vfs",
        "style_index",
        "style_index_label",
        "lexical",
        "syntactic",
        "semantic",
        "readability",
        "weights_used",
        "unavailable_components",
        "confidence_label",
        "lang",
        "text_length_words",
    ):
        assert key in result
    assert "confidence" not in result


def test_vfs_weighted_formula():
    expected = 80 * 0.35 + 70 * 0.25 + 72 * 0.25 + 65 * 0.15
    assert abs(_vfs()["vfs"] - expected) < 0.2
    assert _vfs()["style_index"] == _vfs()["vfs"]


def test_confidence_label_very_low_for_short_text():
    assert _vfs(word_count=20)["confidence_label"] == "VERY LOW"


def test_confidence_label_high_for_long_text():
    assert _vfs(word_count=400)["confidence_label"] == "HIGH"


def test_compute_vfs_renormalises_weights_when_semantic_unavailable():
    result = _vfs(semantic={"score": None, "evidence": []})
    expected = (80 * 0.35 + 70 * 0.25 + 65 * 0.15) / 0.75
    assert result["vfs"] == pytest.approx(expected, abs=0.1)
    assert result["semantic"] is None
    assert result["unavailable_components"] == ["semantic"]
    assert "semantic" not in result["weights_used"]
    assert sum(result["weights_used"].values()) == pytest.approx(1.0, abs=1e-3)


def test_compute_vfs_all_components_unavailable_gives_none():
    none = {"score": None}
    assert (
        _vfs(lexical=none, syntactic=none, semantic=none, readability=none)[
            "style_index"
        ]
        is None
    )


def test_iq_output_requires_validation_flag_and_style_index_label():
    default = predict_iq(70.0, "en", gate=ok_gate())
    assert default["point_estimate"] is None
    assert default["percentile"] is None
    assert default["classification"] is None
    assert "not validated" in default["withheld_reason"]
    assert default["style_index"] == 70.0
    assert default["style_band"] == "Style band 4"
    assert "Not an intelligence measure" in default["style_index_label"]

    pol = validated_policy()
    allowed = predict_iq(70.0, "en", gate=ok_gate(policy=pol), policy=pol)
    assert allowed["point_estimate"] == 110
    assert allowed["withheld_reason"] is None
    assert "Not an intelligence measure" in allowed["style_index_label"]


def test_predict_iq_without_gate_is_withheld_even_when_validated():
    result = predict_iq(70.0, "en", gate=None, policy=validated_policy())
    assert result["point_estimate"] is None
    assert "no gate" in result["withheld_reason"]


def test_predict_iq_interval_not_labelled_95ci_without_validation():
    pol = validated_policy()
    result = predict_iq(62.0, "en", gate=ok_gate(policy=pol), policy=pol)
    assert not any("ci" in key.lower() for key in result)
    assert result["range_label"] == "uncalibrated heuristic range"
    assert result["range_high"] - result["point_estimate"] >= 25
    assert result["point_estimate"] - result["range_low"] >= 25
    assert "95%" not in json.dumps(result)
    withheld = predict_iq(62.0, "en", gate=ok_gate())
    assert withheld["range_low"] is None and withheld["range_high"] is None


@pytest.mark.parametrize(
    "vfs", [0.0, 10.0, 39.99, 40.0, 54.99, 55.0, 62.0, 69.99, 70.0, 84.99, 85.0, 100.0]
)
def test_predict_iq_percentile_consistent_with_normal_cdf(vfs):
    pol = validated_policy()
    result = predict_iq(vfs, "en", gate=ok_gate(policy=pol), policy=pol)
    iq = result["point_estimate"]
    expected = 50 * (1 + math.erf((iq - 100) / (15 * math.sqrt(2))))
    assert result["percentile"] == min(99, max(1, round(expected)))


def test_percentile_is_monotone_in_style_index():
    pol = validated_policy()
    gate = ok_gate(policy=pol)
    pcts = [
        predict_iq(v / 10, "en", gate=gate, policy=pol)["percentile"]
        for v in range(0, 1001, 5)
    ]
    assert pcts == sorted(pcts)
    assert iq_percentile(100) == 50


def test_predict_iq_refused_below_min_word_count():
    pol = validated_policy()
    gate = evaluate_gates(
        {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=120,
        terminal_mark_count=8,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=pol,
    )
    result = predict_iq(70.0, "en", gate=gate, policy=pol)
    assert gate["status"] == "INSUFFICIENT_TEXT"
    assert result["point_estimate"] is None
    assert result["percentile"] is None
    assert "INSUFFICIENT_TEXT" in result["withheld_reason"]


def test_predict_mental_age_not_reported_for_adults_or_assumed_age():
    assumed = predict_mental_age(120.0)
    assert assumed["mental_age"] is None
    assert assumed["age_assumed"] is False
    assert "not supplied" in assumed["withheld_reason"]
    adult = predict_mental_age(120.0, 30)
    assert adult["mental_age"] is None
    assert "16" in adult["withheld_reason"]
    assert predict_mental_age(None, 12)["mental_age"] is None
    child = predict_mental_age(120.0, 12)
    assert child["mental_age"] == 14.4
    assert child["withheld_reason"] is None


def test_band_labels_contain_no_psychometric_terms():
    banned = re.compile(
        r"gifted|superior|average|low|below|high|genius|retard|borderline|"
        r"deficien|intellig|impair",
        re.IGNORECASE,
    )
    bands = json.loads(IQ_NORMS.read_text(encoding="utf-8"))["bands"]
    assert len(bands) == 5
    for band in bands:
        assert re.fullmatch(r"Style band [1-5]", band["label"])
        assert not banned.search(band["label"])
    assert "percentile_min" not in json.dumps(bands)


def test_scores_flag_cross_language_norms_unvalidated_and_block_cross_language_ranking():
    for lang in ("en", "id"):
        result = predict_iq(60.0, lang, gate=ok_gate(lang))
        assert result["language_norm_unvalidated"] is True
    assert (
        predict_iq(60.0, "en", gate=None, policy=validated_policy())[
            "language_norm_unvalidated"
        ]
        is False
    )
    mixed = [
        {"lang": "en", "style_index": 60.0},
        {"lang": "id", "style_index": 70.0},
    ]
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(mixed)


def test_estimate_education_s1_level():
    result = estimate_education_level(12.4, 11.8, 0.53, 2.1)
    assert result["level_code"] in ("S1", "S2", "S3", "D3")
    assert "level_en" in result
    assert "level_id" in result
    assert "confidence" in result
```


In `tests/test_reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    "readability": 65.0,
    "confidence": 0.82,
    "confidence_label": "HIGH",
```

   with:

```python
    "readability": 65.0,
    "style_index": 73.4,
    "confidence_label": "HIGH",
```

2. Replace:

```python
IQ = {
    "point_estimate": 117,
    "ci_low": 110,
    "ci_high": 124,
    "classification": "Above Average / Superior",
    "percentile": 79,
}
MENTAL_AGE = {
    "mental_age": 35.1,
    "based_on_chronological_age": 30,
    "age_assumed": True,
    "formula": "mental_age = (iq / 100) * chronological_age",
}
```

   with:

```python
IQ = {
    "style_index": 73.4,
    "style_band": "Style band 4",
    "point_estimate": 117,
    "range_low": 92,
    "range_high": 142,
    "range_label": "uncalibrated heuristic range",
    "classification": "Style band 4",
    "percentile": 87,
    "withheld_reason": None,
    "language_norm_unvalidated": False,
}
IQ_WITHHELD = {
    **IQ,
    "point_estimate": None,
    "range_low": None,
    "range_high": None,
    "classification": None,
    "percentile": None,
    "withheld_reason": "UNVALIDATED: IQ mapping is not validated for language 'en'",
    "language_norm_unvalidated": True,
}
MENTAL_AGE = {
    "mental_age": None,
    "based_on_chronological_age": None,
    "age_assumed": False,
    "withheld_reason": "chronological age not supplied; never assumed",
    "formula": "mental_age = (iq / 100) * chronological_age",
}
```

3. Replace:

```python
def test_report_contains_iq_value():
    result = _call("--report")
    assert "117" in result["report"]
```

   with:

```python
def test_report_contains_iq_value():
    result = _call("--report")
    assert "Point estimate  : 117" in result["report"]
    assert "uncalibrated heuristic range : 92–142" in result["report"]
    assert "95% CI" not in result["report"]


def test_report_shows_withheld_iq_and_mental_age_reasons():
    report = generate_report(
        LANG, PREP, LEXICAL, SYNTACTIC, SEMANTIC, READABILITY, VFS, IQ_WITHHELD,
        MENTAL_AGE, EDU, format_flag="--report",
    )["report"]
    assert "Withheld        : UNVALIDATED" in report
    assert "chronological age not supplied" in report
    assert "Point estimate" not in report
```


In `tests/test_pipeline.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
from tools.mapper import (
    compute_verbal_fluency_score,
    predict_iq,
    predict_mental_age,
    estimate_education_level,
)
from tools.reporter import generate_report
```

   with:

```python
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_education_level,
    predict_iq,
    predict_mental_age,
)
from tools.policy import evaluate_gates
from tools.reporter import generate_report
```

2. Replace:

```python
    prep_r = preprocess_text(text, lang)
    lex_r = analyze_lexical
```

   with:

```python
    prep_r = preprocess_text(text, lang)
    gate = evaluate_gates(lang_r, prep_r["word_count"], prep_r["terminal_mark_count"])
    lex_r = analyze_lexical
```

3. Replace:

```python
    iq_r = predict_iq(vfs_r["vfs"], vfs_r["confidence"])
```

   with:

```python
    iq_r = predict_iq(vfs_r["style_index"], lang, gate=gate)
```

4. Replace:

```python
    assert result["iq"]["point_estimate"] > 0
```

   with:

```python
    assert result["iq"]["style_band"].startswith("Style band")
    assert result["iq"]["point_estimate"] is None  # withheld by default policy
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: collection ERROR in `tests/test_mapper.py` with `ImportError: cannot import name 'iq_percentile' from 'tools.mapper'`.

- [ ] **Step 3: Implement**


Replace `mcp-server/config/iq_norms.json` with exactly this content:

```json
{
  "status": "uncalibrated: hand-set bands with no norm sample (see docs/validation/validation-protocol.md)",
  "note": "Labels are neutral ordinal style bands, not psychometric classifications.",
  "bands": [
    {
      "vfs_min": 85, "vfs_max": 100,
      "iq_min": 125, "iq_max": 145,
      "label": "Style band 5"
    },
    {
      "vfs_min": 70, "vfs_max": 84.99,
      "iq_min": 110, "iq_max": 124,
      "label": "Style band 4"
    },
    {
      "vfs_min": 55, "vfs_max": 69.99,
      "iq_min": 90, "iq_max": 109,
      "label": "Style band 3"
    },
    {
      "vfs_min": 40, "vfs_max": 54.99,
      "iq_min": 75, "iq_max": 89,
      "label": "Style band 2"
    },
    {
      "vfs_min": 0, "vfs_max": 39.99,
      "iq_min": 55, "iq_max": 74,
      "label": "Style band 1"
    }
  ],
  "iq_mean": 100,
  "iq_sd": 15,
  "max_ratio_mental_age_years": 16
}
```


Replace `mcp-server/tools/mapper.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import math
import os

from tools.policy import (
    STYLE_INDEX_LABEL,
    iq_validated,
    load_policy,
    withheld_reason,
)

_iq_norms = None
_edu_norms = None

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

# Nominal component weights of the style index (hand-set; see
# docs/validation/effective-weights.md for what actually drives the index).
NOMINAL_WEIGHTS = {
    "lexical": 0.35,
    "syntactic": 0.25,
    "semantic": 0.25,
    "readability": 0.15,
}
RANGE_LABEL = "uncalibrated heuristic range"
MIN_RANGE_HALF_WIDTH = 25


def _load_iq_norms() -> dict:
    global _iq_norms
    if _iq_norms is None:
        with open(os.path.join(_CONFIG_DIR, "iq_norms.json"), encoding="utf-8") as f:
            _iq_norms = json.load(f)
    return _iq_norms


def _load_edu_norms() -> dict:
    global _edu_norms
    if _edu_norms is None:
        with open(os.path.join(_CONFIG_DIR, "edu_norms.json"), encoding="utf-8") as f:
            _edu_norms = json.load(f)
    return _edu_norms


def _length_label(word_count: int) -> str:
    """Ordinal text-length reliability label (no numeric pseudo-probability)."""
    if word_count < 30:
        return "VERY LOW"
    if word_count < 100:
        return "LOW"
    if word_count < 300:
        return "MEDIUM"
    return "HIGH"


def compute_verbal_fluency_score(
    lexical: dict,
    syntactic: dict,
    semantic: dict,
    readability: dict,
    word_count: int,
    lang: str,
) -> dict:
    """Weighted style index. Unavailable components (score None) are dropped and
    the remaining nominal weights renormalised (F-016), never imputed."""
    scores = {
        "lexical": lexical.get("score"),
        "syntactic": syntactic.get("score"),
        "semantic": semantic.get("score"),
        "readability": readability.get("score"),
    }
    available = {k: v for k, v in scores.items() if v is not None}
    unavailable = sorted(k for k, v in scores.items() if v is None)
    if available:
        total = sum(NOMINAL_WEIGHTS[k] for k in available)
        weights_used = {k: round(NOMINAL_WEIGHTS[k] / total, 4) for k in available}
        vfs: float | None = round(
            sum(available[k] * NOMINAL_WEIGHTS[k] for k in available) / total, 1
        )
    else:
        weights_used = {}
        vfs = None

    return {
        "vfs": vfs,
        "style_index": vfs,
        "style_index_label": STYLE_INDEX_LABEL,
        **scores,
        "weights_used": weights_used,
        "unavailable_components": unavailable,
        "confidence_label": _length_label(word_count),
        "lang": lang,
        "text_length_words": word_count,
    }


def _band_for(style_index: float) -> dict:
    bands = _load_iq_norms()["bands"]
    for b in bands:
        if b["vfs_min"] <= style_index <= b["vfs_max"]:
            return b
    return bands[0] if style_index > bands[0]["vfs_max"] else bands[-1]


def iq_percentile(iq: float) -> int:
    """Percentile of an IQ point under N(100, 15), clamped to 1..99 (F-004)."""
    norms = _load_iq_norms()
    z = (iq - norms["iq_mean"]) / norms["iq_sd"]
    pct = 50.0 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return int(min(99, max(1, round(pct))))


def predict_iq(
    style_index: float | None,
    lang: str,
    gate: dict | None = None,
    policy: dict | None = None,
) -> dict:
    """Style band always; IQ only when the gate allows it (F-001, F-003, F-009).

    ``gate`` is the dict from ``tools.policy.evaluate_gates``. Without a gate,
    IQ is withheld: there is no way to request IQ without passing every check.
    """
    pol = policy if policy is not None else load_policy()
    half_width = max(MIN_RANGE_HALF_WIDTH, int(pol["uncalibrated_range_half_width"]))
    result: dict = {
        "style_index": style_index,
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": None,
        "point_estimate": None,
        "range_low": None,
        "range_high": None,
        "range_label": RANGE_LABEL,
        "classification": None,
        "percentile": None,
        "withheld_reason": None,
        "language_norm_unvalidated": not iq_validated(lang, pol),
    }
    if style_index is None:
        result["withheld_reason"] = "style index unavailable"
        return result

    band = _band_for(style_index)
    result["style_band"] = band["label"]

    reason = withheld_reason(gate)
    if reason is None and not iq_validated(lang, pol):
        reason = f"IQ mapping is not validated for language {lang!r}"
    if reason is not None:
        result["withheld_reason"] = reason
        return result

    band_range = band["vfs_max"] - band["vfs_min"]
    position = (style_index - band["vfs_min"]) / band_range if band_range > 0 else 0.5
    iq_point = round(band["iq_min"] + position * (band["iq_max"] - band["iq_min"]))
    result.update(
        {
            "point_estimate": iq_point,
            "range_low": iq_point - half_width,
            "range_high": iq_point + half_width,
            "classification": band["label"],
            "percentile": iq_percentile(iq_point),
        }
    )
    return result


def predict_mental_age(
    iq_estimate: float | None, chronological_age: int | None = None
) -> dict:
    """Ratio mental age, only for a supplied age <= 16 (F-017). Never assumed."""
    max_age = _load_iq_norms()["max_ratio_mental_age_years"]
    result: dict = {
        "mental_age": None,
        "based_on_chronological_age": chronological_age,
        "age_assumed": False,
        "withheld_reason": None,
        "formula": "mental_age = (iq / 100) * chronological_age",
    }
    if iq_estimate is None:
        result["withheld_reason"] = "IQ estimate withheld"
    elif chronological_age is None:
        result["withheld_reason"] = "chronological age not supplied; never assumed"
    elif chronological_age > max_age:
        result["withheld_reason"] = (
            f"ratio mental age is undefined beyond age {max_age}"
        )
    else:
        result["mental_age"] = round((iq_estimate / 100) * chronological_age, 1)
    return result


def estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> dict:
    norms = _load_edu_norms()
    matched = norms["levels"][-1]
    for level in norms["levels"]:
        if (
            gunning_fog >= level["fog_min"]
            and ari >= level["ari_min"]
            and lexical_density >= level["lexical_density_min"]
        ):
            matched = level
            break

    thresholds_met = sum(
        [
            gunning_fog >= matched["fog_min"] + 1,
            ari >= matched["ari_min"] + 1,
            lexical_density >= matched["lexical_density_min"] + 0.05,
        ]
    )

    if thresholds_met == 3:
        confidence, conf_label = 0.82, "HIGH"
    elif thresholds_met == 2:
        confidence, conf_label = 0.68, "MEDIUM"
    else:
        confidence, conf_label = 0.50, "LOW"

    return {
        "level_en": matched["level_en"],
        "level_id": matched["level_id"],
        "level_code": matched["code"],
        "confidence": confidence,
        "confidence_label": conf_label,
    }
```


In `mcp-server/tools/reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
        slim = {
            "vfs": vfs_result["vfs"],
            "iq": iq_result["point_estimate"],
            "iq_range": f"{iq_result['ci_low']}–{iq_result['ci_high']}",
            "mental_age": mental_age_result["mental_age"],
```

   with:

```python
        slim = {
            "vfs": vfs_result["vfs"],
            "style_band": iq_result["style_band"],
            "iq": iq_result["point_estimate"],
            "iq_range": (
                f"{iq_result['range_low']}–{iq_result['range_high']}"
                if iq_result["range_low"] is not None
                else None
            ),
            "mental_age": mental_age_result["mental_age"],
```

2. Replace:

```python
    line(
        f"  Analysis confidence : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})"
    )
```

   with:

```python
    line(f"  Text length tier    : {vfs_result['confidence_label']}")
```

3. Replace:

```python
    line("  IQ PREDICTION")
    line(thin)
    line(f"  Point estimate  : {iq_result['point_estimate']}")
    line(f"  95% CI range    : {iq_result['ci_low']} – {iq_result['ci_high']}")
    line(f"  Classification  : {iq_result['classification']}")
    line(f"  Percentile      : ~{iq_result['percentile']}th")
    line()
```

   with:

```python
    line("  IQ (EXPERIMENTAL, UNVALIDATED)")
    line(thin)
    line(f"  Style band      : {iq_result['style_band']}")
    if iq_result["point_estimate"] is None:
        line(f"  Withheld        : {iq_result['withheld_reason']}")
    else:
        line(f"  Point estimate  : {iq_result['point_estimate']}")
        line(
            f"  {iq_result['range_label']} : "
            f"{iq_result['range_low']}–{iq_result['range_high']}"
        )
        line(f"  Percentile      : ~{iq_result['percentile']}th")
    line()
```

4. Replace:

```python
    line(f"  Estimated       : {mental_age_result['mental_age']} years")
    if mental_age_result["age_assumed"]:
        line(
            f"  (Chronological age assumed: {mental_age_result['based_on_chronological_age']} | pass --age=N for precision)"
        )
    line()
```

   with:

```python
    if mental_age_result["mental_age"] is None:
        line(f"  Withheld        : {mental_age_result['withheld_reason']}")
    else:
        line(f"  Estimated       : {mental_age_result['mental_age']} years")
    line()
```

5. Replace:

```python
    line(
        f"  [IQ PREDICTION — {iq_result['point_estimate']}, CI: {iq_result['ci_low']}–{iq_result['ci_high']}]"
    )
```

   with:

```python
    line(f"  [STYLE INDEX — {vfs_result['vfs']}, {iq_result['style_band']}]")
```

6. Replace:

```python
    line(
        f"  Overall confidence    : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})"
    )
```

   with:

```python
    line(f"  Text length tier      : {vfs_result['confidence_label']}")
```

7. Replace:

```python
    line("    • Mental age assumes population median if age not supplied")
```

   with:

```python
    line("    • Mental age is reported only for a supplied age of 16 or less")
```


Replace `scripts/pipeline.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_education_level,
    predict_iq,
    predict_mental_age,
)
from tools.policy import STYLE_INDEX_LABEL, evaluate_gates, load_policy
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def run_pipeline(
    text: str,
    *,
    provenance: str = "unknown",
    text_type: str = "unknown",
    chronological_age: int | None = None,
    policy: dict | None = None,
) -> dict:
    pol = policy if policy is not None else load_policy()
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep = preprocess_text(text, lang)
    gate = evaluate_gates(
        lang_r,
        prep["word_count"],
        prep["terminal_mark_count"],
        provenance,
        text_type,
        pol,
    )
    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["style_index"], lang, gate=gate, policy=pol)
    mental = predict_mental_age(iq["point_estimate"], chronological_age)
    edu = estimate_education_level(
        read["gunning_fog"], read["ari"], lex["lexical_density"], syn["clause_density"]
    )
    has_range = iq["range_low"] is not None
    return {
        "status": gate["status"],
        "statuses": gate["statuses"],
        "reasons": gate["reasons"],
        "lang": lang,
        "lang_confidence": lang_r["confidence"],
        "language_norm_unvalidated": gate["language_norm_unvalidated"],
        "provenance": provenance,
        "text_type": text_type,
        "policy_version": gate["policy_version"],
        "style_index": vfs["style_index"],
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": iq["style_band"],
        "components": {
            k: vfs[k] for k in ("lexical", "syntactic", "semantic", "readability")
        },
        "iq": iq["point_estimate"],
        "percentile": iq["percentile"],
        "classification": iq["classification"],
        "range": [iq["range_low"], iq["range_high"]] if has_range else None,
        "range_label": iq["range_label"] if has_range else None,
        "withheld_reason": iq["withheld_reason"],
        "mental_age": mental["mental_age"],
        "edu": edu["level_code"],
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
    }
```


- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: all pass. `iq_norms.json` has 34 lines (a line floor; keep the `note` line).


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff format mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff check mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_mapper.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_mapper.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add mcp-server/config/iq_norms.json \
  mcp-server/tools/mapper.py \
  mcp-server/tools/reporter.py \
  scripts/pipeline.py \
  tests/test_mapper.py \
  tests/test_reporter.py \
  tests/test_pipeline.py
git commit -m "feat(mapper): gate IQ behind validation, neutral style bands, CDF percentile (AEGIS F-001 F-003 F-004 F-005 F-009 F-016 F-017 F-033)" -m "IQ, percentile and classification are withheld unless the gate is OK and the language is validated in config/validation.json. The interval is an uncalibrated heuristic range of at least +/-25, never a 95% CI. Percentile is the normal CDF of the IQ. Unavailable components are dropped with renormalised weights. Mental age only for a supplied age <= 16. Band labels are Style band 1-5. Every IQ result carries language_norm_unvalidated; cross-language ranking raises." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 4: Text complexity band replaces education level (F-013, F-014, F-019)

**Files:**
- Modify: `mcp-server/tools/mapper.py`, `mcp-server/config/edu_norms.json` (rewritten, file name kept), `mcp-server/tools/reporter.py`, `scripts/pipeline.py`
- Test: `tests/test_mapper.py`, `tests/test_reporter.py`, `tests/test_pipeline.py`

Behaviour changes that break existing tests in this task: `estimate_education_level` and its degree codes disappear; the report JSON key `education_level` becomes `text_complexity`. The old education test and fixtures are updated here.

**Interfaces:**
- Consumes: gate dict from `tools.policy.evaluate_gates` (`text_ok`, `education_allowed`, `reasons`).
- Produces (`tools.mapper`): `TEXT_COMPLEXITY_NOTE: str`; `estimate_text_complexity_band(gunning_fog: float, ari: float, lexical_density: float | None, lang: str, gate: dict | None = None, policy: dict | None = None) -> dict` with keys `text_complexity_band` (`int | None`, 1..7), `label` (`"Complexity band N"` or `None`), `per_metric_bands` (`{"gunning_fog", "ari", "lexical_density"}` → int), `consistency` (`"CONSISTENT" | "CONFLICTING" | None`), `withheld_reason`, `note`. No `confidence`, no `level_*` keys.
- Produces (`edu_norms.json`): `{"status", "note", "bands": [{"band", "label", "fog_min", "ari_min", "lexical_density_min"}]}`.
- Produces (`run_pipeline`): `text_complexity_band`, `text_complexity_consistency` replace `edu`.

- [ ] **Step 1: Write the failing tests**


In `tests/test_mapper.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    estimate_education_level,
    iq_percentile,
```

   with:

```python
    estimate_text_complexity_band,
    iq_percentile,
```

2. Replace:

```python
def test_estimate_education_s1_level():
    result = estimate_education_level(12.4, 11.8, 0.53, 2.1)
    assert result["level_code"] in ("S1", "S2", "S3", "D3")
    assert "level_en" in result
    assert "level_id" in result
    assert "confidence" in result
```

   with:

```python
# --- text complexity band ---


def test_estimate_education_does_not_report_high_confidence_for_conflicting_metrics():
    result = estimate_text_complexity_band(20.0, 2.0, 0.7, "en", gate=ok_gate())
    assert result["per_metric_bands"] == {
        "gunning_fog": 7,
        "ari": 1,
        "lexical_density": 7,
    }
    assert result["consistency"] == "CONFLICTING"
    assert result["text_complexity_band"] == 7
    assert "confidence" not in result
    assert "%" not in json.dumps(result)


def test_text_complexity_band_median_of_consistent_metrics():
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "en", gate=ok_gate())
    assert result["per_metric_bands"] == {
        "gunning_fog": 5,
        "ari": 5,
        "lexical_density": 5,
    }
    assert result["text_complexity_band"] == 5
    assert result["label"] == "Complexity band 5"
    assert result["consistency"] == "CONSISTENT"


def test_education_output_is_text_complexity_not_degree():
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "en", gate=ok_gate())
    dumped = json.dumps(result)
    for code in ("S1", "S2", "S3", "SD", "SMP", "SMA", "D3", "Sarjana", "Doctoral"):
        assert code not in dumped
    for key in ("level_en", "level_id", "level_code"):
        assert key not in result
    assert result["label"].startswith("Complexity band")
    assert "not the writer's education" in result["note"]
    norms = pathlib.Path("mcp-server/config/edu_norms.json").read_text(encoding="utf-8")
    assert "Sarjana" not in norms and '"S1"' not in norms


def test_estimate_education_unavailable_for_indonesian_without_calibrated_norms():
    gate = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
    )
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "id", gate=gate)
    assert result["text_complexity_band"] is None
    assert result["label"] is None
    assert "'id'" in result["withheld_reason"]
    calibrated = validated_policy()
    gate_ok = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        calibrated,
    )
    assert (
        estimate_text_complexity_band(
            12.4, 11.8, 0.53, "id", gate=gate_ok, policy=calibrated
        )["text_complexity_band"]
        == 5
    )


def test_text_complexity_band_withheld_below_min_word_count():
    pol = validated_policy()
    gate = evaluate_gates(
        {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=120,
        terminal_mark_count=8,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=pol,
    )
    band = estimate_text_complexity_band(12.0, 11.0, 0.5, "en", gate=gate, policy=pol)
    assert band["text_complexity_band"] is None
    assert "INSUFFICIENT_TEXT" in band["withheld_reason"]
```


In `tests/test_reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
EDU = {
    "level_en": "Undergraduate",
    "level_id": "Sarjana (S1/D4)",
    "level_code": "S1",
    "confidence": 0.68,
    "confidence_label": "MEDIUM",
}
```

   with:

```python
EDU = {
    "text_complexity_band": 5,
    "label": "Complexity band 5",
    "per_metric_bands": {"gunning_fog": 5, "ari": 5, "lexical_density": 5},
    "consistency": "CONSISTENT",
    "withheld_reason": None,
    "note": "Describes how difficult this text is to read, not the writer's "
    "education. Education cannot be inferred from text.",
}
```

2. Replace:

```python
def test_report_contains_evidence_sentence():
```

   with:

```python
def test_report_shows_text_complexity_band_not_education():
    report = _call("--report")["report"]
    assert "TEXT COMPLEXITY BAND" in report
    assert "Band            : Complexity band 5" in report
    assert "EDUCATION LEVEL" not in report
    assert "Sarjana" not in report


def test_report_contains_evidence_sentence():
```


In `tests/test_pipeline.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    estimate_education_level,
    predict_iq,
```

   with:

```python
    estimate_text_complexity_band,
    predict_iq,
```

2. Replace:

```python
    edu_r = estimate_education_level(
        read_r["gunning_fog"],
        read_r["ari"],
        lex_r["lexical_density"],
        syn_r["clause_density"],
    )
```

   with:

```python
    edu_r = estimate_text_complexity_band(
        read_r["gunning_fog"], read_r["ari"], lex_r["lexical_density"], lang, gate=gate
    )
```

3. Replace:

```python
    assert result["edu"]["level_code"] in ("SD", "SMP", "SMA", "D3", "S1", "S2", "S3")
```

   with:

```python
    # No text complexity band for Indonesian (uncalibrated readability, F-013).
    assert result["edu"]["text_complexity_band"] is None
```

4. Replace:

```python
        "education_level",
```

   with:

```python
        "text_complexity",
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: collection ERROR in `tests/test_mapper.py` with `ImportError: cannot import name 'estimate_text_complexity_band' from 'tools.mapper'`.

- [ ] **Step 3: Implement**


Replace `mcp-server/config/edu_norms.json` with exactly this content:

```json
{
  "status": "uncalibrated: hand-set thresholds with no norm sample",
  "note": "Text complexity bands describe how difficult a text is to read. They are not the writer's education level; education cannot be inferred from text.",
  "bands": [
    {"band": 1, "label": "Complexity band 1", "fog_min": 0, "ari_min": 0, "lexical_density_min": 0.0},
    {"band": 2, "label": "Complexity band 2", "fog_min": 5, "ari_min": 4, "lexical_density_min": 0.30},
    {"band": 3, "label": "Complexity band 3", "fog_min": 7, "ari_min": 6, "lexical_density_min": 0.36},
    {"band": 4, "label": "Complexity band 4", "fog_min": 9, "ari_min": 8, "lexical_density_min": 0.42},
    {"band": 5, "label": "Complexity band 5", "fog_min": 11, "ari_min": 10, "lexical_density_min": 0.48},
    {"band": 6, "label": "Complexity band 6", "fog_min": 14, "ari_min": 13, "lexical_density_min": 0.55},
    {"band": 7, "label": "Complexity band 7", "fog_min": 17, "ari_min": 16, "lexical_density_min": 0.60}
  ]
}
```


In `mcp-server/tools/mapper.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
import os

from tools.policy
```

   with:

```python
import os
import statistics

from tools.policy
```

2. Replace:

```python
MIN_RANGE_HALF_WIDTH = 25
```

   with:

```python
MIN_RANGE_HALF_WIDTH = 25
TEXT_COMPLEXITY_NOTE = (
    "Describes how difficult this text is to read, not the writer's education. "
    "Education cannot be inferred from text."
)
```

3. Replace:

```python
def estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> dict:
    norms = _load_edu_norms()
    matched = norms["levels"][-1]
    for level in norms["levels"]:
        if (
            gunning_fog >= level["fog_min"]
            and ari >= level["ari_min"]
            and lexical_density >= level["lexical_density_min"]
        ):
            matched = level
            break

    thresholds_met = sum(
        [
            gunning_fog >= matched["fog_min"] + 1,
            ari >= matched["ari_min"] + 1,
            lexical_density >= matched["lexical_density_min"] + 0.05,
        ]
    )

    if thresholds_met == 3:
        confidence, conf_label = 0.82, "HIGH"
    elif thresholds_met == 2:
        confidence, conf_label = 0.68, "MEDIUM"
    else:
        confidence, conf_label = 0.50, "LOW"

    return {
        "level_en": matched["level_en"],
        "level_id": matched["level_id"],
        "level_code": matched["code"],
        "confidence": confidence,
        "confidence_label": conf_label,
    }
```

   with:

```python
def _metric_band(value: float, key: str, bands: list[dict]) -> int:
    matched = bands[0]["band"]
    for b in bands:
        if value >= b[key]:
            matched = b["band"]
    return matched


def estimate_text_complexity_band(
    gunning_fog: float,
    ari: float,
    lexical_density: float | None,
    lang: str,
    gate: dict | None = None,
    policy: dict | None = None,
) -> dict:
    """Median of per-metric complexity bands (F-014). Describes the text, not the
    writer's education (F-019); unavailable for uncalibrated languages (F-013)."""
    result: dict = {
        "text_complexity_band": None,
        "label": None,
        "per_metric_bands": None,
        "consistency": None,
        "withheld_reason": None,
        "note": TEXT_COMPLEXITY_NOTE,
    }
    if gate is None:
        result["withheld_reason"] = "no gate evaluation supplied"
        return result
    if not gate["text_ok"]:
        result["withheld_reason"] = "; ".join(gate["reasons"])
        return result
    if not gate["education_allowed"]:
        result["withheld_reason"] = (
            f"text complexity bands are not calibrated for language {lang!r}"
        )
        return result

    bands = sorted(_load_edu_norms()["bands"], key=lambda b: b["band"])
    per_metric = {
        "gunning_fog": _metric_band(gunning_fog, "fog_min", bands),
        "ari": _metric_band(ari, "ari_min", bands),
    }
    if lexical_density is not None:
        per_metric["lexical_density"] = _metric_band(
            lexical_density, "lexical_density_min", bands
        )
    values = list(per_metric.values())
    band = int(statistics.median_low(values))
    result.update(
        {
            "text_complexity_band": band,
            "label": next(b["label"] for b in bands if b["band"] == band),
            "per_metric_bands": per_metric,
            "consistency": "CONSISTENT"
            if max(values) - min(values) <= 1
            else "CONFLICTING",
        }
    )
    return result
```


In `mcp-server/tools/reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
            "education": edu_result["level_code"],
```

   with:

```python
            "text_complexity_band": edu_result["text_complexity_band"],
```

2. Replace:

```python
        "education_level": edu_result,
```

   with:

```python
        "text_complexity": edu_result,
```

3. Replace:

```python
    line("  EDUCATION LEVEL ESTIMATE")
    line(thin)
    line(f"  EN label        : {edu_result['level_en']}")
    line(f"  ID label        : {edu_result['level_id']}")
    line(
        f"  Confidence      : {edu_result['confidence_label']} ({edu_result['confidence']:.0%})"
    )
    line()
```

   with:

```python
    line("  TEXT COMPLEXITY BAND")
    line(thin)
    if edu_result["text_complexity_band"] is None:
        line(f"  Withheld        : {edu_result['withheld_reason']}")
    else:
        line(f"  Band            : {edu_result['label']}")
        line(f"  Metric agreement: {edu_result['consistency']}")
    line(f"  {edu_result['note']}")
    line()
```

4. Replace:

```python
    line(
        f"  [EDUCATION ESTIMATE — {edu_result['level_code']}/{edu_result['level_en']}]"
    )
    line(
        f"  Fog {readability_result['gunning_fog']} + ARI {readability_result['ari']} + lexical density {lexical_result['lexical_density']}."
    )
    line(f"  Writing style consistent with {edu_result['level_en']} authorship.")
    line()
```

   with:

```python
    line(f"  [TEXT COMPLEXITY — {edu_result['label'] or 'withheld'}]")
    line(
        f"  Fog {readability_result['gunning_fog']} + ARI {readability_result['ari']} + lexical density {lexical_result['lexical_density']}."
    )
    line("  Describes the text, not the writer's education.")
    line()
```

5. Replace:

```python
    line("    • Education estimate does not account for self-taught learning")
```

   with:

```python
    line("    • Education cannot be inferred from text")
```


Replace `scripts/pipeline.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import STYLE_INDEX_LABEL, evaluate_gates, load_policy
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def run_pipeline(
    text: str,
    *,
    provenance: str = "unknown",
    text_type: str = "unknown",
    chronological_age: int | None = None,
    policy: dict | None = None,
) -> dict:
    pol = policy if policy is not None else load_policy()
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep = preprocess_text(text, lang)
    gate = evaluate_gates(
        lang_r,
        prep["word_count"],
        prep["terminal_mark_count"],
        provenance,
        text_type,
        pol,
    )
    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["style_index"], lang, gate=gate, policy=pol)
    mental = predict_mental_age(iq["point_estimate"], chronological_age)
    band = estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        lex.get("lexical_density"),
        lang,
        gate=gate,
        policy=pol,
    )
    has_range = iq["range_low"] is not None
    return {
        "status": gate["status"],
        "statuses": gate["statuses"],
        "reasons": gate["reasons"],
        "lang": lang,
        "lang_confidence": lang_r["confidence"],
        "language_norm_unvalidated": gate["language_norm_unvalidated"],
        "provenance": provenance,
        "text_type": text_type,
        "policy_version": gate["policy_version"],
        "style_index": vfs["style_index"],
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": iq["style_band"],
        "components": {
            k: vfs[k] for k in ("lexical", "syntactic", "semantic", "readability")
        },
        "iq": iq["point_estimate"],
        "percentile": iq["percentile"],
        "classification": iq["classification"],
        "range": [iq["range_low"], iq["range_high"]] if has_range else None,
        "range_label": iq["range_label"] if has_range else None,
        "withheld_reason": iq["withheld_reason"],
        "mental_age": mental["mental_age"],
        "text_complexity_band": band["text_complexity_band"],
        "text_complexity_consistency": band["consistency"],
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
    }
```


- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: all pass.


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff format mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff check mcp-server/tools/mapper.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_mapper.py tests/test_reporter.py tests/test_pipeline.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_mapper.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_mapper.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add mcp-server/config/edu_norms.json \
  mcp-server/tools/mapper.py \
  mcp-server/tools/reporter.py \
  scripts/pipeline.py \
  tests/test_mapper.py \
  tests/test_reporter.py \
  tests/test_pipeline.py
git commit -m "feat(mapper): text complexity band replaces education level (AEGIS F-013 F-014 F-019)" -m "Bands are Complexity band 1-7 with no degree codes; the band is the median of per-metric bands with a CONSISTENT/CONFLICTING label and no percentage confidence; unavailable for Indonesian until readability is calibrated; describes the text, not the writer." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 5: Input gates — unsupported and mixed language, punctuation, provenance, text type (F-006, F-007, F-008; F-020 gate)

**Files:**
- Modify: `mcp-server/tools/preprocess.py` (full replacement), `scripts/pipeline.py`
- Test: `tests/test_gates.py` (new), `tests/test_preprocess.py` (replaced)

Behaviour changes that break existing tests in this task: `detect_language` no longer forces unknown languages to English (`test_detect_returns_en_or_id_only` is replaced by `test_detect_reports_unsupported_language_instead_of_forcing_english`).

**Interfaces:**
- Consumes: `tools.policy.count_terminal_marks`, `load_policy`, `evaluate_gates`, `UNSUPPORTED_LANGUAGE`, `STYLE_INDEX_LABEL`; `tests.helpers.corpus_text`, `validated_policy`.
- Produces (`tools.preprocess`): `SUPPORTED_LANGUAGES = ("en", "id")`, `MIN_SEGMENT_WORDS = 5`, `mixed_language_share(text: str, majority: str) -> float | None`, `detect_language(text: str, policy: dict | None = None) -> dict` with keys `lang` (detected ISO code, e.g. `jv`, `ms`, `fr`), `confidence` (heuristic agreement index), `supported` (`lang` in en/id and `confidence >= min_lang_confidence`), `mixed_language_share`.
- Produces (`run_pipeline`): returns without analysis (`style_index`, `components` and all screening fields `None`) when the language is not en/id, the gate status is `UNSUPPORTED_LANGUAGE`, or `word_count == 0`; `provenance`/`text_type` are validated by `evaluate_gates`.

- [ ] **Step 1: Write the failing tests**


Create `tests/test_gates.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""End-to-end input gates (F-006, F-007, F-008, F-020)."""

import re
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from pipeline import run_pipeline
from tools.policy import evaluate_gates

from tests.helpers import corpus_text, validated_policy

JAVANESE = (
    "Aku arep lunga menyang pasar karo ibuku esuk iki. Ing pasar akeh banget wong "
    "sing padha tuku sayuran lan woh-wohan. Sakwise kuwi aku bali menyang omah lan "
    "mangan sega karo iwak pitik. Bapakku lagi nyambut gawe ing sawah, dene adhiku "
    "isih sinau ing sekolahan."
)
FRENCH = (
    "Bonjour le monde, comment ca va aujourd'hui? Je voudrais acheter du pain et "
    "du fromage pour le diner de ce soir avec mes amis."
)
CODE_SWITCHED = (
    "I went to the office early this morning because the meeting started at eight. "
    "Terus aku langsung ke ruang rapat dan ternyata belum ada orang sama sekali. "
    "The manager arrived twenty minutes late and did not even apologise to anyone. "
    "Habis itu kita bahas anggaran sampai jam makan siang dan semua orang "
    "kelihatan capek. After lunch I finally finished the report and sent it to "
    "the client."
)
SCREENING_FIELDS = ("iq", "percentile", "classification", "range", "mental_age")


def _assert_screening_withheld(result):
    for field in SCREENING_FIELDS:
        assert result[field] is None, field


def test_pipeline_refuses_scoring_for_unsupported_or_low_confidence_language():
    for text, lang in ((JAVANESE, "jv"), (FRENCH, "fr")):
        result = run_pipeline(text, policy=validated_policy())
        assert result["status"] == "UNSUPPORTED_LANGUAGE"
        assert result["lang"] == lang
        assert result["style_index"] is None
        assert result["text_complexity_band"] is None
        _assert_screening_withheld(result)

    mixed = run_pipeline(CODE_SWITCHED, policy=validated_policy())
    assert mixed["status"] == "MIXED_LANGUAGE"
    assert any(r.startswith("MIXED_LANGUAGE:") for r in mixed["reasons"])
    assert mixed["text_complexity_band"] is None
    _assert_screening_withheld(mixed)

    low = evaluate_gates(
        {"lang": "id", "confidence": 0.55, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        validated_policy(),
    )
    assert low["status"] == "UNSUPPORTED_LANGUAGE"
    assert low["iq_allowed"] is False


def test_punctuation_only_change_moves_iq_by_less_than_5_points_or_is_refused():
    pol = validated_policy()
    punctuated = corpus_text("id_news_report")
    unpunctuated = re.sub(r"[.!?]", "", punctuated)
    kwargs = {
        "provenance": "supervised_unaided",
        "text_type": "formal_prose",
        "policy": pol,
    }
    a = run_pipeline(punctuated, **kwargs)
    b = run_pipeline(unpunctuated, **kwargs)
    assert a["status"] == "OK", a["reasons"]
    assert a["iq"] is not None
    if b["iq"] is None:
        assert b["status"] == "INSUFFICIENT_STRUCTURE"
        assert any(r.startswith("INSUFFICIENT_STRUCTURE:") for r in b["reasons"])
    else:
        assert abs(a["iq"] - b["iq"]) < 5


def test_pipeline_refuses_iq_for_informal_or_unknown_genre():
    pol = validated_policy()
    text = corpus_text("en_informal_email")
    for text_type in ("informal", "unknown"):
        result = run_pipeline(
            text, provenance="supervised_unaided", text_type=text_type, policy=pol
        )
        assert result["status"] == "UNVALIDATED"
        assert result["iq"] is None
        assert f"text_type {text_type!r}" in result["withheld_reason"]
        assert result["style_index"] is not None
    formal = run_pipeline(
        text, provenance="supervised_unaided", text_type="formal_prose", policy=pol
    )
    assert formal["status"] == "OK", formal["reasons"]
    assert formal["iq"] is not None


def test_pipeline_withholds_iq_without_supervised_unaided_provenance():
    pol = validated_policy()
    text = corpus_text("en_news_report")
    for provenance in ("unsupervised", "unknown"):
        result = run_pipeline(
            text, provenance=provenance, text_type="formal_prose", policy=pol
        )
        assert result["status"] == "UNVERIFIED_PROVENANCE"
        assert result["iq"] is None
        assert result["provenance"] == provenance
    with pytest.raises(ValueError):
        run_pipeline(text, provenance="self-reported", policy=pol)


MALAY = (
    "Kerajaan negeri telah mengumumkan bahawa projek lebuh raya itu akan siap lewat "
    "tiga bulan. Kelewatan ini disebabkan oleh masalah pengambilan tanah dan hujan "
    "lebat sepanjang awal tahun. Para peniaga tempatan menyatakan kekecewaan kerana "
    "kesesakan lalu lintas semakin teruk."
)


def test_malay_is_not_scored_as_indonesian():
    result = run_pipeline(MALAY, policy=validated_policy())
    assert result["lang"] == "ms"
    assert result["status"] == "UNSUPPORTED_LANGUAGE"
    assert result["style_index"] is None


@pytest.mark.parametrize("text", ["", "   ", "😀 🎉 " * 150, "12345 " * 300])
def test_pipeline_returns_no_style_index_for_text_without_words(text):
    result = run_pipeline(text, policy=validated_policy())
    assert result["status"] == "UNSUPPORTED_LANGUAGE"
    assert result["style_index"] is None
    assert result["components"] is None
    _assert_screening_withheld(result)
```


Replace `tests/test_preprocess.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

sys.path.insert(0, "mcp-server")

from tools.preprocess import detect_language, preprocess_text


def test_detect_english():
    result = detect_language("The quick brown fox jumps over the lazy dog.")
    assert result["lang"] == "en"
    assert result["confidence"] > 0.5


def test_detect_indonesian():
    result = detect_language("Saya pergi ke pasar untuk membeli sayuran segar.")
    assert result["lang"] == "id"
    assert result["confidence"] > 0.5


def test_detect_reports_unsupported_language_instead_of_forcing_english():
    result = detect_language("Bonjour le monde, comment ca va aujourd'hui?")
    assert result["lang"] == "fr"
    assert result["supported"] is False


def test_detect_supported_language_has_flags_and_mixed_share():
    result = detect_language("Saya pergi ke pasar untuk membeli sayuran segar.")
    assert result["supported"] is True
    assert result["mixed_language_share"] == 0.0


def test_detect_low_confidence_is_not_supported():
    result = detect_language(
        "The quick brown fox.", policy={"min_lang_confidence": 1.01}
    )
    assert result["lang"] == "en"
    assert result["supported"] is False


def test_preprocess_strips_urls():
    result = preprocess_text("Check this out http://example.com great stuff", "en")
    assert "http" not in " ".join(result["tokens"])


def test_preprocess_strips_mentions():
    result = preprocess_text("Hey @john how are you doing today?", "en")
    assert "@john" not in result["tokens"]


def test_preprocess_returns_sentences_with_idx():
    result = preprocess_text("Hello world. How are you? I am fine.", "en")
    assert len(result["sentences"]) >= 2
    assert all("idx" in s and "text" in s for s in result["sentences"])
    assert result["sentences"][0]["idx"] == 0


def test_preprocess_word_count():
    result = preprocess_text("One two three four five.", "en")
    assert result["word_count"] == 5


def test_preprocess_short_text_minimum():
    result = preprocess_text("Hello.", "en")
    assert result["word_count"] >= 1


def test_detect_empty_string_returns_fallback():
    result = detect_language("")
    assert result["lang"] == "en"
    assert result["confidence"] == 0.0
    assert result["supported"] is False


def test_preprocess_invalid_lang_raises():
    import pytest

    with pytest.raises(ValueError):
        preprocess_text("hello world", "fr")


def test_preprocess_empty_string_returns_empty():
    result = preprocess_text("", "en")
    assert result["word_count"] == 0
    assert result["tokens"] == []


def test_word_count_excludes_numeric_and_symbol_tokens():
    result = preprocess_text(
        "Total 12345 67890 2024 100 200 300 400 500 is fine.", "en"
    )
    assert result["word_count"] == 3
    assert result["token_count"] == 11


def test_preprocess_counts_terminal_marks():
    result = preprocess_text("One two. Three four! Five six? Seven", "en")
    assert result["terminal_mark_count"] == 3
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_gates.py tests/test_preprocess.py -v
```

Expected: FAIL — `test_pipeline_refuses_scoring_for_unsupported_or_low_confidence_language` (`assert 'en' == 'jv'`: the old detector forces Javanese to English), the Malay and no-word cases, and `test_detect_reports_unsupported_language_instead_of_forcing_english` (`'en' == 'fr'`).

- [ ] **Step 3: Implement**

Replace `mcp-server/tools/preprocess.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re
from typing import Any

import spacy
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from tools.policy import count_terminal_marks, load_policy

DetectorFactory.seed = 42

SUPPORTED_LANGUAGES = ("en", "id")
# Sentences shorter than this are too short for reliable segment-level language ID.
MIN_SEGMENT_WORDS = 5

_SEGMENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[^\W\d_]+")

_nlp_cache: dict = {}
_identifiers: dict[str, Any] = {}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        nlp = spacy.load(model)
        # xx_ent_wiki_sm has no dependency parser or sentencizer; add one so
        # doc.sents is available for non-English languages.
        if (
            "sentencizer" not in nlp.pipe_names
            and "parser" not in nlp.pipe_names
            and "senter" not in nlp.pipe_names
        ):
            nlp.add_pipe("sentencizer", first=True)
        _nlp_cache[lang] = nlp
    return _nlp_cache[lang]


def _identifier(name: str):
    """langid identifiers with normalised probabilities.

    ``full`` ranks every langid language (so Javanese, Sundanese, Malay are
    recognised as such); ``pair`` is restricted to en/id for segment-level
    code-switching detection. Built lazily: loading the model takes ~1 s.
    """
    if name not in _identifiers:
        from langid.langid import LanguageIdentifier, model

        ident = LanguageIdentifier.from_modelstring(model, norm_probs=True)
        if name == "pair":
            ident.set_languages(list(SUPPORTED_LANGUAGES))
        _identifiers[name] = ident
    return _identifiers[name]


def mixed_language_share(text: str, majority: str) -> float | None:
    """Word-weighted share of sentences whose en/id language differs from majority.

    Returns None when no sentence has at least MIN_SEGMENT_WORDS words.
    """
    pair = _identifier("pair")
    total = other = 0
    for segment in _SEGMENT_SPLIT_RE.split(text):
        n_words = len(_WORD_RE.findall(segment))
        if n_words < MIN_SEGMENT_WORDS:
            continue
        total += n_words
        if pair.classify(segment)[0] != majority:
            other += n_words
    return round(other / total, 3) if total else None


def detect_language(text: str, policy: dict | None = None) -> dict:
    """Detect the language and whether it is supported for analysis.

    ``confidence`` is the lower of the two detectors' probabilities for the
    detected language (0.0 when they disagree). It is a heuristic agreement
    index, not a calibrated probability, and must never be shown as a percent.
    """
    pol = policy if policy is not None else load_policy()
    if not text or not text.strip():
        return {
            "lang": "en",
            "confidence": 0.0,
            "supported": False,
            "mixed_language_share": None,
        }

    lang, li_prob = _identifier("full").classify(text)
    try:
        ld_probs = {c.lang: c.prob for c in detect_langs(text)}
    except LangDetectException:
        ld_probs = {}
    confidence = round(min(float(li_prob), float(ld_probs.get(lang, 0.0))), 2)

    is_supported_lang = lang in SUPPORTED_LANGUAGES
    mixed = mixed_language_share(text, lang) if is_supported_lang else None
    return {
        "lang": lang,
        "confidence": confidence,
        "supported": is_supported_lang and confidence >= pol["min_lang_confidence"],
        "mixed_language_share": mixed,
    }


def preprocess_text(text: str, lang: str) -> dict:
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang!r}. Must be 'en' or 'id'.")
    if not text or not text.strip():
        return {
            "tokens": [],
            "sentences": [],
            "word_count": 0,
            "token_count": 0,
            "terminal_mark_count": 0,
            "sentence_count": 0,
            "text_clean": "",
        }

    cleaned = re.sub(r"http\S+|www\S+", "", text)
    cleaned = re.sub(r"@\w+|#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    nlp = _get_nlp(lang)
    doc = nlp(cleaned)

    sentences = [
        {"idx": i, "text": sent.text.strip()}
        for i, sent in enumerate(doc.sents)
        if sent.text.strip()
    ]
    tokens = [t.text for t in doc if not t.is_space]
    # word_count: alphabetic words only, so numbers, emoji and symbols cannot
    # inflate length-based reliability (F-031). token_count keeps the old count.
    word_count = len([t for t in doc if t.is_alpha])
    token_count = len([t for t in doc if not t.is_space and not t.is_punct])

    return {
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "token_count": token_count,
        "terminal_mark_count": count_terminal_marks(cleaned),
        "sentence_count": len(sentences),
        "text_clean": cleaned,
    }
```


Replace `scripts/pipeline.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import (
    STYLE_INDEX_LABEL,
    UNSUPPORTED_LANGUAGE,
    evaluate_gates,
    load_policy,
)
from tools.preprocess import SUPPORTED_LANGUAGES, detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def _gate_fields(lang_r: dict, gate: dict) -> dict:
    return {
        "status": gate["status"],
        "statuses": gate["statuses"],
        "reasons": gate["reasons"],
        "lang": lang_r["lang"],
        "lang_confidence": lang_r["confidence"],
        "language_norm_unvalidated": gate["language_norm_unvalidated"],
        "provenance": gate["provenance"],
        "text_type": gate["text_type"],
        "policy_version": gate["policy_version"],
    }


def _not_analysed(lang_r: dict, gate: dict, prep: dict | None) -> dict:
    """Result for text that cannot be analysed (unsupported language, no words)."""
    return {
        **_gate_fields(lang_r, gate),
        "style_index": None,
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": None,
        "components": None,
        "iq": None,
        "percentile": None,
        "classification": None,
        "range": None,
        "range_label": None,
        "withheld_reason": "; ".join(gate["reasons"]),
        "mental_age": None,
        "text_complexity_band": None,
        "text_complexity_consistency": None,
        "word_count": prep["word_count"] if prep else 0,
        "token_count": prep["token_count"] if prep else 0,
    }


def run_pipeline(
    text: str,
    *,
    provenance: str = "unknown",
    text_type: str = "unknown",
    chronological_age: int | None = None,
    policy: dict | None = None,
) -> dict:
    pol = policy if policy is not None else load_policy()
    lang_r = detect_language(text, policy=pol)
    lang = lang_r["lang"]
    if lang not in SUPPORTED_LANGUAGES:
        gate = evaluate_gates(lang_r, 0, 0, provenance, text_type, pol)
        return _not_analysed(lang_r, gate, None)

    prep = preprocess_text(text, lang)
    gate = evaluate_gates(
        lang_r,
        prep["word_count"],
        prep["terminal_mark_count"],
        provenance,
        text_type,
        pol,
    )
    if gate["status"] == UNSUPPORTED_LANGUAGE or prep["word_count"] == 0:
        return _not_analysed(lang_r, gate, prep)

    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["style_index"], lang, gate=gate, policy=pol)
    mental = predict_mental_age(iq["point_estimate"], chronological_age)
    band = estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        lex.get("lexical_density"),
        lang,
        gate=gate,
        policy=pol,
    )
    has_range = iq["range_low"] is not None
    return {
        **_gate_fields(lang_r, gate),
        "style_index": vfs["style_index"],
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": iq["style_band"],
        "components": {
            k: vfs[k] for k in ("lexical", "syntactic", "semantic", "readability")
        },
        "iq": iq["point_estimate"],
        "percentile": iq["percentile"],
        "classification": iq["classification"],
        "range": [iq["range_low"], iq["range_high"]] if has_range else None,
        "range_label": iq["range_label"] if has_range else None,
        "withheld_reason": iq["withheld_reason"],
        "mental_age": mental["mental_age"],
        "text_complexity_band": band["text_complexity_band"],
        "text_complexity_consistency": band["consistency"],
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
    }
```


- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_gates.py tests/test_preprocess.py -v
```

Expected: all pass. (`id_news_report` punctuated is `OK` under `validated_policy()`; with `.!?` stripped it is `INSUFFICIENT_STRUCTURE`.)


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/preprocess.py scripts/pipeline.py tests/test_gates.py tests/test_preprocess.py
.venv/bin/ruff format mcp-server/tools/preprocess.py scripts/pipeline.py tests/test_gates.py tests/test_preprocess.py
.venv/bin/ruff check mcp-server/tools/preprocess.py scripts/pipeline.py tests/test_gates.py tests/test_preprocess.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_gates.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_gates.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add mcp-server/tools/preprocess.py \
  scripts/pipeline.py \
  tests/test_gates.py \
  tests/test_preprocess.py
git commit -m "feat(gates): refuse unsupported, mixed-language, unpunctuated, unattested and non-formal input (AEGIS F-006 F-007 F-008 F-020)" -m "detect_language reports the real language (jv, ms, fr ...) with supported=false, and the code-switched share per sentence. Confidence is the lower of the two detectors' probabilities (old sigmoid refused correct Indonesian). More than 40 words per terminal mark is INSUFFICIENT_STRUCTURE; provenance other than supervised_unaided is UNVERIFIED_PROVENANCE; text_type other than formal_prose refuses IQ. Unanalysable text gets no style index." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 6: Lexical metrics — MTLD, content-word density, one token unit, dictionary filter (F-015, F-021, F-024, F-029)

**Files:**
- Modify: `requirements.txt`, `mcp-server/tools/lexical.py` (full replacement), `mcp-server/tools/reporter.py`, `scripts/pipeline.py`
- Test: `tests/test_lexical.py` (replaced), `tests/test_reporter.py`

Behaviour changes that break existing tests in this task: `hapax_ratio` is removed (old `test_hapax_ratio_between_0_and_1` is replaced by `test_mtld_positive_for_ten_or_more_tokens`); evidence labels change from `hapax:` to `rare:`; the error path returns `score: None`. The reporter's hapax line is replaced here.

**Interfaces:**
- Consumes: `tests.helpers.corpus_text`; `tools.mapper.compute_verbal_fluency_score`.
- Produces (`tools.lexical`): `TOKEN_UNIT = "lowercased_surface_form"`, `STOP_WORDS`, `OOV_RELIABILITY_THRESHOLD = 0.10`, `SCORE_WEIGHTS = {"mattr": 0.45, "mtld": 0.35, "lexical_density": 0.20}`; `analyze_lexical(tokens, sentences, lang) -> dict` with keys `mattr`, `mtld` (`None` below 10 dictionary tokens), `vocd_d`, `lexical_density` (content-word ratio), `avg_word_length` (not scored), `token_unit`, `alpha_token_count`, `known_token_count`, `oov_rate`, `low_reliability`, `reliability_reasons`, `score_weights`, `score`, `evidence`; on no alphabetic tokens `{"score": None, "error": ...}`.
- Produces (`run_pipeline`): `low_reliability: bool`, `reliability_reasons: list[str]`.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_lexical.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re
import sys

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical
from tools.mapper import compute_verbal_fluency_score
from tools.preprocess import preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

from tests.helpers import corpus_text

RICH_TEXT = (
    "The epistemological underpinnings of this philosophical discourse "
    "traverse labyrinthine corridors of ontological ambiguity wherein "
    "conventional paradigms dissolve into hermeneutical uncertainty "
    "requiring unprecedented methodological innovation and interdisciplinary "
    "synthesis across divergent theoretical frameworks"
)
RICH_TOKENS = RICH_TEXT.split()
SIMPLE_TEXT = "the cat sat on the mat the cat sat the mat sat"
SIMPLE_TOKENS = SIMPLE_TEXT.split()

SENTENCES = [
    {"idx": 0, "text": "The cat sat on the mat."},
    {
        "idx": 1,
        "text": "The epistemological underpinnings dissolve into hermeneutical uncertainty.",
    },
]

CLEAN = (
    "The strongest argument for homework is practice. Skills such as reading "
    "fluently or solving equations improve with repetition, and the school day is "
    "short. Yet practice is only useful when students know how to do the task "
    "correctly. A child who misunderstood the lesson will simply repeat the "
    "mistake at home, often without anyone noticing until the next test. In that "
    "case homework does not reinforce learning; it reinforces errors. The "
    "discipline argument is weaker still. Students from calm homes with a quiet "
    "desk and an available parent can complete assignments easily. Students who "
    "share a small room with siblings cannot."
)
MISSPELLED = (
    "The strongset arguemnt for homewrok is practcie. Skills such as raeding "
    "fluetnly or solivng equations improve with repetiiton, and the school day is "
    "short. Yet practice is only usefull when studnets know how to do the task "
    "correclty. A child who misunderstood the lesosn will simply repaet the "
    "mistake at home, often without anyone noticing until the next test. In that "
    "case homework does not reinfroce learning; it reinforces erorrs. The "
    "discipline argument is weaker still. Students from calm homes with a quiet "
    "desk and an available parent can complete assignments easily. Students who "
    "share a small room with siblings cannot."
)


def _lex(text: str, lang: str = "en") -> dict:
    prep = preprocess_text(text, lang)
    return analyze_lexical(prep["tokens"], prep["sentences"], lang)


def test_analyze_lexical_returns_required_keys():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for key in (
        "mattr",
        "mtld",
        "vocd_d",
        "lexical_density",
        "avg_word_length",
        "token_unit",
        "oov_rate",
        "low_reliability",
        "reliability_reasons",
        "score_weights",
        "score",
        "evidence",
    ):
        assert key in result, f"Missing key: {key}"
    assert "hapax_ratio" not in result


def test_rich_vocabulary_scores_higher_than_simple():
    rich = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    simple = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert rich["score"] > simple["score"]


def test_mattr_between_0_and_1():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["mattr"] <= 1


def test_mtld_positive_for_ten_or_more_tokens():
    assert analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")["mtld"] > 0
    assert analyze_lexical(SIMPLE_TOKENS[:5], SENTENCES, "en")["mtld"] is None


def test_score_between_0_and_100():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_evidence_contains_sentence_idx_and_triggered_by():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert result["evidence"]
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert ev["triggered_by"]
        assert all(t.startswith("rare:") for t in ev["triggered_by"])


def test_empty_tokens_returns_error():
    result = analyze_lexical([], SENTENCES, "en")
    assert "error" in result
    assert result["score"] is None


def test_lexical_density_uses_content_words_not_length_threshold():
    en = analyze_lexical(
        [
            "the",
            "cat",
            "sat",
            "on",
            "the",
            "mat",
            "and",
            "the",
            "dog",
            "ran",
            "to",
            "the",
            "park",
        ],
        SENTENCES,
        "en",
    )
    assert en["lexical_density"] == round(6 / 13, 3)
    idn = analyze_lexical(
        [
            "rumah",
            "yang",
            "besar",
            "itu",
            "adalah",
            "milik",
            "dari",
            "keluarga",
            "dengan",
            "anak",
            "untuk",
            "mereka",
        ],
        SENTENCES,
        "id",
    )
    assert idn["lexical_density"] == round(4 / 12, 3)
    assert set(en["score_weights"]) == {"mattr", "mtld", "lexical_density"}
    assert "avg_word_length" not in en["score_weights"]


def test_lexical_diversity_metrics_use_same_token_unit_per_language():
    idn = analyze_lexical(["Membaca", "membaca", "dibaca", "pembaca"], SENTENCES, "id")
    en = analyze_lexical(["Reading", "reading", "read", "reader"], SENTENCES, "en")
    for result in (idn, en):
        assert result["token_unit"] == "lowercased_surface_form"
        # 3 surface types / 4 tokens; stemming would collapse the id case to 1/4.
        assert result["mattr"] == 0.75


def test_misspelled_text_not_scored_higher_than_clean_text_and_flagged_low_reliability():
    clean = _lex(CLEAN)
    noisy = _lex(MISSPELLED)
    assert noisy["score"] <= clean["score"]
    assert clean["low_reliability"] is False
    assert noisy["low_reliability"] is True
    assert noisy["oov_rate"] > 0.10
    assert noisy["reliability_reasons"]


def _truncate(text: str, n_words: int) -> str:
    out, count = [], 0
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        out.append(sentence)
        count += len(re.findall(r"[^\W\d_]+", sentence))
        if count >= n_words:
            break
    return " ".join(out)


def _style_index(text: str) -> tuple[float, dict]:
    prep = preprocess_text(text, "en")
    lex = analyze_lexical(prep["tokens"], prep["sentences"], "en")
    syn = analyze_syntactic(prep["sentences"], "en")
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], "en")
    read = analyze_readability(prep["text_clean"], "en")
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], "en")
    return vfs["style_index"], lex


def test_vfs_stable_across_truncation_lengths_within_tolerance():
    text = corpus_text("en_academic_essay")
    results = [_style_index(_truncate(text, n)) for n in (250, 400, 600)]
    indices = [r[0] for r in results]
    assert max(indices) - min(indices) <= 3.0, indices
    for _, lex in results:
        # The length-biased hapax ratio is gone; MTLD is the diversity measure.
        assert "hapax_ratio" not in lex
        assert lex["mtld"] is not None
```


In `tests/test_reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    "vocd_d": 61.2,
    "hapax_ratio": 0.42,
    "lexical_density": 0.53,
```

   with:

```python
    "vocd_d": 61.2,
    "mtld": 96.4,
    "oov_rate": 0.01,
    "lexical_density": 0.53,
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_lexical.py -v
```

Expected: FAIL — `test_analyze_lexical_returns_required_keys` (`Missing key: mtld`), `test_lexical_density_uses_content_words_not_length_threshold`, `test_lexical_diversity_metrics_use_same_token_unit_per_language` (Indonesian MATTR 0.25 from stemming), `test_misspelled_text_not_scored_higher_than_clean_text_and_flagged_low_reliability` (`KeyError: 'low_reliability'`), `test_vfs_stable_across_truncation_lengths_within_tolerance` (`hapax_ratio` still present).

- [ ] **Step 3: Add the dependency**


In `requirements.txt`, make these exact replacements (each `old` occurs once):

1. Replace:

```text
lexicalrichness>=0.4.2
```

   with:

```text
lexicalrichness>=0.4.2
wordfreq>=3.1.1
```


Then install it:

```bash
.venv/bin/pip install "wordfreq>=3.1.1"
.venv/bin/python -c "from wordfreq import zipf_frequency; print(zipf_frequency('perkembangan', 'id') > 0)"
```

Expected: `True` (wordfreq ships its en and id word lists; nothing is downloaded at run time).

- [ ] **Step 4: Implement**

Replace `mcp-server/tools/lexical.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Lexical diversity and density.

Token unit (F-029): every diversity metric in both languages uses lowercased
alphabetic surface forms. No stemming or lemmatisation for either language.

Dictionary filter (F-024): tokens that the ``wordfreq`` lexicon does not know
(zipf_frequency == 0, e.g. typos and keyboard noise) are excluded from MATTR,
MTLD and lexical density. Their share is ``oov_rate``; above 0.10 the result is
flagged ``low_reliability`` and should be routed to human review.
"""

from collections import Counter
from functools import lru_cache

from lexicalrichness import LexicalRichness
from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP_WORDS
from spacy.lang.id.stop_words import STOP_WORDS as ID_STOP_WORDS
from wordfreq import zipf_frequency

TOKEN_UNIT = "lowercased_surface_form"
STOP_WORDS = {"en": EN_STOP_WORDS, "id": ID_STOP_WORDS}
OOV_RELIABILITY_THRESHOLD = 0.10
MATTR_WINDOW = 50
MIN_MTLD_TOKENS = 10
MIN_VOCD_TOKENS = 50
# Rare-but-real words (shown as evidence only; never scored).
RARE_ZIPF_MAX = 3.5
# avg_word_length is reported but not scored: it duplicates readability (F-015).
SCORE_WEIGHTS = {"mattr": 0.45, "mtld": 0.35, "lexical_density": 0.20}


def _mattr(tokens: list[str], window: int = MATTR_WINDOW) -> float:
    if len(tokens) < window:
        return len(set(tokens)) / len(tokens) if tokens else 0.0
    ttrs = [
        len(set(tokens[i : i + window])) / window
        for i in range(len(tokens) - window + 1)
    ]
    return sum(ttrs) / len(ttrs)


@lru_cache(maxsize=65536)
def _zipf(word: str, lang: str) -> float:
    return zipf_frequency(word, lang)


def _scale(value: float, low: float, high: float) -> float:
    return min(100.0, max(0.0, (value - low) / (high - low) * 100))


def analyze_lexical(tokens: list[str], sentences: list[dict], lang: str) -> dict:
    alpha = [t.lower() for t in tokens if t.isalpha()]
    if not alpha:
        return {"score": None, "error": "No alphabetic tokens found"}

    known = [t for t in alpha if _zipf(t, lang) > 0]
    oov_rate = round(1 - len(known) / len(alpha), 3)
    reliability_reasons = []
    if oov_rate > OOV_RELIABILITY_THRESHOLD:
        reliability_reasons.append(
            f"{oov_rate:.2f} of words are not in the {lang} dictionary "
            f"(max {OOV_RELIABILITY_THRESHOLD:.2f}); route to human review"
        )
    if not known:
        return {
            "score": None,
            "error": "No dictionary words found",
            "oov_rate": oov_rate,
            "low_reliability": True,
            "reliability_reasons": reliability_reasons,
            "token_unit": TOKEN_UNIT,
        }

    mattr = round(_mattr(known), 3)
    mtld = None
    if len(known) >= MIN_MTLD_TOKENS:
        mtld = round(float(LexicalRichness(" ".join(known)).mtld(threshold=0.72)), 1)
    vocd_d = None
    if len(known) >= MIN_VOCD_TOKENS:
        try:
            vocd_d = round(float(LexicalRichness(" ".join(known)).vocd()), 1)
        except (ValueError, ZeroDivisionError):
            vocd_d = None

    stop = STOP_WORDS[lang]
    lexical_density = round(sum(1 for t in known if t not in stop) / len(known), 3)
    avg_word_length = round(sum(len(t) for t in alpha) / len(alpha), 1)

    parts = {
        "mattr": _scale(mattr, 0.3, 0.9),
        "lexical_density": _scale(lexical_density, 0.3, 0.7),
    }
    if mtld is not None:
        parts["mtld"] = _scale(mtld, 40.0, 200.0)
    total_weight = sum(SCORE_WEIGHTS[k] for k in parts)
    score = round(sum(parts[k] * SCORE_WEIGHTS[k] for k in parts) / total_weight, 1)

    freq = Counter(known)
    evidence = []
    for sent in sentences:
        words = [w.lower() for w in sent["text"].split() if w.isalpha()]
        rare = [
            w
            for w in words
            if freq.get(w, 0) == 1 and len(w) > 5 and 0 < _zipf(w, lang) < RARE_ZIPF_MAX
        ]
        if rare:
            evidence.append(
                {
                    "sentence_idx": sent["idx"],
                    "sentence": sent["text"],
                    "triggered_by": [f"rare:{w}" for w in rare[:3]],
                }
            )

    return {
        "mattr": mattr,
        "mtld": mtld,
        "vocd_d": vocd_d,
        "lexical_density": lexical_density,
        "avg_word_length": avg_word_length,
        "token_unit": TOKEN_UNIT,
        "alpha_token_count": len(alpha),
        "known_token_count": len(known),
        "oov_rate": oov_rate,
        "low_reliability": bool(reliability_reasons),
        "reliability_reasons": reliability_reasons,
        "score_weights": {k: SCORE_WEIGHTS[k] for k in parts},
        "score": score,
        "evidence": evidence[:3],
    }
```


In `mcp-server/tools/reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    line(f"  Hapax Legomena ratio  : {lexical_result['hapax_ratio']}")
```

   with:

```python
    line(f"  MTLD                  : {lexical_result.get('mtld')}")
    line(f"  Out-of-dictionary rate: {lexical_result.get('oov_rate')}")
```


In `scripts/pipeline.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
        "word_count": prep["word_count"] if prep else 0,
        "token_count": prep["token_count"] if prep else 0,
    }
```

   with:

```python
        "word_count": prep["word_count"] if prep else 0,
        "token_count": prep["token_count"] if prep else 0,
        "low_reliability": True,
        "reliability_reasons": [],
    }
```

2. Replace:

```python
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
    }
```

   with:

```python
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
        "low_reliability": bool(lex.get("low_reliability", True)),
        "reliability_reasons": lex.get("reliability_reasons", []),
    }
```


- [ ] **Step 5: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_lexical.py tests/test_reporter.py -v
```

Expected: all pass. On `en_academic_essay` truncated to 250/400/600 words the style index stays within 3 points (prototype: 59.1 / 59.5 / 61.2). Note for the reviewer: the hapax bias the finding measured shows mostly below 250 words, which Task 3's `INSUFFICIENT_TEXT` gate now refuses; this test guards the ≥ `min_words` regime and that the length-biased metric is gone.


- [ ] **Step 6: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/lexical.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_lexical.py tests/test_reporter.py
.venv/bin/ruff format mcp-server/tools/lexical.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_lexical.py tests/test_reporter.py
.venv/bin/ruff check mcp-server/tools/lexical.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_lexical.py tests/test_reporter.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 7: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_lexical.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_lexical.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt \
  mcp-server/tools/lexical.py \
  mcp-server/tools/reporter.py \
  scripts/pipeline.py \
  tests/test_lexical.py \
  tests/test_reporter.py
git commit -m "feat(lexical): MTLD, content-word density, surface-form unit, dictionary filter (AEGIS F-015 F-021 F-024 F-029)" -m "Hapax ratio replaced by MTLD; lexical density is the content-word ratio from spaCy stop-word lists; avg word length is reported but not scored; both languages use lowercased surface forms; tokens unknown to wordfreq are excluded from diversity and an out-of-dictionary rate above 0.10 flags low reliability. New dependency wordfreq>=3.1.1." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 7: Semantic metrics — entities informational, drift needs transitions, per-language scaling (F-012, F-028, F-030)

**Files:**
- Create: `mcp-server/config/semantic_scaling.json`
- Modify: `mcp-server/tools/semantic.py` (full replacement), `mcp-server/tools/reporter.py`, `scripts/pipeline.py`
- Test: `tests/test_semantic.py` (replaced), `tests/test_reporter.py`

Behaviour changes that break existing tests in this task: `argument_coherence` → `adjacent_sentence_similarity`, `entity_sophistication` → `entity_labels`, evidence key `coherence` → `similarity`, score `None` (not 50.0) for fewer than 2 sentences. Existing semantic tests and the reporter's semantic lines are updated here.

**Interfaces:**
- Consumes: `tools.policy.load_policy` (`min_drift_transitions`).
- Produces (`tools.semantic`): `SUB_WEIGHTS = {"similarity": 0.45, "drift": 0.25, "chain": 0.20}`; patch points `_entity_labels(text, lang) -> list[str]`, `_load_scaling() -> dict`, `_scaling_for(lang) -> dict`; `analyze_semantic(text, sentences, lang, segment_boundaries=None, policy=None) -> dict` with keys `adjacent_sentence_similarity`, `topic_drift_index` (`None` with fewer than `min_drift_transitions` transitions), `lexical_chain_density`, `entity_labels`, `transitions`, `scaling_status`, `score` (`None` when not measurable), `evidence` (`sentence_idx_from`, `sentence_idx_to`, `similarity`, `note`).
- Produces (`semantic_scaling.json`): `{"status": "uncalibrated", "note", "languages": {"en"|"id": {"similarity_min": 0.3, "similarity_max": 0.9}}}`.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_semantic.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

sys.path.insert(0, "mcp-server")

from tools import semantic
from tools.semantic import analyze_semantic

COHERENT_TEXT = (
    "Climate change is accelerating. The acceleration is driven by carbon emissions. "
    "Carbon emissions must be reduced through policy intervention. "
    "Policy intervention requires international cooperation."
)
COHERENT_SENTENCES = [
    {"idx": 0, "text": "Climate change is accelerating."},
    {"idx": 1, "text": "The acceleration is driven by carbon emissions."},
    {"idx": 2, "text": "Carbon emissions must be reduced through policy intervention."},
    {"idx": 3, "text": "Policy intervention requires international cooperation."},
]

INCOHERENT_TEXT = "Dogs bark at night. The economy grew last quarter. Pizza is delicious. Mountains are tall."
INCOHERENT_SENTENCES = [
    {"idx": 0, "text": "Dogs bark at night."},
    {"idx": 1, "text": "The economy grew last quarter."},
    {"idx": 2, "text": "Pizza is delicious."},
    {"idx": 3, "text": "Mountains are tall."},
]

SIX_SENTENCES = COHERENT_SENTENCES + [
    {"idx": 4, "text": "Cooperation depends on trust between governments."},
    {"idx": 5, "text": "Trust grows when commitments are verified."},
]
SIX_TEXT = " ".join(s["text"] for s in SIX_SENTENCES)

SINGLE_SENTENCE = [{"idx": 0, "text": "Hello world."}]


def test_returns_required_keys():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for key in (
        "adjacent_sentence_similarity",
        "topic_drift_index",
        "lexical_chain_density",
        "entity_labels",
        "transitions",
        "scaling_status",
        "score",
        "evidence",
    ):
        assert key in result


def test_coherent_text_higher_similarity():
    coherent = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    incoherent = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    assert (
        coherent["adjacent_sentence_similarity"]
        > incoherent["adjacent_sentence_similarity"]
    )


def test_score_between_0_and_100():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_single_sentence_returns_none_score_with_note():
    result = analyze_semantic("Hello world.", SINGLE_SENTENCE, "en")
    assert result["score"] is None
    assert "note" in result


def test_evidence_has_similarity_and_note():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx_from" in ev
        assert "sentence_idx_to" in ev
        assert "similarity" in ev
        assert "note" in ev


def test_default_segment_boundaries_unchanged():
    a = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    b = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", None)
    assert a == b


def test_segment_boundary_excludes_cross_document_pair():
    base = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    seg = analyze_semantic(
        INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", segment_boundaries=[2]
    )
    assert seg["adjacent_sentence_similarity"] != base["adjacent_sentence_similarity"]


def test_all_pairs_straddle_boundaries_returns_gracefully():
    result = analyze_semantic(
        INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", segment_boundaries=[1, 2, 3]
    )
    assert result["adjacent_sentence_similarity"] is None
    assert result["score"] is None
    assert "note" in result


def test_semantic_entity_score_independent_of_ner_label_set(monkeypatch):
    scores = []
    for labels in ([], ["PER"], ["ORG"], ["LAW", "NORP"], ["LOC", "MISC"]):
        monkeypatch.setattr(semantic, "_entity_labels", lambda t, lang, ls=labels: ls)
        result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
        assert result["entity_labels"] == labels
        assert "entity_sophistication" not in result
        scores.append(result["score"])
    assert len(set(scores)) == 1


def test_topic_drift_none_when_fewer_than_min_transitions():
    two = analyze_semantic(
        "Climate change is accelerating. Pizza is delicious.",
        [
            {"idx": 0, "text": "Climate change is accelerating."},
            {"idx": 1, "text": "Pizza is delicious."},
        ],
        "en",
    )
    assert two["transitions"] == 1
    assert two["topic_drift_index"] is None
    assert two["score"] is not None
    four = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert four["transitions"] == 3
    assert four["topic_drift_index"] is None
    six = analyze_semantic(SIX_TEXT, SIX_SENTENCES, "en")
    assert six["transitions"] == 5
    assert isinstance(six["topic_drift_index"], float)


def test_semantic_metric_renamed_and_scaling_loaded_per_language(monkeypatch):
    cfg = json.loads(
        pathlib.Path("mcp-server/config/semantic_scaling.json").read_text(
            encoding="utf-8"
        )
    )
    assert cfg["status"] == "uncalibrated"
    assert set(cfg["languages"]) == {"en", "id"}
    for lang in ("en", "id"):
        assert cfg["languages"][lang] == {"similarity_min": 0.3, "similarity_max": 0.9}

    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert "argument_coherence" not in result
    assert result["scaling_status"] == "uncalibrated"

    patched = {
        "status": "uncalibrated",
        "languages": {
            "en": cfg["languages"]["en"],
            "id": {"similarity_min": 0.0, "similarity_max": 1.0},
        },
    }
    monkeypatch.setattr(semantic, "_load_scaling", lambda: patched)
    en_after = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    id_after = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "id")
    assert en_after["score"] == result["score"]
    assert id_after["score"] != result["score"]
```


In `tests/test_reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
SEMANTIC = {
    "argument_coherence": 0.74,
    "topic_drift_index": 0.21,
    "lexical_chain_density": 0.61,
    "entity_sophistication": "ABSTRACT",
    "score": 71.8,
    "evidence": [
        {
            "sentence_idx_from": 0,
            "sentence_idx_to": 1,
            "coherence": 0.81,
            "note": "causal chain detected",
        }
    ],
}
```

   with:

```python
SEMANTIC = {
    "adjacent_sentence_similarity": 0.74,
    "topic_drift_index": 0.21,
    "lexical_chain_density": 0.61,
    "entity_labels": ["ORG"],
    "score": 71.8,
    "evidence": [
        {
            "sentence_idx_from": 0,
            "sentence_idx_to": 1,
            "similarity": 0.81,
            "note": "high overlap",
        }
    ],
}
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_semantic.py -v
```

Expected: FAIL — `test_returns_required_keys` (`adjacent_sentence_similarity` missing), `test_single_sentence_returns_none_score_with_note` (`50.0 is not None`), `test_topic_drift_none_when_fewer_than_min_transitions`, `test_semantic_entity_score_independent_of_ner_label_set` (no `_entity_labels`), `test_semantic_metric_renamed_and_scaling_loaded_per_language` (no config file).

- [ ] **Step 3: Implement**


Create `mcp-server/config/semantic_scaling.json` with exactly this content:

```json
{
  "status": "uncalibrated",
  "note": "Linear 0-100 scaling of mean adjacent-sentence cosine similarity. Placeholder bounds carried over from the original code; to be replaced per language by the reference-corpus calibration in docs/validation/norming-plan.md.",
  "languages": {
    "en": {"similarity_min": 0.3, "similarity_max": 0.9},
    "id": {"similarity_min": 0.3, "similarity_max": 0.9}
  }
}
```


Replace `mcp-server/tools/semantic.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Adjacent-sentence semantic metrics.

``adjacent_sentence_similarity`` is the mean cosine similarity of neighbouring
sentence embeddings from a paraphrase model. It measures topical overlap, not
argument quality (F-030). Its 0-100 scaling is read per language from
``config/semantic_scaling.json`` and is uncalibrated.

Named entities are reported for information only and never scored (F-012).
"""

import json
import os
from collections import defaultdict

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from tools.policy import load_policy

_model_cache: dict = {}
_nlp_cache: dict = {}
_scaling_cache: dict = {}

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

# Nominal sub-weights; unavailable parts are dropped and the rest renormalised.
SUB_WEIGHTS = {"similarity": 0.45, "drift": 0.25, "chain": 0.20}
DRIFT_SCALE_MAX = 0.3


def _get_model():
    if "model" not in _model_cache:
        _model_cache["model"] = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _model_cache["model"]


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        _nlp_cache[lang] = spacy.load(
            "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        )
    return _nlp_cache[lang]


def _load_scaling() -> dict:
    if "scaling" not in _scaling_cache:
        path = os.path.join(_CONFIG_DIR, "semantic_scaling.json")
        with open(path, encoding="utf-8") as f:
            _scaling_cache["scaling"] = json.load(f)
    return _scaling_cache["scaling"]


def _scaling_for(lang: str) -> dict:
    return _load_scaling()["languages"][lang]


def _entity_labels(text: str, lang: str) -> list[str]:
    """Sorted distinct NER labels; label sets differ per model (informational)."""
    return sorted({ent.label_ for ent in _get_nlp(lang)(text).ents})


def _unavailable(note: str) -> dict:
    return {
        "adjacent_sentence_similarity": None,
        "topic_drift_index": None,
        "lexical_chain_density": None,
        "entity_labels": [],
        "transitions": 0,
        "scaling_status": None,
        "score": None,
        "evidence": [],
        "note": note,
    }


def analyze_semantic(
    text: str,
    sentences: list[dict],
    lang: str,
    segment_boundaries: list[int] | None = None,
    policy: dict | None = None,
) -> dict:
    """Semantic metrics over adjacent sentences.

    segment_boundaries: optional list of sentence ``idx`` values at which a NEW
    document begins. Adjacent pairs whose target sentence starts a new document
    are skipped, so multi-file subjects are not penalised for spurious drift at
    document seams. Default None => all adjacent pairs are scored.

    The score is None (not an imputed 50) when it cannot be measured (F-016).
    """
    pol = policy if policy is not None else load_policy()
    if len(sentences) < 2:
        return _unavailable("Too few sentences for semantic analysis")

    boundaries = set(segment_boundaries or [])

    model = _get_model()
    texts = [s["text"] for s in sentences]
    embeddings = model.encode(texts)

    evidence = []
    similarities = []
    for i in range(len(embeddings) - 1):
        # Skip transitions that straddle a document boundary.
        if sentences[i + 1]["idx"] in boundaries:
            continue
        sim = float(cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0])
        similarities.append(sim)
        note = (
            "high overlap"
            if sim > 0.75
            else "low overlap"
            if sim < 0.50
            else "moderate overlap"
        )
        evidence.append(
            {
                "sentence_idx_from": sentences[i]["idx"],
                "sentence_idx_to": sentences[i + 1]["idx"],
                "similarity": round(sim, 3),
                "note": note,
            }
        )

    if not similarities:
        # Every adjacent pair straddled a document boundary.
        return _unavailable(
            "No within-document transitions available for semantic analysis"
        )

    similarity = round(float(np.mean(similarities)), 3)
    # Drift is the spread of similarities; with too few transitions it is 0 by
    # construction, so it is not measured at all (F-028).
    topic_drift_index = None
    if len(similarities) >= pol["min_drift_transitions"]:
        topic_drift_index = round(float(np.std(similarities)), 3)

    word_positions: dict = defaultdict(set)
    for i, s in enumerate(sentences):
        for w in s["text"].lower().split():
            if len(w) > 4:
                word_positions[w].add(i)
    chained = sum(1 for pos in word_positions.values() if len(pos) > 1)
    total = len(word_positions)
    lexical_chain_density = round(chained / total, 3) if total else 0.0

    scaling = _scaling_for(lang)
    low, high = scaling["similarity_min"], scaling["similarity_max"]
    parts = {
        "similarity": min(100.0, max(0.0, (similarity - low) / (high - low) * 100)),
        "chain": min(100.0, max(0.0, (lexical_chain_density - 0.1) / 0.5 * 100)),
    }
    if topic_drift_index is not None:
        parts["drift"] = min(
            100.0, max(0.0, (1 - topic_drift_index / DRIFT_SCALE_MAX) * 100)
        )
    weight_total = sum(SUB_WEIGHTS[k] for k in parts)
    score = round(sum(parts[k] * SUB_WEIGHTS[k] for k in parts) / weight_total, 1)

    return {
        "adjacent_sentence_similarity": similarity,
        "topic_drift_index": topic_drift_index,
        "lexical_chain_density": lexical_chain_density,
        "entity_labels": _entity_labels(text, lang),
        "transitions": len(similarities),
        "scaling_status": _load_scaling()["status"],
        "score": score,
        "evidence": evidence[:5],
    }
```


In `mcp-server/tools/reporter.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
def _bar(score: float, width: int = 10) -> str:
    filled = round(score / 100 * width)
```

   with:

```python
def _bar(score: float | None, width: int = 10) -> str:
    if score is None:
        return ""
    filled = round(score / 100 * width)
```

2. Replace:

```python
    line(f"  Argument coherence    : {semantic_result['argument_coherence']}")
```

   with:

```python
    line(
        f"  Adjacent-sentence similarity : {semantic_result['adjacent_sentence_similarity']}"
    )
```

3. Replace:

```python
    line(f"  Entity sophistication : {semantic_result['entity_sophistication']}")
```

   with:

```python
    line(
        f"  Entity labels         : {', '.join(semantic_result['entity_labels']) or 'none'} (not scored)"
    )
```

4. Replace:

```python
        f"  Argument coherence {semantic_result['argument_coherence']}, topic drift {semantic_result['topic_drift_index']}."
```

   with:

```python
        f"  Adjacent-sentence similarity {semantic_result['adjacent_sentence_similarity']}, topic drift {semantic_result['topic_drift_index']}."
```

5. Replace:

```python
            f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} coherence: {ev['coherence']} [{ev['note']}]"
```

   with:

```python
            f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} similarity: {ev['similarity']} [{ev['note']}]"
```


In `scripts/pipeline.py`, make these exact replacements (each `old` occurs once):

1. Replace:

```python
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
```

   with:

```python
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang, policy=pol)
```


- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_semantic.py tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: all pass. `test_short_text_very_low_confidence` now sees `semantic` = `None` and a renormalised style index (Task 3).


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/semantic.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_semantic.py tests/test_reporter.py
.venv/bin/ruff format mcp-server/tools/semantic.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_semantic.py tests/test_reporter.py
.venv/bin/ruff check mcp-server/tools/semantic.py mcp-server/tools/reporter.py scripts/pipeline.py tests/test_semantic.py tests/test_reporter.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_semantic.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_semantic.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add mcp-server/config/semantic_scaling.json \
  mcp-server/tools/semantic.py \
  mcp-server/tools/reporter.py \
  scripts/pipeline.py \
  tests/test_semantic.py \
  tests/test_reporter.py
git commit -m "feat(semantic): adjacent-sentence similarity, drift gating, entities unscored (AEGIS F-012 F-028 F-030)" -m "Named entities are reported as labels and never scored. Topic drift is None below min_drift_transitions (5) and its weight renormalised. argument_coherence is renamed adjacent_sentence_similarity, scaled per language from config/semantic_scaling.json (marked uncalibrated). Unmeasurable semantic score is None, not 50." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 8: Indonesian syntactic heuristics and cross-language guard (F-010, F-011, F-018, F-023)

**Files:**
- Modify: `mcp-server/tools/syntactic.py` (full replacement), `docs/audit/curated.json`, `docs/audit/2026-10-11-aegis-findings.json` (regenerated)
- Test: `tests/test_syntactic.py`

Behaviour changes: `ter-` words are no longer passive; `dan`/`atau`/`serta` and temporal words count only in their clausal sense; colloquial connectives are normalised. No existing test asserts the old behaviour (`test_en_path_unchanged` still holds: the English path only gains two keys).

**Interfaces:**
- Consumes: `tools.policy.rank_by_style_index`, `CrossLanguageComparisonError`.
- Produces (`tools.syntactic`): word sets `ID_SUBORDINATORS`, `ID_TEMPORAL_JOINERS`, `ID_GATED_COORDINATORS`, `ID_CLAUSE_COORDINATORS`, `ID_COLLOQUIAL_TO_STANDARD`, `ID_FUNCTION_ROOTS`, `ID_LOCATIVE_NOUN_ROOTS`, `ID_BARE_VERBS`, `ID_PREDICATE_MODIFIERS`, `ID_NON_VERB_AFFIXED`; `normalise_colloquial(words: list[str]) -> tuple[list[str], int]`, `is_di_passive(word: str) -> bool`, `is_verb_like(word: str) -> bool`, `count_id_clause_joiners(words: list[str]) -> tuple[int, int]`; every `analyze_syntactic` result has `comparable_across_languages: False` and `note`; Indonesian results also `colloquial_forms_normalised: int`.

- [ ] **Step 1: Write the failing tests**


In `tests/test_syntactic.py`, replace the import block:

```python
import sys

sys.path.insert(0, "mcp-server")

from tools.syntactic import analyze_syntactic
```

with:

```python
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.policy import CrossLanguageComparisonError, rank_by_style_index
from tools.syntactic import analyze_syntactic, is_di_passive
```


Append to the end of `tests/test_syntactic.py`:

```python
def test_id_passive_not_triggered_by_terjadi_terkait_terbaik_dimana_diantara():
    text = (
        "Hal itu terjadi dan terkait dengan hasil terbaik dimana kami berada "
        "diantara mereka"
    )
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["passive_ratio"] == 0
    for word in ("terjadi", "terkait", "terbaik", "dimana", "diantara", "dinas"):
        assert not is_di_passive(word), word
    for word in ("ditulis", "direvisi", "diserahkan", "dilanjutkan", "dikirimi"):
        assert is_di_passive(word), word


def test_id_clause_density_ignores_nominal_coordination_and_temporal_prepositions():
    text = "Saya makan nasi dan atau minum teh sejak pagi sampai malam selama seminggu"
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["clause_density"] == 1.0
    assert result["subordination_index"] == 0.0


def test_id_clausal_coordination_and_temporal_clauses_still_counted():
    text = "Ayah membaca koran dan saya menulis surat sejak dia pindah ke kota."
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["clause_density"] == 3.0
    assert result["subordination_index"] == 1.0


ID_FORMAL = [
    {
        "idx": 0,
        "text": "Kalau hujan turun, kami tetap berangkat agar acara tidak batal.",
    },
    {
        "idx": 1,
        "text": "Saya pulang cepat karena badan saya lelah, tetapi pekerjaan belum selesai.",
    },
    {
        "idx": 2,
        "text": "Ketika dia datang, kami langsung makan karena semua orang sudah lapar.",
    },
]
ID_COLLOQUIAL = [
    {
        "idx": 0,
        "text": "Kalo hujan turun, kami tetap berangkat biar acara tidak batal.",
    },
    {
        "idx": 1,
        "text": "Saya pulang cepat soalnya badan saya lelah, tapi pekerjaan belum selesai.",
    },
    {
        "idx": 2,
        "text": "Pas dia datang, kami langsung makan gara-gara semua orang sudah lapar.",
    },
]


def test_id_syntactic_score_equal_for_formal_and_colloquial_paraphrase():
    formal = analyze_syntactic(ID_FORMAL, "id")
    colloquial = analyze_syntactic(ID_COLLOQUIAL, "id")
    assert colloquial["score"] == formal["score"]
    assert colloquial["clause_density"] == formal["clause_density"]
    assert colloquial["subordination_index"] == formal["subordination_index"]
    assert formal["colloquial_forms_normalised"] == 0
    assert colloquial["colloquial_forms_normalised"] == 6


def test_syntactic_scores_flagged_not_comparable_across_languages():
    en = analyze_syntactic(COMPLEX_SENTENCES, "en")
    idn = analyze_syntactic(ID_COMPLEX, "id")
    for result in (en, idn):
        assert result["comparable_across_languages"] is False
        assert "not comparable across languages" in result["note"]
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(
            [
                {"lang": "en", "style_index": en["score"]},
                {"lang": "id", "style_index": idn["score"]},
            ]
        )


def test_id_locative_written_solid_is_not_passive_but_suffixed_form_is():
    text = "Saya tinggal dirumah dan bekerja dikantor dekat dipasar."
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["passive_ratio"] == 0
    assert is_di_passive("dijalankan")
    assert is_di_passive("dirumahkan")
    assert not is_di_passive("dijalan")
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_syntactic.py -v
```

Expected: collection ERROR — `ImportError: cannot import name 'is_di_passive' from 'tools.syntactic'`.

- [ ] **Step 3: Implement**

Replace `mcp-server/tools/syntactic.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Syntactic complexity.

English uses spaCy dependency labels; Indonesian uses a rule-based lexicon and
morphology (xx_ent_wiki_sm has no parser). These are different instruments, so
syntactic scores are NOT comparable across languages (F-023): every result
carries ``comparable_across_languages: False`` and cross-language ranking is
refused by ``tools.policy.assert_same_language``.
"""

import re
from functools import lru_cache

import spacy
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

_nlp_cache: dict = {}

SUBORDINATE_DEPS = {"advcl", "relcl", "acl", "csubj", "ccomp", "xcomp"}
CLAUSE_DEPS = SUBORDINATE_DEPS | {"ROOT"}

NON_COMPARABLE_NOTE = (
    "Syntactic scores come from different instruments per language and are not "
    "comparable across languages."
)

# --- Indonesian rule-based resources ---
# Konjungsi subordinatif: always open a subordinate clause.
ID_SUBORDINATORS = {
    "yang",
    "karena",
    "sehingga",
    "ketika",
    "meskipun",
    "walaupun",
    "jika",
    "kalau",
    "agar",
    "supaya",
    "sebab",
    "bahwa",
    "apabila",
    "bilamana",
    "seandainya",
    "andai",
    "tatkala",
    "seraya",
    "sambil",
    "sementara",
    "asalkan",
    "kecuali",
    "biarpun",
    "sekalipun",
    "daripada",
    "seolah",
    "seakan",
}
# Temporal words that are prepositions ("sejak pagi") unless a predicate follows
# ("sejak dia pindah"). Counted as subordinators only in the clausal sense (F-011).
ID_TEMPORAL_JOINERS = {"sejak", "selama", "sampai", "hingga", "sebelum", "setelah"}
# Coordinators that also join nouns and verb phrases ("nasi dan teh", "makan dan
# minum"). Counted as clause joiners only before an overt subject + predicate.
ID_GATED_COORDINATORS = {"dan", "atau", "serta"}
# Coordinators that join clauses in standard usage.
ID_CLAUSE_COORDINATORS = {
    "tetapi",
    "namun",
    "melainkan",
    "sedangkan",
    "lalu",
    "kemudian",
    "padahal",
    "maka",
}
ID_JOINERS = (
    ID_SUBORDINATORS
    | ID_TEMPORAL_JOINERS
    | ID_GATED_COORDINATORS
    | ID_CLAUSE_COORDINATORS
)
# Colloquial / Javanese-influenced connectives -> standard form, applied before
# counting so informal writers are not penalised for register (F-018).
ID_COLLOQUIAL_TO_STANDARD = {
    "kalo": "kalau",
    "biar": "agar",
    "soalnya": "karena",
    "makanya": "maka",
    "pas": "ketika",
    "gara-gara": "karena",
    "nek": "kalau",
    "ben": "agar",
    "trus": "lalu",
    "terus": "lalu",
    "tapi": "tetapi",
}
# di- + one of these roots is a locative/relative written solid ("dimana",
# "diantara", "diatas"), not a passive verb (F-010).
ID_FUNCTION_ROOTS = frozenset(
    {
        "mana",
        "antara",
        "sini",
        "situ",
        "sana",
        "atas",
        "bawah",
        "dalam",
        "luar",
        "depan",
        "belakang",
    }
)
# Place nouns commonly written solid after locative "di" in informal writing.
ID_LOCATIVE_NOUN_ROOTS = frozenset(
    {
        "rumah",
        "kantor",
        "sekolah",
        "kampus",
        "kelas",
        "kamar",
        "dapur",
        "jalan",
        "pasar",
        "toko",
        "kota",
        "desa",
        "kampung",
        "sawah",
        "kebun",
        "pantai",
        "laut",
        "gunung",
        "hutan",
    }
)
# Unaffixed verbs that head a predicate (the affixed ones are found by morphology).
ID_BARE_VERBS = frozenset(
    {
        "makan",
        "minum",
        "pergi",
        "datang",
        "pulang",
        "tidur",
        "duduk",
        "turun",
        "naik",
        "masuk",
        "keluar",
        "tiba",
        "lahir",
        "mati",
        "tinggal",
        "bangun",
        "lari",
        "jatuh",
        "ikut",
        "pindah",
        "mandi",
        "kerja",
        "main",
        "tahu",
        "pakai",
        "beli",
        "jual",
        "bayar",
        "baca",
        "tulis",
        "lihat",
        "dengar",
        "buat",
        "bawa",
        "cari",
        "kirim",
        "tunggu",
        "selesai",
        "mulai",
        "hilang",
        "muncul",
        "menang",
        "kalah",
    }
)
# Adverbs/auxiliaries that open a predicate without a subject ("dan tidak minum").
ID_PREDICATE_MODIFIERS = frozenset(
    {
        "tidak",
        "tak",
        "belum",
        "bukan",
        "sudah",
        "telah",
        "akan",
        "sedang",
        "masih",
        "juga",
        "pun",
        "hanya",
        "bisa",
        "dapat",
        "harus",
        "mau",
        "ingin",
        "boleh",
        "perlu",
        "langsung",
        "segera",
        "pernah",
        "sering",
        "selalu",
    }
)
# Affixed words that are prepositions/determiners, not predicates.
ID_NON_VERB_AFFIXED = frozenset(
    {
        "terhadap",
        "tersebut",
        "terdapat",
        "terutama",
        "termasuk",
        "terakhir",
        "terlalu",
        "tertentu",
        "bersama",
        "berbagai",
        "berdasarkan",
        "beberapa",
        "berupa",
    }
)
_VERB_PREFIX_RE = re.compile(r"^(meng|meny|mem|men|me|ber|be|di|ter)")
_PASSIVE_SUFFIXES = ("kan", "i")
_MIN_ROOT_LEN = 4


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        _nlp_cache[lang] = spacy.load(model)
    return _nlp_cache[lang]


@lru_cache(maxsize=1)
def _sastrawi():
    """(root dictionary, stemmer) from PySastrawi's bundled kata-dasar list."""
    factory = StemmerFactory()
    roots = frozenset(w for w in factory.get_words_from_file() if w)
    return roots, factory.create_stemmer()


def normalise_colloquial(words: list[str]) -> tuple[list[str], int]:
    """Map colloquial connectives to standard forms; return (words, n_changed)."""
    out, changed = [], 0
    for w in words:
        standard = ID_COLLOQUIAL_TO_STANDARD.get(w)
        if standard is None:
            out.append(w)
        else:
            out.append(standard)
            changed += 1
    return out, changed


def is_di_passive(word: str) -> bool:
    """di- + a dictionary root (optionally + -kan/-i), excluding function roots.

    A bare di- + place noun ("dirumah", "dikantor") is the locative preposition
    written solid, so it is not passive; with a suffix ("dirumahkan",
    "dijalankan") it is. ter- is deliberately NOT treated as passive: most ter-
    words are adjectives, superlatives or stative forms (terjadi, terkait,
    terbaik).
    """
    if not word.startswith("di") or len(word) < 2 + _MIN_ROOT_LEN:
        return False
    roots, _ = _sastrawi()
    rest = word[2:]
    if rest in ID_FUNCTION_ROOTS or rest in ID_LOCATIVE_NOUN_ROOTS:
        return False
    candidates = [rest] + [
        rest[: -len(s)] for s in _PASSIVE_SUFFIXES if rest.endswith(s)
    ]
    return any(
        len(c) >= _MIN_ROOT_LEN and c in roots and c not in ID_FUNCTION_ROOTS
        for c in candidates
    )


@lru_cache(maxsize=65536)
def is_verb_like(word: str) -> bool:
    """Bare verb from ID_BARE_VERBS, or me-/ber-/di-/ter- on a dictionary root."""
    if word in ID_BARE_VERBS:
        return True
    if word in ID_JOINERS or word in ID_NON_VERB_AFFIXED:
        return False
    if not _VERB_PREFIX_RE.match(word):
        return False
    if word.startswith("di"):
        return is_di_passive(word)
    roots, stemmer = _sastrawi()
    root = stemmer.stem(word)
    return (
        root != word
        and len(root) >= 3
        and root in roots
        and root not in ID_FUNCTION_ROOTS
    )


def _segment_after(words: list[str], i: int) -> list[str]:
    segment = []
    for w in words[i + 1 :]:
        if w in ID_JOINERS:
            break
        segment.append(w)
    return segment


def _opens_clause(segment: list[str], require_subject: bool) -> bool:
    if not segment:
        return False
    if not require_subject:
        return any(is_verb_like(w) for w in segment)
    head = segment[0]
    if is_verb_like(head) or head in ID_PREDICATE_MODIFIERS:
        return False  # shared subject: predicate coordination inside one clause
    return any(is_verb_like(w) for w in segment[1:])


def count_id_clause_joiners(words: list[str]) -> tuple[int, int]:
    """Return (subordinators, coordinators) that actually join clauses."""
    subs = coords = 0
    for i, w in enumerate(words):
        if w in ID_SUBORDINATORS:
            subs += 1
        elif w in ID_CLAUSE_COORDINATORS:
            coords += 1
        elif w in ID_TEMPORAL_JOINERS:
            subs += _opens_clause(_segment_after(words, i), require_subject=False)
        elif w in ID_GATED_COORDINATORS:
            coords += _opens_clause(_segment_after(words, i), require_subject=True)
    return subs, coords


def _dep_depth(token) -> int:
    depth = 0
    seen = set()
    while token.head != token and id(token) not in seen:
        seen.add(id(token))
        token = token.head
        depth += 1
    return depth


def _analyze_syntactic_id(sentences: list[dict]) -> dict:
    """Parser-free Indonesian syntactic analysis.

    Dependency depth is not measurable without a parser, so it is reported as
    None (not 0) and excluded from the weighted score, with the remaining
    weights renormalised.
    """
    lengths, clause_counts, sub_counts = [], [], []
    passive_count = 0
    colloquial_total = 0
    evidence = []

    for sent_data in sentences:
        words = [w for w in sent_data["text"].split() if any(c.isalpha() for c in w)]
        lengths.append(len(words))
        lower = [re.sub(r"[^a-z\-]", "", w.lower()) for w in words]
        lower, n_colloquial = normalise_colloquial(lower)
        colloquial_total += n_colloquial

        subs, coords = count_id_clause_joiners(lower)
        sub_counts.append(subs)
        clause_counts.append(1 + subs + coords)

        passives = [w for w in lower if is_di_passive(w)]
        is_passive = bool(passives)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 1:
            triggered.append(f"subordinators:{subs}")
        if is_passive:
            triggered.append(f"passive:{passives[0]}")
        if triggered:
            evidence.append(
                {
                    "sentence_idx": sent_data["idx"],
                    "sentence": sent_data["text"],
                    "triggered_by": triggered,
                }
            )

    n = len(sentences) or 1
    msl = round(sum(lengths) / n, 1)
    clause_density = round(sum(clause_counts) / n, 2)
    sub_index = round(sum(sub_counts) / n, 3)
    passive_ratio = round(passive_count / n, 3)

    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    # Dependency depth (10% weight) is unmeasurable for id -> drop it and
    # renormalise the remaining 0.30/0.35/0.25 weights (sum 0.90) to 1.0.
    score = round(
        msl_score * (0.30 / 0.90) + cd_score * (0.35 / 0.90) + si_score * (0.25 / 0.90),
        1,
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": None,  # honest: not measurable without a parser
        "passive_ratio": passive_ratio,
        "colloquial_forms_normalised": colloquial_total,
        "comparable_across_languages": False,
        "score": score,
        "evidence": evidence[:3],
        "note": (
            "Indonesian syntactic metrics computed via rule-based morphology; "
            "dependency depth not measured (no parser for id). " + NON_COMPARABLE_NOTE
        ),
    }


def analyze_syntactic(sentences: list[dict], lang: str) -> dict:
    if lang == "id":
        return _analyze_syntactic_id(sentences)

    nlp = _get_nlp(lang)
    lengths, clause_counts, sub_counts, dep_depths = [], [], [], []
    passive_count = 0
    evidence = []

    for sent_data in sentences:
        doc = nlp(sent_data["text"])
        words = [t for t in doc if not t.is_space and not t.is_punct]
        lengths.append(len(words))

        clauses = sum(1 for t in doc if t.dep_ in CLAUSE_DEPS)
        clause_counts.append(max(1, clauses))

        subs = sum(1 for t in doc if t.dep_ in SUBORDINATE_DEPS)
        sub_counts.append(subs)

        max_depth = max((_dep_depth(t) for t in doc if not t.is_space), default=0)
        dep_depths.append(max_depth)

        is_passive = any(t.dep_ in {"nsubjpass", "auxpass", "aux:pass"} for t in doc)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 2:
            triggered.append(f"subordinate_clauses:{subs}")
        if max_depth >= 6:
            triggered.append(f"dep_depth:{max_depth}")
        if is_passive:
            triggered.append("passive_voice")
        if triggered:
            evidence.append(
                {
                    "sentence_idx": sent_data["idx"],
                    "sentence": sent_data["text"],
                    "triggered_by": triggered,
                }
            )

    n = len(sentences)
    msl = round(sum(lengths) / n, 1) if n else 0
    clause_density = round(sum(clause_counts) / n, 2) if n else 0
    sub_index = round(sum(sub_counts) / n, 3) if n else 0
    dep_depth = round(sum(dep_depths) / n, 1) if n else 0
    passive_ratio = round(passive_count / n, 3) if n else 0

    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    dd_score = min(100.0, max(0.0, (dep_depth - 2) / 8 * 100))

    score = round(
        msl_score * 0.30 + cd_score * 0.35 + si_score * 0.25 + dd_score * 0.10, 1
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": dep_depth,
        "passive_ratio": passive_ratio,
        "comparable_across_languages": False,
        "score": score,
        "evidence": evidence[:3],
        "note": NON_COMPARABLE_NOTE,
    }
```


- [ ] **Step 4: Record the F-023 acceptance-test change**

The parallel-text tolerance test cannot be met honestly (decision 1). Change the finding's `acceptance_test` in `docs/audit/curated.json` (matched by title, because curated ids differ from final ids) and regenerate the findings file:

```bash
.venv/bin/python - <<'EOF'
import json, pathlib
cur = pathlib.Path("docs/audit/curated.json")
fin = pathlib.Path("docs/audit/2026-10-11-aegis-findings.json")
curated = json.loads(cur.read_text(encoding="utf-8"))
title = {f["id"]: f["title"] for f in json.loads(fin.read_text(encoding="utf-8"))}["F-023"]
hits = [f for f in curated if f["title"] == title]
assert len(hits) == 1
hits[0]["acceptance_test"] = "test_syntactic_scores_flagged_not_comparable_across_languages"
cur.write_text(json.dumps(curated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
EOF
cp docs/audit/2026-10-11-aegis-findings.json /tmp/aegis-findings-before.json
.venv/bin/python scripts/consolidate_findings.py
.venv/bin/python - <<'EOF'
import json
a = json.load(open("/tmp/aegis-findings-before.json"))
b = json.load(open("docs/audit/2026-10-11-aegis-findings.json"))
assert [(f["id"], f["title"]) for f in a] == [(f["id"], f["title"]) for f in b], "ids moved"
changed = [f["id"] for f, g in zip(a, b) if f != g]
assert changed == ["F-023"], changed
print("ids stable; changed:", changed)
EOF
```

Expected: `wrote 100 findings ...` then `ids stable; changed: ['F-023']`.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_syntactic.py -v
```

Expected: all pass, including `test_en_path_unchanged`.


- [ ] **Step 6: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/syntactic.py tests/test_syntactic.py
.venv/bin/ruff format mcp-server/tools/syntactic.py tests/test_syntactic.py
.venv/bin/ruff check mcp-server/tools/syntactic.py tests/test_syntactic.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 7: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_syntactic.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_syntactic.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 8: Commit**

```bash
git add mcp-server/tools/syntactic.py \
  tests/test_syntactic.py \
  docs/audit/curated.json \
  docs/audit/2026-10-11-aegis-findings.json
git commit -m "feat(syntactic): Indonesian passive, clause and register heuristics; non-comparable flag (AEGIS F-010 F-011 F-018 F-023)" -m "Passive is di- + Sastrawi root (+ -kan/-i) excluding function and locative roots; ter- is not passive. dan/atau/serta join clauses only before an overt subject + predicate; temporal words only before a predicate. Colloquial connectives are normalised before counting. F-023 acceptance test changed to test_syntactic_scores_flagged_not_comparable_across_languages: no equating study exists, so a parallel-text tolerance test would be a fudged tolerance; results carry comparable_across_languages=false and cross-language ranking raises." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 9: Report and README — construct name, provenance caveat, Inspired By, no percentages (F-020, F-025, F-026, F-032)

**Files:**
- Modify: `mcp-server/tools/reporter.py` (full replacement), `README.md`
- Test: `tests/test_reporter.py` (replaced), `tests/test_pipeline.py` (replaced)

Behaviour changes that break existing tests in this task: report title, sections and JSON keys change (`verbal_fluency_score` → `style_index`, new `status`/`reasons`/`provenance`/`notice`), `RESEARCH BASIS` → `INSPIRED BY` without Pennebaker/Crossley/Mairesse (`test_report_contains_research_basis` is replaced by `test_report_contains_inspired_by_section`).

**Interfaces:**
- Consumes: `tools.policy.STYLE_INDEX_LABEL`, `PROVENANCE_CAVEAT`, `NO_INDIVIDUAL_DECISION_NOTICE`, `evaluate_gates`; results of Tasks 3–8.
- Produces (`tools.reporter`): `CONSTRUCT_NAME = "lexical-syntactic complexity"`, `INSPIRED_BY_NOTE`; `generate_report(lang_result, preprocess_result, lexical_result, syntactic_result, semantic_result, readability_result, vfs_result, iq_result, mental_age_result, band_result, format_flag="--both", age=None, verbose_caveats=False, gate=None) -> {"json": dict | None, "report": str | None}`. Full JSON keys: `status`, `reasons`, `provenance`, `notice` (`construct`, `style_index_label`, `no_individual_decision`, `provenance_caveat`), `language` (+ `language_norm_unvalidated`), `style_index`, `iq_prediction`, `mental_age`, `text_complexity`, `metrics`. `--scores-only` keys: `status`, `provenance`, `style_index_label`, `style_index`, `style_band`, `iq`, `iq_range`, `iq_range_label`, `mental_age`, `text_complexity_band`, `length_tier`, `language_norm_unvalidated`. Without a gate the report says `Status: UNVERIFIED` and `Provenance      : not attested`.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_reporter.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import pathlib
import re
import sys

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from pipeline import run_pipeline
from tools.policy import evaluate_gates
from tools.reporter import generate_report

from tests.helpers import corpus_text, ok_gate, validated_policy

README = pathlib.Path("README.md")
LANG = {
    "lang": "en",
    "confidence": 0.97,
    "supported": True,
    "mixed_language_share": 0.0,
}
PREP = {
    "word_count": 412,
    "token_count": 415,
    "sentence_count": 18,
    "sentences": [{"idx": 0, "text": "The cat sat on the mat."}],
    "text_clean": "The cat sat.",
}
LEXICAL = {
    "mattr": 0.78,
    "mtld": 96.4,
    "vocd_d": 61.2,
    "lexical_density": 0.53,
    "avg_word_length": 5.8,
    "oov_rate": 0.01,
    "low_reliability": False,
    "reliability_reasons": [],
    "score": 78.1,
    "evidence": [
        {
            "sentence_idx": 0,
            "sentence": "The epistemological underpinnings.",
            "triggered_by": ["rare:epistemological"],
        }
    ],
}
SYNTACTIC = {
    "mean_sentence_length": 18.3,
    "clause_density": 2.1,
    "subordination_index": 0.48,
    "dependency_depth": 6.0,
    "passive_ratio": 0.12,
    "comparable_across_languages": False,
    "score": 69.2,
    "evidence": [],
}
SEMANTIC = {
    "adjacent_sentence_similarity": 0.74,
    "topic_drift_index": 0.21,
    "lexical_chain_density": 0.61,
    "entity_labels": ["ORG"],
    "score": 71.8,
    "evidence": [
        {
            "sentence_idx_from": 0,
            "sentence_idx_to": 1,
            "similarity": 0.81,
            "note": "high overlap",
        }
    ],
}
READABILITY = {
    "flesch_reading_ease": 52.1,
    "gunning_fog": 12.4,
    "ari": 11.8,
    "coleman_liau": 12.1,
    "score": 65.0,
    "evidence": [],
}
VFS = {
    "vfs": 73.4,
    "style_index": 73.4,
    "lexical": 78.1,
    "syntactic": 69.2,
    "semantic": 71.8,
    "readability": 65.0,
    "unavailable_components": [],
    "confidence_label": "HIGH",
    "lang": "en",
    "text_length_words": 412,
}
IQ_WITHHELD = {
    "style_index": 73.4,
    "style_index_label": "x",
    "style_band": "Style band 4",
    "point_estimate": None,
    "range_low": None,
    "range_high": None,
    "range_label": "uncalibrated heuristic range",
    "classification": None,
    "percentile": None,
    "withheld_reason": "UNVALIDATED: IQ mapping is not validated for language 'en'",
    "language_norm_unvalidated": True,
}
IQ_EMITTED = {
    **IQ_WITHHELD,
    "point_estimate": 117,
    "range_low": 92,
    "range_high": 142,
    "classification": "Style band 4",
    "percentile": 87,
    "withheld_reason": None,
    "language_norm_unvalidated": False,
}
MENTAL_AGE = {
    "mental_age": None,
    "based_on_chronological_age": None,
    "age_assumed": False,
    "withheld_reason": "chronological age not supplied; never assumed",
    "formula": "mental_age = (iq / 100) * chronological_age",
}
BAND = {
    "text_complexity_band": 5,
    "label": "Complexity band 5",
    "per_metric_bands": {"gunning_fog": 5, "ari": 5, "lexical_density": 5},
    "consistency": "CONSISTENT",
    "withheld_reason": None,
    "note": "Describes how difficult this text is to read, not the writer's "
    "education. Education cannot be inferred from text.",
}
DEFAULT_GATE = evaluate_gates(LANG, 412, 20, "unknown", "unknown")


def _call(flag="--both", iq=IQ_WITHHELD, gate=DEFAULT_GATE, **kwargs):
    return generate_report(
        LANG,
        PREP,
        LEXICAL,
        SYNTACTIC,
        SEMANTIC,
        READABILITY,
        VFS,
        iq,
        MENTAL_AGE,
        BAND,
        format_flag=flag,
        gate=gate,
        **kwargs,
    )


def test_json_flag_returns_json_no_report():
    result = _call("--json")
    assert result["json"] is not None
    assert result["report"] is None


def test_report_flag_returns_report_no_json():
    result = _call("--report")
    assert result["report"] is not None
    assert result["json"] is None


def test_both_flag_returns_both():
    result = _call("--both")
    assert result["json"] is not None
    assert result["report"] is not None


def test_scores_only_returns_slim_json_with_status():
    slim = _call("--scores-only")["json"]
    assert slim["status"] == "UNVERIFIED_PROVENANCE"
    assert slim["style_index"] == 73.4
    assert slim["iq"] is None
    assert slim["iq_range"] is None
    assert slim["language_norm_unvalidated"] is True
    assert "Not an intelligence measure" in slim["style_index_label"]


def test_report_shows_iq_only_when_emitted():
    pol = validated_policy()
    withheld = _call("--report")["report"]
    assert "Withheld" in withheld
    emitted = _call("--report", iq=IQ_EMITTED, gate=ok_gate(policy=pol))["report"]
    assert "Point estimate  : 117" in emitted
    assert "Uncalibrated heuristic range : 92–142" in emitted


def test_report_contains_evidence_sentence():
    assert "epistemological" in _call("--report")["report"]


def test_verbose_caveats_adds_extended_section():
    assert "EXTENDED LIMITATIONS" in _call("--report", verbose_caveats=True)["report"]


def test_report_contains_length_tier_label():
    assert "Text length tier    : HIGH" in _call("--report")["report"]


def test_id_report_shows_depth_na_and_caveats():
    id_lang = {**LANG, "lang": "id"}
    report = generate_report(
        id_lang,
        PREP,
        LEXICAL,
        {**SYNTACTIC, "dependency_depth": None},
        SEMANTIC,
        READABILITY,
        {**VFS, "lang": "id"},
        IQ_WITHHELD,
        MENTAL_AGE,
        BAND,
        format_flag="--report",
        gate=evaluate_gates(id_lang, 412, 20),
    )["report"]
    assert "N/A (no parser for id)" in report
    assert "no dependency parser" in report
    assert "uncalibrated for" in report


def test_en_report_still_shows_numeric_depth():
    report = _call("--report")["report"]
    assert "Dependency tree depth : 6.0" in report
    assert "no parser for id" not in report


def test_report_and_readme_name_construct_lexical_syntactic_complexity_not_fluency():
    report = _call("--report")["report"]
    assert "LEXICAL-SYNTACTIC COMPLEXITY REPORT" in report
    assert "VERBAL FLUENCY" not in report.upper()
    assert "Not an intelligence measure" in report
    assert "rewards surface complexity" in report
    assert _call("--json")["json"]["notice"]["construct"] == (
        "lexical-syntactic complexity"
    )
    readme = README.read_text(encoding="utf-8")
    assert "lexical-syntactic complexity" in readme
    assert "does not measure verbal fluency" in readme
    assert "using verbal fluency as a psycholinguistic proxy" not in readme
    assert "rewards complexity, not quality" in readme


def test_report_research_section_states_no_individual_validation():
    report = _call("--report")["report"]
    assert "INSPIRED BY" in report
    assert "RESEARCH BASIS" not in report
    assert "no individual-level validation" in report
    for name in ("Pennebaker", "Crossley", "Mairesse"):
        assert name not in report
    readme = README.read_text(encoding="utf-8")
    assert "## Inspired By" in readme
    assert "## Research Basis" not in readme
    assert "no individual-level validation" in readme


def test_report_does_not_format_heuristic_confidence_as_percent():
    for gate, iq in ((DEFAULT_GATE, IQ_WITHHELD), (ok_gate(), IQ_EMITTED)):
        report = _call("--report", iq=iq, gate=gate)["report"]
        assert not re.search(r"\d+%", report)
        assert "Lang detection      : HIGH" in report
    assert "95% CI" not in README.read_text(encoding="utf-8")


def test_report_band_heading_is_style_band_not_classification():
    report = _call("--report", iq=IQ_EMITTED, gate=ok_gate())["report"]
    assert "Classification" not in report
    assert "Style band      : Style band 4" in report


def test_report_includes_provenance_caveat_and_requires_attestation():
    report = _call("--report")["report"]
    assert "Provenance      : unknown" in report
    assert "Valid only for supervised, unaided writing" in report
    assert "UNVERIFIED_PROVENANCE" in report
    no_gate = _call("--report", gate=None)["report"]
    assert "Provenance      : not attested" in no_gate
    assert "Status: UNVERIFIED" in no_gate

    pol = validated_policy()
    text = corpus_text("en_news_report")
    unattested = run_pipeline(text, text_type="formal_prose", policy=pol)
    assert unattested["status"] == "UNVERIFIED_PROVENANCE"
    assert unattested["iq"] is None
    attested = run_pipeline(
        text, provenance="supervised_unaided", text_type="formal_prose", policy=pol
    )
    assert attested["iq"] is not None


def test_report_flags_language_norms_unvalidated():
    report = _call("--report")["report"]
    assert "Language norms      : UNVALIDATED for English" in report
    assert _call("--json")["json"]["language"]["language_norm_unvalidated"] is True
```


Replace `tests/test_pipeline.py` with:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import evaluate_gates
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

EN_LONG = """
The epistemological foundations of cognitive science have undergone substantial transformation
over the past three decades, driven by advances in computational neuroscience and the emergence
of connectionist models that challenge classical symbolic approaches. Although the data from
early neural network experiments was inconclusive, subsequent research demonstrated that
distributed representations could encode semantic relationships more effectively than
rule-based systems. The implications for natural language processing are profound:
systems that learn statistical regularities from large corpora exhibit emergent properties
that were not explicitly programmed, suggesting that intelligence may be better understood
as a statistical phenomenon than as a logical one. This perspective, while compelling,
requires careful methodological scrutiny to avoid conflating correlation with causation
in the interpretation of model behavior.
"""

ID_MEDIUM = """
Perkembangan teknologi informasi telah mengubah paradigma komunikasi modern secara fundamental.
Implementasi sistem berbasis kecerdasan buatan memerlukan koordinasi multidimensional antara
berbagai pemangku kepentingan yang memiliki perspektif berbeda-beda.
Meskipun tantangan teknis yang dihadapi sangat kompleks, tim pengembang berhasil menyelesaikan
proyek tersebut dengan hasil yang memuaskan karena dedikasi dan kolaborasi yang intensif.
"""

EN_SHORT = "The cat sat on the mat."


def _run_pipeline(text: str) -> dict:
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep_r = preprocess_text(text, lang)
    gate = evaluate_gates(lang_r, prep_r["word_count"], prep_r["terminal_mark_count"])
    lex_r = analyze_lexical(prep_r["tokens"], prep_r["sentences"], lang)
    syn_r = analyze_syntactic(prep_r["sentences"], lang)
    sem_r = analyze_semantic(prep_r["text_clean"], prep_r["sentences"], lang)
    read_r = analyze_readability(prep_r["text_clean"], lang)
    vfs_r = compute_verbal_fluency_score(
        lex_r, syn_r, sem_r, read_r, prep_r["word_count"], lang
    )
    iq_r = predict_iq(vfs_r["style_index"], lang, gate=gate)
    ma_r = predict_mental_age(iq_r["point_estimate"])
    band_r = estimate_text_complexity_band(
        read_r["gunning_fog"], read_r["ari"], lex_r["lexical_density"], lang, gate=gate
    )
    report_r = generate_report(
        lang_r,
        prep_r,
        lex_r,
        syn_r,
        sem_r,
        read_r,
        vfs_r,
        iq_r,
        ma_r,
        band_r,
        "--both",
        gate=gate,
    )
    return {"vfs": vfs_r, "iq": iq_r, "band": band_r, "report": report_r, "gate": gate}


def test_en_long_pipeline_completes():
    result = _run_pipeline(EN_LONG)
    assert 0 < result["vfs"]["style_index"] <= 100
    assert result["iq"]["style_band"].startswith("Style band")
    assert result["report"]["report"] is not None
    assert result["report"]["json"] is not None


def test_en_long_iq_withheld_by_default_policy():
    result = _run_pipeline(EN_LONG)
    assert result["iq"]["point_estimate"] is None
    assert result["iq"]["withheld_reason"]


def test_id_pipeline_detects_indonesian():
    assert detect_language(ID_MEDIUM)["lang"] == "id"


def test_id_pipeline_completes_without_education_band():
    result = _run_pipeline(ID_MEDIUM)
    assert result["vfs"]["style_index"] > 0
    assert result["band"]["text_complexity_band"] is None


def test_short_text_very_low_length_tier_and_insufficient_text():
    result = _run_pipeline(EN_SHORT)
    assert result["vfs"]["confidence_label"] in ("VERY LOW", "LOW")
    assert result["gate"]["status"] == "INSUFFICIENT_TEXT"
    assert result["vfs"]["semantic"] is None


def test_report_contains_inspired_by_section():
    assert "INSPIRED BY" in _run_pipeline(EN_LONG)["report"]["report"]


def test_json_output_has_all_top_level_keys():
    j = _run_pipeline(EN_LONG)["report"]["json"]
    for key in (
        "status",
        "reasons",
        "provenance",
        "notice",
        "language",
        "style_index",
        "iq_prediction",
        "mental_age",
        "text_complexity",
        "metrics",
    ):
        assert key in j


def test_vfs_does_not_drift_more_than_2_points_on_same_input():
    r1 = _run_pipeline(EN_LONG)
    r2 = _run_pipeline(EN_LONG)
    assert abs(r1["vfs"]["style_index"] - r2["vfs"]["style_index"]) < 2.0
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_reporter.py tests/test_pipeline.py -v
```

Expected: FAIL — `TypeError: generate_report() got an unexpected keyword argument 'gate'` across `test_reporter.py`, and the README assertions.

- [ ] **Step 3: Implement the report**

Replace `mcp-server/tools/reporter.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
from datetime import date

from tools.policy import (
    NO_INDIVIDUAL_DECISION_NOTICE,
    PROVENANCE_CAVEAT,
    STYLE_INDEX_LABEL,
)

LANG_LABELS = {"en": "English", "id": "Indonesian"}
CONSTRUCT_NAME = "lexical-syntactic complexity"
INSPIRED_BY_NOTE = (
    "Inspired by the work below. None of it validates this tool, and this "
    "tool has no individual-level validation."
)


def _bar(score: float | None, width: int = 10) -> str:
    if score is None:
        return ""
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _trunc(text: str, max_len: int = 100) -> str:
    return f'"{text[:max_len]}..."' if len(text) > max_len else f'"{text}"'


def _fmt(value, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value}{suffix}"


def _detection_label(confidence: float) -> str:
    """Ordinal label for the detector-agreement heuristic (never a percent)."""
    if confidence >= 0.95:
        return "HIGH"
    if confidence >= 0.80:
        return "MEDIUM"
    return "LOW"


def generate_report(
    lang_result: dict,
    preprocess_result: dict,
    lexical_result: dict,
    syntactic_result: dict,
    semantic_result: dict,
    readability_result: dict,
    vfs_result: dict,
    iq_result: dict,
    mental_age_result: dict,
    band_result: dict,
    format_flag: str = "--both",
    age: int | None = None,
    verbose_caveats: bool = False,
    gate: dict | None = None,
) -> dict:
    status = gate["status"] if gate else "UNVERIFIED"
    reasons = gate["reasons"] if gate else ["no gate evaluation supplied"]
    provenance = gate["provenance"] if gate else "not attested"
    norm_unvalidated = (
        gate["language_norm_unvalidated"]
        if gate
        else iq_result.get("language_norm_unvalidated", True)
    )
    notice = {
        "construct": CONSTRUCT_NAME,
        "style_index_label": STYLE_INDEX_LABEL,
        "no_individual_decision": NO_INDIVIDUAL_DECISION_NOTICE,
        "provenance_caveat": PROVENANCE_CAVEAT,
    }
    full_json = {
        "status": status,
        "reasons": reasons,
        "provenance": provenance,
        "notice": notice,
        "language": {**lang_result, "language_norm_unvalidated": norm_unvalidated},
        "style_index": vfs_result,
        "iq_prediction": iq_result,
        "mental_age": mental_age_result,
        "text_complexity": band_result,
        "metrics": {
            "lexical": lexical_result,
            "syntactic": syntactic_result,
            "semantic": semantic_result,
            "readability": readability_result,
        },
    }

    iq_range = None
    if iq_result.get("range_low") is not None:
        iq_range = f"{iq_result['range_low']}–{iq_result['range_high']}"

    if format_flag == "--scores-only":
        slim = {
            "status": status,
            "provenance": provenance,
            "style_index_label": STYLE_INDEX_LABEL,
            "style_index": vfs_result["style_index"],
            "style_band": iq_result["style_band"],
            "iq": iq_result["point_estimate"],
            "iq_range": iq_range,
            "iq_range_label": iq_result["range_label"] if iq_range else None,
            "mental_age": mental_age_result["mental_age"],
            "text_complexity_band": band_result["text_complexity_band"],
            "length_tier": vfs_result["confidence_label"],
            "language_norm_unvalidated": norm_unvalidated,
        }
        return {"json": slim, "report": None}

    if format_flag == "--json":
        return {"json": full_json, "report": None}

    sep = "━" * 50
    thin = "  " + "─" * 46
    L: list[str] = []

    def line(s: str = "") -> None:
        L.append(s)

    lang_name = LANG_LABELS.get(lang_result["lang"], lang_result["lang"])
    line(sep)
    line("  LEXICAL-SYNTACTIC COMPLEXITY REPORT")
    line(f"  Generated: {date.today().isoformat()} | Language: {lang_name}")
    line(f"  Status: {status}")
    line(sep)
    line()
    line("  NOTICE")
    line(f"  {STYLE_INDEX_LABEL}")
    line(f"  {NO_INDIVIDUAL_DECISION_NOTICE}")
    line(f"  Provenance      : {provenance}")
    line(f"  {PROVENANCE_CAVEAT}")
    if status != "OK":
        line("  Withheld or limited because:")
        for reason in reasons:
            line(f"    • {reason}")
    line()

    line("  SUBJECT TEXT")
    line(
        f"  Text input          : {preprocess_result['word_count']} words "
        f"({preprocess_result.get('token_count', preprocess_result['word_count'])} "
        f"tokens), {preprocess_result['sentence_count']} sentences"
    )
    line(f"  Lang detection      : {_detection_label(lang_result['confidence'])}")
    line(f"  Text length tier    : {vfs_result['confidence_label']}")
    if norm_unvalidated:
        line(
            f"  Language norms      : UNVALIDATED for {lang_name}; "
            "never compare or rank across languages"
        )
    line()

    line(thin)
    line(f"  STYLE INDEX ({CONSTRUCT_NAME})")
    line(thin)
    line(f"  Style index     : {_fmt(vfs_result['style_index'])} / 100")
    line(f"  Style band      : {_fmt(iq_result['style_band'])}")
    for key, label in (
        ("lexical", "Lexical    "),
        ("syntactic", "Syntactic  "),
        ("semantic", "Semantic   "),
        ("readability", "Readability"),
    ):
        value = vfs_result[key]
        line(f"  └── {label} : {_fmt(value)} / 100  {_bar(value)}")
    if vfs_result.get("unavailable_components"):
        unavailable = ", ".join(vfs_result["unavailable_components"])
        line(f"  Not measurable (weights renormalised): {unavailable}")
    line()

    line(thin)
    line("  IQ (EXPERIMENTAL, UNVALIDATED)")
    line(thin)
    if iq_result["point_estimate"] is None:
        line(f"  Withheld        : {iq_result['withheld_reason']}")
    else:
        line(f"  Point estimate  : {iq_result['point_estimate']}")
        line(f"  {iq_result['range_label'].capitalize()} : {iq_range}")
        line(f"  Style band      : {iq_result['classification']}")
        line(f"  Percentile      : ~{iq_result['percentile']}th (from IQ, N(100, 15))")
    line()

    line(thin)
    line("  MENTAL AGE")
    line(thin)
    if mental_age_result["mental_age"] is None:
        line(f"  Withheld        : {mental_age_result['withheld_reason']}")
    else:
        line(
            f"  Estimated       : {mental_age_result['mental_age']} years "
            f"(age {mental_age_result['based_on_chronological_age']})"
        )
    line()

    line(thin)
    line("  TEXT COMPLEXITY BAND")
    line(thin)
    if band_result["text_complexity_band"] is None:
        line(f"  Withheld        : {band_result['withheld_reason']}")
    else:
        line(f"  Band            : {band_result['label']}")
        line(f"  Metric agreement: {band_result['consistency']}")
    line(f"  {band_result['note']}")
    line()

    line(thin)
    line("  DETAILED LEXICAL METRICS")
    line(thin)
    line(f"  MATTR (window=50)     : {_fmt(lexical_result.get('mattr'))}")
    line(f"  MTLD                  : {_fmt(lexical_result.get('mtld'))}")
    line(f"  VOCD-D                : {_fmt(lexical_result.get('vocd_d'))}")
    line(f"  Content-word density  : {_fmt(lexical_result.get('lexical_density'))}")
    line(
        f"  Avg word length       : {_fmt(lexical_result.get('avg_word_length'))} "
        "chars (not scored)"
    )
    line(f"  Out-of-dictionary rate: {_fmt(lexical_result.get('oov_rate'))}")
    for reason in lexical_result.get("reliability_reasons", []):
        line(f"  LOW RELIABILITY       : {reason}")
    line()

    line(thin)
    line("  DETAILED SYNTACTIC METRICS")
    line(thin)
    line(f"  Mean sentence length  : {syntactic_result['mean_sentence_length']} words")
    line(f"  Clause density        : {syntactic_result['clause_density']}")
    line(f"  Subordination index   : {syntactic_result['subordination_index']}")
    _dep_depth = syntactic_result["dependency_depth"]
    line(
        "  Dependency tree depth : "
        f"{_dep_depth if _dep_depth is not None else 'N/A (no parser for id)'}"
    )
    line(f"  Passive voice ratio   : {syntactic_result['passive_ratio']}")
    if syntactic_result.get("colloquial_forms_normalised"):
        line(
            "  Colloquial forms      : "
            f"{syntactic_result['colloquial_forms_normalised']} normalised to "
            "standard Indonesian before counting"
        )
    line()

    line(thin)
    line("  DETAILED SEMANTIC METRICS")
    line(thin)
    line(
        "  Adjacent-sentence similarity : "
        f"{_fmt(semantic_result.get('adjacent_sentence_similarity'))}"
    )
    line(
        "  Topic drift index     : "
        f"{_fmt(semantic_result.get('topic_drift_index'))} (low = focused)"
    )
    line(
        f"  Lexical chain density : {_fmt(semantic_result.get('lexical_chain_density'))}"
    )
    labels = ", ".join(semantic_result.get("entity_labels", [])) or "none"
    line(f"  Entity labels         : {labels} (not scored)")
    line()

    line(thin)
    line("  READABILITY INDICES")
    line(thin)
    line(f"  Flesch Reading Ease   : {readability_result['flesch_reading_ease']}")
    line(f"  Gunning Fog Index     : {readability_result['gunning_fog']}")
    line(f"  ARI                   : {readability_result['ari']}")
    line(f"  Coleman-Liau Index    : {readability_result['coleman_liau']}")
    line()

    line(thin)
    line("  INTERPRETATION WITH EVIDENCE")
    line(thin)
    line()

    line(f"  [LEXICAL — Score {_fmt(vfs_result['lexical'])}]")
    line(
        f"  Vocabulary diversity (MATTR {_fmt(lexical_result.get('mattr'))}, "
        f"MTLD {_fmt(lexical_result.get('mtld'))}), content-word density "
        f"{_fmt(lexical_result.get('lexical_density'))}."
    )
    for ev in lexical_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SYNTACTIC — Score {_fmt(vfs_result['syntactic'])}]")
    line(
        f"  Clause density {syntactic_result['clause_density']}, "
        f"subordination index {syntactic_result['subordination_index']}."
    )
    for ev in syntactic_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SEMANTIC — Score {_fmt(vfs_result['semantic'])}]")
    line(
        "  Adjacent-sentence similarity "
        f"{_fmt(semantic_result.get('adjacent_sentence_similarity'))}, topic drift "
        f"{_fmt(semantic_result.get('topic_drift_index'))}."
    )
    sents = preprocess_result.get("sentences", [])
    sent_map = {s["idx"]: s["text"] for s in sents}
    for ev in semantic_result.get("evidence", [])[:3]:
        line(
            f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} "
            f"similarity: {ev['similarity']} [{ev['note']}]"
        )
        src = sent_map.get(ev["sentence_idx_from"], "")
        if src:
            line(f"       {_trunc(src, 80)}")
    line()

    line(f"  [READABILITY — Score {_fmt(vfs_result['readability'])}]")
    line(
        f"  Gunning Fog {readability_result['gunning_fog']}, "
        f"ARI {readability_result['ari']}."
    )
    for ev in readability_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(thin)
    line("  LIMITATIONS")
    line(thin)
    line(f"  Text length tier      : {vfs_result['confidence_label']}")
    line("  Limiting factors      :")
    line("    • The index rewards surface complexity (longer words and sentences,")
    line("      rarer words, more subordination), not correctness, relevance or")
    line("      argument quality. Padding with jargon raises it.")
    line("    • Genre, topic, editing and first language move every metric.")
    line("    • Punctuation density is a confound for sentence-length metrics.")
    line("    • Education cannot be inferred from text.")
    line("    • Scores are not comparable across languages.")
    if lang_result["lang"] == "id":
        line("    • Indonesian syntactic depth not measured (no dependency parser);")
        line("      syntactic score derived from clause density, subordination, and")
        line("      passive morphology only")
        line("    • Bands and scaling are English-derived and uncalibrated for")
        line("      Indonesian")

    if verbose_caveats or format_flag == "--verbose-caveats":
        line()
        line("  EXTENDED LIMITATIONS (--verbose-caveats)")
        line("    • This tool produces text statistics, NOT clinical diagnoses.")
        line("    • Text proxies cannot replace standardized ability tests")
        line("      (WAIS-IV, Raven's Progressive Matrices, etc.).")
        line("    • The ratio mental-age model is undefined for adults.")
        line("    • Do not use these outputs for hiring, clinical, or legal decisions.")

    line()
    line(thin)
    line("  INSPIRED BY")
    line(thin)
    line(f"  {INSPIRED_BY_NOTE}")
    line("  Gunning (1952)            — Fog Index")
    line("  Coleman & Liau (1975)     — CL Index")
    line("  McCarthy & Jarvis (2010)  — MTLD")
    line("  Covington & McFall (2010) — MATTR")
    line()
    line(sep)

    report_text = "\n".join(L)

    if format_flag == "--report":
        return {"json": None, "report": report_text}
    return {"json": full_json, "report": report_text}
```


- [ ] **Step 4: Rewrite the README claims**

Save the following one-off script outside the repository (for example in your scratchpad as `aegis_t9_readme.py`; do not commit it) and run it with `.venv/bin/python <path>/aegis_t9_readme.py README.md`. It replaces the title paragraph, Overview, the IQ & Education Mapping section, two Output Flags rows, Configuration Reference, Sample Report, Limitations & Ethics and Research Basis, and fails loudly if an anchor is missing:


````python
"""Task 9 README edits: construct naming, limitations, Inspired By (F-025/F-026/F-032)."""

import pathlib
import sys

README = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")

INTRO = """# Verbal Fluency IQ

Measures the **lexical-syntactic complexity** of a text passage: vocabulary diversity, content-word density, clause structure, adjacent-sentence similarity and readability. Supports **English** and **Indonesian**.

**What it is not.** The tool does not measure verbal fluency (the psychological construct of word-generation rate) and it is not an intelligence test. Its style index rewards complexity, not quality: longer words, longer sentences, rarer words and more subordination all raise it, while correctness, relevance and argument quality are not measured. An experimental IQ mapping exists but is withheld unless a validation study has passed for that language (see `docs/validation/validation-protocol.md`); in the shipped configuration it is withheld for every language.

**Tool-first design:** all scores are computed by deterministic MCP tools. The AI orchestrates the pipeline but never estimates scores by reasoning alone.
"""

OVERVIEW = """## Overview

Text complexity statistics correlate weakly, at group level, with many things: education, genre, editing, topic and first language among them. This project computes those statistics deterministically and reports them as a **writing-style index of lexical-syntactic complexity**, with every limitation attached:

```
Raw text
  → Language detection (unsupported or code-switched text is refused)
  → Preprocessing (tokenisation, sentence splitting, alphabetic word count)
  → Validity gates (length, punctuation structure, provenance, text type, validation status)
  → Lexical analysis    (MATTR, MTLD, content-word density, out-of-dictionary rate)
  → Syntactic analysis  (clause complexity, dependency depth for English)
  → Semantic analysis   (adjacent-sentence similarity, topic drift, lexical chains)
  → Readability indices (Fog, ARI, Coleman-Liau, Flesch)
  → Style index (0–100) + neutral style band
  → Experimental IQ, mental age, text complexity band — each withheld unless its gate passes
  → Structured report with status, reasons, provenance caveat and sentence-level evidence
```

Every result carries a `status` (`OK`, `INSUFFICIENT_TEXT`, `UNSUPPORTED_LANGUAGE`, `MIXED_LANGUAGE`, `INSUFFICIENT_STRUCTURE`, `UNVERIFIED_PROVENANCE`, `UNVALIDATED`) and the `reasons` behind it. With the shipped `mcp-server/config/validation.json` no language is validated, so the best possible status is `UNVALIDATED` and no IQ is emitted.
"""

MAPPING = """## Style Bands, Experimental IQ & Text Complexity

### Style index → style band

| Style index | Style band | Experimental IQ range (withheld unless validated) |
|---|---|---|
| 85–100 | Style band 5 | 125–145 |
| 70–84.99 | Style band 4 | 110–124 |
| 55–69.99 | Style band 3 | 90–109 |
| 40–54.99 | Style band 2 | 75–89 |
| 0–39.99 | Style band 1 | 55–74 |

Style bands are neutral ordinal labels. They are not psychometric classifications and carry no clinical meaning. The band table is hand-set and uncalibrated.

When (and only when) a language is marked `iq_validated` in `config/validation.json` and every gate passes, the IQ point is interpolated within the band, the percentile is the normal CDF of that IQ under N(100, 15), and the interval is an **uncalibrated heuristic range** of at least ±25 points. Nothing in this project is a 95% confidence interval.

### Text complexity bands

| Band | Fog Min | ARI Min | Content-word density Min |
|---|---|---|---|
| Complexity band 7 | 17 | 16 | 0.60 |
| Complexity band 6 | 14 | 13 | 0.55 |
| Complexity band 5 | 11 | 10 | 0.48 |
| Complexity band 4 | 9 | 8 | 0.42 |
| Complexity band 3 | 7 | 6 | 0.36 |
| Complexity band 2 | 5 | 4 | 0.30 |
| Complexity band 1 | 0 | 0 | 0.00 |

Each metric is banded on its own; the reported band is the median of the three. `consistency` is `CONSISTENT` when the per-metric bands are within one band of each other and `CONFLICTING` otherwise. No percentage confidence is reported.

A complexity band describes how difficult the text is to read. It is **not** the writer's education level; education cannot be inferred from text. Bands are unavailable for Indonesian because Fog, ARI and Coleman-Liau are English formulas and no Indonesian calibration exists.

### Mental age

The ratio model `mental_age = (iq / 100) × chronological_age` is undefined for adults. Mental age is reported only when an IQ was emitted and a chronological age of 16 or less was supplied; it is never computed from an assumed age.
"""

SCORES_ONLY_OLD = "| `--scores-only` | Slim 6-key JSON: `vfs`, `iq`, `iq_range`, `mental_age`, `education`, `confidence` |"
SCORES_ONLY_NEW = "| `--scores-only` | Slim JSON: `status`, `provenance`, `style_index`, `style_band`, `iq`, `iq_range`, `iq_range_label`, `mental_age`, `text_complexity_band`, `length_tier`, `language_norm_unvalidated` |"
AGE_OLD = "| `--age=N` | Sets chronological age to integer N for mental age calculation |"
AGE_NEW = "| `--age=N` | Sets chronological age to integer N; mental age is reported only for ages up to 16 when IQ is emitted |"

CONFIG = """## Configuration Reference

### `mcp-server/config/validation.json`

The validity policy. Every gate threshold lives here, and IQ output for a language is enabled only by setting `iq_validated: true` after the study in `docs/validation/validation-protocol.md` passes. There is no per-call override.

```json
{
  "version": "2026-10-11",
  "languages": {
    "en": {"iq_validated": false, "education_validated": false},
    "id": {"iq_validated": false, "education_validated": false}
  },
  "min_words": 250,
  "min_lang_confidence": 0.80,
  "max_mixed_language_share": 0.20,
  "max_words_per_terminal_mark": 40,
  "uncalibrated_range_half_width": 25,
  "min_drift_transitions": 5
}
```

### `mcp-server/config/iq_norms.json`

```json
{
  "status": "uncalibrated: hand-set bands with no norm sample (see docs/validation/validation-protocol.md)",
  "note": "Labels are neutral ordinal style bands, not psychometric classifications.",
  "bands": [
    {
      "vfs_min": 85, "vfs_max": 100,
      "iq_min": 125, "iq_max": 145,
      "label": "Style band 5"
    }
    // ... 4 more bands
  ],
  "iq_mean": 100,
  "iq_sd": 15,
  "max_ratio_mental_age_years": 16
}
```

There is no default chronological age: mental age is never computed from an assumed age.

### `mcp-server/config/edu_norms.json`

```json
{
  "status": "uncalibrated: hand-set thresholds with no norm sample",
  "bands": [
    {"band": 1, "label": "Complexity band 1", "fog_min": 0, "ari_min": 0, "lexical_density_min": 0.0}
    // ... 6 more bands
  ]
}
```

Despite the historical file name, these are text complexity bands, not education levels.

### `mcp-server/config/semantic_scaling.json`

Per-language bounds for scaling mean adjacent-sentence similarity to 0–100. Both languages currently use the uncalibrated 0.3–0.9 bounds, and the file is marked `"status": "uncalibrated"`.

### `mcp-server/config/id_syllables.json`

Contains vowel characters and diphthong patterns used by the Indonesian syllable counter. The counter uses vowel-nuclei transitions rather than dictionary lookup for robustness with unknown words.
"""

SAMPLE = """## Sample Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LEXICAL-SYNTACTIC COMPLEXITY REPORT
  Generated: 2026-10-11 | Language: English
  Status: UNVERIFIED_PROVENANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  NOTICE
  Writing-style index (lexical-syntactic complexity). Not an intelligence measure.
  Not validated for decisions about individuals (hiring, admissions, clinical, legal). Human review is mandatory.
  Provenance      : unknown
  Valid only for supervised, unaided writing produced for the same prompt. AI assistance, translation, dictation or editing change every score.
  Withheld or limited because:
    • UNVERIFIED_PROVENANCE: provenance 'unknown': authorship is not attested as supervised and unaided
    • UNVALIDATED: text_type 'unknown' is outside the formal-prose scope; IQ is refused
    • UNVALIDATED: IQ mapping is not validated for language 'en' (config/validation.json)

  SUBJECT TEXT
  Text input          : 312 words (318 tokens), 18 sentences
  Lang detection      : HIGH
  Text length tier    : HIGH
  Language norms      : UNVALIDATED for English; never compare or rank across languages

  ──────────────────────────────────────────────
  STYLE INDEX (lexical-syntactic complexity)
  ──────────────────────────────────────────────
  Style index     : 61.2 / 100
  Style band      : Style band 3
  └── Lexical     : 70.4 / 100  ███████░░░
  └── Syntactic   : 62.9 / 100  ██████░░░░
  └── Semantic    : 19.2 / 100  ██░░░░░░░░
  └── Readability : 68.1 / 100  ███████░░░

  ──────────────────────────────────────────────
  IQ (EXPERIMENTAL, UNVALIDATED)
  ──────────────────────────────────────────────
  Withheld        : UNVERIFIED_PROVENANCE: provenance 'unknown': ...

  ──────────────────────────────────────────────
  MENTAL AGE
  ──────────────────────────────────────────────
  Withheld        : IQ estimate withheld

  ──────────────────────────────────────────────
  TEXT COMPLEXITY BAND
  ──────────────────────────────────────────────
  Band            : Complexity band 5
  Metric agreement: CONSISTENT
  Describes how difficult this text is to read, not the writer's education. Education cannot be inferred from text.

  [... detailed metrics and evidence sections ...]

  ──────────────────────────────────────────────
  LIMITATIONS
  ──────────────────────────────────────────────
  Text length tier      : HIGH
  Limiting factors      :
    • The index rewards surface complexity (longer words and sentences,
      rarer words, more subordination), not correctness, relevance or
      argument quality. Padding with jargon raises it.
    • Genre, topic, editing and first language move every metric.
    • Punctuation density is a confound for sentence-length metrics.
    • Education cannot be inferred from text.
    • Scores are not comparable across languages.

  ──────────────────────────────────────────────
  INSPIRED BY
  ──────────────────────────────────────────────
  Inspired by the work below. None of it validates this tool, and this tool has no individual-level validation.
  Gunning (1952)            — Fog Index
  Coleman & Liau (1975)     — CL Index
  McCarthy & Jarvis (2010)  — MTLD
  Covington & McFall (2010) — MATTR
```
"""

LIMITS = """## Limitations & Ethics

**Not an intelligence measure.** The style index measures lexical-syntactic complexity of one text. It has no criterion validation against any standardised ability test (WAIS-IV, Raven's Progressive Matrices, etc.), so IQ output is withheld by default. The validation study that would be required is specified in `docs/validation/validation-protocol.md`; the reference population and norm groups in `docs/validation/norming-plan.md`.

**It rewards complexity, not quality.** Every component rises with longer words, longer sentences, rarer words and more subordination. Correctness, relevance and argument quality are not measured, and padding with jargon raises the index. `docs/validation/effective-weights.md` shows how much of the index is explained by plain length statistics.

**No numeric confidence is a probability.** Length tiers and language-detection labels are ordinal heuristics and are never shown as percentages. The interval around an experimental IQ is an uncalibrated heuristic range (at least ±25 points), not a 95% confidence interval.

**Short, unpunctuated, mixed-language and unsupported texts are refused.** Fewer than 250 alphabetic words gives `INSUFFICIENT_TEXT`; more than 40 words per sentence-ending mark gives `INSUFFICIENT_STRUCTURE`; languages other than English and Indonesian (including Javanese, Sundanese and Malay) give `UNSUPPORTED_LANGUAGE`; more than 20% of words in a second language gives `MIXED_LANGUAGE`.

**Authorship is not verified by the tool.** AI assistance, translation, dictation or editing change every score. Results are valid only for supervised, unaided writing produced for the same prompt, and anything else is reported as `UNVERIFIED_PROVENANCE`.

**Genre and register.** Chat logs, social posts and transcripts are outside scope; IQ is refused unless `text_type` is `formal_prose`. Colloquial Indonesian connectives are normalised before syntactic counting so register alone does not lower the score.

**Languages are not comparable.** English and Indonesian use different instruments and uncalibrated scales. Every output carries `language_norm_unvalidated`, and ranking across languages is refused.

**Education cannot be inferred from text.** The text complexity band describes the text, not its writer, and is unavailable for Indonesian.

**Do not use for consequential decisions.** These outputs must not be used for hiring, admissions, clinical assessment, academic evaluation, or legal proceedings. Human review is mandatory for any use.

**Privacy.** Text submitted to the MCP server is processed locally. No data is sent to external services beyond the embedding model (downloaded locally on first use).
"""

INSPIRED = """## Inspired By

Inspired by the work below. None of it validates this tool, and this tool has no individual-level validation: no study links its outputs to any individual's ability. The formulas listed are implemented as published; nothing else in this project reproduces a published coefficient.

| Author(s) | What is used here |
|---|---|
| Gunning (1952) | Gunning Fog Index formula |
| Coleman & Liau (1975) | Coleman-Liau Index formula |
| Smith & Senter (1967) | Automated Readability Index formula |
| Flesch (1948) | Flesch Reading Ease formula |
| McCarthy & Jarvis (2010) | MTLD lexical diversity measure |
| Covington & McFall (2010) | MATTR lexical diversity measure |
"""


def replace_section(text: str, start: str, end: str, new: str) -> str:
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[:i] + new + "\n---\n\n" + text[j:]


def main() -> None:
    text = README.read_text(encoding="utf-8")
    text = replace_section(text, "# Verbal Fluency IQ\n", "## Table of Contents", INTRO)
    text = text.replace(
        "- [IQ & Education Mapping](#iq--education-mapping)",
        "- [Style Bands, Experimental IQ & Text Complexity](#style-bands-experimental-iq--text-complexity)",
    )
    text = text.replace("- [Research Basis](#research-basis)", "- [Inspired By](#inspired-by)")
    text = replace_section(text, "## Overview\n", "## Architecture", OVERVIEW)
    text = replace_section(text, "## IQ & Education Mapping\n", "## Output Flags", MAPPING)
    assert SCORES_ONLY_OLD in text and AGE_OLD in text
    text = text.replace(SCORES_ONLY_OLD, SCORES_ONLY_NEW).replace(AGE_OLD, AGE_NEW)
    text = replace_section(text, "## Configuration Reference\n", "## Sample Report", CONFIG)
    text = replace_section(text, "## Sample Report\n", "## Limitations & Ethics", SAMPLE)
    text = replace_section(text, "## Limitations & Ethics\n", "## Research Basis", LIMITS)
    text = replace_section(text, "## Research Basis\n", "## Running Tests", INSPIRED)
    README.write_text(text, encoding="utf-8")
    print(f"{README}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
````


Expected output: `README.md: 984 lines` (must stay ≥ 904). Check:

```bash
grep -c "95% CI\|Pennebaker\|using verbal fluency as a psycholinguistic proxy" README.md
```

Expected: `0`.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_reporter.py tests/test_pipeline.py tests/test_license.py -v
```

Expected: all pass.


- [ ] **Step 6: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix mcp-server/tools/reporter.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff format mcp-server/tools/reporter.py tests/test_reporter.py tests/test_pipeline.py
.venv/bin/ruff check mcp-server/tools/reporter.py tests/test_reporter.py tests/test_pipeline.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 7: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_reporter.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: every `test_reporter.py` test passes. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 8: Commit**

```bash
git add mcp-server/tools/reporter.py \
  tests/test_reporter.py \
  tests/test_pipeline.py \
  README.md
git commit -m "feat(report): lexical-syntactic complexity report with status, provenance caveat and Inspired By (AEGIS F-020 F-025 F-026 F-032)" -m "The report and README name the construct lexical-syntactic complexity and say it rewards complexity, not quality. Every report shows status, reasons, provenance and the supervised-unaided caveat; without a gate it says not attested. RESEARCH BASIS becomes INSPIRED BY with a no individual-level validation sentence and only implemented formulas. Heuristic confidences are ordinal labels, never percentages." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 10: Component correlation and effective weights (F-022)

**Files:**
- Create: `scripts/component_correlation.py`, `docs/validation/effective-weights.md` (generated)
- Modify: `docs/audit/curated.json`, `docs/audit/2026-10-11-aegis-findings.json` (regenerated)
- Test: `tests/test_component_correlation.py`

**Interfaces:**
- Consumes: `tools.mapper.NOMINAL_WEIGHTS`, `compute_verbal_fluency_score`; the analysers; the Task 1 corpus.
- Produces (`scripts/component_correlation.py`): `COMPONENTS`, `CORPUS_DIR`, `DEFAULT_OUT`; `score_passage(text, lang) -> dict`; `compute(corpus_dir=CORPUS_DIR) -> dict` with keys `n_passages`, `passages`, `nominal_weights`, `correlation` (component → component → float), `effective_weights` (sums to 1), `length_share` (0..1); `render(result) -> str`; `main(argv=None) -> int` writing `docs/validation/effective-weights.md`.

- [ ] **Step 1: Write the failing test**


Create `tests/test_component_correlation.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import pathlib
import re
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

import component_correlation

DOC = pathlib.Path("docs/validation/effective-weights.md")
COMPONENTS = ("lexical", "syntactic", "semantic", "readability")


@pytest.fixture(scope="module")
def result():
    return component_correlation.compute()


def test_cross_component_effective_weights_and_length_share_reported(result):
    assert result["n_passages"] == 12
    for a in COMPONENTS:
        assert result["correlation"][a][a] == pytest.approx(1.0)
        for b in COMPONENTS:
            assert result["correlation"][a][b] == pytest.approx(
                result["correlation"][b][a]
            )
    assert sum(result["effective_weights"].values()) == pytest.approx(1.0, abs=1e-6)
    assert 0.0 <= result["length_share"] <= 1.0

    text = DOC.read_text(encoding="utf-8")
    assert "## Correlation matrix" in text
    assert "## Effective weights" in text
    for c in COMPONENTS:
        assert f"| {c} |" in text
    match = re.search(r"length_share = (\d\.\d{3})", text)
    assert match is not None
    assert 0.0 <= float(match.group(1)) <= 1.0


def test_render_is_deterministic_for_a_given_result(result):
    assert component_correlation.render(result) == component_correlation.render(result)
```


- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_component_correlation.py -v
```

Expected: collection ERROR — `ModuleNotFoundError: No module named 'component_correlation'`.

- [ ] **Step 3: Implement and generate the report**


Create `scripts/component_correlation.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Cross-component correlation and effective weights of the style index (F-022).

Runs every passage of the synthetic reference corpus through the pipeline, then
reports:
- the Pearson correlation matrix of the four component scores;
- effective weights: each component's share of style-index variance,
  w_i * cov(c_i, S) / var(S), which sums to 1 when S = sum(w_i * c_i);
- length_share: R^2 of the style index regressed on mean sentence length and
  mean word length, i.e. how much of the index plain length statistics explain.

Usage: python scripts/component_correlation.py [--out docs/validation/effective-weights.md]
"""

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import NOMINAL_WEIGHTS, compute_verbal_fluency_score
from tools.preprocess import preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

CORPUS_DIR = ROOT / "tests" / "fixtures" / "reference_corpus"
DEFAULT_OUT = ROOT / "docs" / "validation" / "effective-weights.md"
COMPONENTS = ("lexical", "syntactic", "semantic", "readability")


def score_passage(text: str, lang: str) -> dict:
    prep = preprocess_text(text, lang)
    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    return {
        **{c: vfs[c] for c in COMPONENTS},
        "style_index": vfs["style_index"],
        "mean_sentence_length": syn["mean_sentence_length"],
        "avg_word_length": lex["avg_word_length"],
    }


def compute(corpus_dir: pathlib.Path = CORPUS_DIR) -> dict:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for p in manifest["passages"]:
        text = (corpus_dir / f"{p['name']}.txt").read_text(encoding="utf-8")
        row = score_passage(text, p["lang"])
        if all(row[c] is not None for c in COMPONENTS):
            rows.append({"name": p["name"], **row})

    comp = np.array([[r[c] for c in COMPONENTS] for r in rows], dtype=float)
    weights = np.array([NOMINAL_WEIGHTS[c] for c in COMPONENTS])
    style = comp @ weights
    corr = np.corrcoef(comp, rowvar=False)
    var_s = float(np.var(style))
    effective = {
        c: float(weights[i] * np.cov(comp[:, i], style, bias=True)[0, 1] / var_s)
        for i, c in enumerate(COMPONENTS)
    }
    lengths = np.array(
        [[1.0, r["mean_sentence_length"], r["avg_word_length"]] for r in rows]
    )
    coef, *_ = np.linalg.lstsq(lengths, style, rcond=None)
    residual = style - lengths @ coef
    length_share = 1.0 - float(np.var(residual)) / var_s
    return {
        "n_passages": len(rows),
        "passages": [r["name"] for r in rows],
        "nominal_weights": dict(NOMINAL_WEIGHTS),
        "correlation": {
            a: {b: float(corr[i, j]) for j, b in enumerate(COMPONENTS)}
            for i, a in enumerate(COMPONENTS)
        },
        "effective_weights": effective,
        "length_share": length_share,
    }


def render(result: dict) -> str:
    lines = [
        "# Style index: component correlation and effective weights",
        "",
        "Generated by `scripts/component_correlation.py` over the synthetic",
        "reference corpus in `tests/fixtures/reference_corpus/`",
        f"({result['n_passages']} passages, English and Indonesian, no real",
        "person's text). This is a structural diagnostic, not a calibration:",
        "the corpus is small and synthetic, so the numbers show how the",
        "index behaves, not how it relates to any ability.",
        "",
        "## Nominal weights",
        "",
        "| Component | Nominal weight |",
        "|---|---|",
    ]
    for c in COMPONENTS:
        lines.append(f"| {c} | {result['nominal_weights'][c]:.2f} |")
    lines += [
        "",
        "## Correlation matrix",
        "",
        "| | " + " | ".join(COMPONENTS) + " |",
        "|---|" + "---|" * len(COMPONENTS),
    ]
    for a in COMPONENTS:
        cells = " | ".join(f"{result['correlation'][a][b]:.3f}" for b in COMPONENTS)
        lines.append(f"| {a} | {cells} |")
    lines += [
        "",
        "## Effective weights",
        "",
        "Share of style-index variance attributable to each component",
        "(w_i * cov(c_i, S) / var(S); sums to 1).",
        "",
        "| Component | Effective weight |",
        "|---|---|",
    ]
    for c in COMPONENTS:
        lines.append(f"| {c} | {result['effective_weights'][c]:.3f} |")
    lines += [
        "",
        "## Length share",
        "",
        "R^2 of the style index on mean sentence length and mean word length:",
        "",
        f"length_share = {result['length_share']:.3f}",
        "",
        "Interpretation: when length_share is high, the style index mostly",
        "re-measures word and sentence length, whatever the nominal weights say.",
        "",
        "No cap is enforced. A defensible cap, and any orthogonalisation or",
        "re-weighting of length-driven components, requires the calibration",
        "sample described in `docs/validation/norming-plan.md`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    result = compute()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(result), encoding="utf-8")
    print(f"wrote {args.out} (length_share={result['length_share']:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```


```bash
.venv/bin/python scripts/component_correlation.py
```

Expected: `wrote .../docs/validation/effective-weights.md (length_share=0.868)` (prototype value; a different third decimal is fine, the test checks structure). The file contains the nominal weights, the 4×4 correlation matrix, the effective weights (prototype: readability ≈ 0.42 against a nominal 0.15) and `length_share = 0.868`.

- [ ] **Step 4: Record the F-022 acceptance-test change**

`length_share` ≈ 0.87 means no meaningful cap can be asserted (decision 2). Update and regenerate exactly as in Task 8 Step 4, with `"F-022"` and `"test_cross_component_effective_weights_and_length_share_reported"`:

```bash
.venv/bin/python - <<'EOF'
import json, pathlib
cur = pathlib.Path("docs/audit/curated.json")
fin = pathlib.Path("docs/audit/2026-10-11-aegis-findings.json")
curated = json.loads(cur.read_text(encoding="utf-8"))
title = {f["id"]: f["title"] for f in json.loads(fin.read_text(encoding="utf-8"))}["F-022"]
hits = [f for f in curated if f["title"] == title]
assert len(hits) == 1
hits[0]["acceptance_test"] = "test_cross_component_effective_weights_and_length_share_reported"
cur.write_text(json.dumps(curated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
EOF
cp docs/audit/2026-10-11-aegis-findings.json /tmp/aegis-findings-before.json
.venv/bin/python scripts/consolidate_findings.py
.venv/bin/python - <<'EOF'
import json
a = json.load(open("/tmp/aegis-findings-before.json"))
b = json.load(open("docs/audit/2026-10-11-aegis-findings.json"))
assert [(f["id"], f["title"]) for f in a] == [(f["id"], f["title"]) for f in b], "ids moved"
changed = [f["id"] for f, g in zip(a, b) if f != g]
assert changed == ["F-022"], changed
print("ids stable; changed:", changed)
EOF
```

Expected: `ids stable; changed: ['F-022']`.

- [ ] **Step 5: Run the test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_component_correlation.py -v
```

Expected: 2 passed.


- [ ] **Step 6: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix scripts/component_correlation.py tests/test_component_correlation.py
.venv/bin/ruff format scripts/component_correlation.py tests/test_component_correlation.py
.venv/bin/ruff check scripts/component_correlation.py tests/test_component_correlation.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 7: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_component_correlation.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: 2 passed in the focused run. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 8: Commit**

```bash
git add scripts/component_correlation.py \
  tests/test_component_correlation.py \
  docs/validation/effective-weights.md \
  docs/audit/curated.json \
  docs/audit/2026-10-11-aegis-findings.json
git commit -m "feat(validation): publish component correlation, effective weights and length share (AEGIS F-022)" -m "scripts/component_correlation.py scores the synthetic reference corpus and writes docs/validation/effective-weights.md. Length statistics explain about 0.87 of style-index variance, so no defensible cap exists; F-022 acceptance test changed to test_cross_component_effective_weights_and_length_share_reported. Re-weighting needs the calibration sample in the norming plan." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 11: Validation protocol and norming plan (F-002, F-027)

**Files:**
- Create: `docs/validation/validation-protocol.md`, `docs/validation/norming-plan.md`
- Test: `tests/test_validation_docs.py`

**Interfaces:**
- Consumes: `mcp-server/tools/policy.py` and `mcp-server/config/iq_norms.json` already reference `docs/validation/validation-protocol.md` (Tasks 2–3); the test pins that link.
- Produces: the two documents; headings the test relies on: protocol `## Criterion measures`, `## Sample size`, `## Subgroup analyses`, `## Acceptance thresholds`; norming plan `## Reference population`, `## Age bands`, `## Language-background strata`, `## Sample size`, `## Norm computation`.

- [ ] **Step 1: Write the failing test**


Create `tests/test_validation_docs.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Process findings F-002 and F-027: the protocols exist and the code points at them."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "docs" / "validation" / "validation-protocol.md"
NORMING = ROOT / "docs" / "validation" / "norming-plan.md"


def test_validation_protocol_names_criterion_sample_subgroups_and_thresholds():
    text = PROTOCOL.read_text(encoding="utf-8")
    for heading in (
        "## Criterion measures",
        "## Sample size",
        "## Subgroup analyses",
        "## Acceptance thresholds",
    ):
        assert heading in text, heading
    assert "WAIS-IV Full Scale IQ" in text
    assert "| Held-out evaluation | 250 |" in text
    assert "r ≥ 0.50" in text
    assert "SEE ≤ 12 IQ points" in text
    assert "PPV and NPV" in text
    assert "Status: not started" in text


def test_norming_plan_defines_population_age_bands_and_language_strata():
    text = NORMING.read_text(encoding="utf-8")
    for heading in (
        "## Reference population",
        "## Age bands",
        "## Language-background strata",
        "## Sample size",
        "## Norm computation",
    ):
        assert heading in text, heading
    for band in ("17 to 19", "55 to 64"):
        assert band in text
    for stratum in ("Javanese first", "Sundanese first", "English as first language"):
        assert stratum in text
    assert "never defaulted" in text


def test_code_and_config_reference_the_validation_protocol():
    policy_src = (ROOT / "mcp-server" / "tools" / "policy.py").read_text(
        encoding="utf-8"
    )
    assert "docs/validation/validation-protocol.md" in policy_src
    norms = (ROOT / "mcp-server" / "config" / "iq_norms.json").read_text(
        encoding="utf-8"
    )
    assert "docs/validation/validation-protocol.md" in norms
```


- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_validation_docs.py -v
```

Expected: FAIL — `FileNotFoundError` for `docs/validation/validation-protocol.md` and `norming-plan.md`.

- [ ] **Step 3: Write the documents**


Create `docs/validation/validation-protocol.md` with exactly this content:

```markdown
# Validation protocol: style index to IQ

**Status: not started.** No part of this study has been run. Until every acceptance
threshold below is met for a language, `iq_validated` for that language stays `false`
in `mcp-server/config/validation.json`, IQ, percentile and mental age are withheld,
and every output is labelled experimental and unvalidated.

This protocol addresses finding F-002: the IQ bands, component weights and scaling
bounds are hand-set with no source, sample or citation, so the current mapping is
circular (the table is the only thing that defines IQ) and cannot be wrong by
construction. Results that require real data collection are specified here, not
fabricated.

## Claims under test

1. The style index predicts a standardised IQ score for an individual well enough to
   report an IQ point estimate with an empirically derived prediction interval.
2. The prediction is equally accurate and unbiased across the subgroups listed under
   *Subgroup analyses*.
3. The index is stable across writing prompts and sessions (reliability).

The text complexity band is **not** under test as a measure of education. Education is
recorded only to check representativeness and differential prediction.

## Criterion measures

| Language of writing | Primary criterion | Secondary criterion |
|---|---|---|
| English | WAIS-IV Full Scale IQ, administered and scored by a licensed psychologist | WAIS-IV Verbal Comprehension Index |
| Indonesian | WAIS-IV Full Scale IQ, Indonesian adaptation licensed from the publisher; if no licensed adaptation is available, the study does not start for Indonesian | WAIS-IV Verbal Comprehension Index (same adaptation) |

The criterion test is administered within 14 days of the writing task, by an examiner
blind to the style index. Raven's Progressive Matrices may be added as an exploratory
non-verbal criterion but cannot substitute for the primary criterion.

## Writing task

- Three standardised prompts per participant (expository, argumentative, narrative),
  identical within a language, translated and back-translated between languages.
- Supervised, unaided: typed on a locked machine with spell-check, autocomplete,
  translation and AI tools disabled; 30 minutes per prompt; target length 350 words
  (minimum 250 alphabetic words, the `min_words` gate).
- Recorded provenance: `supervised_unaided`; text type: `formal_prose`.
- Texts are scored by the exact tool version under test; the git commit and
  `config/validation.json` version are stored with every score.

## Sample size

Per language, recruited by the stratified design in `docs/validation/norming-plan.md`:

| Set | N per language | Purpose |
|---|---|---|
| Calibration | 350 | Fit any re-weighting, band boundaries and the prediction interval |
| Held-out evaluation | 250 | All acceptance statistics; never used for fitting |
| Test-retest subsample | 100 (drawn from calibration) | Second session after 2 to 4 weeks with a different prompt |

Rationale: with N = 250 held out, a correlation of r = 0.40 has a 95% confidence
interval half-width of about 0.10 (Fisher z). Strata are over-sampled so that every
subgroup in the analyses below has at least 60 held-out participants. Recruitment
stops for a stratum once its quota is filled; under-filled strata are reported, not
imputed.

## Analyses

All statistics are computed on the held-out set, per language, with 95% confidence
intervals (bootstrap, 2,000 resamples):

- Pearson r and Spearman rho between style index and the primary criterion.
- Standard error of estimate, SEE = SD_criterion × sqrt(1 − r²), and the resulting
  95% prediction interval (±1.96 × SEE). This replaces the uncalibrated heuristic range.
- Calibration slope and intercept of criterion on predicted IQ.
- Test-retest reliability: ICC(2,1) between sessions; alternate-prompt reliability
  across the three prompts.
- Classification accuracy at every cut-off a user might apply (IQ < 85, > 115, > 130):
  sensitivity, specificity, PPV and NPV at base rates of 5%, 16% and 50%.
- Length dependence: partial correlation of the index with the criterion controlling
  for mean sentence length and mean word length (see
  `docs/validation/effective-weights.md`).

## Subgroup analyses

Differential prediction (Cleary model: criterion regressed on index, group and
index × group) and per-group r, SEE and mean residual for:

- language of writing (English vs Indonesian; never pooled);
- sex;
- age band (as defined in the norming plan);
- highest completed education;
- first language / language background (Indonesian L1, regional-language L1 such as
  Javanese or Sundanese, English L1 for English texts);
- region (Java vs outside Java; urban vs rural);
- self-disclosed dyslexia or other writing-related disability.

Adverse impact ratio (selection rate of each group divided by the highest group's
rate) is reported at every cut-off listed under *Analyses*.

## Acceptance thresholds

All must hold on the held-out set for a language before `iq_validated` may be set to
`true` for it:

| Statistic | Threshold |
|---|---|
| r with primary criterion | r ≥ 0.50 and lower 95% CI bound ≥ 0.40 |
| Standard error of estimate | SEE ≤ 12 IQ points |
| Calibration slope | between 0.90 and 1.10 |
| Test-retest reliability | ICC(2,1) ≥ 0.80 |
| Subgroup accuracy | r ≥ 0.40 in every subgroup with N ≥ 60 |
| Differential prediction | no index × group interaction significant at α = 0.01 (Holm-corrected) and no subgroup with absolute mean residual > 3 IQ points |
| Adverse impact | ratio ≥ 0.80 at every reported cut-off |

If any threshold fails, the result is published as a failed validation and the flag
stays `false`. Thresholds are not relaxed after unblinding.

## Governance

- Pre-registration of hypotheses, thresholds and analysis code before data collection.
- Ethics approval and written informed consent that states the purpose, retention and
  the participant's rights under Indonesia's Personal Data Protection Law (UU PDP,
  Law No. 27 of 2022).
- An independent psychometrician signs off the analysis report.
- Results are stored as `docs/validation/results/<lang>-<yyyy-mm-dd>.md`; the commit
  that sets `iq_validated: true` links to that report.
- Any change to scoring code or configuration after validation (visible as a
  golden-score diff) invalidates the result for the affected language until the
  held-out analysis is re-run. Validation expires after three years.
- The shipped code enforces a minimum ±25-point range. Replacing it with ±1.96 × SEE
  is a separate, reviewed code change made only after this protocol passes.

## Until validation passes

The tool reports a writing-style index of lexical-syntactic complexity and a neutral
style band. It is not an intelligence measure, and its outputs must not be used for
decisions about individuals.
```


Create `docs/validation/norming-plan.md` with exactly this content:

```markdown
# Norming plan: reference population and norm groups

**Status: not started.** No norm sample exists. Until it does, the tool reports no
normed or age-adjusted score, never assumes an age, and every output carries
`language_norm_unvalidated: true`.

This plan addresses finding F-027: verbal style changes with age, schooling era,
dialect and disability, none of which enter the current mapping, and the former
default age of 30 was not a validated population median. It defines who the scores
would be compared against and how.

## Reference population

Separate reference populations per language of writing; scores are never pooled or
compared across languages.

| Language of writing | Reference population |
|---|---|
| Indonesian | Adults aged 17 to 64 resident in Indonesia who write in Indonesian for study or work |
| English | Adults aged 17 to 64 resident in Indonesia who write in English for study or work, plus a separate English-L1 comparison group |

The intended use case (screening in Indonesia) defines the population. A score is
interpretable only for a writer who belongs to the reference population of the
language they wrote in.

## Age bands

| Band | Ages |
|---|---|
| A1 | 17 to 19 |
| A2 | 20 to 24 |
| A3 | 25 to 34 |
| A4 | 35 to 44 |
| A5 | 45 to 54 |
| A6 | 55 to 64 |

Writers under 17 or over 64 are out of scope. Age is a required input for any normed
output; it is never defaulted.

## Language-background strata

| Language of writing | Strata |
|---|---|
| Indonesian | (L1) Indonesian as first home language; (R1) Javanese first; (R2) Sundanese first; (R3) other regional language first; (M) bilingual from birth |
| English | (E1) English as first language; (E2) English as second or later language with Indonesian L1; (E3) English as second or later language with a regional-language L1 |

Language background is a required input for any normed output, recorded as one of the
codes above.

## Additional stratification variables

Recorded for representativeness and subgroup analyses only; never reported as outputs
and never used to adjust an individual's score:

- sex;
- highest completed education (SD/SMP, SMA/SMK, D1 to D3, S1, S2/S3);
- region (Java vs outside Java; urban vs rural);
- self-disclosed dyslexia or other writing-related disability.

## Sample size

- Minimum 50 participants per age band × language-background cell.
- Indonesian: 6 age bands × 5 strata = 30 cells, minimum 1,500 participants.
- English: 6 age bands × 3 strata = 18 cells, minimum 900 participants.
- Quotas within cells follow Statistics Indonesia (BPS) 2020 census margins for sex,
  region and education; post-stratification weights correct residual imbalance.
- The validation study sample (`docs/validation/validation-protocol.md`) may be drawn
  from the norm sample but is analysed separately.

## Data collection

Identical to the writing task in the validation protocol: three standardised prompts,
supervised and unaided, `provenance = supervised_unaided`, `text_type = formal_prose`,
minimum 250 alphabetic words per text, with informed consent under UU PDP.

## Norm computation

- Continuous (regression-based) norming of the style index on age within each
  language-background stratum (for example GAMLSS with age as a smooth term), so
  that adjacent age bands do not create artificial jumps; raw cell percentiles are
  reported alongside as a check.
- Output on the normed scale: within-group percentile and z-score, labelled with the
  language, age band and language-background stratum they refer to.
- Only within-group scores are reported. No score is compared across languages or
  strata.

## Acceptance criteria for the norms

- Every cell reaches its minimum of 50.
- Bootstrap 90% confidence interval of each cell's median style index is within ±3
  index points.
- Norms are rebuilt after any scoring change (golden-score diff) and at least every
  five years.

## How the code will use the norms

- Norms will live in versioned per-language files under `mcp-server/config/norms/`.
- A normed output requires both `chronological_age` and `language_background`; if
  either is missing, the normed fields are withheld with a reason, never imputed.
- Until the norms exist, `config/validation.json` keeps every language unvalidated and
  no normed field is produced.
```


- [ ] **Step 4: Run the test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_validation_docs.py -v
```

Expected: 3 passed.


- [ ] **Step 5: Lint and format the touched Python files**

```bash
.venv/bin/ruff check --fix tests/test_validation_docs.py
.venv/bin/ruff format tests/test_validation_docs.py
.venv/bin/ruff check tests/test_validation_docs.py
```

Expected: `All checks passed!` (the formatter may reflow the code above; that is intended).

- [ ] **Step 6: Run the focused tests, the full suite and the audit gate**

```bash
.venv/bin/python -m pytest tests/test_validation_docs.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: 3 passed in the focused run. The full suite passes; the three `test_golden_scores_match` cases report `xfailed` (an `xpassed` is also acceptable) until Task 12. `audit_status.py` exits 0 and prints `phase 2: 0 done / 33 open` (Task 12 is the only task that changes that line).

- [ ] **Step 7: Commit**

```bash
git add tests/test_validation_docs.py \
  docs/validation/validation-protocol.md \
  docs/validation/norming-plan.md
git commit -m "docs(validation): criterion validation protocol and norming plan (AEGIS F-002 F-027)" -m "Specifies criterion measures (WAIS-IV FSIQ), per-language sample sizes with a held-out set, reliability, PPV/NPV at stated base rates, subgroup and adverse-impact analyses and acceptance thresholds (r >= 0.50, SEE <= 12) that gate iq_validated; and the reference population, age bands, language-background strata and continuous norming. Both state that no study has been run." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


---

### Task 12: Server and agent wiring, README tool reference, golden recapture, close phase 2

**Files:**
- Modify: `mcp-server/server.py` (full replacement), `.agent/SKILL.md`, `.agent/tools.json`, `README.md`, `tests/test_golden.py` (replaced), `tests/fixtures/golden_scores.json` (recaptured), `docs/audit/curated.json`, `docs/audit/2026-10-11-aegis-findings.json`
- Test: `tests/test_server_wiring.py` (new), `tests/test_golden.py`

Behaviour changes that break existing tests in this task: none beyond the golden fixture, which is recaptured here and loses its `xfail` marker.

**Interfaces:**
- Consumes: every public function produced in Tasks 2–9.
- Produces (`server.py` tools, parameters in order): `tool_detect_language(text)`, `tool_preprocess_text(text, lang)`, `tool_evaluate_gates(lang_result_json, word_count, terminal_mark_count, provenance="unknown", text_type="unknown")`, `tool_analyze_lexical(tokens_json, sentences_json, lang)`, `tool_analyze_syntactic(sentences_json, lang)`, `tool_analyze_semantic(text, sentences_json, lang, segment_boundaries_json="")`, `tool_analyze_readability(text, lang)`, `tool_compute_verbal_fluency_score(lexical_json, syntactic_json, semantic_json, readability_json, word_count, lang)`, `tool_predict_iq(style_index, lang, gate_json="")`, `tool_predict_mental_age(iq_estimate=-1.0, chronological_age=0)`, `tool_estimate_text_complexity_band(gunning_fog, ari, lexical_density, lang, gate_json="")`, `tool_generate_report(lang_result_json, preprocess_result_json, lexical_result_json, syntactic_result_json, semantic_result_json, readability_result_json, vfs_result_json, iq_result_json, mental_age_result_json, band_result_json, format_flag="--both", chronological_age=0, verbose_caveats=False, gate_json="")`. `tool_estimate_education_level` no longer exists. `.agent/tools.json` lists exactly these names and parameters.
- Produces (`run_pipeline` final key set): `status`, `statuses`, `reasons`, `lang`, `lang_confidence`, `language_norm_unvalidated`, `provenance`, `text_type`, `policy_version`, `style_index`, `style_index_label`, `style_band`, `components`, `iq`, `percentile`, `classification`, `range`, `range_label`, `withheld_reason`, `mental_age`, `text_complexity_band`, `text_complexity_consistency`, `word_count`, `token_count`, `low_reliability`, `reliability_reasons`.

- [ ] **Step 1: Write the failing tests**


Create `tests/test_server_wiring.py` with exactly this content:

```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Drive server.py tool functions end to end with a stub FastMCP.

The installed ``mcp`` package may not ship ``mcp.server.fastmcp``; the stub keeps
this test about our wiring, not about the transport library.
"""

import importlib.util
import json
import pathlib
import sys
import types

import pytest

from tests.helpers import corpus_text

SERVER = pathlib.Path("mcp-server/server.py")


class _StubFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name

    def tool(self):
        return lambda fn: fn

    def run(self) -> None:  # pragma: no cover - never called in tests
        raise AssertionError("not used in tests")


@pytest.fixture(scope="module")
def server():
    stub = types.ModuleType("mcp.server.fastmcp")
    stub.FastMCP = _StubFastMCP
    saved = sys.modules.get("mcp.server.fastmcp")
    sys.modules["mcp.server.fastmcp"] = stub
    try:
        spec = importlib.util.spec_from_file_location("vf_server", SERVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        if saved is None:
            sys.modules.pop("mcp.server.fastmcp", None)
        else:
            sys.modules["mcp.server.fastmcp"] = saved


def _chain(server, text, provenance="unknown", text_type="unknown", gate=True):
    lang_json = server.tool_detect_language(text)
    lang = json.loads(lang_json)["lang"]
    prep_json = server.tool_preprocess_text(text, lang)
    prep = json.loads(prep_json)
    gate_json = (
        server.tool_evaluate_gates(
            lang_json,
            prep["word_count"],
            prep["terminal_mark_count"],
            provenance,
            text_type,
        )
        if gate
        else ""
    )
    sents = json.dumps(prep["sentences"])
    lex_json = server.tool_analyze_lexical(json.dumps(prep["tokens"]), sents, lang)
    syn_json = server.tool_analyze_syntactic(sents, lang)
    sem_json = server.tool_analyze_semantic(prep["text_clean"], sents, lang)
    read_json = server.tool_analyze_readability(prep["text_clean"], lang)
    vfs_json = server.tool_compute_verbal_fluency_score(
        lex_json, syn_json, sem_json, read_json, prep["word_count"], lang
    )
    vfs = json.loads(vfs_json)
    iq_json = server.tool_predict_iq(vfs["style_index"], lang, gate_json)
    iq = json.loads(iq_json)
    ma_json = server.tool_predict_mental_age(
        iq["point_estimate"] if iq["point_estimate"] is not None else -1.0, 0
    )
    read = json.loads(read_json)
    band_json = server.tool_estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        json.loads(lex_json)["lexical_density"],
        lang,
        gate_json,
    )
    out = server.tool_generate_report(
        lang_json,
        prep_json,
        lex_json,
        syn_json,
        sem_json,
        read_json,
        vfs_json,
        iq_json,
        ma_json,
        band_json,
        "--both",
        0,
        False,
        gate_json,
    )
    return json.loads(out), iq


def test_server_chain_withholds_iq_and_reports_status(server):
    result, iq = _chain(server, corpus_text("en_news_report"))
    assert iq["point_estimate"] is None
    assert iq["style_band"].startswith("Style band")
    assert result["json"]["status"] == "UNVERIFIED_PROVENANCE"
    assert "Provenance      : unknown" in result["report"]


def test_server_chain_without_gate_refuses_iq(server):
    result, iq = _chain(server, corpus_text("en_news_report"), gate=False)
    assert iq["point_estimate"] is None
    assert "no gate" in iq["withheld_reason"]
    assert "Status: UNVERIFIED" in result["report"]


def test_server_has_no_education_level_tool(server):
    assert not hasattr(server, "tool_estimate_education_level")
    assert hasattr(server, "tool_estimate_text_complexity_band")
    assert hasattr(server, "tool_evaluate_gates")


def test_agent_tools_json_matches_server_signatures(server):
    import inspect

    spec = json.loads(pathlib.Path(".agent/tools.json").read_text(encoding="utf-8"))
    declared = {t["name"]: t for t in spec["tools"]}
    defined = {
        name: fn
        for name, fn in vars(server).items()
        if name.startswith("tool_") and callable(fn)
    }
    assert set(declared) == set(defined)
    for name, fn in defined.items():
        params = list(inspect.signature(fn).parameters)
        assert list(declared[name]["parameters"]) == params, name
    skill = pathlib.Path(".agent/SKILL.md").read_text(encoding="utf-8")
    for name in defined:
        assert f"  - {name}" in skill, name
```


Replace `tests/test_golden.py` with (the `xfail` marker is gone; the fixture is recaptured in Step 6):

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
RESULT_KEYS = {
    "status",
    "statuses",
    "reasons",
    "lang",
    "lang_confidence",
    "language_norm_unvalidated",
    "provenance",
    "text_type",
    "policy_version",
    "style_index",
    "style_index_label",
    "style_band",
    "components",
    "iq",
    "percentile",
    "classification",
    "range",
    "range_label",
    "withheld_reason",
    "mental_age",
    "text_complexity_band",
    "text_complexity_consistency",
    "word_count",
    "token_count",
    "low_reliability",
    "reliability_reasons",
}
COMPONENTS = ("lexical", "syntactic", "semantic", "readability")


def test_golden_sources_exclude_untracked_personal_corpus():
    assert GOLDEN_SOURCES
    assert all("example/rahmat" not in s for s in GOLDEN_SOURCES)


def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert set(out) == RESULT_KEYS
    assert out["status"] == "INSUFFICIENT_TEXT"
    assert out["iq"] is None
    assert out["range"] is None


@pytest.mark.parametrize("source", GOLDEN_SOURCES)
def test_golden_scores_match(source):
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))[source]
    text = (ROOT / source).read_text(encoding="utf-8")
    actual = run_pipeline(text)
    assert set(actual) == set(expected)
    for key in (
        "lang",
        "status",
        "statuses",
        "style_band",
        "iq",
        "percentile",
        "classification",
        "range",
        "mental_age",
        "text_complexity_band",
        "word_count",
        "token_count",
        "low_reliability",
    ):
        assert actual[key] == expected[key], key
    assert actual["style_index"] == pytest.approx(expected["style_index"], abs=0.5)
    for c in COMPONENTS:
        if expected["components"][c] is None:
            assert actual["components"][c] is None
        else:
            assert actual["components"][c] == pytest.approx(
                expected["components"][c], abs=0.5
            )
```


- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_server_wiring.py tests/test_golden.py -v
```

Expected: ERROR in the `server` fixture of `tests/test_server_wiring.py` — the old `server.py` fails to import with `ImportError: cannot import name 'estimate_education_level' from 'tools.mapper'` — and `test_golden_scores_match` FAILS against the old fixture.

- [ ] **Step 3: Wire the server**

Replace `mcp-server/server.py` with:


```python
# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import evaluate_gates
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

mcp = FastMCP("verbal-fluency-mcp")


def _gate(gate_json: str) -> dict | None:
    """Empty string means no gate: every screening output is then withheld."""
    return json.loads(gate_json) if gate_json else None


def _age(chronological_age: int) -> int | None:
    return chronological_age if chronological_age > 0 else None


@mcp.tool()
def tool_detect_language(text: str) -> str:
    """Detect language. Returns lang, confidence (heuristic agreement index, not a
    probability), supported, mixed_language_share."""
    return json.dumps(detect_language(text))


@mcp.tool()
def tool_preprocess_text(text: str, lang: str) -> str:
    """Clean and tokenize text. Returns tokens, sentences (with idx), word_count
    (alphabetic words), token_count, terminal_mark_count."""
    return json.dumps(preprocess_text(text, lang))


@mcp.tool()
def tool_evaluate_gates(
    lang_result_json: str,
    word_count: int,
    terminal_mark_count: int,
    provenance: str = "unknown",
    text_type: str = "unknown",
) -> str:
    """Apply validity gates. provenance: supervised_unaided | unsupervised | unknown.
    text_type: formal_prose | informal | unknown. Returns status, reasons and the
    gate JSON that predict_iq, the complexity band and the report require."""
    return json.dumps(
        evaluate_gates(
            json.loads(lang_result_json),
            word_count,
            terminal_mark_count,
            provenance,
            text_type,
        )
    )


@mcp.tool()
def tool_analyze_lexical(tokens_json: str, sentences_json: str, lang: str) -> str:
    """Compute MATTR, MTLD, content-word density, out-of-dictionary rate."""
    return json.dumps(
        analyze_lexical(json.loads(tokens_json), json.loads(sentences_json), lang)
    )


@mcp.tool()
def tool_analyze_syntactic(sentences_json: str, lang: str) -> str:
    """Compute clause density, subordination index, dependency depth (en only).
    Scores are not comparable across languages."""
    return json.dumps(analyze_syntactic(json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_semantic(
    text: str, sentences_json: str, lang: str, segment_boundaries_json: str = ""
) -> str:
    """Compute adjacent-sentence similarity, topic drift, lexical chain density.

    segment_boundaries_json: optional JSON array of sentence idx values where a new
    document begins; cross-document transitions are excluded. Empty string = none.
    """
    boundaries = (
        json.loads(segment_boundaries_json) if segment_boundaries_json else None
    )
    return json.dumps(
        analyze_semantic(text, json.loads(sentences_json), lang, boundaries)
    )


@mcp.tool()
def tool_analyze_readability(text: str, lang: str) -> str:
    """Compute Flesch, Gunning Fog, ARI, Coleman-Liau. Returns score and evidence."""
    return json.dumps(analyze_readability(text, lang))


@mcp.tool()
def tool_compute_verbal_fluency_score(
    lexical_json: str,
    syntactic_json: str,
    semantic_json: str,
    readability_json: str,
    word_count: int,
    lang: str,
) -> str:
    """Combine component scores into the style index (0-100). Unavailable
    components are dropped and weights renormalised."""
    return json.dumps(
        compute_verbal_fluency_score(
            json.loads(lexical_json),
            json.loads(syntactic_json),
            json.loads(semantic_json),
            json.loads(readability_json),
            word_count,
            lang,
        )
    )


@mcp.tool()
def tool_predict_iq(style_index: float, lang: str, gate_json: str = "") -> str:
    """Neutral style band always; experimental IQ only when gate status is OK and
    the language is validated in config/validation.json. Otherwise IQ fields are
    null with withheld_reason."""
    return json.dumps(predict_iq(style_index, lang, gate=_gate(gate_json)))


@mcp.tool()
def tool_predict_mental_age(
    iq_estimate: float = -1.0, chronological_age: int = 0
) -> str:
    """Ratio mental age only for a supplied age <= 16 and an emitted IQ. Pass
    iq_estimate=-1 when IQ was withheld; age is never assumed."""
    iq = iq_estimate if iq_estimate >= 0 else None
    return json.dumps(predict_mental_age(iq, _age(chronological_age)))


@mcp.tool()
def tool_estimate_text_complexity_band(
    gunning_fog: float,
    ari: float,
    lexical_density: float,
    lang: str,
    gate_json: str = "",
) -> str:
    """Text complexity band (describes the text, not the writer's education).
    Unavailable for languages without calibrated readability norms."""
    return json.dumps(
        estimate_text_complexity_band(
            gunning_fog, ari, lexical_density, lang, gate=_gate(gate_json)
        )
    )


@mcp.tool()
def tool_generate_report(
    lang_result_json: str,
    preprocess_result_json: str,
    lexical_result_json: str,
    syntactic_result_json: str,
    semantic_result_json: str,
    readability_result_json: str,
    vfs_result_json: str,
    iq_result_json: str,
    mental_age_result_json: str,
    band_result_json: str,
    format_flag: str = "--both",
    chronological_age: int = 0,
    verbose_caveats: bool = False,
    gate_json: str = "",
) -> str:
    """Generate JSON and/or report with status, provenance caveat and evidence."""
    result = generate_report(
        json.loads(lang_result_json),
        json.loads(preprocess_result_json),
        json.loads(lexical_result_json),
        json.loads(syntactic_result_json),
        json.loads(semantic_result_json),
        json.loads(readability_result_json),
        json.loads(vfs_result_json),
        json.loads(iq_result_json),
        json.loads(mental_age_result_json),
        json.loads(band_result_json),
        format_flag,
        _age(chronological_age),
        verbose_caveats,
        gate=_gate(gate_json),
    )
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
```


Replace `.agent/SKILL.md` with exactly this content:

````markdown
---
name: verbal-fluency-iq
description: >
  Measure the lexical-syntactic complexity of a text passage (a writing-style
  index, not an intelligence measure). Supports English and Indonesian.
  Tool-first: all scores and every withholding decision are computed by
  deterministic MCP tools — never estimated by reasoning alone.
tools_required:
  - tool_detect_language
  - tool_preprocess_text
  - tool_evaluate_gates
  - tool_analyze_lexical
  - tool_analyze_syntactic
  - tool_analyze_semantic
  - tool_analyze_readability
  - tool_compute_verbal_fluency_score
  - tool_predict_iq
  - tool_predict_mental_age
  - tool_estimate_text_complexity_band
  - tool_generate_report
mcp_server: verbal-fluency-mcp
mcp_transport: stdio
mcp_command: "python mcp-server/server.py"
output_flags:
  default: "--both"
  options:
    - "--json"
    - "--report"
    - "--both"
    - "--scores-only"
    - "--verbose-caveats"
optional_params:
  chronological_age: "integer — mental age is reported only for ages up to 16"
  provenance: "supervised_unaided | unsupervised | unknown (default unknown)"
  text_type: "formal_prose | informal | unknown (default unknown)"
---

# Lexical-Syntactic Complexity Skill

## When to invoke

Use this skill when the user provides a text passage and asks for its writing
style, lexical-syntactic complexity, or (experimental) IQ-style analysis.
Always tell the user that the result is a writing-style index, not an
intelligence measure, and that it must not be used to decide about a person.

## Hard constraint

NEVER estimate or reason about any score, and NEVER fill in a field the tools
returned as null (IQ, percentile, mental age, complexity band). Report the
`withheld_reason` instead. If the MCP server is unavailable, return this error:
```
{"error": "verbal-fluency-mcp server not available. Cannot estimate scores without tools."}
```

## Tool call sequence

Call these tools in order. Each output feeds the next.

```
1. tool_detect_language(text)
   → { lang, confidence, supported, mixed_language_share }
   If lang is not "en" or "id": skip to step 3 with word_count=0 and
   terminal_mark_count=0, then report the status and reasons. Do not continue.

2. tool_preprocess_text(text, lang)
   → { tokens, sentences, word_count, token_count, terminal_mark_count, sentence_count, text_clean }

3. tool_evaluate_gates(lang_result_json, word_count, terminal_mark_count, provenance, text_type)
   → { status, statuses, reasons, iq_allowed, text_ok, education_allowed, language_norm_unvalidated, ... }
   Pass provenance and text_type exactly as the user stated them; if the user did
   not state them, pass "unknown". Never upgrade them on the user's behalf.

4. tool_analyze_lexical(tokens_json, sentences_json, lang)
   → { mattr, mtld, vocd_d, lexical_density, avg_word_length, oov_rate, low_reliability, score, evidence, ... }

5. tool_analyze_syntactic(sentences_json, lang)
   → { mean_sentence_length, clause_density, subordination_index, dependency_depth, passive_ratio, comparable_across_languages, score, evidence }

6. tool_analyze_semantic(text_clean, sentences_json, lang, segment_boundaries_json?)
   → { adjacent_sentence_similarity, topic_drift_index, lexical_chain_density, entity_labels, transitions, score, evidence }

7. tool_analyze_readability(text_clean, lang)
   → { flesch_reading_ease, gunning_fog, ari, coleman_liau, score, evidence }

8. tool_compute_verbal_fluency_score(lexical_json, syntactic_json, semantic_json, readability_json, word_count, lang)
   → { style_index, style_index_label, lexical, syntactic, semantic, readability, weights_used, unavailable_components, confidence_label, ... }

9. tool_predict_iq(style_index, lang, gate_json)
   → { style_band, point_estimate, range_low, range_high, range_label, percentile, withheld_reason, language_norm_unvalidated, ... }

10. tool_predict_mental_age(iq_estimate, chronological_age)
    Pass iq_estimate=-1 when point_estimate is null.
    → { mental_age, withheld_reason, ... }

11. tool_estimate_text_complexity_band(gunning_fog, ari, lexical_density, lang, gate_json)
    → { text_complexity_band, label, consistency, withheld_reason, note }

12. tool_generate_report(lang_json, preprocess_json, lexical_json, syntactic_json,
                         semantic_json, readability_json, vfs_json, iq_json,
                         mental_age_json, band_json, format_flag, chronological_age,
                         verbose_caveats, gate_json)
    → { json, report }
```

## Passing JSON between tools

Each tool returns a JSON string. Pass it directly as the `*_json` parameter
of the next tool. Do not parse or summarize intermediate results. The gate
JSON from step 3 must be passed to steps 9, 11 and 12; without it every
screening output is withheld.

## User prompt flags

Parse these from the user's message:
- `--json` / `--report` / `--both` / `--scores-only` / `--verbose-caveats`
- `--age=N` → extract integer N as `chronological_age`
- `--provenance=supervised_unaided|unsupervised|unknown`
- `--text-type=formal_prose|informal|unknown`

Default: `--both`, provenance `unknown`, text type `unknown`.

## Statuses

Relay `status` and every entry of `reasons` to the user verbatim. Only
`OK` permits an IQ figure, and even then it is experimental and requires
human review. Never rank or compare results written in different languages.
````


Replace `.agent/tools.json` with exactly this content:

```json
{
  "schema_version": "2.0",
  "mcp_server": "verbal-fluency-mcp",
  "tools": [
    {
      "name": "tool_detect_language",
      "description": "Detect language; reports unsupported languages as themselves. confidence is a heuristic agreement index, not a probability",
      "parameters": {
        "text": { "type": "string", "required": true }
      },
      "returns": { "lang": "string", "confidence": "number", "supported": "boolean", "mixed_language_share": "number|null" }
    },
    {
      "name": "tool_preprocess_text",
      "description": "Clean, tokenize, and sentence-split text; word_count counts alphabetic words only",
      "parameters": {
        "text": { "type": "string", "required": true },
        "lang": { "type": "string", "enum": ["en", "id"], "required": true }
      },
      "returns": { "tokens": "array", "sentences": "array", "word_count": "integer", "token_count": "integer", "terminal_mark_count": "integer", "sentence_count": "integer", "text_clean": "string" }
    },
    {
      "name": "tool_evaluate_gates",
      "description": "Apply validity gates; the returned JSON is the gate_json required by tool_predict_iq, tool_estimate_text_complexity_band and tool_generate_report",
      "parameters": {
        "lang_result_json": { "type": "string", "required": true },
        "word_count": { "type": "integer", "required": true },
        "terminal_mark_count": { "type": "integer", "required": true },
        "provenance": { "type": "string", "enum": ["supervised_unaided", "unsupervised", "unknown"], "default": "unknown" },
        "text_type": { "type": "string", "enum": ["formal_prose", "informal", "unknown"], "default": "unknown" }
      },
      "returns": { "status": "string", "statuses": "array", "reasons": "array", "iq_allowed": "boolean", "text_ok": "boolean", "education_allowed": "boolean", "language_norm_unvalidated": "boolean", "lang": "string", "provenance": "string", "text_type": "string", "policy_version": "string" }
    },
    {
      "name": "tool_analyze_lexical",
      "description": "Compute MATTR, MTLD, content-word density and out-of-dictionary rate with sentence evidence",
      "parameters": {
        "tokens_json": { "type": "string", "required": true },
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "mattr": "number", "mtld": "number|null", "vocd_d": "number|null", "lexical_density": "number", "avg_word_length": "number", "token_unit": "string", "oov_rate": "number", "low_reliability": "boolean", "reliability_reasons": "array", "score_weights": "object", "score": "number|null", "evidence": "array" }
    },
    {
      "name": "tool_analyze_syntactic",
      "description": "Compute clause density, subordination index, dependency depth (en only); not comparable across languages",
      "parameters": {
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "mean_sentence_length": "number", "clause_density": "number", "subordination_index": "number", "dependency_depth": "number|null", "passive_ratio": "number", "comparable_across_languages": "boolean", "score": "number", "evidence": "array", "note": "string" }
    },
    {
      "name": "tool_analyze_semantic",
      "description": "Compute adjacent-sentence similarity, topic drift (5+ transitions) and lexical chain density; entity labels are informational",
      "parameters": {
        "text": { "type": "string", "required": true },
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true },
        "segment_boundaries_json": { "type": "string", "default": "" }
      },
      "returns": { "adjacent_sentence_similarity": "number|null", "topic_drift_index": "number|null", "lexical_chain_density": "number|null", "entity_labels": "array", "transitions": "integer", "scaling_status": "string|null", "score": "number|null", "evidence": "array" }
    },
    {
      "name": "tool_analyze_readability",
      "description": "Compute Flesch, Gunning Fog, ARI, Coleman-Liau readability indices",
      "parameters": {
        "text": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "flesch_reading_ease": "number", "gunning_fog": "number", "ari": "number", "coleman_liau": "number", "score": "number", "evidence": "array" }
    },
    {
      "name": "tool_compute_verbal_fluency_score",
      "description": "Combine component scores into the style index (0-100); unavailable components are dropped and weights renormalised",
      "parameters": {
        "lexical_json": { "type": "string", "required": true },
        "syntactic_json": { "type": "string", "required": true },
        "semantic_json": { "type": "string", "required": true },
        "readability_json": { "type": "string", "required": true },
        "word_count": { "type": "integer", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "vfs": "number|null", "style_index": "number|null", "style_index_label": "string", "lexical": "number|null", "syntactic": "number|null", "semantic": "number|null", "readability": "number|null", "weights_used": "object", "unavailable_components": "array", "confidence_label": "string", "lang": "string", "text_length_words": "integer" }
    },
    {
      "name": "tool_predict_iq",
      "description": "Neutral style band always; experimental IQ only when gate status is OK and the language is validated, otherwise null with withheld_reason",
      "parameters": {
        "style_index": { "type": "number", "required": true },
        "lang": { "type": "string", "required": true },
        "gate_json": { "type": "string", "default": "" }
      },
      "returns": { "style_index": "number", "style_index_label": "string", "style_band": "string|null", "point_estimate": "integer|null", "range_low": "integer|null", "range_high": "integer|null", "range_label": "string", "classification": "string|null", "percentile": "integer|null", "withheld_reason": "string|null", "language_norm_unvalidated": "boolean" }
    },
    {
      "name": "tool_predict_mental_age",
      "description": "Ratio mental age only for an emitted IQ and a supplied age of 16 or less; never assumes an age",
      "parameters": {
        "iq_estimate": { "type": "number", "default": -1.0 },
        "chronological_age": { "type": "integer", "default": 0 }
      },
      "returns": { "mental_age": "number|null", "based_on_chronological_age": "integer|null", "age_assumed": "boolean", "withheld_reason": "string|null", "formula": "string" }
    },
    {
      "name": "tool_estimate_text_complexity_band",
      "description": "Text complexity band (median of per-metric bands); describes the text, not the writer's education; unavailable for id",
      "parameters": {
        "gunning_fog": { "type": "number", "required": true },
        "ari": { "type": "number", "required": true },
        "lexical_density": { "type": "number", "required": true },
        "lang": { "type": "string", "required": true },
        "gate_json": { "type": "string", "default": "" }
      },
      "returns": { "text_complexity_band": "integer|null", "label": "string|null", "per_metric_bands": "object|null", "consistency": "string|null", "withheld_reason": "string|null", "note": "string" }
    },
    {
      "name": "tool_generate_report",
      "description": "Generate JSON and/or report with status, reasons, provenance caveat and sentence-level evidence",
      "parameters": {
        "lang_result_json": { "type": "string", "required": true },
        "preprocess_result_json": { "type": "string", "required": true },
        "lexical_result_json": { "type": "string", "required": true },
        "syntactic_result_json": { "type": "string", "required": true },
        "semantic_result_json": { "type": "string", "required": true },
        "readability_result_json": { "type": "string", "required": true },
        "vfs_result_json": { "type": "string", "required": true },
        "iq_result_json": { "type": "string", "required": true },
        "mental_age_result_json": { "type": "string", "required": true },
        "band_result_json": { "type": "string", "required": true },
        "format_flag": { "type": "string", "enum": ["--json", "--report", "--both", "--scores-only", "--verbose-caveats"], "default": "--both" },
        "chronological_age": { "type": "integer", "default": 0 },
        "verbose_caveats": { "type": "boolean", "default": false },
        "gate_json": { "type": "string", "default": "" }
      },
      "returns": { "json": "object|null", "report": "string|null" }
    }
  ]
}
```


- [ ] **Step 4: Update the README tool reference**

Save this one-off script outside the repository (for example `aegis_t12_readme.py` in your scratchpad; do not commit it) and run `.venv/bin/python <path>/aegis_t12_readme.py README.md`. It replaces "The 11 MCP Tools" and "Scoring Formulas", adds "Statuses and What They Mean", and updates the component map, dependency table and `.agent` description:


````python
"""Task 12 README edits: tool reference and scoring formulas match the new server."""

import pathlib
import sys

README = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")

TOOLS = """## The 12 MCP Tools

All tools communicate via JSON strings. The server serialises every return value to `str` (JSON) and the AI passes these strings directly as arguments to subsequent tools. The gate JSON from Tool 3 must be passed to Tools 9, 11 and 12; without it every screening output is withheld.

---

### Tool 1 — `tool_detect_language`

**Input:** `text` (`str`).

**Output:**

```json
{
  "lang": "en",
  "confidence": 1.0,
  "supported": true,
  "mixed_language_share": 0.0
}
```

**Algorithm:**

1. langid (all languages, normalised probabilities) picks the language, so Javanese, Sundanese and Malay are reported as themselves instead of being forced to English.
2. `confidence` = the lower of langid's and langdetect's probability for that language (0.0 when they disagree). It is a heuristic agreement index, never a calibrated probability, and is never shown as a percentage.
3. `mixed_language_share` = word-weighted share of sentences (≥ 5 words) that an en/id-only classifier assigns to the other language. `null` for unsupported languages.
4. `supported` is true only for `en`/`id` with `confidence ≥ min_lang_confidence` (0.80).
5. Empty input → `{"lang": "en", "confidence": 0.0, "supported": false, "mixed_language_share": null}`.

---

### Tool 2 — `tool_preprocess_text`

**Input:** `text` (`str`), `lang` (`"en"` or `"id"`; anything else raises an error).

**Output:**

```json
{
  "tokens": ["The", "quick", "brown", "fox", "jumps", "."],
  "sentences": [{"idx": 0, "text": "The quick brown fox jumps."}],
  "word_count": 5,
  "token_count": 5,
  "terminal_mark_count": 1,
  "sentence_count": 1,
  "text_clean": "The quick brown fox jumps."
}
```

`word_count` counts alphabetic words only, so numbers, emoji and symbols cannot reach a length tier. `token_count` is the older count of all non-punctuation tokens. `terminal_mark_count` counts runs of `.`, `!`, `?` and `…`.

**Cleaning steps:** strip URLs, mentions and hashtags; normalise whitespace.

**spaCy models:** English `en_core_web_sm`; Indonesian `xx_ent_wiki_sm` with an added `sentencizer`.

---

### Tool 3 — `tool_evaluate_gates`

Applies every validity gate. Its JSON output is the `gate_json` argument of Tools 9, 11 and 12.

**Input:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `lang_result_json` | `str` | — | Output of Tool 1 |
| `word_count` | `int` | — | `word_count` from Tool 2 |
| `terminal_mark_count` | `int` | — | `terminal_mark_count` from Tool 2 |
| `provenance` | `str` | `"unknown"` | `supervised_unaided`, `unsupervised` or `unknown` |
| `text_type` | `str` | `"unknown"` | `formal_prose`, `informal` or `unknown` |

**Output:**

```json
{
  "status": "UNVERIFIED_PROVENANCE",
  "statuses": ["UNVERIFIED_PROVENANCE", "UNVALIDATED"],
  "reasons": [
    "UNVERIFIED_PROVENANCE: provenance 'unknown': authorship is not attested as supervised and unaided",
    "UNVALIDATED: text_type 'unknown' is outside the formal-prose scope; IQ is refused",
    "UNVALIDATED: IQ mapping is not validated for language 'en' (config/validation.json)"
  ],
  "iq_allowed": false,
  "text_ok": true,
  "education_allowed": true,
  "language_norm_unvalidated": true,
  "lang": "en",
  "provenance": "unknown",
  "text_type": "unknown",
  "policy_version": "2026-10-11"
}
```

**Gates (thresholds from `config/validation.json`):**

| Status | Trigger |
|---|---|
| `UNSUPPORTED_LANGUAGE` | language not en/id, or detection confidence < 0.80 |
| `MIXED_LANGUAGE` | `mixed_language_share` > 0.20 |
| `INSUFFICIENT_TEXT` | fewer than 250 alphabetic words |
| `INSUFFICIENT_STRUCTURE` | more than 40 words per sentence-ending mark |
| `UNVERIFIED_PROVENANCE` | provenance is not `supervised_unaided` |
| `UNVALIDATED` | text type is not `formal_prose`, or the language is not `iq_validated` |

`status` is the highest-precedence triggered status (table order); `OK` only when nothing triggers. IQ is emitted only when `status` is `OK`.

---

### Tool 4 — `tool_analyze_lexical`

**Input:** `tokens_json`, `sentences_json`, `lang`.

**Output:**

```json
{
  "mattr": 0.861,
  "mtld": 155.5,
  "vocd_d": 88.2,
  "lexical_density": 0.498,
  "avg_word_length": 4.7,
  "token_unit": "lowercased_surface_form",
  "alpha_token_count": 650,
  "known_token_count": 650,
  "oov_rate": 0.0,
  "low_reliability": false,
  "reliability_reasons": [],
  "score_weights": {"mattr": 0.45, "mtld": 0.35, "lexical_density": 0.2},
  "score": 87.0,
  "evidence": [
    {
      "sentence_idx": 2,
      "sentence": "The epistemological framework...",
      "triggered_by": ["rare:epistemological"]
    }
  ]
}
```

| Metric | Description |
|---|---|
| MATTR | Moving Average Type-Token Ratio over window=50 tokens |
| MTLD | Measure of Textual Lexical Diversity (threshold 0.72); length-robust replacement for the hapax ratio |
| VOCD-D | Reported only (≥ 50 tokens), not scored |
| Content-word density | Share of tokens not in spaCy's stop-word list for the language |
| Avg word length | Reported only, not scored (it duplicates readability) |
| Out-of-dictionary rate | Share of tokens unknown to `wordfreq`; above 0.10 sets `low_reliability` |

Both languages use lowercased surface forms for every diversity metric; no stemming. Tokens unknown to `wordfreq` (typos, keyboard noise) are excluded from MATTR, MTLD and density, so misspellings cannot raise the score.

---

### Tool 5 — `tool_analyze_syntactic`

**Input:** `sentences_json`, `lang`.

**Output:**

```json
{
  "mean_sentence_length": 22.4,
  "clause_density": 2.8,
  "subordination_index": 1.2,
  "dependency_depth": 6.1,
  "passive_ratio": 0.15,
  "comparable_across_languages": false,
  "score": 68.2,
  "evidence": [
    {
      "sentence_idx": 3,
      "sentence": "Although the committee...",
      "triggered_by": ["subordinate_clauses:3", "dep_depth:8"]
    }
  ],
  "note": "Syntactic scores come from different instruments per language and are not comparable across languages."
}
```

**English:** spaCy dependency labels. Subordinate deps `advcl`, `relcl`, `acl`, `csubj`, `ccomp`, `xcomp`; passive deps `nsubjpass`, `auxpass`, `aux:pass`.

**Indonesian (rule-based, no parser):**
- Colloquial connectives are normalised first (`kalo→kalau`, `biar→agar`, `soalnya→karena`, `makanya→maka`, `pas→ketika`, `gara-gara→karena`, `nek→kalau`, `ben→agar`, `trus/terus→lalu`, `tapi→tetapi`); the count is reported as `colloquial_forms_normalised`.
- `dan`/`atau`/`serta` join clauses only when an overt subject and a predicate follow; temporal words (`sejak`, `selama`, `sampai`, `hingga`, `sebelum`, `setelah`) count only when a predicate follows.
- Passive = `di-` + a PySastrawi dictionary root (optionally + `-kan`/`-i`), excluding locative roots such as `mana`, `antara`, `atas`. `ter-` forms are not counted as passive.
- `dependency_depth` is `null` and its weight is renormalised away.

---

### Tool 6 — `tool_analyze_semantic`

**Input:** `text`, `sentences_json`, `lang`, optional `segment_boundaries_json` (sentence idx values where a new document starts; transitions across them are skipped).

**Output:**

```json
{
  "adjacent_sentence_similarity": 0.414,
  "topic_drift_index": 0.082,
  "lexical_chain_density": 0.341,
  "entity_labels": ["ORG", "PERSON"],
  "transitions": 17,
  "scaling_status": "uncalibrated",
  "score": 32.8,
  "evidence": [
    {"sentence_idx_from": 0, "sentence_idx_to": 1, "similarity": 0.831, "note": "high overlap"}
  ]
}
```

| Metric | Description |
|---|---|
| Adjacent-sentence similarity | Mean cosine similarity of neighbouring sentence embeddings (topical overlap, not argument quality) |
| Topic drift index | Standard deviation of those similarities; `null` with fewer than 5 transitions |
| Lexical chain density | Share of words (> 4 chars) recurring across sentences |
| Entity labels | NER labels, informational only and never scored |

Fewer than 2 sentences (or no within-document transitions) gives `score: null`, which the style index handles by renormalising weights.

---

### Tool 7 — `tool_analyze_readability`

**Input:** `text` (cleaned text from Tool 2), `lang`.

**Output:**

```json
{
  "flesch_reading_ease": 42.3,
  "gunning_fog": 14.8,
  "ari": 13.2,
  "coleman_liau": 12.1,
  "score": 65.7,
  "evidence": [
    {
      "sentence_idx": 1,
      "sentence": "The epistemological...",
      "triggered_by": ["polysyllabic_density:0.42"]
    }
  ]
}
```

**Indonesian:** Flesch uses a vowel-nucleus syllable counter (`_count_id_syllables`) with the English coefficients. Gunning Fog, ARI and Coleman-Liau are English formulas computed by `textstat` for both languages, which is why the text complexity band is unavailable for Indonesian.

**Evidence trigger:** sentences where polysyllabic word density ≥ 0.30.

---

### Tool 8 — `tool_compute_verbal_fluency_score`

Combines the four component scores into the style index (the tool keeps its historical name).

**Input:** `lexical_json`, `syntactic_json`, `semantic_json`, `readability_json`, `word_count`, `lang`.

**Output:**

```json
{
  "vfs": 61.2,
  "style_index": 61.2,
  "style_index_label": "Writing-style index (lexical-syntactic complexity). Not an intelligence measure.",
  "lexical": 87.0,
  "syntactic": 62.9,
  "semantic": 19.2,
  "readability": 68.1,
  "weights_used": {"lexical": 0.35, "syntactic": 0.25, "semantic": 0.25, "readability": 0.15},
  "unavailable_components": [],
  "confidence_label": "HIGH",
  "lang": "en",
  "text_length_words": 650
}
```

`confidence_label` is an ordinal text-length tier (VERY LOW < 30 words, LOW < 100, MEDIUM < 300, HIGH otherwise). No numeric confidence is produced.

---

### Tool 9 — `tool_predict_iq`

**Input:** `style_index` (`float`), `lang` (`str`), `gate_json` (`str`, output of Tool 3; empty string = no gate = withheld).

**Output (shipped configuration):**

```json
{
  "style_index": 61.2,
  "style_index_label": "Writing-style index (lexical-syntactic complexity). Not an intelligence measure.",
  "style_band": "Style band 3",
  "point_estimate": null,
  "range_low": null,
  "range_high": null,
  "range_label": "uncalibrated heuristic range",
  "classification": null,
  "percentile": null,
  "withheld_reason": "UNVERIFIED_PROVENANCE: ...; UNVALIDATED: IQ mapping is not validated for language 'en' (config/validation.json)",
  "language_norm_unvalidated": true
}
```

When the gate status is `OK` and the language is `iq_validated`, `point_estimate` is interpolated in the band, `percentile` is the normal CDF of the IQ under N(100, 15) (clamped to 1–99), and `range_low`/`range_high` are ±25 (or the configured larger half-width).

---

### Tool 10 — `tool_predict_mental_age`

**Input:** `iq_estimate` (`float`; pass `-1` when IQ was withheld), `chronological_age` (`int`; `0` = not supplied).

**Output:**

```json
{
  "mental_age": null,
  "based_on_chronological_age": null,
  "age_assumed": false,
  "withheld_reason": "chronological age not supplied; never assumed",
  "formula": "mental_age = (iq / 100) * chronological_age"
}
```

Reported only for an emitted IQ and a supplied age of 16 or less.

---

### Tool 11 — `tool_estimate_text_complexity_band`

**Input:** `gunning_fog`, `ari`, `lexical_density`, `lang`, `gate_json`.

**Output:**

```json
{
  "text_complexity_band": 5,
  "label": "Complexity band 5",
  "per_metric_bands": {"gunning_fog": 5, "ari": 5, "lexical_density": 5},
  "consistency": "CONSISTENT",
  "withheld_reason": null,
  "note": "Describes how difficult this text is to read, not the writer's education. Education cannot be inferred from text."
}
```

Unavailable (all fields `null` with `withheld_reason`) for Indonesian, and whenever a text gate fails.

---

### Tool 12 — `tool_generate_report`

**Input:** the outputs of Tools 1, 2, 4, 5, 6, 7, 8, 9, 10 and 11, plus:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format_flag` | `str` | `"--both"` | Output format (see [Output Flags](#output-flags)) |
| `chronological_age` | `int` | `0` | Pass-through for display |
| `verbose_caveats` | `bool` | `false` | Append extended limitations block |
| `gate_json` | `str` | `""` | Output of Tool 3; without it the report says `Status: UNVERIFIED` and `Provenance: not attested` |

**Output:** `{"json": {...}, "report": "..."}`; either may be `null` depending on `format_flag`. The JSON carries `status`, `reasons`, `provenance`, `notice`, `language` (with `language_norm_unvalidated`), `style_index`, `iq_prediction`, `mental_age`, `text_complexity` and `metrics`.
"""

FORMULAS = """## Scoring Formulas

### Style index

```
style_index = Σ w_i × component_i / Σ w_i     over available components
nominal w:    lexical 0.35, syntactic 0.25, semantic 0.25, readability 0.15
```

A component whose score is `null` (for example semantic with one sentence) is dropped and the remaining weights renormalised; nothing is imputed. The nominal weights are hand-set; `docs/validation/effective-weights.md` reports what actually drives the index.

### Component sub-scores

Each raw metric is scaled to [0, 100] with `clamp(x) = max(0, min(100, x))`. All bounds are hand-set and uncalibrated.

**Lexical:**
```
mattr_score    = clamp((mattr - 0.3) / 0.6 × 100)
mtld_score     = clamp((mtld - 40) / 160 × 100)
density_score  = clamp((content_word_density - 0.3) / 0.4 × 100)

lexical_score  = (mattr×0.45 + mtld×0.35 + density×0.20) / Σ available weights
```

**Syntactic:**
```
msl_score      = clamp((mean_sentence_length - 8) / 22 × 100)
cd_score       = clamp((clause_density - 1.0) / 2.5 × 100)
si_score       = clamp(subordination_index / 1.5 × 100)
dd_score       = clamp((dep_depth - 2) / 8 × 100)        (English only)

syntactic_score = MSL×0.30 + CD×0.35 + SI×0.25 + DD×0.10
                  (Indonesian: DD dropped, the rest divided by 0.90)
```

**Semantic:**
```
similarity_score = clamp((similarity - min_lang) / (max_lang - min_lang) × 100)
                   (min/max from config/semantic_scaling.json; 0.3/0.9 for en and id)
drift_score      = clamp((1 - drift / 0.3) × 100)          (≥ 5 transitions only)
chain_score      = clamp((chain_density - 0.1) / 0.5 × 100)

semantic_score   = (similarity×0.45 + drift×0.25 + chain×0.20) / Σ available weights
```

**Readability:**
```
fog_score      = clamp((fog - 6) / 12 × 100)
ari_score      = clamp((ari - 5) / 11 × 100)
cl_score       = clamp((cl - 5) / 11 × 100)
flesch_score   = clamp(100 - flesch)

readability_score = fog×0.35 + ari×0.30 + cl×0.20 + flesch×0.15
```
"""

STATUSES = """## Statuses and What They Mean

Every pipeline result, gate evaluation and report carries one `status` and a list of `reasons`. The status decides which outputs exist.

| Status | Meaning | Style index | IQ / percentile / mental age | Complexity band | What to do |
|---|---|---|---|---|---|
| `OK` | Every gate passed and the language is validated | shown | shown (experimental) | shown (en) | Human review is still mandatory |
| `UNVALIDATED` | No validation study has passed for this language, or the text is not formal prose | shown | withheld | shown (en) | Nothing at run time; see `docs/validation/validation-protocol.md` |
| `UNVERIFIED_PROVENANCE` | Authorship is not attested as supervised and unaided | shown | withheld | shown (en) | Collect a supervised, unaided sample and pass `provenance=supervised_unaided` |
| `INSUFFICIENT_STRUCTURE` | More than 40 words per sentence-ending mark | shown | withheld | withheld | Use punctuated prose; sentence-length metrics are meaningless otherwise |
| `INSUFFICIENT_TEXT` | Fewer than 250 alphabetic words | shown | withheld | withheld | Collect a longer sample |
| `MIXED_LANGUAGE` | More than 20% of words in a second language | shown | withheld | withheld | Analyse single-language samples separately |
| `UNSUPPORTED_LANGUAGE` | Not English or Indonesian, or detection confidence below 0.80 | not computed | withheld | withheld | No analysis is possible |

When several conditions apply, `status` is the most severe one (the order of rows from the bottom up) and every triggered condition is listed in `statuses` and `reasons`.

**Enabling IQ output.** IQ output for a language is enabled only by editing `mcp-server/config/validation.json` (`"iq_validated": true`) after the validation study for that language has met every acceptance threshold in `docs/validation/validation-protocol.md`. There is deliberately no per-call flag that bypasses a gate. Even then, the output is experimental and must not be the basis of a decision about a person without human review.

**Comparing people.** Results from different languages must never be ranked against each other. `tools.policy.rank_by_style_index` and `tools.policy.assert_same_language` raise `CrossLanguageComparisonError` when asked to do so, and every output carries `language_norm_unvalidated`.

**Low reliability.** Independently of status, `low_reliability` is set when more than 10% of words are unknown to the dictionary (typos, keyboard noise, heavy dialect). Route such results to human review.
"""


def replace_section(text: str, start: str, end: str, new: str) -> str:
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[:i] + new + "\n---\n\n" + text[j:]


def main() -> None:
    text = README.read_text(encoding="utf-8")
    text = text.replace(
        "- [The 11 MCP Tools](#the-11-mcp-tools)", "- [The 12 MCP Tools](#the-12-mcp-tools)"
    )
    text = replace_section(
        text, "## The 11 MCP Tools\n", "## Scoring Formulas", TOOLS + "\n---\n\n" + STATUSES
    )
    text = replace_section(
        text,
        "## Scoring Formulas\n",
        "## Style Bands, Experimental IQ & Text Complexity",
        FORMULAS,
    )
    replacements = [
        (
            "│   ├── server.py              ← FastMCP entry point (11 @mcp.tool() handlers)",
            "│   ├── server.py              ← FastMCP entry point (12 @mcp.tool() handlers)",
        ),
        (
            "│   │   ├── preprocess.py      ← Language detection + tokenisation",
            "│   │   ├── policy.py          ← Validity gates, statuses, cross-language guard\n"
            "│   │   ├── preprocess.py      ← Language detection + tokenisation",
        ),
        (
            "│   │   ├── lexical.py         ← MATTR, VOCD-D, hapax ratio, lexical density",
            "│   │   ├── lexical.py         ← MATTR, MTLD, content-word density, OOV rate",
        ),
        (
            "│   │   ├── semantic.py        ← Sentence embeddings, coherence, entity types",
            "│   │   ├── semantic.py        ← Adjacent-sentence similarity, drift, chains",
        ),
        (
            "│   │   ├── mapper.py          ← VFS → IQ / mental age / education mapping",
            "│   │   ├── mapper.py          ← Style index, style band, gated IQ, complexity band",
        ),
        (
            "│       ├── iq_norms.json      ← VFS→IQ band table",
            "│       ├── validation.json    ← Validity policy (gates, per-language flags)\n"
            "│       ├── iq_norms.json      ← Style band table (uncalibrated)",
        ),
        (
            "│       ├── edu_norms.json     ← Readability→education thresholds",
            "│       ├── edu_norms.json     ← Text complexity band thresholds\n"
            "│       ├── semantic_scaling.json ← Per-language similarity scaling",
        ),
        (
            "│   └── tools.json             ← JSON Schema for all 11 tools",
            "│   └── tools.json             ← JSON Schema for all 12 tools",
        ),
        (
            "| `lexicalrichness>=0.4.2` | VOCD-D computation |",
            "| `lexicalrichness>=0.4.2` | MTLD and VOCD-D computation |\n"
            "| `wordfreq>=3.1.1` | Dictionary filter for misspellings (bundled en/id data) |",
        ),
        (
            "| `PySastrawi>=1.2.0` | Indonesian stemmer for MATTR normalisation |",
            "| `PySastrawi>=1.2.0` | Indonesian root dictionary for passive and verb detection |",
        ),
        (
            "| `langid>=1.1.6` | Language detection (secondary + confidence) |",
            "| `langid>=1.1.6` | Language detection (primary) and code-switching detection |",
        ),
        (
            "| `langdetect>=1.0.9` | Language detection (primary) |",
            "| `langdetect>=1.0.9` | Language detection (agreement check) |",
        ),
        (
            "- Full 11-step tool call sequence with input/output schemas",
            "- Full 12-step tool call sequence with input/output schemas",
        ),
        (
            "- Minimum text requirement (10 words)",
            "- Status handling: withheld fields are reported with their reasons",
        ),
        (
            "**`.agent/tools.json`** — JSON Schema contracts for all 11 tools, vendor-neutral.",
            "**`.agent/tools.json`** — JSON Schema contracts for all 12 tools, vendor-neutral.",
        ),
        (
            'Analyze this text for verbal fluency: "<paste text here>"',
            'Analyze the lexical-syntactic complexity of this text --provenance=supervised_unaided --text-type=formal_prose: "<paste text here>"',
        ),
    ]
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new)
    README.write_text(text, encoding="utf-8")
    print(f"{README}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
````


Expected output: `README.md: 921 lines` (must stay ≥ 904 because open phase 3–5 findings cite line 904).

- [ ] **Step 5: Run the wiring tests and type check**

```bash
.venv/bin/python -m pytest tests/test_server_wiring.py -v
cd mcp-server && ../.venv/bin/mypy server.py tools/ --ignore-missing-imports; cd ..
```

Expected: 4 passed. mypy reports exactly one error, the pre-existing `server.py:8: error: Module "mcp.server.fastmcp" has no attribute "FastMCP"` (mcp 2.x; out of scope), and nothing in `tools/`.

- [ ] **Step 6: Recapture the golden fixture once and review the diff**

This is the only step that reads `example/{aqilah,bimo,fabhian}/source/1.md`, and only through the script. Never open `example/rahmat`.

```bash
.venv/bin/python scripts/capture_golden.py
.venv/bin/python - <<'EOF'
import json, subprocess
old = json.loads(subprocess.check_output(["git", "show", "HEAD:tests/fixtures/golden_scores.json"]))
new = json.load(open("tests/fixtures/golden_scores.json"))
for src in old:
    o, n = old[src], new[src]
    print(f"{src}: vfs {o['vfs']} -> style_index {n['style_index']} ({n['style_band']}); "
          f"iq {o['iq']} ci {o['ci']} -> iq {n['iq']} status {n['status']}; "
          f"edu {o['edu']} -> complexity band {n['text_complexity_band']}; "
          f"words {o['word_count']} -> {n['word_count']} (tokens {n['token_count']}); "
          f"statuses {n['statuses']}")
    for reason in n["reasons"]:
        print("    ", reason)
EOF
.venv/bin/python -m pytest tests/test_golden.py -v
```

Expected: one line per source plus its reasons (every `iq` becomes `None`; the Indonesian sources get complexity band `None`; the default call has `provenance='unknown'`, so `UNVERIFIED_PROVENANCE` and `UNVALIDATED` are always among the statuses), then all `test_golden.py` tests pass. Review the lines: if a text gate also fires (`UNSUPPORTED_LANGUAGE`, `MIXED_LANGUAGE`, `INSUFFICIENT_STRUCTURE`), its printed reason is the evidence — record it in the commit message as a finding about that text; do not open the source and do not change thresholds to make it go away. A style-index move of more than ~15 points with no gate explaining it is unexpected: stop and investigate with superpowers:systematic-debugging before committing. Keep the printed lines for the commit message.

- [ ] **Step 7: Mark the 33 phase-2 findings done**

```bash
.venv/bin/python - <<'EOF'
import json, pathlib
cur = pathlib.Path("docs/audit/curated.json")
fin = pathlib.Path("docs/audit/2026-10-11-aegis-findings.json")
curated = json.loads(cur.read_text(encoding="utf-8"))
phase2 = {f["title"] for f in json.loads(fin.read_text(encoding="utf-8")) if f["phase"] == 2}
assert len(phase2) == 33
n = 0
for f in curated:
    if f["title"] in phase2:
        f["status"] = "done"
        n += 1
assert n == 33, n
cur.write_text(json.dumps(curated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
EOF
cp docs/audit/2026-10-11-aegis-findings.json /tmp/aegis-findings-before.json
.venv/bin/python scripts/consolidate_findings.py
.venv/bin/python - <<'EOF'
import json
a = json.load(open("/tmp/aegis-findings-before.json"))
b = json.load(open("docs/audit/2026-10-11-aegis-findings.json"))
assert [(f["id"], f["title"]) for f in a] == [(f["id"], f["title"]) for f in b], "ids moved"
assert all(f["status"] == "done" for f in b if f["phase"] == 2)
assert all(f["status"] == "open" for f in b if f["phase"] != 2)
print("ids stable; phase 2 done")
EOF
.venv/bin/python scripts/audit_status.py
```

Expected: `ids stable; phase 2 done`, then

```
phase 2: 33 done / 0 open
phase 3: 0 done / 29 open
phase 4: 0 done / 14 open
phase 5: 0 done / 24 open
total: 33/100 done
```

(`consolidate_findings.py` renumbers by category, severity and phase, none of which change, so ids are stable; `verify_evidence` skips done findings, so their drifted line numbers are fine.)

- [ ] **Step 8: Lint and format everything touched in this task, then the whole tree CI lints**

```bash
.venv/bin/ruff check --fix mcp-server/server.py tests/test_server_wiring.py tests/test_golden.py
.venv/bin/ruff format mcp-server/server.py tests/test_server_wiring.py tests/test_golden.py
.venv/bin/ruff check mcp-server/ tests/ scripts/
.venv/bin/ruff format --check mcp-server/ tests/ scripts/
```

Expected: `All checks passed!` and every file already formatted.

- [ ] **Step 9: Run the full suite and the audit gate**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/audit_status.py
```

Expected: everything passes with no `xfail`; audit as in Step 7, exit 0.

- [ ] **Step 10: Commit**

Paste the three before/after lines from Step 6 into the second `-m`:

```bash
git add mcp-server/server.py .agent/SKILL.md .agent/tools.json README.md \
  tests/test_server_wiring.py tests/test_golden.py tests/fixtures/golden_scores.json \
  docs/audit/curated.json docs/audit/2026-10-11-aegis-findings.json
git commit -m "feat(server): wire phase-2 gates into MCP tools and agent skill; close AEGIS phase 2" \
  -m "Golden fixture recaptured once. Before -> after: <paste the three lines from Step 6>" \
  -m "New tool_evaluate_gates; tool_predict_iq, tool_estimate_text_complexity_band and tool_generate_report take gate_json and withhold without it; tool_estimate_education_level removed. .agent/SKILL.md and tools.json match server signatures (tested). All 33 phase-2 findings marked done; audit_status shows phase 2: 33 done." \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-Review

1. **Spec coverage.** Spec §4 phase 2 scope (scoring honesty, CI, cross-language normalisation, decision guards) maps to Tasks 2–9; process items F-002/F-027 are protocols with config gates (§1 `process`), not fabricated data (Task 11); the exit gate "all phase=2 done; golden-score diff reviewed" is Task 12 Steps 6–7. Every finding F-001…F-033 appears in the map with a task and a test. D1–D12 are implemented; refinements are listed under *Decisions this plan records*.
2. **Placeholder scan.** Every code step carries the full file or exact old/new text; every edit list was applied to the previous task's output and checked to reproduce the shown file. The two README scripts and the findings snippets are complete. The only value an executor supplies is the Step 6 diff pasted into the commit message.
3. **Type consistency.** The gate dict produced in Task 2 is consumed with the same keys in Tasks 3, 4, 5, 9 and 12; `predict_iq(style_index, lang, gate=None, policy=None)`, `estimate_text_complexity_band(gunning_fog, ari, lexical_density, lang, gate=None, policy=None)` and `generate_report(..., band_result, ..., gate=None)` are called with those signatures by the pipeline, tests and server. The full plan was replayed task by task from the current `HEAD` (without `example/`): each task's new tests failed before its implementation, and the full suite and `audit_status.py` passed after it.
4. **Review Focus.** Five uncovered input classes are listed at the top; each has its test in the owning task (Tasks 2, 3, 5, 8, 12).
