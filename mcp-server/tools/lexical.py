# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Lexical diversity and density.

Token unit (F-029): every diversity metric in both languages uses lowercased
alphabetic surface forms. No stemming or lemmatisation for either language.

Dictionary filter (F-024): tokens that the ``wordfreq`` lexicon does not know
(zipf_frequency == 0, e.g. typos and keyboard noise) are excluded from MATTR,
MTLD and lexical density. Their share is ``oov_rate``; above 0.10 the result is
flagged ``low_reliability`` and should be routed to human review.

Nothing is swallowed silently (G-042): every metric that could not be computed
is ``None`` and ``warnings`` says why (``vocd_failed: ...``, ``vocd_too_short``,
``mtld_too_short``). Text without dictionary words returns the same keys with
``error`` set and ``score`` None (G-012).
"""

from collections import Counter
from functools import lru_cache

from lexicalrichness import LexicalRichness
from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP_WORDS
from spacy.lang.id.stop_words import STOP_WORDS as ID_STOP_WORDS
from wordfreq import zipf_frequency

from tools.evidence import rank_evidence
from tools.policy import require_supported_language
from tools.robustness import repeated_ngram_share

TOKEN_UNIT = "lowercased_surface_form"
STOP_WORDS = {"en": EN_STOP_WORDS, "id": ID_STOP_WORDS}
OOV_RELIABILITY_THRESHOLD = 0.10
MATTR_WINDOW = 50
MIN_MTLD_TOKENS = 10
MIN_VOCD_TOKENS = 50
# Rare-but-real words (shown as evidence only; never scored).
RARE_ZIPF_MAX = 3.5
# avg_word_length is reported but not scored: it duplicates readability (F-015).
SCORE_WEIGHTS = {"mattr": 0.45, "mtld": 0.35, "lexical_density": 0.20}


def _mattr(tokens: list[str], window: int = MATTR_WINDOW) -> float:
    if len(tokens) < window:
        return len(set(tokens)) / len(tokens) if tokens else 0.0
    ttrs = [
        len(set(tokens[i : i + window])) / window
        for i in range(len(tokens) - window + 1)
    ]
    return sum(ttrs) / len(ttrs)


@lru_cache(maxsize=65536)
def _zipf(word: str, lang: str) -> float:
    return zipf_frequency(word, lang)


def _scale(value: float, low: float, high: float) -> float:
    return min(100.0, max(0.0, (value - low) / (high - low) * 100))


INSUFFICIENT_TEXT = "INSUFFICIENT_TEXT"


def _not_measured(
    error_message: str,
    alpha_count: int,
    oov_rate: float | None,
    reliability_reasons: list[str],
) -> dict:
    """Full-shape result for text with no dictionary words (G-012)."""
    return {
        "mattr": None,
        "mtld": None,
        "vocd_d": None,
        "lexical_density": None,
        "avg_word_length": None,
        "token_unit": TOKEN_UNIT,
        "alpha_token_count": alpha_count,
        "known_token_count": 0,
        "oov_rate": oov_rate,
        "rare_word_share": None,
        "repeated_ngram_share": None,
        "low_reliability": True,
        "reliability_reasons": reliability_reasons,
        "score_weights": {},
        "score": None,
        "evidence": [],
        "warnings": [f"{INSUFFICIENT_TEXT.lower()}: {error_message}"],
        "error": INSUFFICIENT_TEXT,
    }


def _vocd(known: list[str], warnings: list[str]) -> float | None:
    if len(known) < MIN_VOCD_TOKENS:
        warnings.append(
            f"vocd_too_short: {len(known)} dictionary words; VOCD-D needs "
            f"{MIN_VOCD_TOKENS}"
        )
        return None
    try:
        return round(float(LexicalRichness(" ".join(known)).vocd()), 1)
    except (ArithmeticError, RuntimeError, TypeError, ValueError) as exc:
        # Curve fitting fails with RuntimeError/ValueError: record it (G-042).
        warnings.append(f"vocd_failed: {type(exc).__name__}: {exc}")
        return None


def analyze_lexical(tokens: list[str], sentences: list[dict], lang: str) -> dict:
    require_supported_language(lang)
    alpha = [t.lower() for t in tokens if t.isalpha()]
    if not alpha:
        return _not_measured("no alphabetic tokens", 0, None, [])

    known = [t for t in alpha if _zipf(t, lang) > 0]
    oov_rate = round(1 - len(known) / len(alpha), 3)
    reliability_reasons = []
    if oov_rate > OOV_RELIABILITY_THRESHOLD:
        reliability_reasons.append(
            f"{oov_rate:.2f} of words are not in the {lang} dictionary "
            f"(max {OOV_RELIABILITY_THRESHOLD:.2f}); route to human review"
        )
    if not known:
        return _not_measured(
            "no dictionary words", len(alpha), oov_rate, reliability_reasons
        )

    warnings: list[str] = []
    mattr = round(_mattr(known), 3)
    mtld = None
    if len(known) >= MIN_MTLD_TOKENS:
        mtld = round(float(LexicalRichness(" ".join(known)).mtld(threshold=0.72)), 1)
    else:
        warnings.append(
            f"mtld_too_short: {len(known)} dictionary words; MTLD needs "
            f"{MIN_MTLD_TOKENS}"
        )
    vocd_d = _vocd(known, warnings)

    stop = STOP_WORDS[lang]
    lexical_density = round(sum(1 for t in known if t not in stop) / len(known), 3)
    avg_word_length = round(sum(len(t) for t in alpha) / len(alpha), 1)

    parts = {
        "mattr": _scale(mattr, 0.3, 0.9),
        "lexical_density": _scale(lexical_density, 0.3, 0.7),
    }
    if mtld is not None:
        parts["mtld"] = _scale(mtld, 40.0, 200.0)
    total_weight = sum(SCORE_WEIGHTS[k] for k in parts)
    score = round(sum(parts[k] * SCORE_WEIGHTS[k] for k in parts) / total_weight, 1)

    freq = Counter(known)
    candidates = []
    for sent in sentences:
        words = [w.lower() for w in sent["text"].split() if w.isalpha()]
        if not words:
            continue
        rare = [
            w
            for w in words
            if freq.get(w, 0) == 1 and len(w) > 5 and 0 < _zipf(w, lang) < RARE_ZIPF_MAX
        ]
        share = round(len(rare) / len(words), 3)
        candidates.append(
            {
                "sentence_idx": sent["idx"],
                "sentence": sent["text"],
                "triggered_by": [f"rare:{w}" for w in rare[:3]]
                + [f"rare_share:{share}"],
                "contribution": share,
            }
        )

    return {
        "mattr": mattr,
        "mtld": mtld,
        "vocd_d": vocd_d,
        "lexical_density": lexical_density,
        "avg_word_length": avg_word_length,
        "token_unit": TOKEN_UNIT,
        "alpha_token_count": len(alpha),
        "known_token_count": len(known),
        "oov_rate": oov_rate,
        # Robustness inputs (tools.robustness), not scored.
        "rare_word_share": round(
            sum(1 for t in known if _zipf(t, lang) < RARE_ZIPF_MAX) / len(known), 3
        ),
        "repeated_ngram_share": repeated_ngram_share(alpha),
        "low_reliability": bool(reliability_reasons),
        "reliability_reasons": reliability_reasons,
        "score_weights": {k: SCORE_WEIGHTS[k] for k in parts},
        "score": score,
        "evidence": rank_evidence(candidates),
        "warnings": warnings,
        "error": None,
    }
