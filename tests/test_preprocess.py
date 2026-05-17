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


def test_detect_returns_en_or_id_only():
    result = detect_language("Bonjour le monde, comment ca va aujourd'hui?")
    assert result["lang"] in ("en", "id")


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
