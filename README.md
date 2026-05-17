# Verbal Fluency IQ

Predict IQ, mental age, and education level from text passages using verbal fluency as a psycholinguistic proxy. Supports **English** and **Indonesian**. Works on any text type: essays, social media posts, chat logs, transcripts.

**Tool-first design:** all scores are computed by deterministic MCP tools. The AI orchestrates the pipeline but never estimates scores by reasoning alone.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The 11 MCP Tools](#the-11-mcp-tools)
- [Scoring Formulas](#scoring-formulas)
- [IQ & Education Mapping](#iq--education-mapping)
- [Output Flags](#output-flags)
- [Vendorless `.agent/` Usage](#vendorless-agent-usage)
- [Configuration Reference](#configuration-reference)
- [Sample Report](#sample-report)
- [Limitations & Ethics](#limitations--ethics)
- [Research Basis](#research-basis)

---

## Overview

Verbal fluency — the richness, complexity, and coherence of written language — correlates with cognitive ability measures. This project formalises that relationship into a deterministic pipeline:

```
Raw text
  → Language detection
  → Preprocessing (tokenisation, sentence splitting)
  → Lexical analysis    (vocabulary diversity, density)
  → Syntactic analysis  (clause complexity, dependency depth)
  → Semantic analysis   (coherence, topic drift, entity sophistication)
  → Readability indices (Fog, ARI, Coleman-Liau, Flesch)
  → Verbal Fluency Score (VFS, 0–100)
  → IQ point estimate + 95% CI
  → Mental age
  → Education level
  → Structured report with sentence-level citation evidence
```

---

## Architecture

### Component Map

```
verbal-fluency-iq/
├── mcp-server/
│   ├── server.py              ← FastMCP entry point (11 @mcp.tool() handlers)
│   ├── tools/
│   │   ├── preprocess.py      ← Language detection + tokenisation
│   │   ├── lexical.py         ← MATTR, VOCD-D, hapax ratio, lexical density
│   │   ├── syntactic.py       ← Clause density, subordination, dep depth
│   │   ├── semantic.py        ← Sentence embeddings, coherence, entity types
│   │   ├── readability.py     ← Fog, ARI, Coleman-Liau, Flesch
│   │   ├── mapper.py          ← VFS → IQ / mental age / education mapping
│   │   └── reporter.py        ← Report assembly with citation evidence
│   └── config/
│       ├── iq_norms.json      ← VFS→IQ band table
│       ├── edu_norms.json     ← Readability→education thresholds
│       └── id_syllables.json  ← Indonesian syllable counting rules
├── .agent/
│   ├── SKILL.md               ← Vendorless skill definition (any AI agent)
│   └── tools.json             ← JSON Schema for all 11 tools
├── tests/
│   ├── test_preprocess.py
│   ├── test_lexical.py
│   ├── test_syntactic.py
│   ├── test_semantic.py
│   ├── test_readability.py
│   ├── test_mapper.py
│   ├── test_reporter.py
│   └── test_pipeline.py       ← End-to-end integration tests
└── requirements.txt
```

### Design Principles

**Vendorless:** The `.agent/` folder contains no Claude-specific or OpenAI-specific constructs. `SKILL.md` + `tools.json` work on Claude, GPT-4o, Gemini, or any agent that supports MCP.

**Stateless tools:** Every tool is a pure function. No session state is held on the server. The AI passes JSON strings between tools to chain the pipeline.

**Zero hallucination guarantee:** `SKILL.md` contains a hard constraint: if the MCP server is unavailable, the agent must return an error rather than estimate scores by reasoning.

**Modular:** Each analysis dimension is an independent module. Scores are composed at the VFS layer rather than baked into individual tools.

---

## Installation

Requires Python 3.10+.

```bash
# Clone and enter the project
git clone <repo-url>
cd verbal-fluency-iq

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy models
python -m spacy download en_core_web_sm
python -m spacy download xx_ent_wiki_sm

# Run tests
venv/bin/python -m pytest tests/ -v
```

### Dependencies

| Package | Purpose |
|---|---|
| `fastmcp>=0.4.0` | MCP server framework |
| `spacy>=3.7.0` | Tokenisation, dependency parsing, NER |
| `sentence-transformers>=2.6.0` | Sentence embeddings for semantic analysis |
| `lexicalrichness>=0.4.2` | VOCD-D computation |
| `textstat>=0.7.3` | Readability indices (EN) |
| `langdetect>=1.0.9` | Language detection (primary) |
| `langid>=1.1.6` | Language detection (secondary + confidence) |
| `PySastrawi>=1.2.0` | Indonesian stemmer for MATTR normalisation |
| `scikit-learn>=1.4.0` | Cosine similarity for semantic coherence |
| `numpy>=1.26.0` | Numerical operations |
| `nltk>=3.8.1` | Tokenisation utilities |

---

## Quick Start

### Start the MCP Server

```bash
venv/bin/python mcp-server/server.py
```

The server runs on stdio transport (compatible with Claude Code's MCP integration).

### Configure in Claude Code

Add to `.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "verbal-fluency-mcp": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "/path/to/verbal-fluency-iq"
    }
  }
}
```

### Invoke via Prompt

```
Analyze this text for verbal fluency: "<paste text here>"
```

Add flags to control output:

```
Analyze this text --report --age=25 --verbose-caveats: "<paste text here>"
```

---

## The 11 MCP Tools

All tools communicate via JSON strings. The server serialises every return value to `str` (JSON) and the AI passes these strings directly as arguments to subsequent tools.

---

### Tool 1 — `tool_detect_language`

Detects whether text is English or Indonesian using an ensemble of two libraries.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Raw input text |

**Output:**

```json
{
  "lang": "en",
  "confidence": 0.82
}
```

**Algorithm:**

1. `langdetect.detect(text)` → primary language code
2. `langid.rank(text)` → ranked list with log-probability scores
3. Compute confidence from top-1 vs top-2 log-prob margin via sigmoid:
   ```
   margin = top_score - second_score
   confidence = 1.0 / (1.0 + exp(-margin / 30))
   ```
4. If both libraries agree → apply `+0.05` agreement boost (capped at 0.95)
5. If detected language is neither `en` nor `id` → fallback to `en` with confidence 0.50
6. Empty/whitespace input → `{"lang": "en", "confidence": 0.0}`

---

### Tool 2 — `tool_preprocess_text`

Cleans and tokenises text using spaCy.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Raw input text |
| `lang` | `str` | `"en"` or `"id"` |

**Output:**

```json
{
  "tokens": ["The", "quick", "brown", "fox"],
  "sentences": [{"idx": 0, "text": "The quick brown fox jumps."}],
  "word_count": 4,
  "sentence_count": 1,
  "text_clean": "The quick brown fox jumps."
}
```

**Cleaning steps:**
- Strip URLs (`http://...`, `www...`)
- Strip mentions (`@username`) and hashtags (`#tag`)
- Normalise whitespace

**spaCy models:**
- English: `en_core_web_sm` (full pipeline with dependency parser)
- Indonesian: `xx_ent_wiki_sm` — this model has no sentence boundary component; the tool automatically adds a `sentencizer` pipe if no `parser`, `senter`, or `sentencizer` is present

---

### Tool 3 — `tool_analyze_lexical`

Computes vocabulary diversity and richness metrics.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `tokens_json` | `str` | JSON array of tokens (from Tool 2) |
| `sentences_json` | `str` | JSON array of sentence objects (from Tool 2) |
| `lang` | `str` | `"en"` or `"id"` |

**Output:**

```json
{
  "mattr": 0.847,
  "vocd_d": 82.3,
  "hapax_ratio": 0.612,
  "lexical_density": 0.531,
  "avg_word_length": 5.2,
  "score": 71.4,
  "evidence": [
    {
      "sentence_idx": 2,
      "sentence": "The epistemological framework...",
      "triggered_by": ["hapax:epistemological", "hapax:ontological"]
    }
  ]
}
```

**Metrics:**

| Metric | Description |
|---|---|
| MATTR | Moving Average Type-Token Ratio over window=50 tokens |
| VOCD-D | Length-independent vocabulary richness (requires ≥50 tokens) |
| Hapax ratio | Proportion of unique words appearing exactly once |
| Lexical density | Content words (length > 3) / all alphabetic tokens |
| Avg word length | Mean character count across alphabetic tokens |

**Indonesian:** PySastrawi stemmer is applied to tokens before MATTR computation to normalise morphological variants.

**Score formula:**
```
score = MATTR×0.40 + hapax×0.30 + avg_word_length×0.15 + lexical_density×0.15
```

Each sub-metric is normalised to [0, 100] before weighting.

---

### Tool 4 — `tool_analyze_syntactic`

Analyses grammatical complexity via dependency parsing.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `sentences_json` | `str` | JSON array of sentence objects |
| `lang` | `str` | `"en"` or `"id"` |

**Output:**

```json
{
  "mean_sentence_length": 22.4,
  "clause_density": 2.8,
  "subordination_index": 1.2,
  "dependency_depth": 6.1,
  "passive_ratio": 0.15,
  "score": 68.2,
  "evidence": [
    {
      "sentence_idx": 3,
      "sentence": "Although the committee...",
      "triggered_by": ["subordinate_clauses:3", "dep_depth:8"]
    }
  ]
}
```

**Metrics:**

| Metric | Description |
|---|---|
| Mean sentence length | Average word count per sentence |
| Clause density | Average number of clause-level nodes per sentence |
| Subordination index | Average count of subordinate clauses per sentence |
| Dependency depth | Average max depth of dependency tree per sentence |
| Passive ratio | Proportion of sentences containing passive constructions |

**Subordinate clause detection deps:** `advcl`, `relcl`, `acl`, `csubj`, `ccomp`, `xcomp`

**Passive detection deps:** `nsubjpass`, `auxpass`, `aux:pass`

**Evidence triggers:** ≥2 subordinate clauses, dependency depth ≥6, passive voice.

**Score formula:**
```
score = MSL×0.30 + clause_density×0.35 + subordination×0.25 + dep_depth×0.10
```

---

### Tool 5 — `tool_analyze_semantic`

Measures argument coherence and thematic organisation using sentence embeddings.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Cleaned text (from `text_clean` in Tool 2 output) |
| `sentences_json` | `str` | JSON array of sentence objects |
| `lang` | `str` | `"en"` or `"id"` |

**Output:**

```json
{
  "argument_coherence": 0.714,
  "topic_drift_index": 0.082,
  "lexical_chain_density": 0.341,
  "entity_sophistication": "ABSTRACT",
  "score": 72.8,
  "evidence": [
    {
      "sentence_idx_from": 0,
      "sentence_idx_to": 1,
      "coherence": 0.831,
      "note": "causal chain detected"
    }
  ]
}
```

**Metrics:**

| Metric | Description |
|---|---|
| Argument coherence | Mean cosine similarity between consecutive sentence embeddings |
| Topic drift index | Standard deviation of pairwise coherence values (low = focused) |
| Lexical chain density | Proportion of content words (>4 chars) recurring across multiple sentences |
| Entity sophistication | Highest NER category detected: ABSTRACT > CONCRETE > MINIMAL |

**Embedding model:** `paraphrase-multilingual-MiniLM-L12-v2` (multilingual, handles both EN and ID)

**Entity type classification:**
- ABSTRACT: `LAW`, `ORG`, `NORP`, `EVENT`, `WORK_OF_ART`, `LANGUAGE`
- CONCRETE: `PERSON`, `GPE`, `LOC`, `FAC`, `PRODUCT`

**Coherence note thresholds:** >0.75 = "causal chain detected", <0.50 = "slight drift", else "moderate transition"

**Score formula:**
```
score = coherence×0.45 + (1-drift)×0.25 + chain_density×0.20 + entity_score×0.10
```
where entity scores are: ABSTRACT=80, CONCRETE=50, MINIMAL=20.

Graceful fallback for texts with fewer than 2 sentences (returns `score: 50.0` with explanatory `note` field).

---

### Tool 6 — `tool_analyze_readability`

Computes standard readability indices.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Cleaned text |
| `lang` | `str` | `"en"` or `"id"` |

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

**Indonesian adaptation:** `textstat` syllable counting is inaccurate for Bahasa Indonesia. The tool uses a custom syllable counter that counts vowel-nuclei transitions (`_count_id_syllables`), then applies the standard Flesch formula:
```
flesch_id = 206.835 - 1.015 × avg_sentence_length - 84.6 × avg_syllables_per_word
```
Gunning Fog, ARI, and Coleman-Liau are computed via `textstat` for both languages.

**Evidence trigger:** sentences where polysyllabic word density ≥ 0.30.

**Score formula:**
```
score = fog×0.35 + ari×0.30 + coleman_liau×0.20 + (100-flesch)×0.15
```

---

### Tool 7 — `tool_compute_verbal_fluency_score`

Combines the four dimension scores into a single Verbal Fluency Score.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `lexical_json` | `str` | JSON output from Tool 3 |
| `syntactic_json` | `str` | JSON output from Tool 4 |
| `semantic_json` | `str` | JSON output from Tool 5 |
| `readability_json` | `str` | JSON output from Tool 6 |
| `word_count` | `int` | From Tool 2 |
| `lang` | `str` | `"en"` or `"id"` |

**Output:**

```json
{
  "vfs": 71.2,
  "lexical": 68.4,
  "syntactic": 72.1,
  "semantic": 74.8,
  "readability": 65.7,
  "confidence": 0.82,
  "confidence_label": "HIGH",
  "lang": "en",
  "text_length_words": 312
}
```

**VFS formula:**
```
VFS = lexical×0.35 + syntactic×0.25 + semantic×0.25 + readability×0.15
```

**Confidence tiers:**

| Words | Confidence | Label |
|---|---|---|
| < 30 | 0.30 | VERY LOW |
| 30–99 | 0.55 | LOW |
| 100–299 | 0.70 | MEDIUM |
| ≥ 300 | 0.82–0.95 | HIGH |

For texts ≥300 words: `confidence = 0.82 + min(0.13, (word_count - 300) / 1000 × 0.13)`

---

### Tool 8 — `tool_predict_iq`

Maps VFS to an IQ estimate using the IQ band table.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `vfs` | `float` | Verbal Fluency Score (0–100) |
| `confidence` | `float` | Confidence value from Tool 7 |

**Output:**

```json
{
  "point_estimate": 118,
  "ci_low": 113,
  "ci_high": 123,
  "classification": "Above Average / Superior",
  "percentile": 87
}
```

**Algorithm:**
1. Find the matching VFS band from `iq_norms.json`
2. Linear interpolation within band: `iq = band.iq_min + position × (band.iq_max - band.iq_min)`
3. Confidence interval: `ci_half = round(15 - confidence × 10)`
   - HIGH confidence (0.82) → ±7 points
   - VERY LOW confidence (0.30) → ±12 points
4. Percentile: linear interpolation from `band.percentile_min` to 95

---

### Tool 9 — `tool_predict_mental_age`

Computes mental age from IQ.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `iq_estimate` | `float` | IQ point estimate from Tool 8 |
| `chronological_age` | `int` | Actual age in years; pass `0` to use population default (30) |

**Output:**

```json
{
  "mental_age": 35.4,
  "based_on_chronological_age": 30,
  "age_assumed": true,
  "formula": "mental_age = (iq / 100) * chronological_age"
}
```

**Formula:** `mental_age = (iq / 100) × chronological_age`

The `age_assumed` flag signals when the population default (30) was used. Pass `--age=N` in the user prompt for subject-specific precision.

---

### Tool 10 — `tool_estimate_education_level`

Estimates education level from readability metrics.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `gunning_fog` | `float` | Gunning Fog index |
| `ari` | `float` | Automated Readability Index |
| `lexical_density` | `float` | Lexical density (from Tool 3) |
| `clause_density` | `float` | Clause density (from Tool 4) |

**Output:**

```json
{
  "level_en": "Undergraduate",
  "level_id": "Sarjana (S1/D4)",
  "level_code": "S1",
  "confidence": 0.68,
  "confidence_label": "MEDIUM"
}
```

Levels are matched by scanning `edu_norms.json` from highest to lowest until all three thresholds are met. Confidence reflects how far above the thresholds the metrics fall (see [Configuration Reference](#configuration-reference)).

---

### Tool 11 — `tool_generate_report`

Assembles the final output from all preceding tool results.

**Input:** All 10 preceding JSON result strings, plus:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format_flag` | `str` | `"--both"` | Output format (see [Output Flags](#output-flags)) |
| `chronological_age` | `int` | `0` | Pass-through for mental age display |
| `verbose_caveats` | `bool` | `false` | Append extended limitations block |

**Output:**

```json
{
  "json": { ... },
  "report": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n  VERBAL FLUENCY INTELLIGENCE REPORT\n..."
}
```

Either `json` or `report` may be `null` depending on `format_flag`.

---

## Scoring Formulas

### Verbal Fluency Score

```
VFS = Lexical(0-100) × 0.35
    + Syntactic(0-100) × 0.25
    + Semantic(0-100) × 0.25
    + Readability(0-100) × 0.15
```

### Dimension Sub-scores

Each raw metric is normalised to [0, 100] using min-max scaling before weighting:

**Lexical:**
```
MATTR_score    = clamp((mattr - 0.3) / 0.6 × 100)
hapax_score    = clamp((hapax_ratio - 0.2) / 0.5 × 100)
awl_score      = clamp((avg_word_length - 3.5) / 4.0 × 100)
ld_score       = clamp((lexical_density - 0.3) / 0.4 × 100)

lexical_score  = MATTR×0.40 + hapax×0.30 + awl×0.15 + ld×0.15
```

**Syntactic:**
```
msl_score      = clamp((mean_sentence_length - 8) / 22 × 100)
cd_score       = clamp((clause_density - 1.0) / 2.5 × 100)
si_score       = clamp(subordination_index / 1.5 × 100)
dd_score       = clamp((dep_depth - 2) / 8 × 100)

syntactic_score = MSL×0.30 + CD×0.35 + SI×0.25 + DD×0.10
```

**Semantic:**
```
coh_score      = clamp((coherence - 0.3) / 0.6 × 100)
drift_score    = clamp((1 - drift / 0.3) × 100)
chain_score    = clamp((chain_density - 0.1) / 0.5 × 100)
entity_score   = {ABSTRACT: 80, CONCRETE: 50, MINIMAL: 20}

semantic_score = coh×0.45 + drift×0.25 + chain×0.20 + entity×0.10
```

**Readability:**
```
fog_score      = clamp((fog - 6) / 12 × 100)
ari_score      = clamp((ari - 5) / 11 × 100)
cl_score       = clamp((cl - 5) / 11 × 100)
flesch_score   = clamp(100 - flesch)

readability_score = fog×0.35 + ari×0.30 + cl×0.20 + flesch×0.15
```

`clamp(x) = max(0, min(100, x))`

---

## IQ & Education Mapping

### VFS → IQ Bands

| VFS Range | IQ Range | Classification | Percentile Min |
|---|---|---|---|
| 85–100 | 125–145 | Gifted / Highly Gifted | 95th |
| 70–84.99 | 110–124 | Above Average / Superior | 75th |
| 55–69.99 | 90–109 | Average | 25th |
| 40–54.99 | 75–89 | Below Average | 5th |
| 0–39.99 | 55–74 | Low | 1st |

IQ within each band is computed by linear interpolation: `iq = band_iq_min + position × (band_iq_max - band_iq_min)` where `position = (vfs - band_vfs_min) / (band_vfs_max - band_vfs_min)`.

### Education Level Thresholds

| Code | English Label | Fog Min | ARI Min | Lexical Density Min |
|---|---|---|---|---|
| S3 | Doctoral / Postgrad Research | 17 | 16 | 0.60 |
| S2 | Graduate | 14 | 13 | 0.55 |
| S1 | Undergraduate | 11 | 10 | 0.48 |
| D3 | Vocational / Diploma | 9 | 8 | 0.42 |
| SMA | Senior High School | 7 | 6 | 0.36 |
| SMP | Junior High School | 5 | 4 | 0.30 |
| SD | Primary School | 0 | 0 | 0.00 |

Levels are evaluated from S3 downward; the first level where all three thresholds are met is selected.

**Education confidence:**
- 3 of 3 thresholds exceeded by margin (fog+1, ari+1, density+0.05) → HIGH (0.82)
- 2 of 3 → MEDIUM (0.68)
- 1 or 0 → LOW (0.50)

---

## Output Flags

Pass these flags anywhere in the user's prompt message.

| Flag | Output |
|---|---|
| `--both` (default) | Full JSON scores + structured text report |
| `--json` | Full JSON only (no report) |
| `--report` | Structured text report only (no JSON) |
| `--scores-only` | Slim 6-key JSON: `vfs`, `iq`, `iq_range`, `mental_age`, `education`, `confidence` |
| `--verbose-caveats` | Adds EXTENDED LIMITATIONS block to the report |
| `--age=N` | Sets chronological age to integer N for mental age calculation |

**Example:**
```
Analyze this text --report --age=28 --verbose-caveats: "In contemporary epistemology..."
```

---

## Vendorless `.agent/` Usage

The `.agent/` folder makes this skill portable across AI agents without vendor lock-in.

### Files

**`.agent/SKILL.md`** — Human and machine-readable skill definition:
- YAML front-matter: name, description, required tools, MCP server config, output flags
- Hard constraint block: agent must never estimate scores without tools
- Full 11-step tool call sequence with input/output schemas
- Prompt flag parsing rules
- Minimum text requirement (10 words)

**`.agent/tools.json`** — JSON Schema contracts for all 11 tools, vendor-neutral.

### Using on Different Agents

**Claude Code (native MCP):**
Configure the server in `.claude/mcp_config.json` and reference `.agent/SKILL.md` in the system prompt or CLAUDE.md.

**OpenAI / GPT-4o:**
Convert `.agent/tools.json` to OpenAI function calling format. Use `SKILL.md` as a system prompt section.

**Gemini:**
Use Vertex AI Function Declarations from `.agent/tools.json`. Adapt the MCP server to HTTP/REST if needed.

**Any agent with stdio MCP support:**
Point directly at `mcp-server/server.py` and load `SKILL.md` as skill context.

---

## Configuration Reference

### `mcp-server/config/iq_norms.json`

```json
{
  "bands": [
    {
      "vfs_min": 85, "vfs_max": 100,
      "iq_min": 125, "iq_max": 145,
      "label": "Gifted / Highly Gifted",
      "percentile_min": 95
    }
    // ... 4 more bands
  ],
  "default_chronological_age": 30
}
```

`default_chronological_age` is used when no `--age=N` flag is supplied. Set to the population median (30).

### `mcp-server/config/edu_norms.json`

```json
{
  "levels": [
    {
      "fog_min": 17, "ari_min": 16, "lexical_density_min": 0.60,
      "level_en": "Doctoral / Postgrad Research",
      "level_id": "Doktor / Peneliti Pascasarjana",
      "code": "S3"
    }
    // ... 6 more levels
  ]
}
```

Both `level_en` and `level_id` are included in every output for bilingual display.

### `mcp-server/config/id_syllables.json`

Contains vowel characters and diphthong patterns used by the Indonesian syllable counter. The counter uses vowel-nuclei transitions rather than dictionary lookup for robustness with unknown words.

---

## Sample Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERBAL FLUENCY INTELLIGENCE REPORT
  Generated: 2026-05-18 | Language: English
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SUBJECT PROFILE
  Text input          : 312 words, 18 sentences
  Lang detection conf : 97%
  Analysis confidence : HIGH (82%)

  ──────────────────────────────────────────────
  VERBAL FLUENCY SCORE
  ──────────────────────────────────────────────
  Overall VFS     : 71.2 / 100
  └── Lexical     : 68.4 / 100  ██████░░░░
  └── Syntactic   : 72.1 / 100  ███████░░░
  └── Semantic    : 74.8 / 100  ███████░░░
  └── Readability : 65.7 / 100  ██████░░░░

  ──────────────────────────────────────────────
  IQ PREDICTION
  ──────────────────────────────────────────────
  Point estimate  : 118
  95% CI range    : 111 – 125
  Classification  : Above Average / Superior
  Percentile      : ~87th

  ──────────────────────────────────────────────
  MENTAL AGE
  ──────────────────────────────────────────────
  Estimated       : 35.4 years
  (Chronological age assumed: 30 | pass --age=N for precision)

  ──────────────────────────────────────────────
  EDUCATION LEVEL ESTIMATE
  ──────────────────────────────────────────────
  EN label        : Undergraduate
  ID label        : Sarjana (S1/D4)
  Confidence      : MEDIUM (68%)

  [... metrics and evidence sections ...]

  ──────────────────────────────────────────────
  INTERPRETATION WITH EVIDENCE
  ──────────────────────────────────────────────

  [LEXICAL — Score 68.4]
  Vocabulary diversity (MATTR 0.847), lexical density 0.531.
  Evidence:
    → "The epistemological framework underpinning this analysis..."
       [hapax:epistemological, hapax:underpinning]

  [SEMANTIC — Score 74.8]
  Argument coherence 0.714, topic drift 0.082.
    → S0→S1 coherence: 0.831 [causal chain detected]
       "Modern cognitive science has demonstrated that..."

  ──────────────────────────────────────────────
  CONFIDENCE & LIMITATIONS
  ──────────────────────────────────────────────
  Overall confidence    : HIGH (82%)
  Limiting factors      :
    • Text-based IQ estimation carries ±10–15 pt error margin
    • Mental age assumes population median if age not supplied
    • Education estimate does not account for self-taught learning
    • Cultural/linguistic background affects psycholinguistic norms
    • Short texts (< 100 words) significantly reduce reliability
```

---

## Limitations & Ethics

**Statistical estimates, not clinical diagnoses.** This tool produces probabilistic estimates from text patterns. It cannot replace standardised psychometric assessments (WAIS-IV, Raven's Progressive Matrices, etc.).

**Error margins are real.** The 95% CI is mathematically derived from the confidence tier, not from validation against a reference population. Treat point estimates as approximate.

**Short text penalty.** Texts under 100 words carry LOW confidence. Under 30 words, VOCD-D cannot be computed and most metrics are unstable.

**Cultural and linguistic norms.** Psycholinguistic norms underlying the scoring scales are primarily derived from English-language research. Indonesian adaptation uses approximated thresholds.

**Education assumes formal schooling.** The education level estimator cannot distinguish self-taught expertise from institutional education.

**Do not use for consequential decisions.** These estimates must not be used for hiring, clinical assessment, academic evaluation, or legal proceedings.

**Privacy.** Text submitted to the MCP server is processed locally. No data is sent to external services beyond the embedding model (downloaded locally on first use).

---

## Research Basis

| Author(s) | Contribution |
|---|---|
| Pennebaker et al. | LIWC studies linking language style to personality and intelligence |
| Crossley et al. | Lexical sophistication indices (MATTR, VOCD-D applications) |
| Mairesse et al. | Big Five personality and intelligence prediction from text |
| Gunning (1952) | Gunning Fog Index formula and grade-level calibration |
| Coleman & Liau (1975) | Coleman-Liau Index |
| Covington & McFall (2010) | VOCD-D methodology |

---

## Running Tests

```bash
# Full test suite (60 tests)
venv/bin/python -m pytest tests/ -v

# Single module
venv/bin/python -m pytest tests/test_lexical.py -v

# End-to-end pipeline only
venv/bin/python -m pytest tests/test_pipeline.py -v
```

All tests use real text inputs — no mocks — to catch integration issues early.
