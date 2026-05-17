import sys

sys.path.insert(0, "mcp-server")

from tools.mapper import (
    compute_verbal_fluency_score,
    predict_iq,
    predict_mental_age,
    estimate_education_level,
)

MOCK_LEXICAL = {
    "score": 80.0,
    "mattr": 0.78,
    "hapax_ratio": 0.42,
    "lexical_density": 0.53,
    "avg_word_length": 5.8,
    "vocd_d": 61.2,
    "evidence": [],
}
MOCK_SYNTACTIC = {
    "score": 70.0,
    "mean_sentence_length": 18.3,
    "clause_density": 2.1,
    "subordination_index": 0.48,
    "dependency_depth": 6.0,
    "passive_ratio": 0.12,
    "evidence": [],
}
MOCK_SEMANTIC = {
    "score": 72.0,
    "argument_coherence": 0.74,
    "topic_drift_index": 0.21,
    "lexical_chain_density": 0.61,
    "entity_sophistication": "ABSTRACT",
    "evidence": [],
}
MOCK_READABILITY = {
    "score": 65.0,
    "flesch_reading_ease": 52.1,
    "gunning_fog": 12.4,
    "ari": 11.8,
    "coleman_liau": 12.1,
    "evidence": [],
}


def test_vfs_returns_required_keys():
    result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en"
    )
    for key in (
        "vfs",
        "lexical",
        "syntactic",
        "semantic",
        "readability",
        "confidence",
        "confidence_label",
        "lang",
        "text_length_words",
    ):
        assert key in result


def test_vfs_weighted_formula():
    result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en"
    )
    expected = 80 * 0.35 + 70 * 0.25 + 72 * 0.25 + 65 * 0.15
    assert abs(result["vfs"] - expected) < 0.2


def test_confidence_very_low_for_short_text():
    result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 20, "en"
    )
    assert result["confidence_label"] == "VERY LOW"
    assert result["confidence"] == 0.30


def test_confidence_high_for_long_text():
    result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 400, "en"
    )
    assert result["confidence_label"] == "HIGH"


def test_predict_iq_returns_ci_and_classification():
    vfs_result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en"
    )
    result = predict_iq(vfs_result["vfs"], vfs_result["confidence"])
    for key in ("point_estimate", "ci_low", "ci_high", "classification", "percentile"):
        assert key in result


def test_predict_iq_ci_low_less_than_high():
    vfs_result = compute_verbal_fluency_score(
        MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en"
    )
    result = predict_iq(vfs_result["vfs"], vfs_result["confidence"])
    assert result["ci_low"] < result["point_estimate"] < result["ci_high"]


def test_predict_mental_age_with_known_age():
    result = predict_mental_age(120.0, 25)
    assert result["mental_age"] == 30.0
    assert result["age_assumed"] is False


def test_predict_mental_age_assumes_default():
    result = predict_mental_age(100.0)
    assert result["age_assumed"] is True
    assert result["mental_age"] == 30.0


def test_estimate_education_s1_level():
    result = estimate_education_level(12.4, 11.8, 0.53, 2.1)
    assert result["level_code"] in ("S1", "S2", "S3", "D3")
    assert "level_en" in result
    assert "level_id" in result
    assert "confidence" in result
