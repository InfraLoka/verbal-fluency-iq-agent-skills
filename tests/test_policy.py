# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.policy import (
    INSUFFICIENT_STRUCTURE,
    INSUFFICIENT_TEXT,
    MIXED_LANGUAGE,
    OK,
    UNSUPPORTED_LANGUAGE,
    UNVALIDATED,
    UNVERIFIED_PROVENANCE,
    CrossLanguageComparisonError,
    assert_same_language,
    count_terminal_marks,
    evaluate_gates,
    load_policy,
    rank_by_style_index,
    withheld_reason,
)

from tests.helpers import ok_gate, validated_policy

CONFIG = pathlib.Path("mcp-server/config/validation.json")
EN_GOOD = {"lang": "en", "confidence": 0.99, "mixed_language_share": 0.0}


def _gate(
    lang_result=None,
    words=400,
    marks=20,
    prov="supervised_unaided",
    text_type="formal_prose",
    policy=None,
):
    return evaluate_gates(
        lang_result or EN_GOOD,
        words,
        marks,
        prov,
        text_type,
        policy if policy is not None else validated_policy(),
    )


def test_validation_config_ships_with_every_language_unvalidated():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["version"] == "2026-10-11"
    for lang in ("en", "id"):
        assert cfg["languages"][lang] == {
            "iq_validated": False,
            "education_validated": False,
        }
    assert cfg["min_words"] == 250
    assert cfg["min_lang_confidence"] == 0.80
    assert cfg["max_mixed_language_share"] == 0.20
    assert cfg["max_words_per_terminal_mark"] == 40
    assert cfg["uncalibrated_range_half_width"] == 25
    assert cfg["min_drift_transitions"] == 5


def test_load_policy_returns_independent_copies():
    a = load_policy()
    a["languages"]["en"]["iq_validated"] = True
    assert load_policy()["languages"]["en"]["iq_validated"] is False


def test_default_policy_is_unvalidated_even_when_every_input_is_good():
    gate = evaluate_gates(EN_GOOD, 400, 20, "supervised_unaided", "formal_prose")
    assert gate["status"] == UNVALIDATED
    assert gate["iq_allowed"] is False
    assert gate["language_norm_unvalidated"] is True
    assert any("not validated" in r for r in gate["reasons"])


def test_validated_policy_with_good_inputs_is_ok():
    gate = ok_gate()
    assert gate["status"] == OK
    assert gate["reasons"] == []
    assert gate["iq_allowed"] is True
    assert withheld_reason(gate, "en", validated_policy()) is None


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"lang_result": {"lang": "jv", "confidence": 0.99}}, UNSUPPORTED_LANGUAGE),
        ({"lang_result": {"lang": "en", "confidence": 0.6}}, UNSUPPORTED_LANGUAGE),
        (
            {
                "lang_result": {
                    "lang": "en",
                    "confidence": 0.9,
                    "mixed_language_share": 0.4,
                }
            },
            MIXED_LANGUAGE,
        ),
        ({"words": 120}, INSUFFICIENT_TEXT),
        ({"marks": 2}, INSUFFICIENT_STRUCTURE),
        ({"prov": "unknown"}, UNVERIFIED_PROVENANCE),
        ({"prov": "unsupervised"}, UNVERIFIED_PROVENANCE),
        ({"text_type": "informal"}, UNVALIDATED),
        ({"text_type": "unknown"}, UNVALIDATED),
    ],
)
def test_each_gate_sets_its_status_and_blocks_iq(kwargs, expected):
    gate = _gate(**kwargs)
    assert gate["status"] == expected
    assert expected in gate["statuses"]
    assert gate["iq_allowed"] is False
    assert any(r.startswith(expected + ":") for r in gate["reasons"])


def test_status_precedence_and_all_reasons_kept():
    gate = _gate(words=100, marks=1, prov="unknown")
    assert gate["status"] == INSUFFICIENT_TEXT
    assert gate["statuses"] == [
        INSUFFICIENT_TEXT,
        INSUFFICIENT_STRUCTURE,
        UNVERIFIED_PROVENANCE,
    ]
    assert len(gate["reasons"]) == 3


def test_invalid_enum_values_are_rejected():
    with pytest.raises(ValueError):
        _gate(prov="self-reported")
    with pytest.raises(ValueError):
        _gate(text_type="essay")


def test_education_allowed_only_for_calibrated_languages_and_good_text():
    assert _gate()["education_allowed"] is True
    id_gate = evaluate_gates(
        {"lang": "id", "confidence": 0.99, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        load_policy(),
    )
    assert id_gate["education_allowed"] is False
    assert _gate(words=100)["education_allowed"] is False
    # Provenance and text type govern IQ, not the descriptive text band.
    assert _gate(prov="unknown")["education_allowed"] is True


def test_withheld_reason_without_gate_refuses():
    assert "no gate" in withheld_reason(None)


def test_count_terminal_marks():
    assert count_terminal_marks("One. Two! Three? Four...") == 4
    assert count_terminal_marks("no punctuation at all") == 0
    assert count_terminal_marks("") == 0


def test_rank_refuses_mixed_languages_and_sorts_same_language():
    en = [{"lang": "en", "style_index": 40.0}, {"lang": "en", "style_index": 60.0}]
    assert [r["style_index"] for r in rank_by_style_index(en)] == [60.0, 40.0]
    assert assert_same_language(en) == "en"
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(en + [{"lang": "id", "style_index": 50.0}])


def test_forged_gate_with_iq_allowed_but_unvalidated_status_is_withheld():
    pol = validated_policy()
    forged = {
        "iq_allowed": True,
        "status": "UNVALIDATED",
        "reasons": ["forged"],
        "lang": "en",
    }
    assert withheld_reason(forged, "en", pol) is not None
    assert withheld_reason({"iq_allowed": True, "reasons": []}, "en", pol) is not None


def test_gate_for_other_language_is_withheld():
    pol = validated_policy()
    gate = ok_gate("en", policy=pol)
    assert withheld_reason(gate, "id", pol) is not None
    assert withheld_reason(gate, "en", pol) is None


def test_ok_gate_is_withheld_when_language_not_validated_in_policy():
    gate = ok_gate("en", policy=validated_policy())
    assert withheld_reason(gate, "en") is not None  # shipped policy: unvalidated
