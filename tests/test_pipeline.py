# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import evaluate_gates
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

EN_LONG = """
The epistemological foundations of cognitive science have undergone substantial transformation
over the past three decades, driven by advances in computational neuroscience and the emergence
of connectionist models that challenge classical symbolic approaches. Although the data from
early neural network experiments was inconclusive, subsequent research demonstrated that
distributed representations could encode semantic relationships more effectively than
rule-based systems. The implications for natural language processing are profound:
systems that learn statistical regularities from large corpora exhibit emergent properties
that were not explicitly programmed, suggesting that intelligence may be better understood
as a statistical phenomenon than as a logical one. This perspective, while compelling,
requires careful methodological scrutiny to avoid conflating correlation with causation
in the interpretation of model behavior.
"""

ID_MEDIUM = """
Perkembangan teknologi informasi telah mengubah paradigma komunikasi modern secara fundamental.
Implementasi sistem berbasis kecerdasan buatan memerlukan koordinasi multidimensional antara
berbagai pemangku kepentingan yang memiliki perspektif berbeda-beda.
Meskipun tantangan teknis yang dihadapi sangat kompleks, tim pengembang berhasil menyelesaikan
proyek tersebut dengan hasil yang memuaskan karena dedikasi dan kolaborasi yang intensif.
"""

EN_SHORT = "The cat sat on the mat."


def _run_pipeline(text: str) -> dict:
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep_r = preprocess_text(text, lang)
    gate = evaluate_gates(lang_r, prep_r["word_count"], prep_r["terminal_mark_count"])
    lex_r = analyze_lexical(prep_r["tokens"], prep_r["sentences"], lang)
    syn_r = analyze_syntactic(prep_r["sentences"], lang)
    sem_r = analyze_semantic(prep_r["text_clean"], prep_r["sentences"], lang)
    read_r = analyze_readability(prep_r["text_clean"], lang, prep_r["sentences"])
    vfs_r = compute_verbal_fluency_score(
        lex_r, syn_r, sem_r, read_r, prep_r["word_count"], lang
    )
    iq_r = predict_iq(vfs_r["style_index"], lang, gate=gate)
    ma_r = predict_mental_age(iq_r["point_estimate"])
    band_r = estimate_text_complexity_band(
        read_r["gunning_fog"], read_r["ari"], lex_r["lexical_density"], lang, gate=gate
    )
    report_r = generate_report(
        lang_r,
        prep_r,
        lex_r,
        syn_r,
        sem_r,
        read_r,
        vfs_r,
        iq_r,
        ma_r,
        band_r,
        "--both",
        gate=gate,
    )
    return {"vfs": vfs_r, "iq": iq_r, "band": band_r, "report": report_r, "gate": gate}


def test_en_long_pipeline_completes():
    result = _run_pipeline(EN_LONG)
    assert 0 < result["vfs"]["style_index"] <= 100
    assert result["iq"]["style_band"].startswith("Style band")
    assert result["report"]["report"] is not None
    assert result["report"]["json"] is not None


def test_en_long_iq_withheld_by_default_policy():
    result = _run_pipeline(EN_LONG)
    assert result["iq"]["point_estimate"] is None
    assert result["iq"]["withheld_reason"]


def test_id_pipeline_detects_indonesian():
    assert detect_language(ID_MEDIUM)["lang"] == "id"


def test_id_pipeline_completes_without_education_band():
    result = _run_pipeline(ID_MEDIUM)
    assert result["vfs"]["style_index"] > 0
    assert result["band"]["text_complexity_band"] is None


def test_short_text_very_low_length_tier_and_insufficient_text():
    result = _run_pipeline(EN_SHORT)
    assert result["vfs"]["confidence_label"] in ("VERY LOW", "LOW")
    assert result["gate"]["status"] == "INSUFFICIENT_TEXT"
    assert result["vfs"]["semantic"] is None


def test_report_contains_inspired_by_section():
    assert "INSPIRED BY" in _run_pipeline(EN_LONG)["report"]["report"]


def test_json_output_has_all_top_level_keys():
    j = _run_pipeline(EN_LONG)["report"]["json"]
    for key in (
        "status",
        "reasons",
        "provenance",
        "notice",
        "language",
        "style_index",
        "iq_prediction",
        "mental_age",
        "text_complexity",
        "metrics",
    ):
        assert key in j


def test_vfs_does_not_drift_more_than_2_points_on_same_input():
    r1 = _run_pipeline(EN_LONG)
    r2 = _run_pipeline(EN_LONG)
    assert abs(r1["vfs"]["style_index"] - r2["vfs"]["style_index"]) < 2.0
