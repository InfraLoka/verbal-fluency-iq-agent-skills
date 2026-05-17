import sys

sys.path.insert(0, "mcp-server")

from tools.syntactic import analyze_syntactic

COMPLEX_SENTENCES = [
    {
        "idx": 0,
        "text": "Although the data was inconclusive, the team proceeded because the deadline demanded immediate action.",
    },
    {
        "idx": 1,
        "text": "The report, which had been revised three times by external reviewers who questioned the methodology, was finally submitted.",
    },
    {
        "idx": 2,
        "text": "Researchers who study complex systems argue that emergent properties cannot be predicted from constituent parts alone.",
    },
]

SIMPLE_SENTENCES = [
    {"idx": 0, "text": "The cat sat."},
    {"idx": 1, "text": "Dogs run fast."},
    {"idx": 2, "text": "Birds fly high."},
]


def test_returns_required_keys():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    for key in (
        "mean_sentence_length",
        "clause_density",
        "subordination_index",
        "dependency_depth",
        "passive_ratio",
        "score",
        "evidence",
    ):
        assert key in result


def test_complex_scores_higher_than_simple():
    complex_result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    simple_result = analyze_syntactic(SIMPLE_SENTENCES, "en")
    assert complex_result["score"] > simple_result["score"]


def test_score_between_0_and_100():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_mean_sentence_length_positive():
    result = analyze_syntactic(SIMPLE_SENTENCES, "en")
    assert result["mean_sentence_length"] > 0


def test_passive_ratio_between_0_and_1():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    assert 0 <= result["passive_ratio"] <= 1


def test_evidence_has_correct_structure():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert "triggered_by" in ev
