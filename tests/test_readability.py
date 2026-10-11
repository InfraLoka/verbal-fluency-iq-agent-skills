# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

sys.path.insert(0, "mcp-server")

from tools.preprocess import preprocess_text
from tools.readability import analyze_readability

COMPLEX_TEXT = (
    "The epistemological underpinnings of contemporary hermeneutical theory "
    "necessitate a comprehensive reevaluation of ontological presuppositions "
    "embedded within conventional philosophical frameworks. "
    "Unprecedented methodological innovations require interdisciplinary synthesis "
    "across divergent theoretical paradigms."
)

SIMPLE_TEXT = "The cat sat on the mat. Dogs like to run. Birds can fly."

ID_TEXT = (
    "Perkembangan teknologi informasi yang pesat telah mengubah paradigma "
    "komunikasi modern secara fundamental dan komprehensif. "
    "Implementasi sistem yang berkelanjutan memerlukan koordinasi multidimensional."
)


def _read(text: str, lang: str) -> dict:
    prep = preprocess_text(text, lang)
    return analyze_readability(prep["text_clean"], lang, prep["sentences"])


def test_returns_required_keys():
    result = _read(COMPLEX_TEXT, "en")
    for key in (
        "flesch_reading_ease",
        "gunning_fog",
        "ari",
        "coleman_liau",
        "score",
        "evidence",
    ):
        assert key in result


def test_complex_text_higher_fog_than_simple():
    complex_r = _read(COMPLEX_TEXT, "en")
    simple_r = _read(SIMPLE_TEXT, "en")
    assert complex_r["gunning_fog"] > simple_r["gunning_fog"]


def test_score_between_0_and_100():
    result = _read(COMPLEX_TEXT, "en")
    assert 0 <= result["score"] <= 100


def test_indonesian_text_runs_without_error():
    result = _read(ID_TEXT, "id")
    assert "score" in result
    assert result["score"] >= 0


def test_evidence_contains_polysyllabic_trigger():
    result = _read(COMPLEX_TEXT, "en")
    if result["evidence"]:
        for ev in result["evidence"]:
            assert "sentence_idx" in ev
            assert any("polysyllabic" in t for t in ev["triggered_by"])
