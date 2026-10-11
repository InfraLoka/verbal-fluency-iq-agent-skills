# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import sys

sys.path.insert(0, "mcp-server")

from tools.preprocess import detect_language, preprocess_text


def test_detect_english():
    result = detect_language("The quick brown fox jumps over the lazy dog.")
    assert result["lang"] == "en"
    assert result["confidence"] > 0.5


def test_detect_indonesian():
    result = detect_language("Saya pergi ke pasar untuk membeli sayuran segar.")
    assert result["lang"] == "id"
    assert result["confidence"] > 0.5


def test_detect_reports_unsupported_language_instead_of_forcing_english():
    result = detect_language("Bonjour le monde, comment ca va aujourd'hui?")
    assert result["lang"] == "fr"
    assert result["supported"] is False


def test_detect_supported_language_has_flags_and_mixed_share():
    result = detect_language("Saya pergi ke pasar untuk membeli sayuran segar.")
    assert result["supported"] is True
    assert result["mixed_language_share"] == 0.0


def test_detect_low_confidence_is_not_supported():
    result = detect_language(
        "The quick brown fox.", policy={"min_lang_confidence": 1.01}
    )
    assert result["lang"] == "en"
    assert result["supported"] is False


def test_preprocess_strips_urls():
    result = preprocess_text("Check this out http://example.com great stuff", "en")
    assert "http" not in " ".join(result["tokens"])


def test_preprocess_strips_mentions():
    result = preprocess_text("Hey @john how are you doing today?", "en")
    assert "@john" not in result["tokens"]


def test_preprocess_returns_sentences_with_idx():
    result = preprocess_text("Hello world. How are you? I am fine.", "en")
    assert len(result["sentences"]) >= 2
    assert all("idx" in s and "text" in s for s in result["sentences"])
    assert result["sentences"][0]["idx"] == 0


def test_preprocess_word_count():
    result = preprocess_text("One two three four five.", "en")
    assert result["word_count"] == 5


def test_preprocess_short_text_minimum():
    result = preprocess_text("Hello.", "en")
    assert result["word_count"] >= 1


def test_detect_empty_string_returns_fallback():
    result = detect_language("")
    assert result["lang"] == "en"
    assert result["confidence"] == 0.0
    assert result["supported"] is False


def test_preprocess_invalid_lang_raises():
    import pytest

    with pytest.raises(ValueError):
        preprocess_text("hello world", "fr")


def test_preprocess_empty_string_returns_empty():
    result = preprocess_text("", "en")
    assert result["word_count"] == 0
    assert result["tokens"] == []


def test_word_count_excludes_numeric_and_symbol_tokens():
    result = preprocess_text(
        "Total 12345 67890 2024 100 200 300 400 500 is fine.", "en"
    )
    assert result["word_count"] == 3
    assert result["token_count"] == 11


def test_preprocess_counts_terminal_marks():
    result = preprocess_text("One two. Three four! Five six? Seven", "en")
    assert result["terminal_mark_count"] == 3


def test_preprocess_rejects_text_over_max_chars_with_clear_error(monkeypatch):
    import pytest
    from tools import models
    from tools.preprocess import InputTooLargeError, check_input_size

    def _no_model(lang):
        raise AssertionError("spaCy must not run on oversized input")

    monkeypatch.setattr(models, "get_spacy", _no_model)
    too_big = "word " * 20001  # 100,005 characters
    with pytest.raises(InputTooLargeError) as excinfo:
        preprocess_text(too_big, "en")
    message = str(excinfo.value)
    assert "100005 characters" in message and "100000" in message
    assert excinfo.value.code == "INPUT_TOO_LARGE"
    assert isinstance(excinfo.value, ValueError)
    with pytest.raises(InputTooLargeError):
        detect_language(too_big)
    check_input_size("x" * 100000)  # exactly at the limit is accepted
    with pytest.raises(InputTooLargeError):
        check_input_size("x" * 11, max_chars=10)
