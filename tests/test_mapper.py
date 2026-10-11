# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import copy
import json
import math
import pathlib
import re
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    iq_percentile,
    predict_iq,
    predict_mental_age,
)
from tools.norms import (
    NormsConfigError,
    load_edu_norms,
    load_iq_norms,
    validate_edu_norms,
    validate_iq_norms,
)
from tools.policy import (
    CrossLanguageComparisonError,
    evaluate_gates,
    rank_by_style_index,
)

from tests.helpers import ok_gate, validated_policy

MOCK_LEXICAL = {"score": 80.0, "mattr": 0.78, "lexical_density": 0.53, "evidence": []}
MOCK_SYNTACTIC = {"score": 70.0, "clause_density": 2.1, "evidence": []}
MOCK_SEMANTIC = {"score": 72.0, "evidence": []}
MOCK_READABILITY = {"score": 65.0, "gunning_fog": 12.4, "ari": 11.8, "evidence": []}
IQ_NORMS = pathlib.Path("mcp-server/config/iq_norms.json")


def _vfs(word_count=412, **override):
    parts = {
        "lexical": MOCK_LEXICAL,
        "syntactic": MOCK_SYNTACTIC,
        "semantic": MOCK_SEMANTIC,
        "readability": MOCK_READABILITY,
    }
    parts.update(override)
    return compute_verbal_fluency_score(
        parts["lexical"],
        parts["syntactic"],
        parts["semantic"],
        parts["readability"],
        word_count,
        "en",
    )


def test_vfs_returns_required_keys():
    result = _vfs()
    for key in (
        "vfs",
        "style_index",
        "style_index_label",
        "lexical",
        "syntactic",
        "semantic",
        "readability",
        "weights_used",
        "unavailable_components",
        "confidence_label",
        "lang",
        "text_length_words",
    ):
        assert key in result
    assert "confidence" not in result


def test_vfs_weighted_formula():
    expected = 80 * 0.35 + 70 * 0.25 + 72 * 0.25 + 65 * 0.15
    assert abs(_vfs()["vfs"] - expected) < 0.2
    assert _vfs()["style_index"] == _vfs()["vfs"]


def test_confidence_label_very_low_for_short_text():
    assert _vfs(word_count=20)["confidence_label"] == "VERY LOW"


def test_confidence_label_high_for_long_text():
    assert _vfs(word_count=400)["confidence_label"] == "HIGH"


def test_compute_vfs_renormalises_weights_when_semantic_unavailable():
    result = _vfs(semantic={"score": None, "evidence": []})
    expected = (80 * 0.35 + 70 * 0.25 + 65 * 0.15) / 0.75
    assert result["vfs"] == pytest.approx(expected, abs=0.1)
    assert result["semantic"] is None
    assert result["unavailable_components"] == ["semantic"]
    assert "semantic" not in result["weights_used"]
    assert sum(result["weights_used"].values()) == pytest.approx(1.0, abs=1e-3)


def test_compute_vfs_all_components_unavailable_gives_none():
    none = {"score": None}
    assert (
        _vfs(lexical=none, syntactic=none, semantic=none, readability=none)[
            "style_index"
        ]
        is None
    )


def test_iq_output_requires_validation_flag_and_style_index_label():
    default = predict_iq(70.0, "en", gate=ok_gate())
    assert default["point_estimate"] is None
    assert default["percentile"] is None
    assert default["classification"] is None
    assert "not validated" in default["withheld_reason"]
    assert default["style_index"] == 70.0
    assert default["style_band"] == "Style band 4"
    assert "Not an intelligence measure" in default["style_index_label"]

    pol = validated_policy()
    allowed = predict_iq(70.0, "en", gate=ok_gate(policy=pol), policy=pol)
    assert allowed["point_estimate"] == 110
    assert allowed["withheld_reason"] is None
    assert "Not an intelligence measure" in allowed["style_index_label"]


def test_predict_iq_without_gate_is_withheld_even_when_validated():
    result = predict_iq(70.0, "en", gate=None, policy=validated_policy())
    assert result["point_estimate"] is None
    assert "no gate" in result["withheld_reason"]


def test_predict_iq_interval_not_labelled_95ci_without_validation():
    pol = validated_policy()
    result = predict_iq(62.0, "en", gate=ok_gate(policy=pol), policy=pol)
    assert not any("ci" in key.lower() for key in result)
    assert result["range_label"] == "uncalibrated heuristic range"
    assert result["range_high"] - result["point_estimate"] >= 25
    assert result["point_estimate"] - result["range_low"] >= 25
    assert "95%" not in json.dumps(result)
    withheld = predict_iq(62.0, "en", gate=ok_gate())
    assert withheld["range_low"] is None and withheld["range_high"] is None


@pytest.mark.parametrize(
    "vfs", [0.0, 10.0, 39.99, 40.0, 54.99, 55.0, 62.0, 69.99, 70.0, 84.99, 85.0, 100.0]
)
def test_predict_iq_percentile_consistent_with_normal_cdf(vfs):
    pol = validated_policy()
    result = predict_iq(vfs, "en", gate=ok_gate(policy=pol), policy=pol)
    iq = result["point_estimate"]
    expected = 50 * (1 + math.erf((iq - 100) / (15 * math.sqrt(2))))
    assert result["percentile"] == min(99, max(1, round(expected)))


def test_percentile_is_monotone_in_style_index():
    pol = validated_policy()
    gate = ok_gate(policy=pol)
    pcts = [
        predict_iq(v / 10, "en", gate=gate, policy=pol)["percentile"]
        for v in range(0, 1001, 5)
    ]
    assert pcts == sorted(pcts)
    assert iq_percentile(100) == 50


def test_predict_iq_refused_below_min_word_count():
    pol = validated_policy()
    gate = evaluate_gates(
        {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=120,
        terminal_mark_count=8,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=pol,
    )
    result = predict_iq(70.0, "en", gate=gate, policy=pol)
    assert gate["status"] == "INSUFFICIENT_TEXT"
    assert result["point_estimate"] is None
    assert result["percentile"] is None
    assert "INSUFFICIENT_TEXT" in result["withheld_reason"]


def test_predict_mental_age_not_reported_for_adults_or_assumed_age():
    assumed = predict_mental_age(120.0)
    assert assumed["mental_age"] is None
    assert assumed["age_assumed"] is False
    assert "not supplied" in assumed["withheld_reason"]
    adult = predict_mental_age(120.0, 30)
    assert adult["mental_age"] is None
    assert "16" in adult["withheld_reason"]
    assert predict_mental_age(None, 12)["mental_age"] is None
    child = predict_mental_age(120.0, 12)
    assert child["mental_age"] == 14.4
    assert child["withheld_reason"] is None


def test_band_labels_contain_no_psychometric_terms():
    banned = re.compile(
        r"gifted|superior|average|low|below|high|genius|retard|borderline|"
        r"deficien|intellig|impair",
        re.IGNORECASE,
    )
    bands = json.loads(IQ_NORMS.read_text(encoding="utf-8"))["bands"]
    assert len(bands) == 5
    for band in bands:
        assert re.fullmatch(r"Style band [1-5]", band["label"])
        assert not banned.search(band["label"])
    assert "percentile_min" not in json.dumps(bands)


def test_scores_flag_cross_language_norms_unvalidated_and_block_cross_language_ranking():
    for lang in ("en", "id"):
        result = predict_iq(60.0, lang, gate=ok_gate(lang))
        assert result["language_norm_unvalidated"] is True
    assert (
        predict_iq(60.0, "en", gate=None, policy=validated_policy())[
            "language_norm_unvalidated"
        ]
        is False
    )
    mixed = [
        {"lang": "en", "style_index": 60.0},
        {"lang": "id", "style_index": 70.0},
    ]
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(mixed)


# --- text complexity band ---


def test_estimate_education_does_not_report_high_confidence_for_conflicting_metrics():
    result = estimate_text_complexity_band(20.0, 2.0, 0.7, "en", gate=ok_gate())
    assert result["per_metric_bands"] == {
        "gunning_fog": 7,
        "ari": 1,
        "lexical_density": 7,
    }
    assert result["consistency"] == "CONFLICTING"
    assert result["text_complexity_band"] == 7
    assert "confidence" not in result
    assert "%" not in json.dumps(result)


def test_text_complexity_band_median_of_consistent_metrics():
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "en", gate=ok_gate())
    assert result["per_metric_bands"] == {
        "gunning_fog": 5,
        "ari": 5,
        "lexical_density": 5,
    }
    assert result["text_complexity_band"] == 5
    assert result["label"] == "Complexity band 5"
    assert result["consistency"] == "CONSISTENT"


def test_education_output_is_text_complexity_not_degree():
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "en", gate=ok_gate())
    dumped = json.dumps(result)
    for code in ("S1", "S2", "S3", "SD", "SMP", "SMA", "D3", "Sarjana", "Doctoral"):
        assert code not in dumped
    for key in ("level_en", "level_id", "level_code"):
        assert key not in result
    assert result["label"].startswith("Complexity band")
    assert "not the writer's education" in result["note"]
    norms = pathlib.Path("mcp-server/config/edu_norms.json").read_text(encoding="utf-8")
    assert "Sarjana" not in norms and '"S1"' not in norms


def test_estimate_education_unavailable_for_indonesian_without_calibrated_norms():
    gate = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
    )
    result = estimate_text_complexity_band(12.4, 11.8, 0.53, "id", gate=gate)
    assert result["text_complexity_band"] is None
    assert result["label"] is None
    assert "'id'" in result["withheld_reason"]
    calibrated = validated_policy()
    gate_ok = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        calibrated,
    )
    assert (
        estimate_text_complexity_band(
            12.4, 11.8, 0.53, "id", gate=gate_ok, policy=calibrated
        )["text_complexity_band"]
        == 5
    )


def test_text_complexity_band_withheld_below_min_word_count():
    pol = validated_policy()
    gate = evaluate_gates(
        {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=120,
        terminal_mark_count=8,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=pol,
    )
    band = estimate_text_complexity_band(12.0, 11.0, 0.5, "en", gate=gate, policy=pol)
    assert band["text_complexity_band"] is None
    assert "INSUFFICIENT_TEXT" in band["withheld_reason"]


# --- input validation and norms schema (phase 3) ---


@pytest.mark.parametrize(
    ("style_index", "band"),
    [
        (0.0, "Style band 1"),
        (39.995, "Style band 1"),
        (40.0, "Style band 2"),
        (54.995, "Style band 2"),
        (69.995, "Style band 3"),
        (84.995, "Style band 4"),
        (85.0, "Style band 5"),
        (100.0, "Style band 5"),
    ],
)
def test_predict_iq_gap_values_map_to_adjacent_band(style_index, band):
    pol = validated_policy()
    result = predict_iq(style_index, "en", gate=ok_gate(policy=pol), policy=pol)
    assert result["style_band"] == band
    assert result["classification"] == band
    norms = json.loads(IQ_NORMS.read_text(encoding="utf-8"))
    bounds = next(b for b in norms["bands"] if b["label"] == band)
    assert bounds["iq_min"] <= result["point_estimate"] <= bounds["iq_max"]


@pytest.mark.parametrize("bad", [150.0, 100.01, -5.0, -0.001, math.nan, math.inf])
def test_predict_iq_rejects_out_of_range_inputs(bad):
    with pytest.raises(ValueError, match="style_index"):
        predict_iq(bad, "en", gate=ok_gate())
    pol = validated_policy()
    with pytest.raises(ValueError, match="style_index"):
        predict_iq(bad, "en", gate=ok_gate(policy=pol), policy=pol)
    assert predict_iq(None, "en")["withheld_reason"] == "style index unavailable"


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_norms_config_bands_are_contiguous_and_valid(tmp_path):
    iq = json.loads(IQ_NORMS.read_text(encoding="utf-8"))
    edu = json.loads(
        pathlib.Path("mcp-server/config/edu_norms.json").read_text(encoding="utf-8")
    )
    validate_iq_norms(iq)
    validate_edu_norms(edu)
    assert load_iq_norms() == iq
    assert load_edu_norms() == edu

    def broken_iq(mutate):
        data = copy.deepcopy(iq)
        mutate(data)
        return data

    cases = {
        "not contiguous": broken_iq(lambda d: d["bands"][1].update(vfs_max=84.99)),
        "start at 0": broken_iq(lambda d: d["bands"][-1].update(vfs_min=1)),
        "end at 100": broken_iq(lambda d: d["bands"][0].update(vfs_max=99)),
        "missing keys": broken_iq(lambda d: d["bands"][2].pop("iq_min")),
        "not increasing": broken_iq(lambda d: d["bands"][0].update(iq_min=100)),
        "iq_sd": broken_iq(lambda d: d.update(iq_sd=0)),
    }
    for message, data in cases.items():
        with pytest.raises(NormsConfigError, match=message):
            validate_iq_norms(data)
        with pytest.raises(NormsConfigError, match=message):
            load_iq_norms(_write(tmp_path, "iq.json", data))

    bad_edu = copy.deepcopy(edu)
    bad_edu["bands"][3]["fog_min"] = 2
    with pytest.raises(NormsConfigError, match="fog_min"):
        load_edu_norms(_write(tmp_path, "edu.json", bad_edu))
    with pytest.raises(NormsConfigError, match="no bands"):
        validate_edu_norms({"bands": []})
    with pytest.raises(NormsConfigError, match="no bands"):
        validate_iq_norms({**iq, "bands": []})
    gap_edu = copy.deepcopy(edu)
    gap_edu["bands"][2]["band"] = 9
    with pytest.raises(NormsConfigError, match="numbered"):
        validate_edu_norms(gap_edu)


def test_predict_mental_age_rejects_invalid_age():
    for age in (-5, 0, 2, 121, 500, 12.5, True):
        with pytest.raises(ValueError, match="chronological_age"):
            predict_mental_age(120.0, age)
    with pytest.raises(ValueError, match="iq_estimate"):
        predict_mental_age(math.nan, 12)
    assert predict_mental_age(120.0, 3)["mental_age"] == 3.6
    assert predict_mental_age(120.0, 120)["mental_age"] is None
    assert predict_mental_age(120.0, None)["age_assumed"] is False


def test_style_index_and_iq_input_reject_str_bool_and_non_finite():
    from tools.mapper import check_style_index

    for bad in ("55", True, False, math.inf, -math.inf, math.nan):
        with pytest.raises(ValueError, match="style_index"):
            check_style_index(bad)
        with pytest.raises(ValueError, match="iq_estimate"):
            predict_mental_age(bad, 12)
    assert check_style_index(55) == 55.0
