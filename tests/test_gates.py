# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""End-to-end input gates (F-006, F-007, F-008, F-020)."""

import re
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from pipeline import run_pipeline
from tools.policy import evaluate_gates

from tests.helpers import corpus_text, validated_policy

JAVANESE = (
    "Aku arep lunga menyang pasar karo ibuku esuk iki. Ing pasar akeh banget wong "
    "sing padha tuku sayuran lan woh-wohan. Sakwise kuwi aku bali menyang omah lan "
    "mangan sega karo iwak pitik. Bapakku lagi nyambut gawe ing sawah, dene adhiku "
    "isih sinau ing sekolahan."
)
FRENCH = (
    "Bonjour le monde, comment ca va aujourd'hui? Je voudrais acheter du pain et "
    "du fromage pour le diner de ce soir avec mes amis."
)
CODE_SWITCHED = (
    "I went to the office early this morning because the meeting started at eight. "
    "Terus aku langsung ke ruang rapat dan ternyata belum ada orang sama sekali. "
    "The manager arrived twenty minutes late and did not even apologise to anyone. "
    "Habis itu kita bahas anggaran sampai jam makan siang dan semua orang "
    "kelihatan capek. After lunch I finally finished the report and sent it to "
    "the client."
)
SCREENING_FIELDS = ("iq", "percentile", "classification", "range", "mental_age")


def _assert_screening_withheld(result):
    for field in SCREENING_FIELDS:
        assert result[field] is None, field


def test_pipeline_refuses_scoring_for_unsupported_or_low_confidence_language():
    for text, lang in ((JAVANESE, "jv"), (FRENCH, "fr")):
        result = run_pipeline(text, policy=validated_policy())
        assert result["status"] == "UNSUPPORTED_LANGUAGE"
        assert result["lang"] == lang
        assert result["style_index"] is None
        assert result["text_complexity_band"] is None
        _assert_screening_withheld(result)

    mixed = run_pipeline(CODE_SWITCHED, policy=validated_policy())
    assert mixed["status"] == "MIXED_LANGUAGE"
    assert any(r.startswith("MIXED_LANGUAGE:") for r in mixed["reasons"])
    assert mixed["text_complexity_band"] is None
    _assert_screening_withheld(mixed)

    low = evaluate_gates(
        {"lang": "id", "confidence": 0.55, "mixed_language_share": 0.0},
        400,
        20,
        "supervised_unaided",
        "formal_prose",
        validated_policy(),
    )
    assert low["status"] == "UNSUPPORTED_LANGUAGE"
    assert low["iq_allowed"] is False


def test_punctuation_only_change_moves_iq_by_less_than_5_points_or_is_refused():
    pol = validated_policy()
    punctuated = corpus_text("id_news_report")
    unpunctuated = re.sub(r"[.!?]", "", punctuated)
    kwargs = {
        "provenance": "supervised_unaided",
        "text_type": "formal_prose",
        "policy": pol,
    }
    a = run_pipeline(punctuated, **kwargs)
    b = run_pipeline(unpunctuated, **kwargs)
    assert a["status"] == "OK", a["reasons"]
    assert a["iq"] is not None
    if b["iq"] is None:
        assert b["status"] == "INSUFFICIENT_STRUCTURE"
        assert any(r.startswith("INSUFFICIENT_STRUCTURE:") for r in b["reasons"])
    else:
        assert abs(a["iq"] - b["iq"]) < 5


def test_pipeline_refuses_iq_for_informal_or_unknown_genre():
    pol = validated_policy()
    text = corpus_text("en_informal_email")
    for text_type in ("informal", "unknown"):
        result = run_pipeline(
            text, provenance="supervised_unaided", text_type=text_type, policy=pol
        )
        assert result["status"] == "UNVALIDATED"
        assert result["iq"] is None
        assert f"text_type {text_type!r}" in result["withheld_reason"]
        assert result["style_index"] is not None
    formal = run_pipeline(
        text, provenance="supervised_unaided", text_type="formal_prose", policy=pol
    )
    assert formal["status"] == "OK", formal["reasons"]
    assert formal["iq"] is not None


def test_pipeline_withholds_iq_without_supervised_unaided_provenance():
    pol = validated_policy()
    text = corpus_text("en_news_report")
    for provenance in ("unsupervised", "unknown"):
        result = run_pipeline(
            text, provenance=provenance, text_type="formal_prose", policy=pol
        )
        assert result["status"] == "UNVERIFIED_PROVENANCE"
        assert result["iq"] is None
        assert result["provenance"] == provenance
    with pytest.raises(ValueError):
        run_pipeline(text, provenance="self-reported", policy=pol)


MALAY = (
    "Kerajaan negeri telah mengumumkan bahawa projek lebuh raya itu akan siap lewat "
    "tiga bulan. Kelewatan ini disebabkan oleh masalah pengambilan tanah dan hujan "
    "lebat sepanjang awal tahun. Para peniaga tempatan menyatakan kekecewaan kerana "
    "kesesakan lalu lintas semakin teruk."
)


def test_malay_is_not_scored_as_indonesian():
    result = run_pipeline(MALAY, policy=validated_policy())
    assert result["lang"] == "ms"
    assert result["status"] == "UNSUPPORTED_LANGUAGE"
    assert result["style_index"] is None


@pytest.mark.parametrize("text", ["", "   ", "😀 🎉 " * 150, "12345 " * 300])
def test_pipeline_returns_no_style_index_for_text_without_words(text):
    result = run_pipeline(text, policy=validated_policy())
    assert result["status"] == "UNSUPPORTED_LANGUAGE"
    assert result["style_index"] is None
    assert result["components"] is None
    _assert_screening_withheld(result)


@pytest.mark.parametrize("text", ["", "12345 6789 !!!", "!!! ??? ...", "😀"])
def test_pipeline_rejects_empty_or_nonalpha_text(text):
    from tools.lexical import analyze_lexical
    from tools.mapper import compute_verbal_fluency_score, estimate_text_complexity_band

    result = run_pipeline(text)
    assert result["style_index"] is None
    assert result["components"] is None
    assert result["word_count"] == 0
    assert set(result["statuses"]) & {"UNSUPPORTED_LANGUAGE", "INSUFFICIENT_TEXT"}
    assert result["reasons"]
    _assert_screening_withheld(result)

    lex = analyze_lexical(text.split(), [], "en")
    assert lex["error"] == "INSUFFICIENT_TEXT"
    vfs = compute_verbal_fluency_score(
        lex, {"score": None}, {"score": None}, {"score": None}, 0, "en"
    )
    assert vfs["style_index"] is None
    assert vfs["unavailable_components"] == [
        "lexical",
        "readability",
        "semantic",
        "syntactic",
    ]
    gate = evaluate_gates({"lang": "en", "confidence": 0.0}, 0, 0)
    band = estimate_text_complexity_band(
        0.0, 0.0, lex["lexical_density"], "en", gate=gate
    )
    assert band["text_complexity_band"] is None


# Follow-up to F-006: repetitive Javanese that langid labels Indonesian.
JAVANESE_REPETITIVE = (
    "Aku arep lunga menyang pasar karo ibu. Wong-wong padha teka saka desa sebelah. "
    * 20
)
SUNDANESE = (
    "Abdi teu acan terang naon anu kedah dilakukeun ku urang dinten ieu. Kumaha "
    "upami urang angkat ka pasar jeung anjeun? Abdi mah geus siap ti tadi isuk. "
    "Urang teu kedah buru-buru, sabab pasar teh dibuka dugi ka sonten. Anjeun "
    "hoyong meser naon di pasar engke?"
)


def test_regional_language_function_words_are_refused():
    from tools.preprocess import detect_language, regional_function_word_share

    lang_r = detect_language(JAVANESE_REPETITIVE)
    assert lang_r["lang"] == "id"  # the regression: langid calls it Indonesian
    assert lang_r["regional_language"] == "jv"
    assert lang_r["regional_function_word_share"] == 0.5
    assert lang_r["supported"] is False
    result = run_pipeline(JAVANESE_REPETITIVE, policy=validated_policy())
    assert result["status"] == "UNSUPPORTED_LANGUAGE"
    assert result["style_index"] is None
    assert any(
        r.startswith("UNSUPPORTED_LANGUAGE: Javanese function words make up 0.50")
        for r in result["reasons"]
    )
    _assert_screening_withheld(result)

    assert regional_function_word_share(SUNDANESE)[0] == "su"
    assert regional_function_word_share(SUNDANESE)[1] > 0.15
    sundanese = run_pipeline(SUNDANESE, policy=validated_policy())
    assert sundanese["status"] == "UNSUPPORTED_LANGUAGE"
    assert sundanese["style_index"] is None
    assert any("Sundanese function words" in r for r in sundanese["reasons"])

    assert regional_function_word_share("") == (None, None)
    assert regional_function_word_share("The cat sat.") == (None, 0.0)


@pytest.mark.parametrize(
    "name", ["id_academic_essay", "id_news_report", "id_informal_chat", "en_opinion"]
)
def test_reference_corpus_is_not_refused_as_regional_language(name):
    result = run_pipeline(corpus_text(name), policy=validated_policy())
    assert not any("function words" in r for r in result["reasons"]), name
    assert result["style_index"] is not None
