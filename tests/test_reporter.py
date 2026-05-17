import sys
sys.path.insert(0, "mcp-server")

from tools.reporter import generate_report

LANG = {"lang": "en", "confidence": 0.92}
PREP = {"word_count": 412, "sentence_count": 18, "sentences": [{"idx": 0, "text": "The cat sat on the mat."}], "text_clean": "The cat sat."}
LEXICAL = {"mattr": 0.78, "vocd_d": 61.2, "hapax_ratio": 0.42, "lexical_density": 0.53, "avg_word_length": 5.8, "score": 78.1, "evidence": [{"sentence_idx": 0, "sentence": "The epistemological underpinnings.", "triggered_by": ["hapax:epistemological"]}]}
SYNTACTIC = {"mean_sentence_length": 18.3, "clause_density": 2.1, "subordination_index": 0.48, "dependency_depth": 6.0, "passive_ratio": 0.12, "score": 69.2, "evidence": []}
SEMANTIC = {"argument_coherence": 0.74, "topic_drift_index": 0.21, "lexical_chain_density": 0.61, "entity_sophistication": "ABSTRACT", "score": 71.8, "evidence": [{"sentence_idx_from": 0, "sentence_idx_to": 1, "coherence": 0.81, "note": "causal chain detected"}]}
READABILITY = {"flesch_reading_ease": 52.1, "gunning_fog": 12.4, "ari": 11.8, "coleman_liau": 12.1, "score": 65.0, "evidence": []}
VFS = {"vfs": 73.4, "lexical": 78.1, "syntactic": 69.2, "semantic": 71.8, "readability": 65.0, "confidence": 0.82, "confidence_label": "HIGH", "lang": "en", "text_length_words": 412}
IQ = {"point_estimate": 117, "ci_low": 110, "ci_high": 124, "classification": "Above Average / Superior", "percentile": 79}
MENTAL_AGE = {"mental_age": 35.1, "based_on_chronological_age": 30, "age_assumed": True, "formula": "mental_age = (iq / 100) * chronological_age"}
EDU = {"level_en": "Undergraduate", "level_id": "Sarjana (S1/D4)", "level_code": "S1", "confidence": 0.68, "confidence_label": "MEDIUM"}


def _call(flag="--both", **kwargs):
    return generate_report(LANG, PREP, LEXICAL, SYNTACTIC, SEMANTIC, READABILITY, VFS, IQ, MENTAL_AGE, EDU, format_flag=flag, **kwargs)


def test_json_flag_returns_json_no_report():
    result = _call("--json")
    assert result["json"] is not None
    assert result["report"] is None


def test_report_flag_returns_report_no_json():
    result = _call("--report")
    assert result["report"] is not None
    assert result["json"] is None


def test_both_flag_returns_both():
    result = _call("--both")
    assert result["json"] is not None
    assert result["report"] is not None


def test_scores_only_returns_slim_json():
    result = _call("--scores-only")
    assert "vfs" in result["json"]
    assert "iq" in result["json"]
    assert result["report"] is None


def test_report_contains_iq_value():
    result = _call("--report")
    assert "117" in result["report"]


def test_report_contains_evidence_sentence():
    result = _call("--report")
    assert "epistemological" in result["report"]


def test_verbose_caveats_adds_extended_section():
    result = _call("--report", verbose_caveats=True)
    assert "EXTENDED LIMITATIONS" in result["report"]


def test_report_contains_confidence_label():
    result = _call("--report")
    assert "HIGH" in result["report"]
