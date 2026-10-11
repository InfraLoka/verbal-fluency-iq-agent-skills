# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
from datetime import date

from tools.policy import (
    NO_INDIVIDUAL_DECISION_NOTICE,
    PROVENANCE_CAVEAT,
    STYLE_INDEX_LABEL,
    withheld_reason,
)

LANG_LABELS = {"en": "English", "id": "Indonesian"}
CONSTRUCT_NAME = "lexical-syntactic complexity"
INSPIRED_BY_NOTE = (
    "Inspired by the work below. None of it validates this tool, and this "
    "tool has no individual-level validation."
)


def _bar(score: float | None, width: int = 10) -> str:
    if score is None:
        return ""
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _trunc(text: str, max_len: int = 100) -> str:
    return f'"{text[:max_len]}..."' if len(text) > max_len else f'"{text}"'


def _fmt(value, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value}{suffix}"


def _detection_label(confidence: float) -> str:
    """Ordinal label for the detector-agreement heuristic (never a percent)."""
    if confidence >= 0.95:
        return "HIGH"
    if confidence >= 0.80:
        return "MEDIUM"
    return "LOW"


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
    band_result: dict,
    format_flag: str = "--both",
    age: int | None = None,
    verbose_caveats: bool = False,
    gate: dict | None = None,
    policy: dict | None = None,
) -> dict:
    # Never print caller-supplied IQ or mental age unless the gate genuinely allows it.
    iq_block = withheld_reason(gate, lang_result.get("lang"), policy)
    if iq_block is not None:
        iq_result = {
            **iq_result,
            "point_estimate": None,
            "range_low": None,
            "range_high": None,
            "classification": None,
            "percentile": None,
            "withheld_reason": f"withheld: {iq_block}",
        }
        mental_age_result = {
            **mental_age_result,
            "mental_age": None,
            "withheld_reason": f"withheld: {iq_block}",
        }
    status = gate["status"] if gate else "UNVERIFIED"
    reasons = gate["reasons"] if gate else ["no gate evaluation supplied"]
    provenance = gate["provenance"] if gate else "not attested"
    norm_unvalidated = (
        gate["language_norm_unvalidated"]
        if gate
        else iq_result.get("language_norm_unvalidated", True)
    )
    notice = {
        "construct": CONSTRUCT_NAME,
        "style_index_label": STYLE_INDEX_LABEL,
        "no_individual_decision": NO_INDIVIDUAL_DECISION_NOTICE,
        "provenance_caveat": PROVENANCE_CAVEAT,
    }
    full_json = {
        "status": status,
        "reasons": reasons,
        "provenance": provenance,
        "notice": notice,
        "language": {**lang_result, "language_norm_unvalidated": norm_unvalidated},
        "style_index": vfs_result,
        "iq_prediction": iq_result,
        "mental_age": mental_age_result,
        "text_complexity": band_result,
        "metrics": {
            "lexical": lexical_result,
            "syntactic": syntactic_result,
            "semantic": semantic_result,
            "readability": readability_result,
        },
    }

    iq_range = None
    if iq_result.get("range_low") is not None:
        iq_range = f"{iq_result['range_low']}–{iq_result['range_high']}"

    if format_flag == "--scores-only":
        slim = {
            "status": status,
            "provenance": provenance,
            "style_index_label": STYLE_INDEX_LABEL,
            "style_index": vfs_result["style_index"],
            "style_band": iq_result["style_band"],
            "iq": iq_result["point_estimate"],
            "iq_range": iq_range,
            "iq_range_label": iq_result["range_label"] if iq_range else None,
            "iq_withheld_reason": iq_result.get("withheld_reason"),
            "mental_age": mental_age_result["mental_age"],
            "text_complexity_band": band_result["text_complexity_band"],
            "length_tier": vfs_result["confidence_label"],
            "language_norm_unvalidated": norm_unvalidated,
        }
        return {"json": slim, "report": None}

    if format_flag == "--json":
        return {"json": full_json, "report": None}

    sep = "━" * 50
    thin = "  " + "─" * 46
    L: list[str] = []

    def line(s: str = "") -> None:
        L.append(s)

    lang_name = LANG_LABELS.get(lang_result["lang"], lang_result["lang"])
    line(sep)
    line("  LEXICAL-SYNTACTIC COMPLEXITY REPORT")
    line(f"  Generated: {date.today().isoformat()} | Language: {lang_name}")
    line(f"  Status: {status}")
    line(sep)
    line()
    line("  NOTICE")
    line(f"  {STYLE_INDEX_LABEL}")
    line(f"  {NO_INDIVIDUAL_DECISION_NOTICE}")
    line(f"  Provenance      : {provenance}")
    line(f"  {PROVENANCE_CAVEAT}")
    if status != "OK":
        line("  Withheld or limited because:")
        for reason in reasons:
            line(f"    • {reason}")
    line()

    line("  SUBJECT TEXT")
    line(
        f"  Text input          : {preprocess_result['word_count']} words "
        f"({preprocess_result.get('token_count', preprocess_result['word_count'])} "
        f"tokens), {preprocess_result['sentence_count']} sentences"
    )
    line(f"  Lang detection      : {_detection_label(lang_result['confidence'])}")
    line(f"  Text length tier    : {vfs_result['confidence_label']}")
    if norm_unvalidated:
        line(
            f"  Language norms      : UNVALIDATED for {lang_name}; "
            "never compare or rank across languages"
        )
    line()

    line(thin)
    line(f"  STYLE INDEX ({CONSTRUCT_NAME})")
    line(thin)
    line(f"  Style index     : {_fmt(vfs_result['style_index'])} / 100")
    line(f"  Style band      : {_fmt(iq_result['style_band'])}")
    for key, label in (
        ("lexical", "Lexical    "),
        ("syntactic", "Syntactic  "),
        ("semantic", "Semantic   "),
        ("readability", "Readability"),
    ):
        value = vfs_result[key]
        line(f"  └── {label} : {_fmt(value)} / 100  {_bar(value)}")
    if vfs_result.get("unavailable_components"):
        unavailable = ", ".join(vfs_result["unavailable_components"])
        line(f"  Not measurable (weights renormalised): {unavailable}")
    line()

    line(thin)
    line("  IQ (EXPERIMENTAL, UNVALIDATED)")
    line(thin)
    if iq_result["point_estimate"] is None:
        line(f"  Withheld        : {iq_result['withheld_reason']}")
    else:
        line(f"  Point estimate  : {iq_result['point_estimate']}")
        line(f"  {iq_result['range_label'].capitalize()} : {iq_range}")
        line(f"  Style band      : {iq_result['classification']}")
        line(f"  Percentile      : ~{iq_result['percentile']}th (from IQ, N(100, 15))")
    line()

    line(thin)
    line("  MENTAL AGE")
    line(thin)
    if mental_age_result["mental_age"] is None:
        line(f"  Withheld        : {mental_age_result['withheld_reason']}")
    else:
        line(
            f"  Estimated       : {mental_age_result['mental_age']} years "
            f"(age {mental_age_result['based_on_chronological_age']})"
        )
    line()

    line(thin)
    line("  TEXT COMPLEXITY BAND")
    line(thin)
    if band_result["text_complexity_band"] is None:
        line(f"  Withheld        : {band_result['withheld_reason']}")
    else:
        line(f"  Band            : {band_result['label']}")
        line(f"  Metric agreement: {band_result['consistency']}")
    line(f"  {band_result['note']}")
    line()

    line(thin)
    line("  DETAILED LEXICAL METRICS")
    line(thin)
    line(f"  MATTR (window=50)     : {_fmt(lexical_result.get('mattr'))}")
    line(f"  MTLD                  : {_fmt(lexical_result.get('mtld'))}")
    line(f"  VOCD-D                : {_fmt(lexical_result.get('vocd_d'))}")
    line(f"  Content-word density  : {_fmt(lexical_result.get('lexical_density'))}")
    line(
        f"  Avg word length       : {_fmt(lexical_result.get('avg_word_length'))} "
        "chars (not scored)"
    )
    line(f"  Out-of-dictionary rate: {_fmt(lexical_result.get('oov_rate'))}")
    for reason in lexical_result.get("reliability_reasons", []):
        line(f"  LOW RELIABILITY       : {reason}")
    line()

    line(thin)
    line("  DETAILED SYNTACTIC METRICS")
    line(thin)
    line(f"  Mean sentence length  : {syntactic_result['mean_sentence_length']} words")
    line(f"  Clause density        : {syntactic_result['clause_density']}")
    line(f"  Subordination index   : {syntactic_result['subordination_index']}")
    _dep_depth = syntactic_result["dependency_depth"]
    line(
        "  Dependency tree depth : "
        f"{_dep_depth if _dep_depth is not None else 'N/A (no parser for id)'}"
    )
    line(f"  Passive voice ratio   : {syntactic_result['passive_ratio']}")
    if syntactic_result.get("colloquial_forms_normalised"):
        line(
            "  Colloquial forms      : "
            f"{syntactic_result['colloquial_forms_normalised']} normalised to "
            "standard Indonesian before counting"
        )
    line()

    line(thin)
    line("  DETAILED SEMANTIC METRICS")
    line(thin)
    line(
        "  Adjacent-sentence similarity : "
        f"{_fmt(semantic_result.get('adjacent_sentence_similarity'))}"
    )
    line(
        "  Topic drift index     : "
        f"{_fmt(semantic_result.get('topic_drift_index'))} (low = focused)"
    )
    line(
        f"  Lexical chain density : {_fmt(semantic_result.get('lexical_chain_density'))}"
    )
    labels = ", ".join(semantic_result.get("entity_labels", [])) or "none"
    line(f"  Entity labels         : {labels} (not scored)")
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

    line(f"  [LEXICAL — Score {_fmt(vfs_result['lexical'])}]")
    line(
        f"  Vocabulary diversity (MATTR {_fmt(lexical_result.get('mattr'))}, "
        f"MTLD {_fmt(lexical_result.get('mtld'))}), content-word density "
        f"{_fmt(lexical_result.get('lexical_density'))}."
    )
    for ev in lexical_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SYNTACTIC — Score {_fmt(vfs_result['syntactic'])}]")
    line(
        f"  Clause density {syntactic_result['clause_density']}, "
        f"subordination index {syntactic_result['subordination_index']}."
    )
    for ev in syntactic_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SEMANTIC — Score {_fmt(vfs_result['semantic'])}]")
    line(
        "  Adjacent-sentence similarity "
        f"{_fmt(semantic_result.get('adjacent_sentence_similarity'))}, topic drift "
        f"{_fmt(semantic_result.get('topic_drift_index'))}."
    )
    sents = preprocess_result.get("sentences", [])
    sent_map = {s["idx"]: s["text"] for s in sents}
    for ev in semantic_result.get("evidence", [])[:3]:
        line(
            f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} "
            f"similarity: {ev['similarity']} [{ev['note']}]"
        )
        src = sent_map.get(ev["sentence_idx_from"], "")
        if src:
            line(f"       {_trunc(src, 80)}")
    line()

    line(f"  [READABILITY — Score {_fmt(vfs_result['readability'])}]")
    line(
        f"  Gunning Fog {readability_result['gunning_fog']}, "
        f"ARI {readability_result['ari']}."
    )
    for ev in readability_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(thin)
    line("  LIMITATIONS")
    line(thin)
    line(f"  Text length tier      : {vfs_result['confidence_label']}")
    line("  Limiting factors      :")
    line("    • The index rewards surface complexity (longer words and sentences,")
    line("      rarer words, more subordination), not correctness, relevance or")
    line("      argument quality. Padding with jargon raises it.")
    line("    • Genre, topic, editing and first language move every metric.")
    line("    • Punctuation density is a confound for sentence-length metrics.")
    line("    • Education cannot be inferred from text.")
    line("    • Scores are not comparable across languages.")
    if lang_result["lang"] == "id":
        line("    • Indonesian syntactic depth not measured (no dependency parser);")
        line("      syntactic score derived from clause density, subordination, and")
        line("      passive morphology only")
        line("    • Bands and scaling are English-derived and uncalibrated for")
        line("      Indonesian")

    if verbose_caveats or format_flag == "--verbose-caveats":
        line()
        line("  EXTENDED LIMITATIONS (--verbose-caveats)")
        line("    • This tool produces text statistics, NOT clinical diagnoses.")
        line("    • Text proxies cannot replace standardized ability tests")
        line("      (WAIS-IV, Raven's Progressive Matrices, etc.).")
        line("    • The ratio mental-age model is undefined for adults.")
        line("    • Do not use these outputs for hiring, clinical, or legal decisions.")

    line()
    line(thin)
    line("  INSPIRED BY")
    line(thin)
    line(f"  {INSPIRED_BY_NOTE}")
    line("  Gunning (1952)            — Fog Index")
    line("  Coleman & Liau (1975)     — CL Index")
    line("  McCarthy & Jarvis (2010)  — MTLD")
    line("  Covington & McFall (2010) — MATTR")
    line()
    line(sep)

    report_text = "\n".join(L)

    if format_flag == "--report":
        return {"json": None, "report": report_text}
    return {"json": full_json, "report": report_text}
