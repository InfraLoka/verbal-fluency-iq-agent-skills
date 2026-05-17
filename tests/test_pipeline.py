import sys
sys.path.insert(0, "mcp-server")

from tools.preprocess import detect_language, preprocess_text
from tools.lexical import analyze_lexical
from tools.syntactic import analyze_syntactic
from tools.semantic import analyze_semantic
from tools.readability import analyze_readability
from tools.mapper import compute_verbal_fluency_score, predict_iq, predict_mental_age, estimate_education_level
from tools.reporter import generate_report

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
    lex_r = analyze_lexical(prep_r["tokens"], prep_r["sentences"], lang)
    syn_r = analyze_syntactic(prep_r["sentences"], lang)
    sem_r = analyze_semantic(prep_r["text_clean"], prep_r["sentences"], lang)
    read_r = analyze_readability(prep_r["text_clean"], lang)
    vfs_r = compute_verbal_fluency_score(lex_r, syn_r, sem_r, read_r, prep_r["word_count"], lang)
    iq_r = predict_iq(vfs_r["vfs"], vfs_r["confidence"])
    ma_r = predict_mental_age(iq_r["point_estimate"])
    edu_r = estimate_education_level(read_r["gunning_fog"], read_r["ari"], lex_r["lexical_density"], syn_r["clause_density"])
    report_r = generate_report(lang_r, prep_r, lex_r, syn_r, sem_r, read_r, vfs_r, iq_r, ma_r, edu_r, "--both")
    return {"vfs": vfs_r, "iq": iq_r, "edu": edu_r, "report": report_r}


def test_en_long_pipeline_completes():
    result = _run_pipeline(EN_LONG)
    assert 0 < result["vfs"]["vfs"] <= 100
    assert result["iq"]["point_estimate"] > 0
    assert result["report"]["report"] is not None
    assert result["report"]["json"] is not None


def test_en_long_has_high_confidence():
    result = _run_pipeline(EN_LONG)
    assert result["vfs"]["confidence_label"] in ("HIGH", "MEDIUM")


def test_id_pipeline_detects_indonesian():
    lang_r = detect_language(ID_MEDIUM)
    assert lang_r["lang"] == "id"


def test_id_pipeline_completes():
    result = _run_pipeline(ID_MEDIUM)
    assert result["vfs"]["vfs"] > 0
    assert result["edu"]["level_code"] in ("SD", "SMP", "SMA", "D3", "S1", "S2", "S3")


def test_short_text_very_low_confidence():
    result = _run_pipeline(EN_SHORT)
    assert result["vfs"]["confidence_label"] in ("VERY LOW", "LOW")


def test_report_contains_research_basis():
    result = _run_pipeline(EN_LONG)
    assert "Pennebaker" in result["report"]["report"]


def test_json_output_has_all_top_level_keys():
    result = _run_pipeline(EN_LONG)
    j = result["report"]["json"]
    for key in ("language", "verbal_fluency_score", "iq_prediction", "mental_age", "education_level", "metrics"):
        assert key in j


def test_vfs_does_not_drift_more_than_2_points_on_same_input():
    r1 = _run_pipeline(EN_LONG)
    r2 = _run_pipeline(EN_LONG)
    assert abs(r1["vfs"]["vfs"] - r2["vfs"]["vfs"]) < 2.0
