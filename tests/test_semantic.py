import sys

sys.path.insert(0, "mcp-server")

from tools.semantic import analyze_semantic

COHERENT_TEXT = (
    "Climate change is accelerating. The acceleration is driven by carbon emissions. "
    "Carbon emissions must be reduced through policy intervention. "
    "Policy intervention requires international cooperation."
)
COHERENT_SENTENCES = [
    {"idx": 0, "text": "Climate change is accelerating."},
    {"idx": 1, "text": "The acceleration is driven by carbon emissions."},
    {"idx": 2, "text": "Carbon emissions must be reduced through policy intervention."},
    {"idx": 3, "text": "Policy intervention requires international cooperation."},
]

INCOHERENT_TEXT = "Dogs bark at night. The economy grew last quarter. Pizza is delicious. Mountains are tall."
INCOHERENT_SENTENCES = [
    {"idx": 0, "text": "Dogs bark at night."},
    {"idx": 1, "text": "The economy grew last quarter."},
    {"idx": 2, "text": "Pizza is delicious."},
    {"idx": 3, "text": "Mountains are tall."},
]

SINGLE_SENTENCE = [{"idx": 0, "text": "Hello world."}]


def test_returns_required_keys():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for key in (
        "argument_coherence",
        "topic_drift_index",
        "lexical_chain_density",
        "entity_sophistication",
        "score",
        "evidence",
    ):
        assert key in result


def test_coherent_text_higher_coherence():
    coherent = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    incoherent = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    assert coherent["argument_coherence"] > incoherent["argument_coherence"]


def test_score_between_0_and_100():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_single_sentence_returns_gracefully():
    result = analyze_semantic("Hello world.", SINGLE_SENTENCE, "en")
    assert "note" in result or result["score"] is not None


def test_evidence_has_coherence_and_note():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx_from" in ev
        assert "sentence_idx_to" in ev
        assert "coherence" in ev
        assert "note" in ev


def test_entity_sophistication_is_valid_label():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert result["entity_sophistication"] in ("ABSTRACT", "CONCRETE", "MINIMAL")
