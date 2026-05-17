from datetime import date
from typing import Optional

LANG_LABELS = {"en": "English", "id": "Indonesian"}


def _bar(score: float, width: int = 10) -> str:
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _trunc(text: str, max_len: int = 100) -> str:
    return f'"{text[:max_len]}..."' if len(text) > max_len else f'"{text}"'


def generate_report(
    lang_result: dict,
    preprocess_result: dict,
    lexical_result: dict,
    syntactic_result: dict,
    semantic_result: dict,
    readability_result: dict,
    vfs_result: dict,
    iq_result: dict,
    mental_age_result: dict,
    edu_result: dict,
    format_flag: str = "--both",
    age: Optional[int] = None,
    verbose_caveats: bool = False,
) -> dict:
    full_json = {
        "language": lang_result,
        "verbal_fluency_score": vfs_result,
        "iq_prediction": iq_result,
        "mental_age": mental_age_result,
        "education_level": edu_result,
        "metrics": {
            "lexical": lexical_result,
            "syntactic": syntactic_result,
            "semantic": semantic_result,
            "readability": readability_result,
        },
    }

    if format_flag == "--scores-only":
        slim = {
            "vfs": vfs_result["vfs"],
            "iq": iq_result["point_estimate"],
            "iq_range": f"{iq_result['ci_low']}–{iq_result['ci_high']}",
            "mental_age": mental_age_result["mental_age"],
            "education": edu_result["level_code"],
            "confidence": vfs_result["confidence_label"],
        }
        return {"json": slim, "report": None}

    if format_flag == "--json":
        return {"json": full_json, "report": None}

    # Build structured report
    sep = "━" * 50
    thin = "  " + "─" * 46
    L = []

    def line(s=""):
        L.append(s)

    line(sep)
    line("  VERBAL FLUENCY INTELLIGENCE REPORT")
    line(
        f"  Generated: {date.today().isoformat()} | Language: {LANG_LABELS.get(lang_result['lang'], lang_result['lang'])}"
    )
    line(sep)
    line()
    line("  SUBJECT PROFILE")
    line(
        f"  Text input          : {preprocess_result['word_count']} words, {preprocess_result['sentence_count']} sentences"
    )
    line(f"  Lang detection conf : {lang_result['confidence']:.0%}")
    line(
        f"  Analysis confidence : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})"
    )
    line()

    line(thin)
    line("  VERBAL FLUENCY SCORE")
    line(thin)
    line(f"  Overall VFS     : {vfs_result['vfs']} / 100")
    line(
        f"  └── Lexical     : {vfs_result['lexical']} / 100  {_bar(vfs_result['lexical'])}"
    )
    line(
        f"  └── Syntactic   : {vfs_result['syntactic']} / 100  {_bar(vfs_result['syntactic'])}"
    )
    line(
        f"  └── Semantic    : {vfs_result['semantic']} / 100  {_bar(vfs_result['semantic'])}"
    )
    line(
        f"  └── Readability : {vfs_result['readability']} / 100  {_bar(vfs_result['readability'])}"
    )
    line()

    line(thin)
    line("  IQ PREDICTION")
    line(thin)
    line(f"  Point estimate  : {iq_result['point_estimate']}")
    line(f"  95% CI range    : {iq_result['ci_low']} – {iq_result['ci_high']}")
    line(f"  Classification  : {iq_result['classification']}")
    line(f"  Percentile      : ~{iq_result['percentile']}th")
    line()

    line(thin)
    line("  MENTAL AGE")
    line(thin)
    line(f"  Estimated       : {mental_age_result['mental_age']} years")
    if mental_age_result["age_assumed"]:
        line(
            f"  (Chronological age assumed: {mental_age_result['based_on_chronological_age']} | pass --age=N for precision)"
        )
    line()

    line(thin)
    line("  EDUCATION LEVEL ESTIMATE")
    line(thin)
    line(f"  EN label        : {edu_result['level_en']}")
    line(f"  ID label        : {edu_result['level_id']}")
    line(
        f"  Confidence      : {edu_result['confidence_label']} ({edu_result['confidence']:.0%})"
    )
    line()

    line(thin)
    line("  DETAILED LEXICAL METRICS")
    line(thin)
    line(f"  MATTR (window=50)     : {lexical_result['mattr']}")
    line(
        f"  VOCD-D                : {lexical_result.get('vocd_d') or 'N/A (< 50 words)'}"
    )
    line(f"  Hapax Legomena ratio  : {lexical_result['hapax_ratio']}")
    line(f"  Lexical density       : {lexical_result['lexical_density']}")
    line(f"  Avg word length       : {lexical_result['avg_word_length']} chars")
    line()

    line(thin)
    line("  DETAILED SYNTACTIC METRICS")
    line(thin)
    line(f"  Mean sentence length  : {syntactic_result['mean_sentence_length']} words")
    line(f"  Clause density        : {syntactic_result['clause_density']}")
    line(f"  Subordination index   : {syntactic_result['subordination_index']}")
    line(f"  Dependency tree depth : {syntactic_result['dependency_depth']}")
    line(f"  Passive voice ratio   : {syntactic_result['passive_ratio']}")
    line()

    line(thin)
    line("  DETAILED SEMANTIC METRICS")
    line(thin)
    line(f"  Argument coherence    : {semantic_result['argument_coherence']}")
    line(
        f"  Topic drift index     : {semantic_result['topic_drift_index']} (low = focused)"
    )
    line(f"  Lexical chain density : {semantic_result['lexical_chain_density']}")
    line(f"  Entity sophistication : {semantic_result['entity_sophistication']}")
    line()

    line(thin)
    line("  READABILITY INDICES")
    line(thin)
    line(f"  Flesch Reading Ease   : {readability_result['flesch_reading_ease']}")
    line(f"  Gunning Fog Index     : {readability_result['gunning_fog']}")
    line(f"  ARI                   : {readability_result['ari']}")
    line(f"  Coleman-Liau Index    : {readability_result['coleman_liau']}")
    line()

    line(thin)
    line("  INTERPRETATION WITH EVIDENCE")
    line(thin)
    line()

    line(f"  [LEXICAL — Score {vfs_result['lexical']}]")
    line(
        f"  Vocabulary diversity (MATTR {lexical_result['mattr']}), lexical density {lexical_result['lexical_density']}."
    )
    for ev in lexical_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SYNTACTIC — Score {vfs_result['syntactic']}]")
    line(
        f"  Clause density {syntactic_result['clause_density']}, subordination index {syntactic_result['subordination_index']}."
    )
    for ev in syntactic_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SEMANTIC — Score {vfs_result['semantic']}]")
    line(
        f"  Argument coherence {semantic_result['argument_coherence']}, topic drift {semantic_result['topic_drift_index']}."
    )
    sents = preprocess_result.get("sentences", [])
    sent_map = {s["idx"]: s["text"] for s in sents}
    for ev in semantic_result.get("evidence", [])[:3]:
        line(
            f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} coherence: {ev['coherence']} [{ev['note']}]"
        )
        src = sent_map.get(ev["sentence_idx_from"], "")
        if src:
            line(f"       {_trunc(src, 80)}")
    line()

    line(f"  [READABILITY — Score {vfs_result['readability']}]")
    line(
        f"  Gunning Fog {readability_result['gunning_fog']}, ARI {readability_result['ari']}."
    )
    for ev in readability_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(
        f"  [IQ PREDICTION — {iq_result['point_estimate']}, CI: {iq_result['ci_low']}–{iq_result['ci_high']}]"
    )
    line(
        f"  Driven by lexical sophistication (score {vfs_result['lexical']}) and syntactic complexity (score {vfs_result['syntactic']})."
    )
    for ev in lexical_result.get("evidence", [])[:3]:
        line(f"    → [S{ev['sentence_idx']}] {_trunc(ev['sentence'], 80)}")
    line()

    line(
        f"  [EDUCATION ESTIMATE — {edu_result['level_code']}/{edu_result['level_en']}]"
    )
    line(
        f"  Fog {readability_result['gunning_fog']} + ARI {readability_result['ari']} + lexical density {lexical_result['lexical_density']}."
    )
    line(f"  Writing style consistent with {edu_result['level_en']} authorship.")
    line()

    line(thin)
    line("  CONFIDENCE & LIMITATIONS")
    line(thin)
    line(
        f"  Overall confidence    : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})"
    )
    line("  Limiting factors      :")
    line("    • Text-based IQ estimation carries ±10–15 pt error margin")
    line("    • Mental age assumes population median if age not supplied")
    line("    • Education estimate does not account for self-taught learning")
    line("    • Cultural/linguistic background affects psycholinguistic norms")
    line("    • Short texts (< 100 words) significantly reduce reliability")

    if verbose_caveats or format_flag == "--verbose-caveats":
        line()
        line("  EXTENDED LIMITATIONS (--verbose-caveats)")
        line("    • This tool produces statistical estimates, NOT clinical diagnoses.")
        line("    • Verbal fluency text proxies cannot replace standardized IQ tests")
        line("      (WAIS-IV, Raven's Progressive Matrices, etc.).")
        line("    • The IQ→mental age formula is a simplified ratio model.")
        line("    • Education estimates assume formal schooling context.")
        line(
            "    • Indonesian norms are approximated from EN research with ID adaptation."
        )
        line(
            "    • Do not use these estimates for hiring, clinical, or legal decisions."
        )

    line()
    line(thin)
    line("  RESEARCH BASIS")
    line(thin)
    line("  Pennebaker et al.   — LIWC personality/intelligence studies")
    line("  Crossley et al.     — Lexical Sophistication indices")
    line("  Mairesse et al.     — Big Five + intelligence from text")
    line("  Gunning (1952)      — Fog Index")
    line("  Coleman & Liau (1975) — CL Index")
    line("  Covington & McFall (2010) — VOCD-D")
    line()
    line(sep)

    report_text = "\n".join(L)

    if format_flag == "--report":
        return {"json": None, "report": report_text}
    return {"json": full_json, "report": report_text}
