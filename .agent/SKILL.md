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

10. tool_predict_mental_age(iq_estimate, chronological_age, gate_json)
    Pass iq_estimate=-1 when point_estimate is null; withheld without a passing gate.
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
