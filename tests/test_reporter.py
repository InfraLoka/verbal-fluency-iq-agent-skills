# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import re
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from pipeline import run_pipeline
from tools.policy import evaluate_gates
from tools.reporter import generate_report

from tests.helpers import corpus_text, ok_gate, validated_policy

README = pathlib.Path("README.md")
LANG = {
    "lang": "en",
    "confidence": 0.97,
    "supported": True,
    "mixed_language_share": 0.0,
}
PREP = {
    "word_count": 412,
    "token_count": 415,
    "sentence_count": 18,
    "sentences": [{"idx": 0, "text": "The cat sat on the mat."}],
    "text_clean": "The cat sat.",
}
LEXICAL = {
    "mattr": 0.78,
    "mtld": 96.4,
    "vocd_d": 61.2,
    "lexical_density": 0.53,
    "avg_word_length": 5.8,
    "oov_rate": 0.01,
    "low_reliability": False,
    "reliability_reasons": [],
    "score": 78.1,
    "evidence": [
        {
            "sentence_idx": 0,
            "sentence": "The epistemological underpinnings.",
            "triggered_by": ["rare:epistemological"],
        }
    ],
}
SYNTACTIC = {
    "mean_sentence_length": 18.3,
    "clause_density": 2.1,
    "subordination_index": 0.48,
    "dependency_depth": 6.0,
    "passive_ratio": 0.12,
    "comparable_across_languages": False,
    "score": 69.2,
    "evidence": [],
}
SEMANTIC = {
    "adjacent_sentence_similarity": 0.74,
    "topic_drift_index": 0.21,
    "lexical_chain_density": 0.61,
    "entity_labels": ["ORG"],
    "score": 71.8,
    "evidence": [
        {
            "sentence_idx_from": 0,
            "sentence_idx_to": 1,
            "similarity": 0.81,
            "note": "high overlap",
        }
    ],
}
READABILITY = {
    "flesch_reading_ease": 52.1,
    "gunning_fog": 12.4,
    "ari": 11.8,
    "coleman_liau": 12.1,
    "score": 65.0,
    "evidence": [],
}
VFS = {
    "vfs": 73.4,
    "style_index": 73.4,
    "lexical": 78.1,
    "syntactic": 69.2,
    "semantic": 71.8,
    "readability": 65.0,
    "unavailable_components": [],
    "confidence_label": "HIGH",
    "lang": "en",
    "text_length_words": 412,
}
IQ_WITHHELD = {
    "style_index": 73.4,
    "style_index_label": "x",
    "style_band": "Style band 4",
    "point_estimate": None,
    "range_low": None,
    "range_high": None,
    "range_label": "uncalibrated heuristic range",
    "classification": None,
    "percentile": None,
    "withheld_reason": "UNVALIDATED: IQ mapping is not validated for language 'en'",
    "language_norm_unvalidated": True,
}
IQ_EMITTED = {
    **IQ_WITHHELD,
    "point_estimate": 117,
    "range_low": 92,
    "range_high": 142,
    "classification": "Style band 4",
    "percentile": 87,
    "withheld_reason": None,
    "language_norm_unvalidated": False,
}
MENTAL_AGE = {
    "mental_age": None,
    "based_on_chronological_age": None,
    "age_assumed": False,
    "withheld_reason": "chronological age not supplied; never assumed",
    "formula": "mental_age = (iq / 100) * chronological_age",
}
BAND = {
    "text_complexity_band": 5,
    "label": "Complexity band 5",
    "per_metric_bands": {"gunning_fog": 5, "ari": 5, "lexical_density": 5},
    "consistency": "CONSISTENT",
    "withheld_reason": None,
    "note": "Describes how difficult this text is to read, not the writer's "
    "education. Education cannot be inferred from text.",
}
DEFAULT_GATE = evaluate_gates(LANG, 412, 20, "unknown", "unknown")


def _call(
    flag="--both", iq=IQ_WITHHELD, gate=DEFAULT_GATE, mental=MENTAL_AGE, **kwargs
):
    return generate_report(
        LANG,
        PREP,
        LEXICAL,
        SYNTACTIC,
        SEMANTIC,
        READABILITY,
        VFS,
        iq,
        mental,
        BAND,
        format_flag=flag,
        gate=gate,
        **kwargs,
    )


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


def test_scores_only_returns_slim_json_with_status():
    slim = _call("--scores-only")["json"]
    assert slim["status"] == "UNVERIFIED_PROVENANCE"
    assert slim["style_index"] == 73.4
    assert slim["iq"] is None
    assert slim["iq_range"] is None
    assert slim["language_norm_unvalidated"] is True
    assert "Not an intelligence measure" in slim["style_index_label"]


def test_report_shows_iq_only_when_emitted():
    pol = validated_policy()
    withheld = _call("--report")["report"]
    assert "Withheld" in withheld
    emitted = _call("--report", iq=IQ_EMITTED, gate=ok_gate(policy=pol), policy=pol)[
        "report"
    ]
    assert "Point estimate  : 117" in emitted
    assert "Uncalibrated heuristic range : 92–142" in emitted


def test_report_contains_evidence_sentence():
    assert "epistemological" in _call("--report")["report"]


def test_verbose_caveats_adds_extended_section():
    assert "EXTENDED LIMITATIONS" in _call("--report", verbose_caveats=True)["report"]


def test_report_contains_length_tier_label():
    assert "Text length tier    : HIGH" in _call("--report")["report"]


def test_id_report_shows_depth_na_and_caveats():
    id_lang = {**LANG, "lang": "id"}
    report = generate_report(
        id_lang,
        PREP,
        LEXICAL,
        {**SYNTACTIC, "dependency_depth": None},
        SEMANTIC,
        READABILITY,
        {**VFS, "lang": "id"},
        IQ_WITHHELD,
        MENTAL_AGE,
        BAND,
        format_flag="--report",
        gate=evaluate_gates(id_lang, 412, 20),
    )["report"]
    assert "N/A (no parser for id)" in report
    assert "no dependency parser" in report
    assert "uncalibrated for" in report


def test_en_report_still_shows_numeric_depth():
    report = _call("--report")["report"]
    assert "Dependency tree depth : 6.0" in report
    assert "no parser for id" not in report


def test_report_and_readme_name_construct_lexical_syntactic_complexity_not_fluency():
    report = _call("--report")["report"]
    assert "LEXICAL-SYNTACTIC COMPLEXITY REPORT" in report
    assert "VERBAL FLUENCY" not in report.upper()
    assert "Not an intelligence measure" in report
    assert "rewards surface complexity" in report
    assert _call("--json")["json"]["notice"]["construct"] == (
        "lexical-syntactic complexity"
    )
    readme = README.read_text(encoding="utf-8")
    assert "lexical-syntactic complexity" in readme
    assert "does not measure verbal fluency" in readme
    assert "using verbal fluency as a psycholinguistic proxy" not in readme
    assert "rewards complexity, not quality" in readme


def test_report_research_section_states_no_individual_validation():
    report = _call("--report")["report"]
    assert "INSPIRED BY" in report
    assert "RESEARCH BASIS" not in report
    assert "no individual-level validation" in report
    for name in ("Pennebaker", "Crossley", "Mairesse"):
        assert name not in report
    readme = README.read_text(encoding="utf-8")
    assert "## Inspired By" in readme
    assert "## Research Basis" not in readme
    assert "no individual-level validation" in readme


def test_report_does_not_format_heuristic_confidence_as_percent():
    for gate, iq in ((DEFAULT_GATE, IQ_WITHHELD), (ok_gate(), IQ_EMITTED)):
        report = _call("--report", iq=iq, gate=gate)["report"]
        assert not re.search(r"\d+%", report)
        assert "Lang detection      : HIGH" in report
    assert "95% CI" not in README.read_text(encoding="utf-8")


def test_report_band_heading_is_style_band_not_classification():
    report = _call("--report", iq=IQ_EMITTED, gate=ok_gate())["report"]
    assert "Classification" not in report
    assert "Style band      : Style band 4" in report


def test_report_includes_provenance_caveat_and_requires_attestation():
    report = _call("--report")["report"]
    assert "Provenance      : unknown" in report
    assert "Valid only for supervised, unaided writing" in report
    assert "UNVERIFIED_PROVENANCE" in report
    no_gate = _call("--report", gate=None)["report"]
    assert "Provenance      : not attested" in no_gate
    assert "Status: UNVERIFIED" in no_gate

    pol = validated_policy()
    text = corpus_text("en_news_report")
    unattested = run_pipeline(text, text_type="formal_prose", policy=pol)
    assert unattested["status"] == "UNVERIFIED_PROVENANCE"
    assert unattested["iq"] is None
    attested = run_pipeline(
        text, provenance="supervised_unaided", text_type="formal_prose", policy=pol
    )
    assert attested["iq"] is not None


def test_report_flags_language_norms_unvalidated():
    report = _call("--report")["report"]
    assert "Language norms      : UNVALIDATED for English" in report
    assert _call("--json")["json"]["language"]["language_norm_unvalidated"] is True


FORGED_IQ = {
    **IQ_EMITTED,
    "point_estimate": 135,
    "percentile": 99,
    "range_low": 110,
    "range_high": 160,
    "classification": "Style band 7",
}
FORGED_AGE = {**MENTAL_AGE, "mental_age": 16.2, "withheld_reason": None}


def _forged_output(flag, gate):
    out = _call(flag, iq=FORGED_IQ, gate=gate, mental=FORGED_AGE)
    return (out["report"] or "") + json.dumps(out["json"])


@pytest.mark.parametrize("flag", ["--report", "--json", "--scores-only", "--both"])
@pytest.mark.parametrize("gate_kind", ["none", "not_ok", "forged"])
def test_reporter_withholds_caller_supplied_iq_unless_gate_allows(flag, gate_kind):
    gate = {
        "none": None,
        "not_ok": DEFAULT_GATE,
        "forged": {**DEFAULT_GATE, "iq_allowed": True},
    }[gate_kind]
    text = _forged_output(flag, gate)
    assert "135" not in text
    assert "99th" not in text
    assert "16.2" not in text
    assert "withheld" in text.lower()
