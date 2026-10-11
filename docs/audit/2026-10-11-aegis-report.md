# AEGIS Audit Report: verbal-fluency-iq-agent-skills

Date: 2026-10-11. Internal document. Source of truth: `docs/audit/2026-10-11-aegis-findings.json` (100 verified findings). All counts below are computed from that file.

## 1. Verdict

**Composite 2.95 / 10: FAIL** (bands: >=8 PASS, 6-8 CONDITIONAL MINOR, 4-6 CONDITIONAL MAJOR, <4 FAIL).

Composite = 0.25 x CTO + 0.30 x CEO + 0.30 x CRO + 0.15 x Hacker = 0.25x4 + 0.30x3 + 0.30x2 + 0.15x3 = 2.95.

| Persona | Weight | Score | Justification |
|---|---|---|---|
| CTO | 25% | 4 | Core pipeline crashes or emits garbage on ordinary input (G-007, G-008, G-012, G-013), MCP layer does not import (G-009), nothing is pinned or versioned (G-010, G-011); fallacy findings on the scoring maths (F-003, F-004, F-007, F-016, F-021, F-022) lower it further. |
| CEO | 30% | 3 | The product claim (an IQ estimate) has no validation harness or reference corpus (N-001, F-002), no explanation or appeal path (N-002, N-003), and the research-basis wording implies validation that does not exist (F-026); the economist and data-detective fallacies (F-001, F-019, F-020) undercut the value proposition itself. |
| CRO | 30% | 2 | Default output carries no use restriction (G-002), no consent (G-003), no audit trail (G-004), no human-in-the-loop gate (G-005), no adverse-impact monitoring (G-016), no retention or DPIA (G-019, G-021), committed example corpora contain identifiable third-party personal data with no consent record and are pinned as CI fixtures (G-006), and wrong-language scoring is silent (F-005, F-006). |
| Hacker | 15% | 3 | Vocabulary stuffing trivially inflates scores (G-001), client-supplied scores are trusted (G-015), analysed text is echoed into agent context unfenced (G-014); attack surface is otherwise small (local tool, no network service). |

The fallacy personas (data-detective, skeptical-economist, pragmatist) hold no weight of their own; their 34 findings feed the CTO (maths and robustness) and CRO/CEO (validity and fairness claims) scores above.

**Is this fit to screen people today?** No. The tool turns a style proxy (sentence length, word rarity, readability) into an "IQ" with a "95% CI" and percentile, without any criterion validation (F-001, F-002), with a confidence interval that is a word-count heuristic and not measurement error (F-003), with a percentile that is non-monotonic (F-004), with one English-derived table applied to Indonesian and to unsupported or code-switched text (F-005, F-006), and with scores that swing about 35 points on punctuation alone (F-007). It is trivially gameable (G-001). Default outputs carry no use restriction, no consent record, no audit trail and no human review step (G-002 to G-005), and it infers education level, which is adjacent to protected attributes (G-017). Its example corpora are real people's writing committed without a consent record (G-006). Using it to decide hiring or admissions would be unreliable, unfair to non-native and non-formal writers, and a regulatory exposure (UU PDP, EU AI Act high-risk). It must not be used for decisions about people until Phase 2 (scoring validity) and Phase 4 (compliance) are complete and the validation protocol has been executed. Even then, scores should be treated as a writing-style indicator, not intelligence.

Other notes for the owner:
- Lint debt: ruff 0.17 reported 23 pre-existing errors (19 auto-fixable) at audit time; auto-fixes applied to two tool modules after the audit brought it to 15, the rest is deferred and tracked by a gap finding.
- LICENSE wording added in Phase 1 should receive owner legal review. This is a note, not a finding.

## 2. Top 13: all P0 findings

Selection rule: all P0 findings, ordered by severity then id (the order of the findings file).
1. **F-001** (P0) Verbal-fluency style score is reified as IQ with no criterion validation
   - Impact on the screened person: A candidate is assigned a numeric IQ and a label such as 'Low' or 'Gifted' by an instrument whose only validity evidence is the author's thresholds; a hiring or admissions reader will treat this as a measurement.
   - Fix: Refuse to emit IQ/classification as a measurement. Output only a labelled 'writing-style index' with explicit 'not an intelligence measure' text in every output format, and gate IQ fields behind a documented validation-study pass flag (default off).
2. **F-002** (P0) No criterion validation: hand-set norms, weights and bands make the IQ mapping circular
   - Impact on the screened person: People are labelled 'Below Average' or 'Low' (IQ 55-89) and assigned an education level by constants nobody can defend, with no accountable basis for appeal.
   - Fix: Write a validation-study protocol (criterion measure, per-language sample sizes, held-out evaluation, reliability, correlation/SEE, PPV/NPV at stated base rates, subgroup error reporting); until results exist, label IQ/percentile/education 'experimental, unvalidated'.
3. **F-003** (P0) '95% CI' is a word-count heuristic, not measurement error, and is narrower than the tool's own stated error
   - Impact on the screened person: A screened candidate is shown a narrow-looking interval (e.g. 103-115) that implies far more certainty than exists; a reviewer can treat a 109 vs 124 difference as meaningful and reject on it.
   - Fix: Stop labelling the value a 95% CI. Until a validation study supplies an SEE, either withhold the interval or report a wide, explicitly 'uncalibrated heuristic range' (>= +/-25) and refuse IQ output for screening use.
4. **F-004** (P0) Percentile is interpolated toward 95 inside every band: non-monotonic and contradicts the IQ
   - Impact on the screened person: Reports shown to hiring/admissions staff carry internally inconsistent figures (average IQ at 95th percentile) that either inflate or mislead; undermines any decision based on them.
   - Fix: Compute percentile from the IQ point with the normal CDF (mean 100, SD 15) and drop the per-band interpolation; cap/mark extremes.
5. **F-005** (P0) One English-derived VFS-to-IQ table is applied to both languages; lang is ignored in scoring
   - Impact on the screened person: Applicants writing in Indonesian are scored on a different effective scale than English writers and can be ranked above or below peers purely because of language, with no disclosure in --json/--scores-only output.
   - Fix: Refuse or loudly flag any cross-language comparison; add per-language norm tables with documented calibration data, and until validated emit a language_norm_unvalidated flag in every output and block rank-ordering across languages.
6. **F-006** (P0) Unsupported languages and code-switched text silently analysed as English
   - Impact on the screened person: A candidate who writes in regional language, or mixes languages naturally, receives an IQ/education estimate that is meaningless but presented as normal output.
   - Fix: Return an explicit unsupported_language / mixed_language status with no IQ, mental age or education output when detection confidence is below a threshold or the language is not en/id; add segment-level language ID for code-switching.
7. **F-007** (P0) Punctuation alone swings IQ ~35 points: unpunctuated chat text collapses into one giant sentence
   - Impact on the screened person: A candidate who writes chat-style without full stops can be scored ~35 IQ points and four education levels higher (or lower) than the same words punctuated.
   - Fix: Detect low-punctuation input (words per terminal mark above a threshold) and refuse sentence-length-based metrics or route to INSUFFICIENT_STRUCTURE; cap per-sentence length used in MSL/readability; document that punctuation density is a confound.
8. **G-001** (P0) Vocabulary stuffing trivially inflates IQ estimate (no adversarial robustness)
   - Impact on the screened person: Screened people who know the metric (or use an LLM to rewrite their text) outrank honest candidates; the decision rewards gaming, not ability.
   - Fix: Add a gaming/anomaly flag (rare-word ratio vs. coherence mismatch, repeated n-gram padding, word-salad detection via low semantic coherence with high lexical score) that downgrades confidence and forces a human-review label; document that the score is not tamper-resistant.
9. **G-002** (P0) Use restriction and caveats are opt-in; default, --json and --scores-only outputs carry none
   - Impact on the screened person: A recruiter receiving the default or slim score output sees an IQ number with no warning and may reject a candidate on it.
   - Fix: Make a prohibited/high-risk-use notice mandatory in every output format (including --scores-only and --json via a 'use_restriction' field) and require an explicit use_context acknowledgement; refuse or degrade when context is hiring/admission.
10. **G-003** (P0) No consent or lawful-basis capture for processing a person's text (UU PDP)
   - Impact on the screened person: A person's writing is scored and profiled without their knowledge or ability to refuse, with no lawful basis on record.
   - Fix: Add docs/compliance/consent-and-lawful-basis.md with consent text (ID/EN), purpose statement and lawful-basis matrix, and require a consent_ref + purpose argument that the pipeline refuses to run without.
11. **G-004** (P0) No audit trail of who scored whom, when, with which model/norm version
   - Impact on the screened person: A rejected applicant cannot obtain or contest the basis of the decision, and the operator cannot prove what was computed.
   - Fix: Emit an append-only audit record (UTC timestamp, operator id, SHA-256 of input, tool versions, norms hash, outputs) for every pipeline run, stored without raw text.
12. **G-005** (P0) No human-in-the-loop gate or automated-decision safeguard
   - Impact on the screened person: A low-band label such as 'Low' can drive an automated rejection with nobody accountable and no route to appeal.
   - Fix: Add a mandatory 'decision_status: advisory_only / requires_human_review' field to all outputs, a reviewer sign-off record, and refuse outputs shaped as pass/fail thresholds.
13. **G-006** (P0) Committed example corpora contain identifiable third-party personal data
   - Impact on the screened person: Named private individuals have their personal writing and derived scores published and retained in the repository history without consent, with no erasure path that does not break CI.
   - Fix: Replace with synthetic or documented-consent text, re-capture golden fixtures, purge from history before any publication, and add a provenance/consent manifest checked by a test.

## 3. Counts

Total 100: fallacy 33, gap 43, feature 24. By severity: P0 13, P1 38, P2 43, P3 6.

Category x severity

| Category | P0 | P1 | P2 | P3 | Total |
|---|---|---|---|---|---|
| fallacy | 7 | 16 | 10 | 0 | 33 |
| gap | 6 | 18 | 15 | 4 | 43 |
| feature | 0 | 4 | 18 | 2 | 24 |

Phase x fixability

| Phase | code | guardrail | process | Total |
|---|---|---|---|---|
| 2 | 17 | 14 | 2 | 33 |
| 3 | 26 | 3 | 0 | 29 |
| 4 | 3 | 5 | 6 | 14 |
| 5 | 18 | 3 | 3 | 24 |

## 4. Full ranked table

Ranked by severity, then id.

| id | severity | title | fixability | phase |
|---|---|---|---|---|
| F-001 | P0 | Verbal-fluency style score is reified as IQ with no criterion validation | guardrail | 2 |
| F-002 | P0 | No criterion validation: hand-set norms, weights and bands make the IQ mapping circular | process | 2 |
| F-003 | P0 | '95% CI' is a word-count heuristic, not measurement error, and is narrower than the tool's own stated error | guardrail | 2 |
| F-004 | P0 | Percentile is interpolated toward 95 inside every band: non-monotonic and contradicts the IQ | code | 2 |
| F-005 | P0 | One English-derived VFS-to-IQ table is applied to both languages; lang is ignored in scoring | guardrail | 2 |
| F-006 | P0 | Unsupported languages and code-switched text silently analysed as English | guardrail | 2 |
| F-007 | P0 | Punctuation alone swings IQ ~35 points: unpunctuated chat text collapses into one giant sentence | code | 2 |
| G-001 | P0 | Vocabulary stuffing trivially inflates IQ estimate (no adversarial robustness) | guardrail | 3 |
| G-002 | P0 | Use restriction and caveats are opt-in; default, --json and --scores-only outputs carry none | guardrail | 4 |
| G-003 | P0 | No consent or lawful-basis capture for processing a person's text (UU PDP) | process | 4 |
| G-004 | P0 | No audit trail of who scored whom, when, with which model/norm version | code | 4 |
| G-005 | P0 | No human-in-the-loop gate or automated-decision safeguard | guardrail | 4 |
| G-006 | P0 | Committed example corpora contain identifiable third-party personal data | process | 4 |
| F-008 | P1 | Genre, register, topic, editing and L1 confounds are uncontrolled: style proxy presented as IQ | guardrail | 2 |
| F-009 | P1 | Short-text scores are still emitted as a point IQ with a narrow-looking CI | guardrail | 2 |
| F-010 | P1 | Indonesian passive detection is a prefix regex with a hand-written denylist; non-passives counted as passive | code | 2 |
| F-011 | P1 | Indonesian clause density counts noun coordination and temporal prepositions as clauses | code | 2 |
| F-012 | P1 | Semantic entity score uses English NER labels but Indonesian model emits PER/ORG/LOC/MISC; 'person' scores lowest | code | 2 |
| F-013 | P1 | Indonesian readability and education use English-calibrated Fog/ARI/Coleman-Liau and Flesch coefficients | guardrail | 2 |
| F-014 | P1 | Education matching uses a brittle AND of three uncalibrated cutoffs with a meaningless confidence | code | 2 |
| F-015 | P1 | 'lexical_density' is a word-length proxy (len>3) that favours Indonesian affixation and is double-counted | code | 2 |
| F-016 | P1 | Unmeasurable components are imputed as numbers (semantic 50.0, lexical 0.0) and blended into VFS at full weight | code | 2 |
| F-017 | P1 | Ratio mental age (IQ/100 x age) is applied to adults with an assumed age of 30 | guardrail | 2 |
| F-018 | P1 | Indonesian syntactic lexicon is formal-register only; colloquial and dialect writing is penalised | code | 2 |
| F-019 | P1 | Education level is inferred from readability and treated as formal schooling attainment | guardrail | 2 |
| F-020 | P1 | No control for AI-assisted writing, translation, dictation or ghostwriting | guardrail | 2 |
| F-021 | P1 | Hapax and MATTR components bias scores by text length and then confidence rewards length | code | 2 |
| F-022 | P1 | Readability and syntactic components re-measure word and sentence length, so nominal VFS weights are misleading | code | 2 |
| F-023 | P1 | English and Indonesian syntactic scores come from different instruments placed on the same curves | code | 2 |
| G-007 | P1 | IQ band lookup falls through to 'Low' for VFS in the gaps between bands (e.g. 84.995); range truncated to 55-145 | code | 3 |
| G-008 | P1 | predict_iq accepts NaN and out-of-range VFS/confidence: percentile 354, negative percentile, inverted CI | code | 3 |
| G-009 | P1 | server.py cannot import under the installed mcp 2.x; fastmcp unpinned and the MCP layer is untested | code | 3 |
| G-010 | P1 | Dependencies and models unpinned (no lockfile, hashes or model revisions): scores drift and supply chain is open | code | 3 |
| G-011 | P1 | Scores carry no model/norm/version provenance for reproducibility or audit | code | 3 |
| G-012 | P1 | Empty or non-alphabetic input crashes the pipeline with KeyError | code | 3 |
| G-013 | P1 | No input size limit: 1M-character text crashes spaCy; large inputs are unbounded in memory/time | code | 3 |
| G-014 | P1 | Analysed text is echoed verbatim into agent context and report with no untrusted-data fencing (prompt injection) | guardrail | 3 |
| G-015 | P1 | Scoring tools trust client-supplied scores: no integrity or provenance (score tampering) | code | 3 |
| G-016 | P1 | No adverse-impact (four-fifths) or subgroup-parity monitoring or tooling | process | 4 |
| G-017 | P1 | Education-level inference is protected-attribute-adjacent with no safeguard | guardrail | 4 |
| G-018 | P1 | No data minimisation: reports quote the subject's own sentences verbatim | code | 4 |
| G-019 | P1 | No retention, deletion or data-subject-rights process | process | 4 |
| G-020 | P1 | Privacy claim is unverified and cross-border transfer is unaddressed | process | 4 |
| G-021 | P1 | No DPIA or EU AI Act high-risk conformity documentation | process | 4 |
| G-022 | P1 | Norm and weight changes have no change-control process | code | 4 |
| G-023 | P1 | Score explanation does not state how the IQ was derived or that it is unvalidated | guardrail | 4 |
| G-024 | P1 | Agent skill is triggered to profile any 'target person' with no purpose or consent check | guardrail | 4 |
| N-001 | P1 | Calibration and validation harness against labelled reference corpus | code | 5 |
| N-002 | P1 | Per-metric explanation of why a score came out as it did | code | 5 |
| N-003 | P1 | Score appeal and contestation path | process | 5 |
| N-004 | P1 | AI-generated text detection flag | guardrail | 5 |
| F-024 | P2 | Misspellings and orthographic variation are scored as lexical sophistication | guardrail | 2 |
| F-025 | P2 | Dominance of surface complexity: the VFS cannot distinguish ornate from competent | guardrail | 2 |
| F-026 | P2 | Research-basis block implies validation the cited works do not provide | guardrail | 2 |
| F-027 | P2 | Population-level norm presented as individual causal claim; mean-age default hides age effect | process | 2 |
| F-028 | P2 | Two-sentence texts get a perfect topic-drift score because the std of one value is zero | code | 2 |
| F-029 | P2 | Indonesian MATTR uses stems while hapax uses surface forms and English uses neither | code | 2 |
| F-030 | P2 | 'Argument coherence' is paraphrase similarity on uncalibrated 0.3-0.9 scaling shared by both languages | code | 2 |
| F-031 | P2 | word_count counts numbers, emoji and symbols, so confidence tiers can be reached by non-words | code | 2 |
| F-032 | P2 | Heuristic confidences are printed as percentages, implying calibrated probabilities | code | 2 |
| F-033 | P2 | Band label strings use clinical psychometric terms ('Gifted / Highly Gifted', 'Low') | guardrail | 2 |
| G-025 | P2 | Malformed JSON args raise uncaught JSONDecodeError across MCP tools (incl. segment_boundaries_json) | code | 3 |
| G-026 | P2 | MCP tools inconsistent on language and input validation (lang not validated outside preprocess) | guardrail | 3 |
| G-027 | P2 | Per-sentence nlp() calls and quadratic-ish loops in syntactic/semantic hurt long-text performance | code | 3 |
| G-028 | P2 | Model loading is unguarded: duplicate spaCy caches, no thread safety, no friendly error when models are missing | code | 3 |
| G-029 | P2 | Non-determinism not controlled for model inference; only langdetect seeded | code | 3 |
| G-030 | P2 | Reporter indexes result dicts directly (KeyError on error/partial results) and 'Generated' date breaks determinism | code | 3 |
| G-031 | P2 | predict_mental_age accepts impossible ages and the tool silently substitutes 30 for 0 or negatives | code | 3 |
| G-032 | P2 | No operational logging: errors, language coercions and model loads are invisible | code | 3 |
| G-033 | P2 | CI: ruff unpinned (0.17 reports lint errors), spaCy models and sentence-transformer weights not cached, ruff ignores scripts/ | code | 3 |
| G-034 | P2 | CI runs Python 3.14 only, with no lock environment and no coverage threshold | code | 3 |
| G-035 | P2 | Golden fixtures only cover three tracked example people and encode current (possibly wrong) outputs | code | 3 |
| G-036 | P2 | Sentence padding / repetition not detected; lexical chain and coherence reward repetition | code | 3 |
| G-037 | P2 | Report text interpolates analysed content unescaped (markdown/terminal injection) | code | 3 |
| G-038 | P2 | Readability evidence uses its own '.'-split indices, so cited sentences do not match preprocess S-numbers | code | 3 |
| G-039 | P2 | CI has no dependency audit, actions pinned by tag not SHA, and default token permissions | code | 3 |
| N-005 | P2 | API authentication for the MCP server | code | 5 |
| N-006 | P2 | Per-caller rate limiting and abuse throttling | code | 5 |
| N-007 | P2 | Batch scoring with per-document results and error isolation | code | 5 |
| N-008 | P2 | Writing-improvement feedback for the screened person | code | 5 |
| N-009 | P2 | Language expansion beyond English and Indonesian | guardrail | 5 |
| N-010 | P2 | Multi-sample aggregation for the same person | code | 5 |
| N-011 | P2 | Structured machine-readable output schema with versioning | code | 5 |
| N-012 | P2 | Confidence interval that reflects real measurement error | code | 5 |
| N-013 | P2 | Reviewer-facing evidence view with sentence citations | code | 5 |
| N-014 | P2 | Accommodation mode for non-native writers and disabilities | guardrail | 5 |
| N-015 | P2 | Single server-side scoring tool that runs the whole pipeline | code | 5 |
| N-016 | P2 | Standardised writing-task elicitation mode | process | 5 |
| N-017 | P2 | Classification probabilities across bands instead of a single label | code | 5 |
| N-018 | P2 | Non-prose content filter (lists, code, tables, quotations) before scoring | code | 5 |
| N-019 | P2 | Offline model bundle for air-gapped installs | process | 5 |
| N-020 | P2 | Candidate-facing plain-language score explanation in Bahasa Indonesia (UU PDP transparency) | code | 5 |
| N-021 | P2 | Split-half stability gate that withholds a score when two halves of the text disagree | code | 5 |
| N-022 | P2 | Data-subject access export of every score, label and evidence quote derived about a person | code | 5 |
| G-040 | P3 | Typing is weak: bare dict returns, no TypedDict/pydantic result models across tool boundaries | code | 3 |
| G-041 | P3 | Config norms/edu files are loaded without schema validation; broken JSON or missing key crashes at first call | code | 3 |
| G-042 | P3 | Exceptions are swallowed silently in lexical analysis and the report mislabels the result | code | 3 |
| G-043 | P3 | Evidence shown to reviewers is the first N triggering sentences, not the most influential | code | 3 |
| N-023 | P3 | Dry-run / what-if comparison between norm versions | code | 5 |
| N-024 | P3 | Sample-size advisor telling the submitter how much more text the refusal gate requires | code | 5 |

## 5. What code cannot fix

These items are `process` or `guardrail` findings. Code can support them, but they remain open until a person or organisation acts. For example, scores remain unvalidated against standardised IQ tests until the validation protocol is executed.

### process (11)

- F-002 (P0, phase 2): No criterion validation: hand-set norms, weights and bands make the IQ mapping circular
- G-003 (P0, phase 4): No consent or lawful-basis capture for processing a person's text (UU PDP)
- G-006 (P0, phase 4): Committed example corpora contain identifiable third-party personal data
- G-016 (P1, phase 4): No adverse-impact (four-fifths) or subgroup-parity monitoring or tooling
- G-019 (P1, phase 4): No retention, deletion or data-subject-rights process
- G-020 (P1, phase 4): Privacy claim is unverified and cross-border transfer is unaddressed
- G-021 (P1, phase 4): No DPIA or EU AI Act high-risk conformity documentation
- N-003 (P1, phase 5): Score appeal and contestation path
- F-027 (P2, phase 2): Population-level norm presented as individual causal claim; mean-age default hides age effect
- N-016 (P2, phase 5): Standardised writing-task elicitation mode
- N-019 (P2, phase 5): Offline model bundle for air-gapped installs

### guardrail (25)

- F-001 (P0, phase 2): Verbal-fluency style score is reified as IQ with no criterion validation
- F-003 (P0, phase 2): '95% CI' is a word-count heuristic, not measurement error, and is narrower than the tool's own stated error
- F-005 (P0, phase 2): One English-derived VFS-to-IQ table is applied to both languages; lang is ignored in scoring
- F-006 (P0, phase 2): Unsupported languages and code-switched text silently analysed as English
- G-001 (P0, phase 3): Vocabulary stuffing trivially inflates IQ estimate (no adversarial robustness)
- G-002 (P0, phase 4): Use restriction and caveats are opt-in; default, --json and --scores-only outputs carry none
- G-005 (P0, phase 4): No human-in-the-loop gate or automated-decision safeguard
- F-008 (P1, phase 2): Genre, register, topic, editing and L1 confounds are uncontrolled: style proxy presented as IQ
- F-009 (P1, phase 2): Short-text scores are still emitted as a point IQ with a narrow-looking CI
- F-013 (P1, phase 2): Indonesian readability and education use English-calibrated Fog/ARI/Coleman-Liau and Flesch coefficients
- F-017 (P1, phase 2): Ratio mental age (IQ/100 x age) is applied to adults with an assumed age of 30
- F-019 (P1, phase 2): Education level is inferred from readability and treated as formal schooling attainment
- F-020 (P1, phase 2): No control for AI-assisted writing, translation, dictation or ghostwriting
- G-014 (P1, phase 3): Analysed text is echoed verbatim into agent context and report with no untrusted-data fencing (prompt injection)
- G-017 (P1, phase 4): Education-level inference is protected-attribute-adjacent with no safeguard
- G-023 (P1, phase 4): Score explanation does not state how the IQ was derived or that it is unvalidated
- G-024 (P1, phase 4): Agent skill is triggered to profile any 'target person' with no purpose or consent check
- N-004 (P1, phase 5): AI-generated text detection flag
- F-024 (P2, phase 2): Misspellings and orthographic variation are scored as lexical sophistication
- F-025 (P2, phase 2): Dominance of surface complexity: the VFS cannot distinguish ornate from competent
- F-026 (P2, phase 2): Research-basis block implies validation the cited works do not provide
- F-033 (P2, phase 2): Band label strings use clinical psychometric terms ('Gifted / Highly Gifted', 'Low')
- G-026 (P2, phase 3): MCP tools inconsistent on language and input validation (lang not validated outside preprocess)
- N-009 (P2, phase 5): Language expansion beyond English and Indonesian
- N-014 (P2, phase 5): Accommodation mode for non-native writers and disabilities

## 6. Remediation roadmap

Phases 0 and 1 (baseline, licence, audit) are complete. All 100 findings are currently open.

- Phase 2, scoring validity (33 items): fix the maths and the language handling. Internal dependencies: F-033 -> F-001. Gate for everything else: validation protocol (F-002) feeds N-001 later and is a prerequisite of G-024.
- Phase 3, robustness and security (29 items): input validation, pinning, provenance, adversarial resistance. Internal dependencies: G-034 -> G-010, G-041 -> G-007. Provenance (G-011) is a prerequisite for the Phase 4 audit trail (G-004).
- Phase 4, compliance and governance (14 items): consent, audit trail, human-in-the-loop, DPIA, retention, adverse-impact monitoring, example-corpus consent and provenance (G-006). Dependencies: G-004 -> G-011, G-022 -> G-011, G-023 -> F-002, G-024 -> G-003.
- Phase 5, features and hardening (24 items): validation harness (N-001), explanations, appeals (N-003 depends on G-005), AI-text detection, accommodation mode (N-014). Heaviest cross-phase dependency: 12 edges into earlier phases. `--require-complete` is enabled in CI only at the end of Phase 5.

Next step: brainstorm, spec and plan for Phase 2 from the `phase: 2` findings.
