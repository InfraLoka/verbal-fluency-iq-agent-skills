# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.policy import CrossLanguageComparisonError, rank_by_style_index
from tools.syntactic import analyze_syntactic, is_di_passive

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


def test_id_passive_not_triggered_by_terjadi_terkait_terbaik_dimana_diantara():
    text = (
        "Hal itu terjadi dan terkait dengan hasil terbaik dimana kami berada "
        "diantara mereka"
    )
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["passive_ratio"] == 0
    for word in ("terjadi", "terkait", "terbaik", "dimana", "diantara", "dinas"):
        assert not is_di_passive(word), word
    for word in ("ditulis", "direvisi", "diserahkan", "dilanjutkan", "dikirimi"):
        assert is_di_passive(word), word


def test_id_clause_density_ignores_nominal_coordination_and_temporal_prepositions():
    text = "Saya makan nasi dan atau minum teh sejak pagi sampai malam selama seminggu"
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["clause_density"] == 1.0
    assert result["subordination_index"] == 0.0


def test_id_clausal_coordination_and_temporal_clauses_still_counted():
    text = "Ayah membaca koran dan saya menulis surat sejak dia pindah ke kota."
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["clause_density"] == 3.0
    assert result["subordination_index"] == 1.0


ID_FORMAL = [
    {
        "idx": 0,
        "text": "Kalau hujan turun, kami tetap berangkat agar acara tidak batal.",
    },
    {
        "idx": 1,
        "text": "Saya pulang cepat karena badan saya lelah, tetapi pekerjaan belum selesai.",
    },
    {
        "idx": 2,
        "text": "Ketika dia datang, kami langsung makan karena semua orang sudah lapar.",
    },
]
ID_COLLOQUIAL = [
    {
        "idx": 0,
        "text": "Kalo hujan turun, kami tetap berangkat biar acara tidak batal.",
    },
    {
        "idx": 1,
        "text": "Saya pulang cepat soalnya badan saya lelah, tapi pekerjaan belum selesai.",
    },
    {
        "idx": 2,
        "text": "Pas dia datang, kami langsung makan gara-gara semua orang sudah lapar.",
    },
]


def test_id_syntactic_score_equal_for_formal_and_colloquial_paraphrase():
    formal = analyze_syntactic(ID_FORMAL, "id")
    colloquial = analyze_syntactic(ID_COLLOQUIAL, "id")
    assert colloquial["score"] == formal["score"]
    assert colloquial["clause_density"] == formal["clause_density"]
    assert colloquial["subordination_index"] == formal["subordination_index"]
    assert formal["colloquial_forms_normalised"] == 0
    assert colloquial["colloquial_forms_normalised"] == 6


def test_syntactic_scores_flagged_not_comparable_across_languages():
    en = analyze_syntactic(COMPLEX_SENTENCES, "en")
    idn = analyze_syntactic(ID_COMPLEX, "id")
    for result in (en, idn):
        assert result["comparable_across_languages"] is False
        assert "not comparable across languages" in result["note"]
    with pytest.raises(CrossLanguageComparisonError):
        rank_by_style_index(
            [
                {"lang": "en", "style_index": en["score"]},
                {"lang": "id", "style_index": idn["score"]},
            ]
        )


def test_id_locative_written_solid_is_not_passive_but_suffixed_form_is():
    text = "Saya tinggal dirumah dan bekerja dikantor dekat dipasar."
    result = analyze_syntactic([{"idx": 0, "text": text}], "id")
    assert result["passive_ratio"] == 0
    assert is_di_passive("dijalankan")
    assert is_di_passive("dirumahkan")
    assert not is_di_passive("dijalan")
