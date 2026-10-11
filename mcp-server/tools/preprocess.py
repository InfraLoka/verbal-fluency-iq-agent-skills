# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re
from typing import Any

import spacy
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from tools.policy import count_terminal_marks, load_policy

DetectorFactory.seed = 42

SUPPORTED_LANGUAGES = ("en", "id")
# Sentences shorter than this are too short for reliable segment-level language ID.
MIN_SEGMENT_WORDS = 5

_SEGMENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[^\W\d_]+")

_nlp_cache: dict = {}
_identifiers: dict[str, Any] = {}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        nlp = spacy.load(model)
        # xx_ent_wiki_sm has no dependency parser or sentencizer; add one so
        # doc.sents is available for non-English languages.
        if (
            "sentencizer" not in nlp.pipe_names
            and "parser" not in nlp.pipe_names
            and "senter" not in nlp.pipe_names
        ):
            nlp.add_pipe("sentencizer", first=True)
        _nlp_cache[lang] = nlp
    return _nlp_cache[lang]


def _identifier(name: str):
    """langid identifiers with normalised probabilities.

    ``full`` ranks every langid language (so Javanese, Sundanese, Malay are
    recognised as such); ``pair`` is restricted to en/id for segment-level
    code-switching detection. Built lazily: loading the model takes ~1 s.
    """
    if name not in _identifiers:
        from langid.langid import LanguageIdentifier, model

        ident = LanguageIdentifier.from_modelstring(model, norm_probs=True)
        if name == "pair":
            ident.set_languages(list(SUPPORTED_LANGUAGES))
        _identifiers[name] = ident
    return _identifiers[name]


def mixed_language_share(text: str, majority: str) -> float | None:
    """Word-weighted share of sentences whose en/id language differs from majority.

    Returns None when no sentence has at least MIN_SEGMENT_WORDS words.
    """
    pair = _identifier("pair")
    total = other = 0
    for segment in _SEGMENT_SPLIT_RE.split(text):
        n_words = len(_WORD_RE.findall(segment))
        if n_words < MIN_SEGMENT_WORDS:
            continue
        total += n_words
        if pair.classify(segment)[0] != majority:
            other += n_words
    return round(other / total, 3) if total else None


def detect_language(text: str, policy: dict | None = None) -> dict:
    """Detect the language and whether it is supported for analysis.

    ``confidence`` is the lower of the two detectors' probabilities for the
    detected language (0.0 when they disagree). It is a heuristic agreement
    index, not a calibrated probability, and must never be shown as a percent.
    """
    pol = policy if policy is not None else load_policy()
    if not text or not text.strip():
        return {
            "lang": "en",
            "confidence": 0.0,
            "supported": False,
            "mixed_language_share": None,
        }

    lang, li_prob = _identifier("full").classify(text)
    try:
        ld_probs = {c.lang: c.prob for c in detect_langs(text)}
    except LangDetectException:
        ld_probs = {}
    confidence = round(min(float(li_prob), float(ld_probs.get(lang, 0.0))), 2)

    is_supported_lang = lang in SUPPORTED_LANGUAGES
    mixed = mixed_language_share(text, lang) if is_supported_lang else None
    return {
        "lang": lang,
        "confidence": confidence,
        "supported": is_supported_lang and confidence >= pol["min_lang_confidence"],
        "mixed_language_share": mixed,
    }


def preprocess_text(text: str, lang: str) -> dict:
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang!r}. Must be 'en' or 'id'.")
    if not text or not text.strip():
        return {
            "tokens": [],
            "sentences": [],
            "word_count": 0,
            "token_count": 0,
            "terminal_mark_count": 0,
            "sentence_count": 0,
            "text_clean": "",
        }

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
    # word_count: alphabetic words only, so numbers, emoji and symbols cannot
    # inflate length-based reliability (F-031). token_count keeps the old count.
    word_count = len([t for t in doc if t.is_alpha])
    token_count = len([t for t in doc if not t.is_space and not t.is_punct])

    return {
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "token_count": token_count,
        "terminal_mark_count": count_terminal_marks(cleaned),
        "sentence_count": len(sentences),
        "text_clean": cleaned,
    }
