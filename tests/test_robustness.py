# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Gaming and padding are flagged for human review (G-001, G-036)."""

import sys

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from pipeline import run_pipeline
from tools.lexical import analyze_lexical
from tools.mapper import compute_verbal_fluency_score
from tools.preprocess import preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.robustness import dedupe_sentences, repeated_ngram_share
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

from tests.helpers import corpus_manifest, corpus_text

# Stacked nominalisations with no content (the G-001 example, extended).
STUFFED = (
    "Notwithstanding epistemological heterogeneity, the ontological ramifications "
    "of hermeneutical paradigms necessitate multidimensional recontextualisation. "
    "Quintessential phenomenological substrates instantiate inexorable dialectical "
    "juxtapositions vis-a-vis transcendental axiological considerations. "
    "Consequently, paradigmatic incommensurability engenders heuristic "
    "indeterminacy throughout poststructuralist historiographical discourse. "
    "Ineluctable teleological presuppositions circumscribe methodological "
    "reflexivity within interdisciplinary epistemic communities."
)


def _analyse(text: str, lang: str = "en") -> dict:
    prep = preprocess_text(text, lang)
    out = {"prep": prep}
    out["lex"] = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    out["syn"] = analyze_syntactic(prep["sentences"], lang)
    out["sem"] = analyze_semantic(prep["text_clean"], prep["sentences"], lang)
    out["read"] = analyze_readability(prep["text_clean"], lang, prep["sentences"])
    out["vfs"] = compute_verbal_fluency_score(
        out["lex"], out["syn"], out["sem"], out["read"], prep["word_count"], lang
    )
    return out


def test_pipeline_flags_vocabulary_stuffing_text_low_confidence():
    result = run_pipeline(STUFFED)
    assert "vocabulary_stuffing" in result["review_flags"]
    assert result["low_reliability"] is True
    assert any(
        r.startswith("vocabulary_stuffing:") for r in result["reliability_reasons"]
    )
    assert result["iq"] is None

    a = _analyse(STUFFED)
    report = generate_report(
        {"lang": "en", "confidence": 0.99},
        a["prep"],
        a["lex"],
        a["syn"],
        a["sem"],
        a["read"],
        a["vfs"],
        {"style_band": None, "point_estimate": None, "withheld_reason": "x"},
        {"mental_age": None, "withheld_reason": "x"},
        {"text_complexity_band": None, "withheld_reason": "x", "note": "n"},
        "--both",
    )
    assert "LOW RELIABILITY: route to human review:" in report["report"]
    assert report["json"]["review_flags"] == ["vocabulary_stuffing"]

    for passage in corpus_manifest():  # ordinary prose is never flagged
        clean = run_pipeline(corpus_text(passage["name"]))
        assert clean["review_flags"] == [], passage["name"]


def test_semantic_duplicate_sentences_do_not_inflate_coherence():
    prep = preprocess_text(corpus_text("en_news_report"), "en")
    base_sents = prep["sentences"][:6]
    base_text = " ".join(s["text"] for s in base_sents)
    padded_text = " ".join(
        f"{s['text']} {s['text']} {s['text'].rstrip('.')} indeed." for s in base_sents
    )
    base, pad = _analyse(base_text), _analyse(padded_text)
    base_lex, base_sem, base_vfs = base["lex"], base["sem"], base["vfs"]
    pad_lex, pad_sem, pad_vfs = pad["lex"], pad["sem"], pad["vfs"]

    assert pad_sem["duplicate_sentences_removed"] == 12
    assert pad_sem["duplicate_sentence_ratio"] == round(12 / 18, 3)
    assert (
        pad_sem["adjacent_sentence_similarity"]
        == base_sem["adjacent_sentence_similarity"]
    )
    assert pad_sem["lexical_chain_density"] == base_sem["lexical_chain_density"]
    assert pad_sem["score"] == base_sem["score"]
    assert base_sem["duplicate_sentences_removed"] == 0

    assert "sentence_repetition" in pad_vfs["review_flags"]
    assert "ngram_padding" in pad_vfs["review_flags"]
    assert pad_vfs["low_reliability"] is True
    assert base_vfs["review_flags"] == [] and base_vfs["low_reliability"] is False
    assert pad_lex["repeated_ngram_share"] > 0.2 >= base_lex["repeated_ngram_share"]

    kept, removed = dedupe_sentences(
        [
            {"idx": 0, "text": "A b c d e."},
            {"idx": 1, "text": "a B c d e!"},
            {"idx": 2, "text": "Something else entirely."},
        ]
    )
    assert removed == 1 and [s["idx"] for s in kept] == [0, 2]
    assert repeated_ngram_share(["a", "b", "c", "a", "b", "c"]) == 0.25
    assert repeated_ngram_share(["a", "b"]) == 0.0
