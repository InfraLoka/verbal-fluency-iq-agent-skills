# Verbal Fluency IQ — Design Spec
**Date:** 2026-05-18
**Status:** Approved

---

## Overview

An agent skill that predicts IQ, mental age, and education level from any text
passages written by a target user. Uses verbal fluency as the primary proxy for
cognitive estimation. Designed with a tool-first, vendorless approach: works on
Claude, GPT, Gemini, or any agent that can read a skill file and call MCP tools.

---

## Goals

- Predict IQ (point estimate + 95% confidence interval) from text passages
- Predict mental age (optionally anchored to user-supplied chronological age)
- Estimate education level (Indonesian and English labels)
- Support English and Indonesian text (auto-detected)
- Handle any text length and register: social media, chat, essays, transcripts
- Produce JSON scores and/or a highly detailed structured report with sentence-level citations
- Never hallucinate: all scores computed by deterministic tool functions, not LLM estimation

---

## Non-Goals

- Real-time streaming analysis
- Audio/speech input (text only)
- Clinical or diagnostic use (tool explicitly disclaims this)
- Languages other than English and Indonesian (v1)

---

## Architecture

### Approach: Modular Tool Pipeline + Vendorless `.agent/`

The MCP server exposes 11 atomic tools. The skill file (`.agent/SKILL.md`) tells
the agent the exact call sequence and how to chain outputs. The agent is the
orchestrator — the server has no orchestration logic.

```
User (any agent: Claude, GPT, Gemini)
        │
        ▼
  .agent/SKILL.md          ← reads skill, learns tool contracts
        │
        ▼
  MCP Server (localhost)   ← agent calls tools via MCP protocol
        │
   ┌────┴──────────────────────────────────────┐
   │              Tool Pipeline                │
   │                                           │
   │  1.  detect_language(text)                │
   │  2.  preprocess_text(text, lang)          │
   │  3.  analyze_lexical(tokens, lang)        │
   │  4.  analyze_syntactic(sentences, lang)   │
   │  5.  analyze_semantic(text, lang)         │
   │  6.  analyze_readability(text, lang)      │
   │  7.  compute_verbal_fluency_score(...)    │
   │  8.  predict_iq(vfs, metrics)             │
   │  9.  predict_mental_age(iq, age?)         │
   │  10. estimate_education_level(metrics)    │
   │  11. generate_report(all, format, mode)   │
   └───────────────────────────────────────────┘
        │
        ▼
  Output: JSON | Structured Report | Both
```

---

## Project Structure

```
verbal-fluency-iq/
  .agent/
    SKILL.md              ← vendorless skill definition
    tools.json            ← tool schemas (JSON Schema, no vendor syntax)
  mcp-server/
    server.py             ← MCP server entry point (FastMCP)
    tools/
      lexical.py          ← TTR, MATTR, VOCD-D, hapax, lexical density
      syntactic.py        ← sentence length, clause density, dep depth
      semantic.py         ← coherence, topic drift, lexical chains, NER
      readability.py      ← Flesch, Gunning Fog, ARI, Coleman-Liau
      mapper.py           ← metrics → IQ / mental age / education mapping
      reporter.py         ← JSON + structured report with sentence citations
    config/
      iq_norms.json       ← VFS → IQ lookup table (piecewise distribution)
      edu_norms.json      ← readability composite → education mapping
      id_syllables.json   ← Indonesian syllable counting rules
  tests/
    test_lexical.py
    test_syntactic.py
    test_semantic.py
    test_readability.py
    test_pipeline.py
  requirements.txt
  README.md
```

---

## Verbal Fluency Score (VFS)

The VFS is a weighted composite (0–100 scale) of four metric categories:

```
VFS = (Lexical × 0.35) + (Syntactic × 0.25) + (Semantic × 0.25) + (Readability × 0.15)
```

Weights reflect psycholinguistic research priority: lexical richness is the
strongest empirically validated proxy for fluid intelligence.

---

## Tool Specifications

### Tool 1 — `detect_language`
**Input:** `text: str`
**Output:** `{ lang: "en" | "id", confidence: float }`
**Library:** `langdetect` + `langid` ensemble vote
**Notes:** If confidence < 0.80, flag as LOW and default to EN.

---

### Tool 2 — `preprocess_text`
**Input:** `text: str, lang: str`
**Output:** `{ tokens: list[str], sentences: list[str], word_count: int, sentence_count: int }`
**Libraries:**
- EN: `spaCy` (en_core_web_sm)
- ID: `spaCy` + `PySastrawi` stemmer for MATTR normalization
**Notes:** Strips URLs, mentions, hashtags. Preserves punctuation for syntactic analysis. Tags each sentence with its original index for citation tracking.

---

### Tool 3 — `analyze_lexical`
**Input:** `tokens: list[str], sentences: list[str], lang: str`
**Output:**
```json
{
  "mattr": 0.78,
  "vocd_d": 61.2,
  "hapax_ratio": 0.42,
  "lexical_density": 0.53,
  "avg_word_length": 5.8,
  "score": 78.1,
  "evidence": [
    { "sentence_idx": 2, "sentence": "...", "triggered_by": ["hapax:epistemological", "hapax:underpinnings"] },
    { "sentence_idx": 5, "sentence": "...", "triggered_by": ["rare_vocab:labyrinthine"] }
  ]
}
```
**Libraries:** `lexicalrichness`, `spaCy` (POS tagging for lexical density)
**Indonesian note:** MATTR computed after PySastrawi stemming to avoid inflection TTR inflation.

---

### Tool 4 — `analyze_syntactic`
**Input:** `sentences: list[str], lang: str`
**Output:**
```json
{
  "mean_sentence_length": 18.3,
  "clause_density": 2.1,
  "subordination_index": 0.48,
  "dependency_depth": 6,
  "passive_ratio": 0.12,
  "score": 69.2,
  "evidence": [
    { "sentence_idx": 3, "sentence": "...", "triggered_by": ["subordinate_clause", "dep_depth:7"] },
    { "sentence_idx": 7, "sentence": "...", "triggered_by": ["embedded_relative_clause"] }
  ]
}
```
**Libraries:** `spaCy` (dependency parser)

---

### Tool 5 — `analyze_semantic`
**Input:** `text: str, sentences: list[str], lang: str`
**Output:**
```json
{
  "argument_coherence": 0.74,
  "topic_drift_index": 0.21,
  "lexical_chain_density": 0.61,
  "entity_sophistication": "ABSTRACT",
  "score": 71.8,
  "evidence": [
    { "sentence_idx_from": 0, "sentence_idx_to": 1, "coherence": 0.81, "note": "causal chain detected" },
    { "sentence_idx_from": 1, "sentence_idx_to": 2, "coherence": 0.67, "note": "slight drift — new entity" }
  ]
}
```
**Libraries:**
- `sentence-transformers` (paraphrase-multilingual-MiniLM-L12-v2 — supports EN + ID)
- `NLTK` WordNet (EN lexical chains)
- `IndoNLU` / `IndoBERT` embeddings (ID lexical chains)
- `spaCy` NER

---

### Tool 6 — `analyze_readability`
**Input:** `text: str, lang: str`
**Output:**
```json
{
  "flesch_reading_ease": 52.1,
  "gunning_fog": 12.4,
  "ari": 11.8,
  "coleman_liau": 12.1,
  "score": 65.0,
  "evidence": [
    { "sentence_idx": 4, "sentence": "...", "triggered_by": ["polysyllabic_density:0.38"] }
  ]
}
```
**Libraries:** `textstat` (calibrated with Indonesian syllable rules for ID)

---

### Tool 7 — `compute_verbal_fluency_score`
**Input:** lexical, syntactic, semantic, readability outputs
**Output:**
```json
{
  "vfs": 73.4,
  "lexical": 78.1,
  "syntactic": 69.2,
  "semantic": 71.8,
  "readability": 65.0,
  "confidence": 0.82,
  "confidence_label": "HIGH",
  "lang": "en",
  "text_length_words": 412
}
```
**Confidence penalties:**
- < 30 words → VERY LOW (0.30)
- 30–99 words → LOW (0.55)
- 100–299 words → MEDIUM (0.70)
- 300+ words → HIGH (0.82–0.95, scales with diversity)

---

### Tool 8 — `predict_iq`
**Input:** `vfs: float, metrics: dict`
**Output:**
```json
{
  "point_estimate": 117,
  "ci_low": 110,
  "ci_high": 124,
  "classification": "Above Average / Superior",
  "percentile": 79,
  "key_evidence_sentences": [2, 3, 7],
  "vfs_contribution": 0.61
}
```
**Norms (from `config/iq_norms.json`):**

| VFS Range | IQ Range | Classification |
|-----------|----------|---------------|
| 85–100 | 125–145+ | Gifted / Highly Gifted |
| 70–84 | 110–124 | Above Average / Superior |
| 55–69 | 90–109 | Average |
| 40–54 | 75–89 | Below Average |
| < 40 | < 75 | Low |

**Research basis:** Pennebaker et al. (LIWC), Crossley et al. (Lexical Sophistication),
Mairesse et al. (Personality/Intelligence from text).

---

### Tool 9 — `predict_mental_age`
**Input:** `iq_estimate: float, chronological_age: int | None`
**Output:**
```json
{
  "mental_age": 35.1,
  "based_on_chronological_age": 30,
  "age_assumed": true,
  "formula": "mental_age = (iq / 100) * chronological_age"
}
```
**Notes:** If `chronological_age` not provided, defaults to population median (30).
User passes `--age=N` in prompt to improve precision.

---

### Tool 10 — `estimate_education_level`
**Input:** `metrics: dict` (gunning_fog, ari, lexical_density, clause_density)
**Output:**
```json
{
  "level_en": "Bachelor's Degree",
  "level_id": "Sarjana (S1)",
  "level_code": "S1",
  "confidence": 0.68,
  "confidence_label": "MEDIUM"
}
```
**Education level ladder:**

| EN Label | ID Label | Code |
|----------|----------|------|
| Doctoral / Postgrad Research | Doktor / Peneliti Pascasarjana | S3 |
| Graduate | Magister (S2) | S2 |
| Undergraduate | Sarjana (S1/D4) | S1 |
| Vocational / Diploma | Diploma (D1–D3) | D3 |
| Senior High School | SMA/SMK | SMA |
| Junior High School | SMP | SMP |
| Primary School | SD | SD |

---

### Tool 11 — `generate_report`
**Input:** all previous tool outputs, `format: str`, `mode: str`
**Output:** formatted string (report) and/or JSON block

**Format flags (user-controlled via prompt):**

| Flag | Output |
|------|--------|
| `--json` | JSON scores only |
| `--report` | Full structured narrative report |
| `--both` | JSON block + full report (default) |
| `--scores-only` | Minimal JSON, no caveats |
| `--verbose-caveats` | Report + extended limitations section |

---

## Report Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERBAL FLUENCY INTELLIGENCE REPORT
  Generated: YYYY-MM-DD | Language: English
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SUBJECT PROFILE
  Text input          : N words across N passages
  Text type           : Mixed / Essay / Social / Transcript
  Analysis confidence : HIGH / MEDIUM / LOW (%)

  VERBAL FLUENCY SCORE
  Overall VFS     : 73.4 / 100
  └── Lexical     : 78.1 / 100  ████████░░
  └── Syntactic   : 69.2 / 100  ██████░░░░
  └── Semantic    : 71.8 / 100  ███████░░░
  └── Readability : 65.0 / 100  ██████░░░░

  IQ PREDICTION
  Point estimate  : 117
  95% CI range    : 110 – 124
  Classification  : Above Average / Superior
  Percentile      : ~79th

  MENTAL AGE
  Estimated       : 35.1 years
  (Chronological age assumed: 30 | pass --age=N to improve)

  EDUCATION LEVEL ESTIMATE
  Estimated level : Undergraduate (S1/Bachelor)
  Confidence      : MEDIUM (68%)
  EN label        : Bachelor's Degree
  ID label        : Sarjana (S1)

  DETAILED LEXICAL METRICS
  MATTR (window=50)     : 0.78
  VOCD-D                : 61.2
  Hapax Legomena ratio  : 0.42
  Lexical density       : 0.53
  Avg word length       : 5.8 chars

  DETAILED SYNTACTIC METRICS
  Mean sentence length  : 18.3 words
  Clause density        : 2.1
  Subordination index   : 0.48
  Dependency tree depth : 6
  Passive voice ratio   : 0.12

  DETAILED SEMANTIC METRICS
  Argument coherence    : 0.74
  Topic drift index     : 0.21 (low drift = focused)
  Lexical chain density : 0.61
  Entity sophistication : ABSTRACT

  READABILITY INDICES
  Flesch Reading Ease   : 52.1 (Fairly Difficult)
  Gunning Fog Index     : 12.4 (College level)
  ARI                   : 11.8
  Coleman-Liau Index    : 12.1

  INTERPRETATION WITH EVIDENCE
  ─────────────────────────────────────────

  [LEXICAL — Score 78.1]
  Strong vocabulary diversity detected (MATTR 0.78).
  Evidence:
    → "The epistemological underpinnings of this argument
       rest on empirical validation..."
       [hapax: 'epistemological', 'underpinnings']
    → "He traversed the labyrinthine corridors of
       bureaucratic ambiguity..."
       [rare vocab: 'labyrinthine', 'bureaucratic']

  [SYNTACTIC — Score 69.2]
  Moderate-high clause density (2.1) indicates structured
  argumentation.
  Evidence:
    → "Although the data was inconclusive, the team proceeded
       because the deadline demanded action."
       [subordinate clauses: 'Although...', 'because...']
    → "The report, which had been revised three times by
       external reviewers, was finally submitted."
       [embedded relative clause, dependency depth: 7]

  [SEMANTIC — Score 71.8]
  Argument coherence is strong (0.74) with low topic drift (0.21).
  Evidence:
    → Passage 1→2 coherence: 0.81
       "The policy failed." → "Its failure stemmed from poor
       implementation..." [causal chain detected]
    → Passage 2→3 coherence: 0.67
       [slight drift — new entity introduced]

  [READABILITY — Score 65.0]
  Writing calibrated for college-educated audience (Fog 12.4).
  Evidence:
    → "The multifaceted implications of decentralized
       governance cannot be understated..."
       [polysyllabic density: 0.38 in this sentence]

  [IQ PREDICTION — 117, CI: 110–124]
  Driven by lexical sophistication and syntactic embedding depth.
  Key evidence sentences:
    → [S2] "The epistemological underpinnings..."
    → [S3] "Although the data was inconclusive..."
    → [S7] "The multifaceted implications..."
  These 3 sentences account for 61% of VFS uplift above median.

  [EDUCATION ESTIMATE — S1/Bachelor]
  Gunning Fog 12.4 + ARI 11.8 + lexical density 0.53.
    → Writing consistent with academic/professional authorship.
    → No sentence exceeded graduate-level complexity (Fog > 17).

  CONFIDENCE & LIMITATIONS
  Overall confidence    : HIGH (82%)
  Limiting factors      :
    • Text-based IQ estimation has ±10–15 pt error margin
    • Mental age assumes population median if age not supplied
    • Education estimate does not account for self-taught learning
    • Cultural/linguistic background affects psycholinguistic norms
    • Short texts (<100 words) significantly reduce reliability

  RESEARCH BASIS
  Pennebaker et al. — LIWC personality/intelligence studies
  Crossley et al.  — Lexical Sophistication indices
  Mairesse et al.  — Big Five + intelligence from text
  Gunning (1952)   — Fog Index
  Coleman & Liau (1975) — CL Index
  Covington & McFall (2010) — VOCD-D

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Vendorless Skill File — `.agent/SKILL.md`

```markdown
---
name: verbal-fluency-iq
description: >
  Predict IQ, mental age, and education level from text passages
  using verbal fluency analysis. Supports English and Indonesian.
  Tool-first: all scores are computed by deterministic MCP tools.
tools_required:
  - detect_language
  - preprocess_text
  - analyze_lexical
  - analyze_syntactic
  - analyze_semantic
  - analyze_readability
  - compute_verbal_fluency_score
  - predict_iq
  - predict_mental_age
  - estimate_education_level
  - generate_report
mcp_server: verbal-fluency-mcp
mcp_transport: stdio
output_flags:
  default: --both
  options: [--json, --report, --both, --scores-only, --verbose-caveats]
optional_params:
  --age: chronological age integer for mental age precision
---

## When to invoke
When given one or more text passages from a user and asked to analyze
intelligence, verbal fluency, IQ, mental age, or education level.

## Tool call sequence
1. detect_language(text) → { lang, confidence }
2. preprocess_text(text, lang) → { tokens, sentences, word_count }
3. analyze_lexical(tokens, sentences, lang) → lexical_result
4. analyze_syntactic(sentences, lang) → syntactic_result
5. analyze_semantic(text, sentences, lang) → semantic_result
6. analyze_readability(text, lang) → readability_result
7. compute_verbal_fluency_score(lexical, syntactic, semantic, readability) → vfs
8. predict_iq(vfs, metrics) → iq_result
9. predict_mental_age(iq_result.point_estimate, age?) → mental_age_result
10. estimate_education_level(metrics) → edu_result
11. generate_report(all_results, format_flag, mode_flag) → report

## Never skip tools
Do not estimate any score from reasoning. If the MCP server is
unavailable, report the error — do not substitute LLM estimation.
```

---

## Dependencies (`requirements.txt`)

```
fastmcp>=0.4.0
spacy>=3.7.0
lexicalrichness>=0.4.2
textstat>=0.7.3
sentence-transformers>=2.6.0
langdetect>=1.0.9
langid>=1.1.6
PySastrawi>=1.2.0
nltk>=3.8.1
```

spaCy models (downloaded separately):
```
python -m spacy download en_core_web_sm
python -m spacy download xx_ent_wiki_sm  # multilingual for ID
```

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Text < 10 words | Reject with error: "Insufficient text for analysis" |
| Text 10–29 words | Proceed with VERY LOW confidence, flag prominently |
| Language confidence < 0.80 | Flag as uncertain, default to EN norms |
| MCP server unavailable | Return structured error, never substitute LLM estimation |
| Missing `--age` flag | Default to population median (30), flag in report |

---

## Testing Strategy

- **Unit tests** per tool: deterministic inputs → known outputs
- **Integration test** (`test_pipeline.py`): full pipeline on 3 sample texts (EN short, EN long, ID essay)
- **Regression test**: VFS must not drift > 2 points between versions for same input
- **Confidence calibration test**: word-count thresholds produce correct confidence labels

---

## Research Basis & Ethical Notes

This tool produces statistical estimates, not clinical diagnoses. Every report
includes a mandatory limitations section. The skill must never be described as
a replacement for standardized IQ testing (WAIS, Raven's, etc.).

Primary research sources:
- Pennebaker, J.W. et al. — LIWC studies on language and personality/intelligence
- Crossley, S.A. et al. — Lexical Sophistication and academic achievement
- Mairesse, F. et al. — Words mark the nerds: computational models of personality
- Covington, M.A. & McFall, J.D. (2010) — Cutting the Gordian knot: VOCD-D
- Gunning, R. (1952) — The Technique of Clear Writing
- Coleman, M. & Liau, T.L. (1975) — A computer readability formula
