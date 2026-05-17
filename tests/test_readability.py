import sys

sys.path.insert(0, "mcp-server")

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


def test_returns_required_keys():
    result = analyze_readability(COMPLEX_TEXT, "en")
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
    complex_r = analyze_readability(COMPLEX_TEXT, "en")
    simple_r = analyze_readability(SIMPLE_TEXT, "en")
    assert complex_r["gunning_fog"] > simple_r["gunning_fog"]


def test_score_between_0_and_100():
    result = analyze_readability(COMPLEX_TEXT, "en")
    assert 0 <= result["score"] <= 100


def test_indonesian_text_runs_without_error():
    result = analyze_readability(ID_TEXT, "id")
    assert "score" in result
    assert result["score"] >= 0


def test_evidence_contains_polysyllabic_trigger():
    result = analyze_readability(COMPLEX_TEXT, "en")
    if result["evidence"]:
        for ev in result["evidence"]:
            assert "sentence_idx" in ev
            assert any("polysyllabic" in t for t in ev["triggered_by"])
