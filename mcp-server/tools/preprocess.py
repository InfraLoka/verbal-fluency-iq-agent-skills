# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re
from typing import Any

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from tools import models
from tools.policy import (
    SUPPORTED_LANGUAGES,
    count_terminal_marks,
    load_policy,
    require_supported_language,
)
from tools.sanitize import detect_injection_phrases

DetectorFactory.seed = 42

# Sentences shorter than this are too short for reliable segment-level language ID.
MIN_SEGMENT_WORDS = 5

_SEGMENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[^\W\d_]+")

_identifiers: dict[str, Any] = {}

# Closed-class words of Javanese and Sundanese that standard Indonesian does not
# use (or rarely: "aku"). langid labels such text Indonesian with high
# confidence, so their share is checked separately (follow-up to F-006).
REGIONAL_FUNCTION_WORDS = {
    "jv": frozenset(
        {
            "aku",
            "arep",
            "lunga",
            "menyang",
            "karo",
            "padha",
            "saka",
            "ora",
            "iki",
            "kuwi",
            "wis",
            "opo",
            "kowe",
            "sing",
            "neng",
        }
    ),
    "su": frozenset(
        {
            "abdi",
            "teu",
            "jeung",
            "ka",
            "ti",
            "mah",
            "geus",
            "naon",
            "anjeun",
            "urang",
            "kumaha",
        }
    ),
}


class InputTooLargeError(ValueError):
    """The text exceeds ``max_chars`` in config/validation.json (G-013)."""

    code = "INPUT_TOO_LARGE"


def check_input_size(text: str, max_chars: int | None = None) -> None:
    """Refuse oversized input before any model sees it.

    The limit bounds memory and time on a shared server; spaCy itself fails
    above ~1,000,000 characters.
    """
    limit = int(max_chars if max_chars is not None else load_policy()["max_chars"])
    size = len(text or "")
    if size > limit:
        raise InputTooLargeError(
            f"text has {size} characters; the maximum is {limit} "
            "(max_chars in config/validation.json). Split the text and analyse "
            "each part separately."
        )


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


def regional_function_word_share(text: str) -> tuple[str | None, float | None]:
    """(language code, share of words) for the regional list with most hits.

    Returns (None, None) without words and (None, 0.0) without any hit.
    """
    words = [w.lower() for w in _WORD_RE.findall(text or "")]
    if not words:
        return None, None
    shares = {
        code: sum(1 for w in words if w in vocab) / len(words)
        for code, vocab in REGIONAL_FUNCTION_WORDS.items()
    }
    code = max(shares, key=lambda c: shares[c])
    if shares[code] == 0:
        return None, 0.0
    return code, round(shares[code], 3)


def detect_language(text: str, policy: dict | None = None) -> dict:
    """Detect the language and whether it is supported for analysis.

    ``confidence`` is the lower of the two detectors' probabilities for the
    detected language (0.0 when they disagree). It is a heuristic agreement
    index, not a calibrated probability, and must never be shown as a percent.
    """
    pol = policy if policy is not None else load_policy()
    check_input_size(text)
    if not text or not text.strip():
        return {
            "lang": "en",
            "confidence": 0.0,
            "supported": False,
            "mixed_language_share": None,
            "regional_language": None,
            "regional_function_word_share": None,
        }

    lang, li_prob = _identifier("full").classify(text)
    try:
        ld_probs = {c.lang: c.prob for c in detect_langs(text)}
    except LangDetectException:
        ld_probs = {}
    confidence = round(min(float(li_prob), float(ld_probs.get(lang, 0.0))), 2)

    is_supported_lang = lang in SUPPORTED_LANGUAGES
    mixed = mixed_language_share(text, lang) if is_supported_lang else None
    regional, regional_share = regional_function_word_share(text)
    regional_ok = regional_share is None or regional_share <= pol.get(
        "max_regional_function_word_share", 1.0
    )
    return {
        "lang": lang,
        "confidence": confidence,
        "supported": is_supported_lang
        and confidence >= pol["min_lang_confidence"]
        and regional_ok,
        "mixed_language_share": mixed,
        "regional_language": regional,
        "regional_function_word_share": regional_share,
    }


def preprocess_text(text: str, lang: str) -> dict:
    require_supported_language(lang)
    check_input_size(text)
    if not text or not text.strip():
        return {
            "lang": lang,
            "tokens": [],
            "sentences": [],
            "word_count": 0,
            "token_count": 0,
            "terminal_mark_count": 0,
            "sentence_count": 0,
            "text_clean": "",
            "injection_phrases": [],
        }

    cleaned = re.sub(r"http\S+|www\S+", "", text)
    cleaned = re.sub(r"@\w+|#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    doc = models.get_spacy(lang)(cleaned)

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
        "lang": lang,
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "token_count": token_count,
        "terminal_mark_count": count_terminal_marks(cleaned),
        "sentence_count": len(sentences),
        "text_clean": cleaned,
        # Instruction-like phrases (G-014); the text is never acted on.
        "injection_phrases": detect_injection_phrases(cleaned),
    }
