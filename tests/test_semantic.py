# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

sys.path.insert(0, "mcp-server")

from tools import semantic
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

SIX_SENTENCES = COHERENT_SENTENCES + [
    {"idx": 4, "text": "Cooperation depends on trust between governments."},
    {"idx": 5, "text": "Trust grows when commitments are verified."},
]
SIX_TEXT = " ".join(s["text"] for s in SIX_SENTENCES)

SINGLE_SENTENCE = [{"idx": 0, "text": "Hello world."}]


def test_returns_required_keys():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for key in (
        "adjacent_sentence_similarity",
        "topic_drift_index",
        "lexical_chain_density",
        "entity_labels",
        "transitions",
        "scaling_status",
        "score",
        "evidence",
    ):
        assert key in result


def test_coherent_text_higher_similarity():
    coherent = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    incoherent = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    assert (
        coherent["adjacent_sentence_similarity"]
        > incoherent["adjacent_sentence_similarity"]
    )


def test_score_between_0_and_100():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_single_sentence_returns_none_score_with_note():
    result = analyze_semantic("Hello world.", SINGLE_SENTENCE, "en")
    assert result["score"] is None
    assert "note" in result


def test_evidence_has_similarity_and_note():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx_from" in ev
        assert "sentence_idx_to" in ev
        assert "similarity" in ev
        assert "note" in ev


def test_default_segment_boundaries_unchanged():
    a = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    b = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", None)
    assert a == b


def test_segment_boundary_excludes_cross_document_pair():
    base = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    seg = analyze_semantic(
        INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", segment_boundaries=[2]
    )
    assert seg["adjacent_sentence_similarity"] != base["adjacent_sentence_similarity"]


def test_all_pairs_straddle_boundaries_returns_gracefully():
    result = analyze_semantic(
        INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en", segment_boundaries=[1, 2, 3]
    )
    assert result["adjacent_sentence_similarity"] is None
    assert result["score"] is None
    assert "note" in result


def test_semantic_entity_score_independent_of_ner_label_set(monkeypatch):
    scores = []
    for labels in ([], ["PER"], ["ORG"], ["LAW", "NORP"], ["LOC", "MISC"]):
        monkeypatch.setattr(semantic, "_entity_labels", lambda t, lang, ls=labels: ls)
        result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
        assert result["entity_labels"] == labels
        assert "entity_sophistication" not in result
        scores.append(result["score"])
    assert len(set(scores)) == 1


def test_topic_drift_none_when_fewer_than_min_transitions():
    two = analyze_semantic(
        "Climate change is accelerating. Pizza is delicious.",
        [
            {"idx": 0, "text": "Climate change is accelerating."},
            {"idx": 1, "text": "Pizza is delicious."},
        ],
        "en",
    )
    assert two["transitions"] == 1
    assert two["topic_drift_index"] is None
    assert two["score"] is not None
    four = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert four["transitions"] == 3
    assert four["topic_drift_index"] is None
    six = analyze_semantic(SIX_TEXT, SIX_SENTENCES, "en")
    assert six["transitions"] == 5
    assert isinstance(six["topic_drift_index"], float)


def test_semantic_metric_renamed_and_scaling_loaded_per_language(monkeypatch):
    cfg = json.loads(
        pathlib.Path("mcp-server/config/semantic_scaling.json").read_text(
            encoding="utf-8"
        )
    )
    assert cfg["status"] == "uncalibrated"
    assert set(cfg["languages"]) == {"en", "id"}
    for lang in ("en", "id"):
        assert cfg["languages"][lang] == {"similarity_min": 0.3, "similarity_max": 0.9}

    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert "argument_coherence" not in result
    assert result["scaling_status"] == "uncalibrated"

    patched = {
        "status": "uncalibrated",
        "languages": {
            "en": cfg["languages"]["en"],
            "id": {"similarity_min": 0.0, "similarity_max": 1.0},
        },
    }
    monkeypatch.setattr(semantic, "_load_scaling", lambda: patched)
    en_after = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    id_after = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "id")
    assert en_after["score"] == result["score"]
    assert id_after["score"] != result["score"]
