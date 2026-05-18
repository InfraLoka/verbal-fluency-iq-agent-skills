# Fabhian Text Analysis Report

Date: 2026-05-18
Analyst: Project agent (tool-first pipeline)
Input file: example/fabhian/source/1.md

## 1) Executive Summary

The text in example/fabhian/source/1.md was analyzed using the project pipeline specified in .agent/SKILL.md and implemented in mcp-server tools.

Primary result:
- Language detected: Indonesian (confidence 0.71)
- Verbal Fluency Score (VFS): 47.7 / 100 (confidence HIGH, 0.83)
- IQ mapping output: 82 (95% CI 75-89), classification "Below Average"
- Mental age output: 24.6 (assuming chronological age 30)
- Education level output: S1 (Undergraduate), confidence MEDIUM

Interpretation at a glance:
- High lexical richness and lexical density, but lower than the bimo sample.
- Very low syntactic complexity signal (dependency depth and subordination collapse to zero), same tooling limitation as observed in other Indonesian samples with xx_ent_wiki_sm.
- Low semantic coherence with higher topic drift than the bimo sample — abrupt switching between accusation, self-defense, and social commentary.
- Moderate readability complexity (Flesch 33.4 indicates difficult text, but lower grade-level scores than bimo).

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
- Required spaCy models were loaded from cache:
  - en_core_web_sm-3.8.0
  - xx_ent_wiki_sm-3.8.0

## 3) Input Profile

From preprocessing:
- Word count: 340
- Sentence count: 16
- Language: id (confidence 0.71 — lower than typical due to heavy code-switching and colloquial abbreviation)

Text characteristics observed:
- Mixed Indonesian colloquial, English fragments, and social-media shorthand (tp, bbrp, skg, bgt, wkwk, dll).
- Contains list-style evidence blocks and direct-quote-like segments.
- Includes personal attacks, insults, and profanity.
- Discourse is reactional and fragmented: accusations, self-assertion, and dismissal alternate without sustained topic development.
- The author explicitly disclaims being "fabhian aws" and addresses a person named Rahmat directly.

## 4) Metric Results

### 4.1 Lexical

Values:
- MATTR: 0.874
- VOCD-D: 216.6
- Hapax ratio: 0.743
- Lexical density: 0.677
- Avg word length: 4.6
- Lexical score: 86.5

Reading:
- Lexical variety is high (MATTR 0.874, many unique tokens).
- Density is above average at 0.677, reflecting predominantly content-word usage.
- Slightly lower than the bimo sample on all sub-metrics, consistent with shorter word length and more filler/discourse particles.
- Still the dominant positive contributor to VFS.

### 4.2 Syntactic

Values:
- Mean sentence length: 21.2
- Clause density: 1.0
- Subordination index: 0.0
- Dependency depth: 0.0
- Passive ratio: 0.0
- Syntactic score: 18.0

Reading:
- Same flat-structure output as observed in other Indonesian text samples.
- Zero subordination and dependency depth are a known tooling artifact with xx_ent_wiki_sm for Indonesian — this model does not provide reliable dependency parsing for this language.
- Mean sentence length of 21.2 suggests some structural complexity not captured by the parser.

### 4.3 Semantic

Values:
- Argument coherence: 0.274
- Topic drift index: 0.146
- Lexical chain density: 0.092
- Entity sophistication: ABSTRACT
- Semantic score: 20.8

Reading:
- Argument coherence is lower than the bimo sample (0.274 vs 0.345), indicating weaker continuity between adjacent sentences.
- Topic drift index is higher (0.146 vs 0.125), confirming more abrupt topic shifts.
- Lexical chain density is slightly higher (0.092 vs 0.075), meaning some recurring word clusters exist.
- Entity type is ABSTRACT, but this does not offset low transition consistency.

### 4.4 Readability

Values:
- Flesch Reading Ease: 33.4
- Gunning Fog: 12.2
- ARI: 10.8
- Coleman-Liau: 9.3
- Readability score: 51.7

Reading:
- Flesch 33.4 classifies as "Difficult" text (academic-level range), though lower complexity than the bimo sample.
- Grade-level indices (Gunning Fog 12.2, ARI 10.8, Coleman-Liau 9.3) are consistent with high-school to early undergraduate reading level.
- Readability score 51.7 is notably lower than bimo's 71.9, pulling VFS down further.

## 5) Composite and Mapping Outputs

### 5.1 VFS Composition

Weighted formula:
- Lexical 35%
- Syntactic 25%
- Semantic 25%
- Readability 15%

Output:
- VFS 47.7
- Component scores: lexical 86.5, syntactic 18.0, semantic 20.8, readability 51.7
- Confidence: HIGH (0.83), driven by 340 words

Comparison note: VFS 47.7 is lower than the bimo sample's 52.7, primarily due to lower readability and semantic scores. Both samples share the same syntactic floor caused by the Indonesian parser limitation.

### 5.2 IQ Mapping Output

Current mapper output:
- Point estimate: 82
- 95% CI: 75-89
- Classification: Below Average
- Percentile: 51

Important quality note:
- Percentile 51 is inconsistent with IQ 82 and classification "Below Average" (IQ 82 maps to roughly the 12th percentile on a normal distribution).
- This is the same percentile interpolation bug documented in the bimo report (Finding A).

### 5.3 Mental Age Output

- Mental age: 24.6
- Chronological age assumed: 30
- Formula used: mental_age = (iq / 100) * chronological_age

### 5.4 Education Output

- Level code: S1
- Label EN: Undergraduate
- Label ID: Sarjana (S1/D4)
- Confidence: MEDIUM (0.68)

Note: confidence is MEDIUM rather than the HIGH seen in the bimo sample, due to lower grade-level readability indices (ARI 10.8 vs 14.3) pulling against the education-level mapping rules.

## 6) Content Risk Layer (Non-score Interpretation)

The source text contains personal attacks, harassment-like insults, and social-media confrontation directed at a named individual. This has implications:
- High lexical variety does not imply pro-social or constructive discourse.
- Low coherence and high drift are consistent with reactive, emotion-driven writing rather than deliberate argumentation.
- The text explicitly disclaims authorship of a known username and names a target person, raising identity and defamation risk dimensions outside the scope of linguistic scoring.
- Any downstream use should incorporate behavioral/toxicity moderation and privacy-risk dimensions alongside cognitive-linguistic scoring.

## 7) Implementation Quality Findings

### Finding A (inherited): Potential percentile mapping bug
- File: mcp-server/tools/mapper.py (percentile computation in predict_iq)
- Symptom: output shows percentile 51 for IQ 82, which is implausible.
- Impact: user-facing interpretability mismatch; classification says "Below Average" but percentile implies median.
- Priority: High (same as documented in bimo report).

### Finding B (inherited): Indonesian syntactic analyzer underpowered
- File: mcp-server/tools/syntactic.py
- Symptom: dependency_depth and subordination_index collapse to 0.0 on Indonesian text.
- Root cause candidate: xx_ent_wiki_sm lacks robust dependency parser coverage.
- Impact: syntactic score is systematically deflated for Indonesian, biasing VFS downward across all Indonesian samples.
- Priority: High (cross-sample systematic bias).

### Finding C (new): Language detection confidence lower for heavy code-switched text
- File: mcp-server/tools/preprocess.py (detect_language)
- Symptom: confidence 0.71 vs 0.95 in bimo — heavy social-media abbreviation and English insertions confuse the detector.
- Impact: if lang detection falls below threshold and flips to 'en', English spaCy parser would be used, producing different (not necessarily better) scores.
- Priority: Medium (robustness for noisy, code-switched Indonesian input).

## 8) Reliability Assessment for This Specific Input

Overall reliability: Medium-Low

Why not Higher:
- Confidence label is length-based (340 words, above threshold) but quality-based reliability is dragged down by:
  - Heavy social-media abbreviation and code-switching reducing parser and language-detection accuracy.
  - Same Indonesian syntactic parsing limitation as all other samples.
  - Reactional, fragmented discourse produces systematically low semantic coherence regardless of actual cognitive ability.
- The input is not representative of deliberate, structured writing — results should be interpreted as a floor estimate.

## 9) Recommended Next Actions

1. Fix percentile interpolation in predict_iq (same recommendation as bimo report — high priority).
2. Replace or augment Indonesian syntactic parsing strategy with rule-based clause heuristics or an Indonesian-specific parser.
3. Add toxicity/abuse indicator module to separate linguistic complexity from discourse harmfulness.
4. Investigate language detection robustness for heavy code-switching (Indonesian + English + abbreviations).
5. Add calibration samples covering social-media register Indonesian to validate score ranges for this input type.
6. Expose an explicit warning when VFS confidence is labelled HIGH but language detection confidence is below 0.80, to distinguish length-based confidence from quality-based confidence.

## 10) Conclusion

For this sample, the system detects:
- High lexical sophistication (second-strongest component),
- Moderate readability complexity (below the bimo sample),
- Low semantic coherence with above-average topic drift,
- Very low syntactic structure signal (tool-limited for Indonesian),

which combines into a low VFS (47.7) and a low IQ mapping output (82) that is internally inconsistent on percentile — the same known bug observed in the bimo sample.

The sample is better interpreted as reactive, fragmented, and adversarial social-media discourse than as a stable indicator of general cognitive ability. The higher topic drift and lower coherence relative to the bimo sample are consistent with a more confrontational and less sustained argumentative register.
