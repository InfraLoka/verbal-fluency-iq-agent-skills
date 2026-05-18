# Bimo Text Analysis Report

Date: 2026-05-18
Analyst: Project agent (tool-first pipeline)
Input file: bimo/source/1.md

## 1) Executive Summary

The text in bimo/source/1.md was analyzed using the project pipeline specified in .agent/SKILL.md and implemented in mcp-server tools.

Primary result:
- Language detected: Indonesian (confidence 0.95)
- Verbal Fluency Score (VFS): 52.7 / 100 (confidence HIGH, 0.84)
- IQ mapping output: 87 (95% CI 80-94), classification "Below Average"
- Mental age output: 26.1 (assuming chronological age 30)
- Education level output: S1 (Undergraduate), confidence HIGH

Interpretation at a glance:
- Very high lexical richness and lexical density.
- Very low syntactic complexity signal (especially dependency depth and subordination), likely due model limitations on Indonesian parser coverage in current implementation.
- Low semantic coherence / high drift pattern due abrupt topic switching and mixed discourse blocks.
- High readability-complexity indicators from long and polysyllabic sentence segments.

## 2) Method and Reproducibility

Pipeline sequence followed:
1. detect_language
2. preprocess_text
3. analyze_lexical
4. analyze_syntactic
5. analyze_semantic
6. analyze_readability
7. compute_verbal_fluency_score
8. predict_iq
9. predict_mental_age
10. estimate_education_level

All scores were computed by code modules under mcp-server/tools, not estimated by reasoning.

Runtime notes:
- Required spaCy models were installed to execute the pipeline:
  - en_core_web_sm-3.8.0
  - xx_ent_wiki_sm-3.8.0

## 3) Input Profile

From preprocessing:
- Word count: 436
- Sentence count: 21
- Language: id

Text characteristics observed:
- Mixed Indonesian, Javanese colloquial, and English fragments.
- Contains list-style evidence blocks and direct quote-like segments.
- Includes strong insult and sexual/offensive language.
- Topic progression is non-linear (abrupt jumps between accusation, self-assertion, insult, and justification).

## 4) Metric Results

### 4.1 Lexical

Values:
- MATTR: 0.867
- VOCD-D: 282.9
- Hapax ratio: 0.791
- Lexical density: 0.766
- Avg word length: 5.1
- Lexical score: 88.8

Reading:
- Lexical variety is high (many unique tokens, high hapax ratio).
- Density is high, suggesting heavy content-word usage.
- This component is the strongest contributor to VFS.

### 4.2 Syntactic

Values:
- Mean sentence length: 20.8
- Clause density: 1.0
- Subordination index: 0.0
- Dependency depth: 0.0
- Passive ratio: 0.0
- Syntactic score: 17.5

Reading:
- Despite long sentence length, parser-derived structure is mostly flat in outputs.
- Zero depth/subordination is likely a tooling artifact for Indonesian with xx_ent_wiki_sm in syntactic.py, because this model does not provide full dependency parsing quality comparable to English parser models.

### 4.3 Semantic

Values:
- Argument coherence: 0.345
- Topic drift index: 0.125
- Lexical chain density: 0.075
- Entity sophistication: ABSTRACT
- Semantic score: 26.0

Reading:
- Coherence is low across adjacent sentence transitions.
- Topic chain continuity is weak.
- Entity type includes abstract classes, but this does not offset low transition consistency.

### 4.4 Readability

Values:
- Flesch Reading Ease: 12.8
- Gunning Fog: 12.5
- ARI: 14.3
- Coleman-Liau: 13.0
- Readability score: 71.9

Reading:
- Complexity markers are high (long and polysyllabic segments).
- Readability complexity supports higher formal education mapping in current rules.

## 5) Composite and Mapping Outputs

### 5.1 VFS Composition

Weighted formula:
- Lexical 35%
- Syntactic 25%
- Semantic 25%
- Readability 15%

Output:
- VFS 52.7
- Component scores: lexical 88.8, syntactic 17.5, semantic 26.0, readability 71.9
- Confidence: HIGH (0.84), driven by 436 words

### 5.2 IQ Mapping Output

Current mapper output:
- Point estimate: 87
- 95% CI: 80-94
- Classification: Below Average
- Percentile: 81

Important quality note:
- Percentile 81 is inconsistent with label "Below Average" and IQ 87.
- This likely comes from percentile interpolation logic in mapper.py that uses each band's percentile_min up to 95 for all bands.

### 5.3 Mental Age Output

- Mental age: 26.1
- Chronological age assumed: 30
- Formula used: mental_age = (iq / 100) * chronological_age

### 5.4 Education Output

- Level code: S1
- Label EN: Undergraduate
- Label ID: Sarjana (S1/D4)
- Confidence: HIGH (0.82)

## 6) Content Risk Layer (Non-score Interpretation)

The source text contains repeated harassment-like and sexualized insults. This has implications:
- High lexical creativity does not imply pro-social or healthy discourse quality.
- Coherence scores can degrade when discourse is reactional, fragmented, and attack-oriented.
- Any downstream use should include behavioral/toxicity moderation dimensions, not just cognitive-linguistic scoring.

## 7) Implementation Quality Findings

### Finding A: Potential percentile mapping bug
- File: mcp-server/tools/mapper.py (around percentile computation in predict_iq)
- Symptom: output can show high percentile even in low IQ band.
- Impact: user-facing interpretability mismatch.
- Priority: High (report trust issue).

### Finding B: Indonesian syntactic analyzer likely underpowered
- File: mcp-server/tools/syntactic.py
- Symptom: dependency_depth and subordination can collapse to 0 on Indonesian text.
- Root cause candidate: xx_ent_wiki_sm model lacks robust dependency parser behavior for this use case.
- Impact: syntactic score systematically deflated for Indonesian, biasing VFS downward.
- Priority: High (systematic language bias risk).

### Finding C: Readability and education mapping can conflict with IQ output
- Files: mcp-server/tools/readability.py, mcp-server/tools/mapper.py
- Symptom: high readability complexity and high lexical metrics alongside low IQ mapping due weak syntax/semantic signals.
- Impact: contradictory output profile may confuse users.
- Priority: Medium (requires calibration and communication improvements).

## 8) Reliability Assessment for This Specific Input

Overall reliability: Medium

Why not High despite high confidence label:
- The confidence label is mostly length-based, not quality-based.
- Indonesian syntactic parsing limitations likely distort one major score component.
- Input includes noisy style shifts, profanity, and mixed registers.

## 9) Recommended Next Actions

1. Fix percentile interpolation in predict_iq so each band maps to a realistic percentile range.
2. Replace or augment Indonesian syntactic parsing strategy (rule-based clause heuristics or Indonesian-specific parser).
3. Add toxicity/abuse indicator module so reporting separates linguistic complexity from harmfulness.
4. Add calibration tests with known Indonesian benchmark samples to reduce cross-language bias.
5. Expose explicit inconsistency warnings when IQ label, percentile, and education estimate diverge strongly.

## 10) Conclusion

For this sample, the system detects:
- High lexical sophistication,
- High readability complexity,
- Low semantic continuity,
- Very low syntactic structure signal (likely tool-limited for Indonesian),
which combines into a mid-low VFS and a low IQ mapping output that currently appears internally inconsistent on percentile.

The sample is better interpreted as rhetorically varied but fragmented and highly toxic discourse, rather than as a stable indicator of general cognitive ability.
