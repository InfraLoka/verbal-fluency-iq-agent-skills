# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
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


# --- Indonesian rule-based path (no spaCy parser available) ---

ID_COMPLEX = [
    {
        "idx": 0,
        "text": "Meskipun data tidak lengkap, tim tetap melanjutkan karena tenggat menuntut tindakan yang cepat.",
    },
    {
        "idx": 1,
        "text": "Laporan yang telah direvisi oleh peninjau eksternal akhirnya diserahkan sehingga proyek dapat dilanjutkan.",
    },
]

ID_SIMPLE = [
    {"idx": 0, "text": "Kucing itu duduk."},
    {"idx": 1, "text": "Anjing berlari cepat."},
]


def test_id_returns_required_keys():
    result = analyze_syntactic(ID_COMPLEX, "id")
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


def test_id_complex_scores_higher_than_simple():
    assert (
        analyze_syntactic(ID_COMPLEX, "id")["score"]
        > analyze_syntactic(ID_SIMPLE, "id")["score"]
    )


def test_id_dependency_depth_is_none_not_zero():
    # Honest: depth is unmeasurable without a parser, so None — never a fake 0.
    assert analyze_syntactic(ID_COMPLEX, "id")["dependency_depth"] is None


def test_id_subordination_and_clause_density_nonzero():
    result = analyze_syntactic(ID_COMPLEX, "id")
    assert result["subordination_index"] > 0
    assert result["clause_density"] > 1.0


def test_id_passive_detected():
    # "direvisi", "diserahkan", "dilanjutkan" are di- passives.
    assert analyze_syntactic(ID_COMPLEX, "id")["passive_ratio"] > 0


def test_id_locative_di_not_counted_as_passive():
    # "di rumah" / "di kantor": locative preposition, not passive morphology.
    result = analyze_syntactic(
        [{"idx": 0, "text": "Saya di rumah dan di kantor."}], "id"
    )
    assert result["passive_ratio"] == 0


def test_id_score_between_0_and_100():
    result = analyze_syntactic(ID_COMPLEX, "id")
    assert 0 <= result["score"] <= 100


def test_en_path_unchanged():
    # Snapshot captured from the pre-change English (parser) branch.
    sents = [
        {
            "idx": 0,
            "text": "Although the data was inconclusive, the team proceeded because the deadline demanded immediate action.",
        },
        {
            "idx": 1,
            "text": "The report, which had been revised three times by external reviewers who questioned the methodology, was finally submitted.",
        },
    ]
    r = analyze_syntactic(sents, "en")
    assert r["mean_sentence_length"] == 16.0
    assert r["clause_density"] == 3.0
    assert r["subordination_index"] == 2.0
    assert r["dependency_depth"] == 3.0
    assert r["passive_ratio"] == 0.5
    assert r["score"] == 65.2


def test_id_non_passive_di_ter_words_not_counted():
    text = "Terhadap dirinya, direktur tersebut menyebut terdapat diskusi."
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["passive_ratio"] == 0
    for ev in result["evidence"]:
        assert not any(t.startswith("passive:") for t in ev["triggered_by"])


def test_id_true_passive_still_detected():
    result = analyze_syntactic([{"idx": 0, "text": "Surat itu ditulis kemarin."}], "id")
    assert result["passive_ratio"] > 0
