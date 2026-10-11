# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import (
    STYLE_INDEX_LABEL,
    UNSUPPORTED_LANGUAGE,
    evaluate_gates,
    load_policy,
)
from tools.preprocess import SUPPORTED_LANGUAGES, detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def _gate_fields(lang_r: dict, gate: dict) -> dict:
    return {
        "status": gate["status"],
        "statuses": gate["statuses"],
        "reasons": gate["reasons"],
        "lang": lang_r["lang"],
        "lang_confidence": lang_r["confidence"],
        "language_norm_unvalidated": gate["language_norm_unvalidated"],
        "provenance": gate["provenance"],
        "text_type": gate["text_type"],
        "policy_version": gate["policy_version"],
    }


def _not_analysed(lang_r: dict, gate: dict, prep: dict | None) -> dict:
    """Result for text that cannot be analysed (unsupported language, no words)."""
    return {
        **_gate_fields(lang_r, gate),
        "style_index": None,
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": None,
        "components": None,
        "iq": None,
        "percentile": None,
        "classification": None,
        "range": None,
        "range_label": None,
        "withheld_reason": "; ".join(gate["reasons"]),
        "mental_age": None,
        "text_complexity_band": None,
        "text_complexity_consistency": None,
        "word_count": prep["word_count"] if prep else 0,
        "token_count": prep["token_count"] if prep else 0,
        "low_reliability": True,
        "reliability_reasons": [],
        "review_flags": [],
    }


def run_pipeline(
    text: str,
    *,
    provenance: str = "unknown",
    text_type: str = "unknown",
    chronological_age: int | None = None,
    policy: dict | None = None,
) -> dict:
    pol = policy if policy is not None else load_policy()
    lang_r = detect_language(text, policy=pol)
    lang = lang_r["lang"]
    if lang not in SUPPORTED_LANGUAGES:
        gate = evaluate_gates(lang_r, 0, 0, provenance, text_type, pol)
        return _not_analysed(lang_r, gate, None)

    prep = preprocess_text(text, lang)
    gate = evaluate_gates(
        lang_r,
        prep["word_count"],
        prep["terminal_mark_count"],
        provenance,
        text_type,
        pol,
    )
    if gate["status"] == UNSUPPORTED_LANGUAGE or prep["word_count"] == 0:
        return _not_analysed(lang_r, gate, prep)

    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang, policy=pol)
    read = analyze_readability(prep["text_clean"], lang, prep["sentences"])
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["style_index"], lang, gate=gate, policy=pol)
    mental = predict_mental_age(iq["point_estimate"], chronological_age)
    band = estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        lex.get("lexical_density"),
        lang,
        gate=gate,
        policy=pol,
    )
    has_range = iq["range_low"] is not None
    return {
        **_gate_fields(lang_r, gate),
        "style_index": vfs["style_index"],
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": iq["style_band"],
        "components": {
            k: vfs[k] for k in ("lexical", "syntactic", "semantic", "readability")
        },
        "iq": iq["point_estimate"],
        "percentile": iq["percentile"],
        "classification": iq["classification"],
        "range": [iq["range_low"], iq["range_high"]] if has_range else None,
        "range_label": iq["range_label"] if has_range else None,
        "withheld_reason": iq["withheld_reason"],
        "mental_age": mental["mental_age"],
        "text_complexity_band": band["text_complexity_band"],
        "text_complexity_consistency": band["consistency"],
        "word_count": prep["word_count"],
        "token_count": prep["token_count"],
        "low_reliability": bool(lex.get("low_reliability", True))
        or vfs["low_reliability"]
        or bool(prep["injection_phrases"]),
        "reliability_reasons": lex.get("reliability_reasons", [])
        + vfs["review_reasons"],
        "review_flags": vfs["review_flags"]
        + (["possible_prompt_injection"] if prep["injection_phrases"] else []),
    }
