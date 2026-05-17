import math
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import langid
import spacy

DetectorFactory.seed = 42

_nlp_cache: dict = {}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        _nlp_cache[lang] = spacy.load(model)
    return _nlp_cache[lang]


def _langid_confidence(text: str) -> tuple[str, float]:
    """Return (lang, confidence) from langid using log-prob margin."""
    ranked = langid.rank(text)
    top_lang, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else top_score - 1.0
    margin = top_score - second_score  # always >= 0
    # sigmoid(margin/30): margin ~30 -> 0.73, margin ~5 -> 0.54, large -> ~1.0
    confidence = round(1.0 / (1.0 + math.exp(-margin / 30)), 2)
    return top_lang, confidence


def detect_language(text: str) -> dict:
    try:
        ld_lang = detect(text)
    except LangDetectException:
        ld_lang = "en"

    li_lang, li_conf = _langid_confidence(text)

    if ld_lang == li_lang:
        lang = ld_lang
        confidence = round(min(0.95, li_conf + 0.05), 2)
    else:
        lang = li_lang
        confidence = li_conf

    if lang not in ("en", "id"):
        lang = "en"
        confidence = 0.50

    return {"lang": lang, "confidence": confidence}


def preprocess_text(text: str, lang: str) -> dict:
    cleaned = re.sub(r"http\S+|www\S+", "", text)
    cleaned = re.sub(r"@\w+|#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    nlp = _get_nlp(lang)
    doc = nlp(cleaned)

    sentences = [
        {"idx": i, "text": sent.text.strip()}
        for i, sent in enumerate(doc.sents)
        if sent.text.strip()
    ]
    tokens = [t.text for t in doc if not t.is_space]
    word_count = len([t for t in doc if not t.is_space and not t.is_punct])

    return {
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "text_clean": cleaned,
    }
