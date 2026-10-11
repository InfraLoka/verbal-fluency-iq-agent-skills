# Verbal Fluency IQ

Measures the **lexical-syntactic complexity** of a text passage: vocabulary diversity, content-word density, clause structure, adjacent-sentence similarity and readability. Supports **English** and **Indonesian**.

**What it is not.** The tool does not measure verbal fluency (the psychological construct of word-generation rate) and it is not an intelligence test. Its style index rewards complexity, not quality: longer words, longer sentences, rarer words and more subordination all raise it, while correctness, relevance and argument quality are not measured. An experimental IQ mapping exists but is withheld unless a validation study has passed for that language (see `docs/validation/validation-protocol.md`); in the shipped configuration it is withheld for every language.

**Tool-first design:** all scores are computed by deterministic MCP tools. The AI orchestrates the pipeline but never estimates scores by reasoning alone.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The 12 MCP Tools](#the-12-mcp-tools)
- [Scoring Formulas](#scoring-formulas)
- [Style Bands, Experimental IQ & Text Complexity](#style-bands-experimental-iq--text-complexity)
- [Output Flags](#output-flags)
- [Vendorless `.agent/` Usage](#vendorless-agent-usage)
- [Configuration Reference](#configuration-reference)
- [Sample Report](#sample-report)
- [Limitations & Ethics](#limitations--ethics)
- [Inspired By](#inspired-by)

---

## Overview

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

---

## Architecture

### Component Map

```
verbal-fluency-iq/
├── mcp-server/
│   ├── server.py              ← FastMCP entry point (12 @mcp.tool() handlers)
│   ├── tools/
│   │   ├── policy.py          ← Validity gates, statuses, cross-language guard
│   │   ├── preprocess.py      ← Language detection + tokenisation
│   │   ├── lexical.py         ← MATTR, MTLD, content-word density, OOV rate
│   │   ├── syntactic.py       ← Clause density, subordination, dep depth
│   │   ├── semantic.py        ← Adjacent-sentence similarity, drift, chains
│   │   ├── readability.py     ← Fog, ARI, Coleman-Liau, Flesch
│   │   ├── mapper.py          ← Style index, style band, gated IQ, complexity band
│   │   └── reporter.py        ← Report assembly with citation evidence
│   └── config/
│       ├── validation.json    ← Validity policy (gates, per-language flags)
│       ├── iq_norms.json      ← Style band table (uncalibrated)
│       ├── edu_norms.json     ← Text complexity band thresholds
│       ├── semantic_scaling.json ← Per-language similarity scaling
│       └── id_syllables.json  ← Indonesian syllable counting rules
├── .agent/
│   ├── SKILL.md               ← Vendorless skill definition (any AI agent)
│   └── tools.json             ← JSON Schema for all 12 tools
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
| `lexicalrichness>=0.4.2` | MTLD and VOCD-D computation |
| `wordfreq>=3.1.1` | Dictionary filter for misspellings (bundled en/id data) |
| `textstat>=0.7.3` | Readability indices (EN) |
| `langdetect>=1.0.9` | Language detection (agreement check) |
| `langid>=1.1.6` | Language detection (primary) and code-switching detection |
| `PySastrawi>=1.2.0` | Indonesian root dictionary for passive and verb detection |
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
Analyze the lexical-syntactic complexity of this text --provenance=supervised_unaided --text-type=formal_prose: "<paste text here>"
```

Add flags to control output:

```
Analyze this text --report --age=25 --verbose-caveats: "<paste text here>"
```

---

## The 12 MCP Tools

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

---

## Statuses and What They Mean

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

---

## Scoring Formulas

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

---

## Style Bands, Experimental IQ & Text Complexity

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

---

## Output Flags

Pass these flags anywhere in the user's prompt message.

| Flag | Output |
|---|---|
| `--both` (default) | Full JSON scores + structured text report |
| `--json` | Full JSON only (no report) |
| `--report` | Structured text report only (no JSON) |
| `--scores-only` | Slim JSON: `status`, `provenance`, `style_index`, `style_band`, `iq`, `iq_range`, `iq_range_label`, `mental_age`, `text_complexity_band`, `length_tier`, `language_norm_unvalidated` |
| `--verbose-caveats` | Adds EXTENDED LIMITATIONS block to the report |
| `--age=N` | Sets chronological age to integer N; mental age is reported only for ages up to 16 when IQ is emitted |

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
- Full 12-step tool call sequence with input/output schemas
- Prompt flag parsing rules
- Status handling: withheld fields are reported with their reasons

**`.agent/tools.json`** — JSON Schema contracts for all 12 tools, vendor-neutral.

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

---

## Sample Report

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

---

## Limitations & Ethics

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

---

## Inspired By

Inspired by the work below. None of it validates this tool, and this tool has no individual-level validation: no study links its outputs to any individual's ability. The formulas listed are implemented as published; nothing else in this project reproduces a published coefficient.

| Author(s) | What is used here |
|---|---|
| Gunning (1952) | Gunning Fog Index formula |
| Coleman & Liau (1975) | Coleman-Liau Index formula |
| Smith & Senter (1967) | Automated Readability Index formula |
| Flesch (1948) | Flesch Reading Ease formula |
| McCarthy & Jarvis (2010) | MTLD lexical diversity measure |
| Covington & McFall (2010) | MATTR lexical diversity measure |

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

---

## License

Proprietary. Copyright (c) 2026 InfraLoka. All rights reserved. See [LICENSE](LICENSE).
Use, copying, or distribution requires a written agreement with InfraLoka.
Versions previously published under GPL-3.0 remain GPL only for those who received them.
