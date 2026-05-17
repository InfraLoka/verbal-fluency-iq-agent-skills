---
name: verbal-fluency-iq
description: >
  Predict IQ, mental age, and education level from text passages using
  verbal fluency analysis. Supports English and Indonesian. Tool-first:
  all scores are computed by deterministic MCP tools — never estimated
  by reasoning alone.
tools_required:
  - tool_detect_language
  - tool_preprocess_text
  - tool_analyze_lexical
  - tool_analyze_syntactic
  - tool_analyze_semantic
  - tool_analyze_readability
  - tool_compute_verbal_fluency_score
  - tool_predict_iq
  - tool_predict_mental_age
  - tool_estimate_education_level
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
  chronological_age: "integer — improves mental age precision"
---

# Verbal Fluency IQ Skill

## When to invoke

Use this skill when the user provides one or more text passages from a
target person and asks to analyze intelligence, verbal fluency, IQ,
mental age, or education level.

## Hard constraint

NEVER estimate or reason about any score. If the MCP server is
unavailable, return this error:
```
{"error": "verbal-fluency-mcp server not available. Cannot estimate scores without tools."}
```

## Tool call sequence

Call these tools in order. Each output feeds the next.

```
1. tool_detect_language(text)
   → { lang, confidence }

2. tool_preprocess_text(text, lang)
   → { tokens, sentences, word_count, sentence_count, text_clean }

3. tool_analyze_lexical(tokens_json, sentences_json, lang)
   → { mattr, vocd_d, hapax_ratio, lexical_density, avg_word_length, score, evidence }

4. tool_analyze_syntactic(sentences_json, lang)
   → { mean_sentence_length, clause_density, subordination_index, dependency_depth, passive_ratio, score, evidence }

5. tool_analyze_semantic(text_clean, sentences_json, lang)
   → { argument_coherence, topic_drift_index, lexical_chain_density, entity_sophistication, score, evidence }

6. tool_analyze_readability(text_clean, lang)
   → { flesch_reading_ease, gunning_fog, ari, coleman_liau, score, evidence }

7. tool_compute_verbal_fluency_score(lexical_json, syntactic_json, semantic_json, readability_json, word_count, lang)
   → { vfs, lexical, syntactic, semantic, readability, confidence, confidence_label, lang, text_length_words }

8. tool_predict_iq(vfs, confidence)
   → { point_estimate, ci_low, ci_high, classification, percentile }

9. tool_predict_mental_age(iq_estimate, chronological_age)
   → { mental_age, based_on_chronological_age, age_assumed, formula }

10. tool_estimate_education_level(gunning_fog, ari, lexical_density, clause_density)
    → { level_en, level_id, level_code, confidence, confidence_label }

11. tool_generate_report(lang_json, preprocess_json, lexical_json, syntactic_json,
                         semantic_json, readability_json, vfs_json, iq_json,
                         mental_age_json, edu_json, format_flag, chronological_age, verbose_caveats)
    → { json, report }
```

## Passing JSON between tools

Each tool returns a JSON string. Pass it directly as the `*_json` parameter
of the next tool. Do not parse or summarize intermediate results.

## User prompt flags

Parse these from the user's message:
- `--json` / `--report` / `--both` / `--scores-only` / `--verbose-caveats`
- `--age=N` → extract integer N as `chronological_age`

Default: `--both` if no flag specified.

## Minimum text requirement

If `word_count < 10`, return:
```
{"error": "Text too short for analysis. Minimum 10 words required."}
```
