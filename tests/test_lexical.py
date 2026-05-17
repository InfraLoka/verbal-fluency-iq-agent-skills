import sys

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical


RICH_TOKENS = (
    "The epistemological underpinnings of this philosophical discourse "
    "traverse labyrinthine corridors of ontological ambiguity wherein "
    "conventional paradigms dissolve into hermeneutical uncertainty "
    "requiring unprecedented methodological innovation and interdisciplinary "
    "synthesis across divergent theoretical frameworks"
).split()

SIMPLE_TOKENS = "the cat sat on the mat the cat sat the mat sat".split()

SENTENCES = [
    {"idx": 0, "text": "The cat sat on the mat."},
    {
        "idx": 1,
        "text": "The epistemological underpinnings dissolve into hermeneutical uncertainty.",
    },
]


def test_analyze_lexical_returns_required_keys():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for key in (
        "mattr",
        "hapax_ratio",
        "lexical_density",
        "avg_word_length",
        "score",
        "evidence",
    ):
        assert key in result, f"Missing key: {key}"


def test_rich_vocabulary_scores_higher_than_simple():
    rich = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    simple = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert rich["score"] > simple["score"]


def test_mattr_between_0_and_1():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["mattr"] <= 1


def test_hapax_ratio_between_0_and_1():
    result = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert 0 <= result["hapax_ratio"] <= 1


def test_score_between_0_and_100():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_evidence_contains_sentence_idx_and_triggered_by():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert "triggered_by" in ev
        assert len(ev["triggered_by"]) > 0


def test_empty_tokens_returns_error():
    result = analyze_lexical([], SENTENCES, "en")
    assert "error" in result
