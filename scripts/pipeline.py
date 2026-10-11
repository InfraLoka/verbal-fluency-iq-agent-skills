# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Deterministic end-to-end scoring used by golden fixtures and audits."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_education_level,
    predict_iq,
)
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic


def run_pipeline(text: str) -> dict:
    lang = detect_language(text)["lang"]
    prep = preprocess_text(text, lang)
    lex = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    syn = analyze_syntactic(prep["sentences"], lang)
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    read = analyze_readability(prep["text_clean"], lang)
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], lang)
    iq = predict_iq(vfs["vfs"], vfs["confidence"])
    edu = estimate_education_level(
        read["gunning_fog"], read["ari"], lex["lexical_density"], syn["clause_density"]
    )
    return {
        "lang": lang,
        "vfs": vfs["vfs"],
        "iq": iq["point_estimate"],
        "ci": [iq["ci_low"], iq["ci_high"]],
        "edu": edu["level_code"],
        "word_count": prep["word_count"],
    }
