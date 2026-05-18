# Aqilah Text Analysis Report

Date: 2026-05-18
Analyst: Project agent (tool-first pipeline)
Input file: example/aqilah/source/1.md

## 1) Executive Summary

The text in example/aqilah/source/1.md was analyzed using the project pipeline.

Primary result:
- Language detected: Indonesian (id)
- Verbal Fluency Score (VFS): 16.3 / 100 (confidence HIGH, 0.95)
- IQ mapping output: 63 (95% CI 57–69), classification "Low"
- Mental age output: 15.8 (assuming chronological age 25)
- Education level output: SD (Primary School), confidence MEDIUM (0.68)

Interpretation at a glance:
- Extremely low lexical richness score (2.7) — primarily a tool artifact from multi-author conversational text with embedded timestamps and metadata tokens.
- Very low syntactic complexity (8.6) — same root cause; the xx_ent_wiki_sm parser produces near-zero dependency depth and subordination for Indonesian.
- Low-to-moderate semantic coherence (25.3) with high topic drift across 199 sentence blocks.
- Moderate readability complexity (45.8) driven by moderate Gunning Fog and ARI scores.

**Critical caveat**: This source file is a multi-author conversation thread, not the writing of a single individual. Attribution of VFS, IQ, or education estimates to any specific person named in the file is methodologically invalid. Results describe the aggregate text, not any individual's cognitive output.

## 2) Method and Reproducibility

Pipeline sequence followed:
1. detect_language (manual: `id`)
2. preprocess_text
3. analyze_lexical
4. analyze_syntactic
5. analyze_semantic
6. analyze_readability
7. compute_verbal_fluency_score
8. predict_iq
9. predict_mental_age
10. estimate_education_level

Runtime environment:
- spaCy models: en_core_web_sm, xx_ent_wiki_sm
- SentenceTransformer: loaded for semantic analysis

## 3) Input Profile

From preprocessing:
- Word count: 2,837
- Sentence count: 199
- Language: id

Text characteristics observed:
- Multi-author conversation thread (WhatsApp messages, forum posts, coordinated announcements).
- Contains timestamps (`[HH:MM pm, DD/MM/YYYY]`) embedded inline — these inflate token count and distort lexical metrics.
- Mixed Indonesian (colloquial/formal), English, and Javanese slang fragments.
- Highly reactive, fragmented discourse: personal attacks, legal threats, coordinated harassment campaigns, and status updates from multiple parties.
- Identifiable author blocks: (a) Aqilah directly, (b) an anonymous organizer coordinating legal action, (c) various commenters.
- Total text volume (2,837 words) is ~6.5× larger than the bimo sample (436 words), but quality signals are weaker due to multi-author noise.

## 4) Metric Results

### 4.1 Lexical

Values:
- MATTR: 0.34
- VOCD-D: 5.3
- Hapax ratio: 0.0
- Lexical density: 0.0
- Avg word length: 1.0
- Lexical score: 2.7

Reading:
- All lexical metrics are severely deflated. Hapax ratio 0.0 and avg word length 1.0 are not plausible for real text — these values indicate the tokenizer is counting punctuation characters, emoji, and timestamp fragments (e.g. `[`, `:`, `1`, `58`) as individual tokens.
- MATTR 0.34 reflects extreme repetition expected in a long multi-author thread reusing the same target names, legal terms, and insults.
- This component score (2.7) should be treated as a tool artifact, not as evidence of lexical poverty in any participant.

### 4.2 Syntactic

Values:
- Mean sentence length: 14.3
- Clause density: 1.0
- Subordination index: 0.0
- Dependency depth: 0.0
- Passive ratio: 0.0
- Syntactic score: 8.6

Reading:
- Zero dependency depth and subordination index is the known limitation of the xx_ent_wiki_sm model on Indonesian text (same finding as bimo sample).
- Clause density of 1.0 reflects minimum baseline (no multi-clause sentences detected).
- Mean sentence length of 14.3 tokens is lower than bimo (20.8), consistent with more fragmented conversational style and shorter individual message blocks.
- This score is systematically deflated for Indonesian by the parser — the same bias noted in bimo.

### 4.3 Semantic

Values:
- Argument coherence: 0.287
- Topic drift index: 0.158
- Lexical chain density: 0.237
- Entity sophistication: ABSTRACT
- Semantic score: 25.3

Reading:
- Coherence (0.287) is lower than bimo (0.345), consistent with 199 sentence blocks from multiple authors with abrupt topic changes.
- Topic drift (0.158) is higher than bimo (0.125), confirming more fragmented discourse.
- Lexical chain density (0.237) is higher than bimo (0.075) — threads repeatedly reference the same target names and legal terms, creating surface-level lexical chains despite incoherent argumentation.
- Entity sophistication ABSTRACT is consistent with heavy use of legal terms (LAW/ORG entities: "LBH", "Bareskrim", "PIDANA", "pengadilan").
- Evidence sample shows alternating slight-drift and moderate transitions across adjacent sentences.

### 4.4 Readability

Values:
- Flesch Reading Ease: 27.5
- Gunning Fog: 9.7
- ARI: 9.9
- Coleman-Liau: 10.9
- Readability score: 45.8

Reading:
- Gunning Fog 9.7 and ARI 9.9 correspond to roughly 9th–10th grade reading level in English calibration, but Indonesian colloquial text tends to score lower on these formulae.
- Flesch 27.5 indicates difficult text (lower = harder), consistent with formal-sounding legal vocabulary mixed into informal register.
- Readability score (45.8) is significantly lower than bimo (71.9), suggesting less polysyllabic density and shorter sentence segments overall — expected for short message bursts.
- Three readability evidence triggers were flagged: dense sentences containing polysyllabic words at density 0.33–0.50.

## 5) Composite and Mapping Outputs

### 5.1 VFS Composition

Weighted formula:
- Lexical 35%
- Syntactic 25%
- Semantic 25%
- Readability 15%

Output:
- VFS: 16.3
- Component scores: lexical 2.7, syntactic 8.6, semantic 25.3, readability 45.8
- Confidence: HIGH (0.95), driven by 2,837 word count

Comparison with bimo sample:
| Component     | Bimo  | Aqilah thread |
|---------------|-------|---------------|
| Lexical       | 88.8  | 2.7           |
| Syntactic     | 17.5  | 8.6           |
| Semantic      | 26.0  | 25.3          |
| Readability   | 71.9  | 45.8          |
| **VFS**       | **52.7** | **16.3**   |

The dramatic lexical score drop (88.8 → 2.7) is the dominant driver of the lower VFS and is a tool artifact, not a valid cognitive signal. See Finding A.

### 5.2 IQ Mapping Output

Current mapper output:
- Point estimate: 63
- 95% CI: 57–69
- Classification: Low
- Percentile: 39

Important quality note:
- This estimate is based on a VFS that is dominated by a near-zero lexical score artifact. The real underlying linguistic competence of any individual author in this thread cannot be derived from this figure.
- The same percentile interpolation issue noted in the bimo report (high percentile for low IQ band) does not appear here — percentile 39 for IQ 63 "Low" is more internally consistent.

### 5.3 Mental Age Output

- Mental age: 15.8
- Chronological age assumed: 25
- Formula used: mental_age = (iq / 100) * chronological_age

### 5.4 Education Output

- Level code: SD
- Label EN: Primary School
- Label ID: Sekolah Dasar (SD)
- Confidence: MEDIUM (0.68)

## 6) Content Risk Layer (Non-score Interpretation)

The source text is a coordinated multi-party harassment campaign thread targeting a named individual. Key observations:
- The organizer role (anonymous) is directing mass reporting, media pressure, legal coordination against the target across multiple platforms (Instagram, LinkedIn, Twitter/X).
- Text contains doxxing-adjacent content: references to home address, employer, mother's contact, SPPG employees.
- Heavy use of psychiatric stigma as rhetorical weapon ("gila", "RSJ", "cacat mental", "waham pasal").
- Legal threats are mixed with mockery and explicit coordination to harm reputation.
- The Aqilah-attributed messages (lines 1–18) are substantively different in tone from the bulk of the thread — more measured, requesting to stop contact. The overwhelming majority of the text is from other parties.

This content type is high-risk for:
- Attribution error: VFS scores appear to characterize the anonymous organizer's voice, not Aqilah's.
- Harm amplification: any scoring output applied to "Aqilah" would be misattributed.

## 7) Implementation Quality Findings

### Finding A: Lexical tool tokenization failure on conversational/timestamp text
- File: mcp-server/tools/lexical.py
- Symptom: hapax_ratio 0.0, lexical_density 0.0, avg_word_length 1.0 for 2,837 word input.
- Root cause: tokenizer likely splitting inline timestamps (`[1:58 pm, 04/05/2026]`) into individual character/punctuation tokens, massively inflating token count while suppressing word-level statistics.
- Impact: lexical score collapses to near-zero for any text with embedded metadata. This is the most severe accuracy issue identified.
- Priority: Critical. Preprocessing should strip or normalize metadata/timestamp tokens before lexical analysis.

### Finding B: Indonesian syntactic analyzer underpowered (same as bimo)
- File: mcp-server/tools/syntactic.py
- Symptom: dependency_depth = 0.0, subordination_index = 0.0 for all Indonesian input.
- Already documented in bimo report. Applies equally here.
- Priority: High.

### Finding C: Multi-author source files require attribution segmentation
- Files: pipeline architecture (no specific file)
- Symptom: entire conversation thread analyzed as single-author sample.
- Impact: all per-author cognitive estimates are invalid; aggregate scores conflate voices.
- Priority: High for any use case involving per-person scoring.

## 8) Reliability Assessment for This Specific Input

Overall reliability: Low

Reasons:
- Primary: lexical component (35% weight) is a tool artifact producing near-zero score.
- Secondary: multi-author text makes individual attribution impossible.
- Tertiary: Indonesian syntactic parser limitations persist.
- The HIGH confidence label (0.95) reflects only word count volume, not signal quality. Volume confidence is misleading here.

## 9) Recommended Next Actions

1. **Fix lexical preprocessing**: strip timestamps, usernames, brackets, and metadata tokens before computing lexical metrics. Apply a regex pass in `preprocess_text` to remove `[HH:MM ...]` patterns.
2. **Implement speaker segmentation**: for conversation thread inputs, segment by speaker before analysis, and produce per-speaker VFS where possible.
3. **Carry forward bimo findings**: fix Indonesian syntactic parser (rule-based clauses or Indonesian-specific model) and fix percentile interpolation in mapper.py.
4. **Add input type detection**: flag conversation/thread inputs vs. single-author prose so the pipeline can apply appropriate preprocessing and issue per-author caveats.
5. **Add attribution warning**: when source text contains multiple identifiable speakers, block or clearly flag any IQ/mental-age output to prevent misuse.

## 10) Conclusion

For this sample, the pipeline produces:
- Near-zero lexical score (tool artifact from timestamp tokenization),
- Near-zero syntactic structure (parser limitation, same as bimo),
- Low-moderate semantic coherence (multi-author fragmentation),
- Moderate readability complexity,

resulting in VFS 16.3 and IQ estimate 63 "Low" — neither of which reflects any individual's cognitive ability.

The source text is a multi-party conflict and harassment thread. Its linguistic characteristics are dominated by the anonymous organizer's voice, not Aqilah's. Aqilah's own contribution (lines 1–18) is a brief, coherent, formal apology message. Any scoring purporting to characterize "Aqilah's" intelligence from this file is invalid on both methodological and ethical grounds.

Pipeline improvements targeting the lexical tokenization artifact and multi-author segmentation are required before this tool can produce valid output on conversational or multi-party sources.
