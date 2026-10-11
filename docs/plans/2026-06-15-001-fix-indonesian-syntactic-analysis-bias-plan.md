---
title: Fix Indonesian syntactic-analysis bias in verbal-fluency-iq
type: fix
status: active
date: 2026-06-15
---

# 🐛 Fix Indonesian syntactic-analysis bias in verbal-fluency-iq

## Overview

The verbal-fluency-iq pipeline systematically **under-scores Indonesian text**. The
syntactic analyzer depends on spaCy dependency labels that the Indonesian model
(`xx_ent_wiki_sm`) does not produce, so three of its outputs collapse to zero for
*every* Indonesian input. Because the syntactic component is 25% of the Verbal
Fluency Score (VFS), this drags VFS — and therefore the IQ estimate — downward for
all Indonesian writers. This plan replaces the parser-dependent path with a
principled, parser-free Indonesian heuristic, stops reporting unmeasurable metrics
as `0`, makes multi-document analysis fair, and surfaces honest cross-language
caveats.

## Problem Statement / Motivation

Observed on a private long-form Indonesian corpus:

```
syntactic: {
  mean_sentence_length: (typical),
  clause_density:        1.0,   ← pinned to 1.0
  subordination_index:   0.0,   ← always 0 for id
  dependency_depth:      0.0,   ← always 0 for id
  passive_ratio:         0.0,   ← always 0 for id
  score:                 (very low)   ← drags the composite VFS and mapped IQ down
}
```

Root cause (confirmed by reading `mcp-server/tools/syntactic.py` +
`mcp-server/tools/preprocess.py`):

- `xx_ent_wiki_sm` ships **no dependency parser** — only NER plus an added
  `sentencizer`. Every token therefore has an empty `dep_` and `token.head == token`.
- `SUBORDINATE_DEPS`/`CLAUSE_DEPS` match nothing → `subs = 0`,
  `clauses = max(1, 0) = 1` → `clause_density = 1.0`, `subordination_index = 0.0`.
- `_dep_depth()` returns 0 for every token (no head chain) → `dependency_depth = 0.0`.
- Passive detection looks for `aux:pass`/`nsubjpass` deps that never appear →
  `passive_ratio = 0.0`. (It is also currently **not used** in the score formula.)

This is a measurement defect, not a property of the writing. The same English path
works correctly because `en_core_web_sm` has a real parser.

### Hard constraint (non-negotiable)

This change is a **general, principled measurement fix**. It must NOT be tuned,
hardcoded, or calibrated toward any target IQ value (e.g. a claimed 138.53 for the
subject). `mcp-server/config/iq_norms.json` and the VFS weighting in
`mcp-server/tools/mapper.py` are **out of scope** and must not be edited to chase a
number. Validation is by linguistic correctness and tests; the resulting score for
any subject is reported honestly wherever it lands.

## Proposed Solution

Three independent, backward-compatible changes:

1. **Parser-free Indonesian syntactic analyzer** (`syntactic.py`). When
   `lang == "id"`, compute the components that are *validly measurable without a
   parser* using Indonesian morphology and a curated conjunction lexicon, and stop
   emitting fabricated zeros:
   - `subordination_index` ← count of subordinating conjunctions per sentence.
   - `clause_density` ← `1 + subordinators + clausal coordinators` per sentence.
   - `passive_ratio` ← fraction of sentences with morphological passive
     (`di-`/`ter-` verbal prefixes, optionally with an `oleh` agent).
   - `dependency_depth` ← `None` (honestly "not measurable without a parser"),
     **excluded** from the score with the remaining weights renormalized. We do NOT
     invent a depth number.
   - English path is unchanged (still uses the real parser and all four components).

2. **Document-boundary–aware semantic coherence** (`semantic.py`). Add an optional
   `segment_boundaries` parameter so adjacent-sentence coherence pairs that straddle
   a document boundary are skipped. Multi-file subjects are no longer penalized for
   spurious drift at file seams. Default `None` ⇒ current behavior exactly.

3. **Honest cross-language caveats** (`reporter.py`). When `lang == "id"`, the report
   states that dependency depth was not measured (no Indonesian parser) and that the
   syntactic score derives from clause/subordination/passive morphology, plus the
   existing note that norms are EN-derived.

## Technical Approach

### 3.1 `mcp-server/tools/syntactic.py` — Indonesian heuristic

Add Indonesian lexicons and a language-conditional branch. Keep the English branch
byte-for-byte identical.

```python
# mcp-server/tools/syntactic.py  (new module-level constants)

# Konjungsi subordinatif (subordinating conjunctions)
ID_SUBORDINATORS = {
    "yang", "karena", "sehingga", "ketika", "meskipun", "walaupun", "jika",
    "kalau", "agar", "supaya", "sebab", "sejak", "setelah", "sebelum", "bahwa",
    "hingga", "sampai", "apabila", "bilamana", "seandainya", "andai", "tatkala",
    "seraya", "sambil", "selama", "sementara", "asalkan", "kecuali", "biarpun",
    "sekalipun", "daripada", "seolah", "seakan",
}
# Konjungsi koordinatif yang menghubungkan klausa (clause-joining coordinators)
ID_CLAUSE_COORDINATORS = {
    "dan", "atau", "tetapi", "tapi", "namun", "melainkan", "sedangkan",
    "lalu", "kemudian", "serta", "padahal",
}
# Passive morphology: di-/ter- verbal prefixes. Exclude the locative preposition
# "di " (separate token) and short non-verb tokens.
import re
_ID_PASSIVE_RE = re.compile(r"^(di|ter)[a-z]{4,}$")  # e.g. ditipu, terlihat, dianggap

def _analyze_syntactic_id(sentences):
    lengths, clause_counts, sub_counts = [], [], []
    passive_count = 0
    evidence = []
    for s in sentences:
        toks = [t for t in s["text"].split()]
        words = [w for w in toks if any(c.isalpha() for c in w)]
        lengths.append(len(words))
        lower = [re.sub(r"[^a-z\-]", "", w.lower()) for w in words]

        subs = sum(1 for w in lower if w in ID_SUBORDINATORS)
        coords = sum(1 for w in lower if w in ID_CLAUSE_COORDINATORS)
        sub_counts.append(subs)
        clause_counts.append(1 + subs + coords)

        passives = [w for w in lower if _ID_PASSIVE_RE.match(w)]
        is_passive = bool(passives)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 1:
            triggered.append(f"subordinators:{subs}")
        if is_passive:
            triggered.append(f"passive:{passives[0]}")
        if triggered:
            evidence.append({"sentence_idx": s["idx"], "sentence": s["text"],
                             "triggered_by": triggered})

    n = len(sentences) or 1
    msl = round(sum(lengths) / n, 1)
    clause_density = round(sum(clause_counts) / n, 2)
    sub_index = round(sum(sub_counts) / n, 3)
    passive_ratio = round(passive_count / n, 3)

    # Reuse the SAME component-scoring curves as English so the scales stay comparable.
    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score  = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score  = min(100.0, max(0.0, sub_index / 1.5 * 100))
    # dependency_depth is NOT measurable without a parser → exclude it and
    # renormalize the remaining weights (0.30/0.35/0.25, sum 0.90) to sum to 1.0.
    score = round(msl_score * (0.30/0.90) + cd_score * (0.35/0.90)
                  + si_score * (0.25/0.90), 1)

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": None,        # honest: not measured for id
        "passive_ratio": passive_ratio,
        "score": score,
        "evidence": evidence[:3],
        "note": "Indonesian syntactic metrics computed via rule-based morphology; "
                "dependency depth not measured (no parser for id).",
    }

def analyze_syntactic(sentences, lang):
    if lang == "id":
        return _analyze_syntactic_id(sentences)
    # ... existing English/parser path unchanged ...
```

Design notes / decisions:
- **Why renormalize instead of inventing a depth proxy.** A depth value built from
  sentence length or comma counts would be a fabricated metric that could be tuned to
  inflate scores — exactly what the hard constraint forbids. Excluding it and
  renormalizing is honest and bounded.
- **Why reuse the English scoring curves.** Keeps the `id` and `en` component scales
  comparable; we change *what is measured*, not the score-to-component mapping.
- **`dependency_depth: None`** signals "not measured" rather than "measured as zero".
  Downstream code (`reporter.py`, `mapper`/`estimate_education_level`) must tolerate
  `None` here — see §3.4.

### 3.2 `mcp-server/tools/semantic.py` — boundary-aware coherence

```python
def analyze_semantic(text, sentences, lang, segment_boundaries=None):
    # segment_boundaries: set/list of sentence indices at which a NEW document begins.
    boundaries = set(segment_boundaries or [])
    ...
    for i in range(len(embeddings) - 1):
        if sentences[i + 1]["idx"] in boundaries:
            continue  # skip cross-document transition
        sim = ...
```

If skipping leaves `< 1` valid pair, fall back to the existing "too few sentences"
result. Default `segment_boundaries=None` ⇒ identical to today. Expose the param on
`tool_analyze_semantic` in `server.py` (optional, default `""` → `None`).

### 3.3 `mcp-server/tools/reporter.py` — caveats

In the "Limiting factors" block, when `lang_result['lang'] == 'id'` append:

```
• Indonesian syntactic depth not measured (no dependency parser); syntactic
  score derived from clause density, subordination, and passive morphology.
• IQ/VFS norms are English-derived and only approximately adapted to Indonesian.
```

Also render `dependency_depth` as `N/A (no parser for id)` when it is `None` in the
"DETAILED SYNTACTIC METRICS" block.

### 3.4 Tolerate `dependency_depth = None` downstream

- `reporter.py`: guard the dependency-depth line (done in §3.3).
- `estimate_education_level(...)` is called with `syn["clause_density"]` — unaffected
  (does not read depth). Confirm no other caller reads `dependency_depth`.
- `compute_verbal_fluency_score(...)` reads only component `score` values — unaffected.

### 3.5 Runner / skill plumbing for per-document mode

The private-corpus pipeline runner (and the documented usage in `.agent/SKILL.md`) build
`segment_boundaries` from per-file sentence counts: analyze each file's sentence span,
record the first sentence index of each file, and pass the set to the semantic step.
This is an *optional* analysis mode; single-document callers pass nothing.

## System-Wide Impact

- **Interaction graph:** `analyze_syntactic` → `compute_verbal_fluency_score`
  (reads `.score`) → `predict_iq` → `predict_mental_age`; and
  `analyze_syntactic.clause_density` → `estimate_education_level`. Only the `id`
  branch values change; English path is untouched.
- **Error propagation:** new failure surface is `dependency_depth = None`. Audited
  consumers: reporter (guarded), education estimator (doesn't read it), VFS (doesn't
  read it). No other reader exists.
- **State lifecycle:** pure functions, no persisted state; nothing to orphan.
- **API surface parity:** `analyze_semantic` gains an optional param in both the tool
  function and the MCP wrapper in `server.py`; both must stay in sync.
- **Integration scenarios:** (a) full id corpus end-to-end; (b) en corpus regression
  (must be byte-identical to pre-change); (c) per-document boundaries vs concatenated.

## Acceptance Criteria

- [x] For Indonesian input, `subordination_index > 0` and `clause_density > 1.0`
      whenever subordinating/coordinating conjunctions are present.
- [x] For Indonesian input, `dependency_depth` is `None` (not `0.0`).
- [x] For Indonesian input, `passive_ratio > 0` when `di-`/`ter-` passive verbs occur.
- [x] Complex Indonesian prose scores strictly higher (syntactic) than simple
      Indonesian sentences (parallel to the existing English test).
- [x] English path output is unchanged (regression test passes identically).
- [x] `analyze_semantic(..., segment_boundaries=[...])` excludes straddling pairs;
      default (no arg) is identical to current behavior.
- [x] Report shows `N/A (no parser for id)` for depth and the two id caveats.
- [x] `mcp-server/config/iq_norms.json` and mapper weights are **unchanged**
      (verified by `git diff` — proves no target-fitting).
- [x] Full test suite green; pipeline re-run on a private long-form corpus completes and the
      regenerated report states the new score honestly with the new caveats. — substituted: verified via tests/test_pipeline.py; private corpus re-run deliberately skipped (privacy)

## Test Plan (files)

### tests/test_syntactic.py (add Indonesian cases)
```python
ID_COMPLEX = [
  {"idx":0,"text":"Meskipun data tidak lengkap, tim tetap melanjutkan karena tenggat menuntut tindakan yang cepat."},
  {"idx":1,"text":"Laporan yang telah direvisi oleh peninjau eksternal akhirnya diserahkan sehingga proyek dapat dilanjutkan."},
]
ID_SIMPLE = [
  {"idx":0,"text":"Kucing itu duduk."},
  {"idx":1,"text":"Anjing berlari cepat."},
]
def test_id_complex_higher_than_simple(): assert analyze_syntactic(ID_COMPLEX,"id")["score"] > analyze_syntactic(ID_SIMPLE,"id")["score"]
def test_id_depth_is_none(): assert analyze_syntactic(ID_COMPLEX,"id")["dependency_depth"] is None
def test_id_subordination_detected(): assert analyze_syntactic(ID_COMPLEX,"id")["subordination_index"] > 0
def test_id_passive_detected(): assert analyze_syntactic(ID_COMPLEX,"id")["passive_ratio"] > 0
def test_en_path_unchanged(): ...  # snapshot of COMPLEX_SENTENCES result
```

### tests/test_semantic.py (add boundary case)
```python
def test_segment_boundary_skips_cross_doc_pair():
    # 4 sentences, boundary before idx 2; the 1→2 pair must be excluded
    base = analyze_semantic(text, sents, "id")
    seg  = analyze_semantic(text, sents, "id", segment_boundaries=[2])
    assert seg["argument_coherence"] != base["argument_coherence"]
def test_default_unchanged(): assert analyze_semantic(text,sents,"id") == analyze_semantic(text,sents,"id",None)
```

### tests/test_reporter.py (add id caveats)
```python
def test_id_report_has_depth_na_and_caveats():
    rep = generate_report(...lang id..., syntactic with dependency_depth=None ...)["report"]
    assert "no parser for id" in rep
    assert "English-derived" in rep
```

### Manual / integration
- Re-run the pipeline on a private long-form Indonesian corpus → confirm syntactic score is no longer pinned very low, depth N/A,
  caveats present; regenerate the report honestly (kept out of version control).

## Edge Cases (inline spec-flow analysis)

- **No conjunctions at all** (terse id text) → `subordination_index = 0`,
  `clause_density = 1.0`; score low but not artificially zero — correct.
- **"di" as preposition** ("di rumah") → separate token, fails `^(di|ter)[a-z]{4,}$`
  (space-split, "di" alone is len 2) → not counted as passive. Good.
- **"yang" overcount**: "yang" is extremely frequent; subordination curve caps at
  `sub_index/1.5`, and the score is bounded [0,100]. Acceptable; documented.
- **Mixed EN-in-ID text** (code-switching, as in the corpus): English subordinators
  won't match the id lexicon; they contribute via clause/length only. Acceptable for a
  heuristic; noted as a limitation.
- **Single-sentence document** → semantic already returns the "too few sentences"
  branch; boundary logic must not crash on `< 2` sentences.
- **All pairs straddle boundaries** (every sentence its own doc) → fall back to
  too-few-pairs result rather than dividing by zero.
- **`dependency_depth = None`** reaching any `f"{...}"`/`round()` → audited; only the
  reporter prints it, now guarded.

## Dependencies & Risks

- **No new runtime dependencies.** (A real Indonesian parser via Stanza/UD-GSD is the
  long-term fix but is a heavy dependency and out of scope here; noted as future work.)
- **Risk: heuristic over/under-counts clauses.** Mitigated by reusing bounded scoring
  curves and by tests asserting *ordering* (complex > simple) rather than absolute
  targets — we never assert a specific score, which keeps us honest.
- **Risk: silent English regression.** Mitigated by a snapshot regression test.

## Out of Scope

- Editing `iq_norms.json`, VFS weights, or any calibration toward a target IQ.
- Replacing `xx_ent_wiki_sm` with a full Indonesian dependency parser (future work).
- Toxicity/abuse scoring (tracked separately in prior reports).

## Success Metrics

- Indonesian syntactic component reflects real clause/subordination structure
  (no longer a fixed ~13 from forced zeros).
- English outputs unchanged (zero regression).
- Re-run report on a private long-form corpus is internally consistent and explicitly honest
  about what is and isn't measured — with the final IQ reported as-is, not fitted.

## Sources & References

- Root-cause code: `mcp-server/tools/syntactic.py:10-72`,
  `mcp-server/tools/preprocess.py:13-26` (model has no parser).
- Score formula: `mcp-server/tools/syntactic.py:74-81`.
- Reporter caveats block: `mcp-server/tools/reporter.py:242-268`.
- Evidence of the defect: reports generated from two independent private corpora showed the same pinned-to-zero syntactic metrics (same bug, independently observed).
- Skill contract: `.agent/SKILL.md`.
