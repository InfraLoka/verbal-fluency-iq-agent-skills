# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Gaming and padding checks (G-001, G-036).

The style index rewards rare words, long sentences and topical overlap, so it
can be inflated on purpose. These checks do not change any score: they add
``review_flags`` with reasons and mark the result ``low_reliability`` so a human
reviews it. Thresholds live in ``config/robustness.json``.

- ``vocabulary_stuffing``: a high lexical score together with a rare-word share
  far above normal prose, or with adjacent sentences that do not relate.
- ``sentence_repetition``: many sentences are near-duplicates of earlier ones
  (they are also removed before semantic scoring, see ``dedupe_sentences``).
- ``ngram_padding``: a large share of word trigrams repeat.
"""

import copy
import functools
import json
import os
import re
from collections import Counter
from typing import Any

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "robustness.json"
)
_WORD_RE = re.compile(r"[^\W\d_]+")

VOCABULARY_STUFFING = "vocabulary_stuffing"
SENTENCE_REPETITION = "sentence_repetition"
NGRAM_PADDING = "ngram_padding"


@functools.cache
def _load() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def load_thresholds() -> dict[str, Any]:
    """A fresh copy of config/robustness.json."""
    return copy.deepcopy(_load())


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def dedupe_sentences(
    sentences: list[dict], jaccard: float | None = None
) -> tuple[list[dict], int]:
    """Drop sentences whose word set is a near-duplicate of an earlier one.

    Two sentences are near-duplicates when the Jaccard overlap of their word
    sets is at least ``jaccard``. The first occurrence is kept, so ``idx``
    values of kept sentences are unchanged. Returns (kept, number removed).
    """
    limit = jaccard if jaccard is not None else _load()["near_duplicate_jaccard"]
    kept: list[dict] = []
    kept_sets: list[frozenset[str]] = []
    seen_exact: set[frozenset[str]] = set()
    removed = 0
    for sent in sentences:
        words = frozenset(_words(sent["text"]))
        if not words:
            kept.append(sent)
            continue
        duplicate = words in seen_exact or any(
            len(words & other) / len(words | other) >= limit for other in kept_sets
        )
        if duplicate:
            removed += 1
            continue
        kept.append(sent)
        kept_sets.append(words)
        seen_exact.add(words)
    return kept, removed


def repeated_ngram_share(words: list[str], n: int | None = None) -> float:
    """Share of word n-grams that repeat an earlier n-gram (0 when too short)."""
    size = n if n is not None else int(_load()["ngram_n"])
    grams = [tuple(words[i : i + size]) for i in range(len(words) - size + 1)]
    if not grams:
        return 0.0
    counts = Counter(grams)
    repeats = sum(c - 1 for c in counts.values() if c > 1)
    return round(repeats / len(grams), 3)


def assess(
    lexical: dict, semantic: dict, thresholds: dict | None = None
) -> dict[str, Any]:
    """Review flags from analyser outputs. Never changes a score."""
    t = thresholds if thresholds is not None else _load()
    flags: list[str] = []
    reasons: list[str] = []

    score = lexical.get("score")
    rare = lexical.get("rare_word_share")
    similarity = semantic.get("adjacent_sentence_similarity")
    if score is not None and score >= t["stuffing_min_lexical_score"]:
        if rare is not None and rare > t["max_rare_word_share"]:
            flags.append(VOCABULARY_STUFFING)
            reasons.append(
                f"{VOCABULARY_STUFFING}: lexical score {score} with {rare:.2f} of "
                f"words rare (max {t['max_rare_word_share']:.2f}); route to human "
                "review"
            )
        elif similarity is not None and similarity < t["min_adjacent_similarity"]:
            flags.append(VOCABULARY_STUFFING)
            reasons.append(
                f"{VOCABULARY_STUFFING}: lexical score {score} while adjacent "
                f"sentences barely relate (similarity {similarity:.2f}, min "
                f"{t['min_adjacent_similarity']:.2f}); route to human review"
            )

    dup = semantic.get("duplicate_sentence_ratio")
    if dup is not None and dup > t["max_duplicate_sentence_ratio"]:
        flags.append(SENTENCE_REPETITION)
        reasons.append(
            f"{SENTENCE_REPETITION}: {dup:.2f} of sentences repeat earlier ones "
            f"(max {t['max_duplicate_sentence_ratio']:.2f}); duplicates were "
            "removed before semantic scoring"
        )

    padding = lexical.get("repeated_ngram_share")
    if padding is not None and padding > t["max_repeated_ngram_share"]:
        flags.append(NGRAM_PADDING)
        reasons.append(
            f"{NGRAM_PADDING}: {padding:.2f} of word {t['ngram_n']}-grams repeat "
            f"(max {t['max_repeated_ngram_share']:.2f})"
        )
    return {
        "review_flags": flags,
        "review_reasons": reasons,
        "low_reliability": bool(flags),
    }
