# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import textstat

from tools.evidence import rank_evidence
from tools.policy import require_supported_language


def _count_id_syllables(word: str) -> int:
    vowels = set("aeiouAEIOU")
    count, prev_vowel = 0, False
    for ch in word:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    return max(1, count)


def _syllable_count(word: str, lang: str) -> int:
    if lang == "id":
        return _count_id_syllables(word)
    return textstat.syllable_count(word)


def analyze_readability(text: str, lang: str, sentences: list[dict]) -> dict:
    """Readability indices of ``text``; evidence cites ``sentences`` (the
    preprocess sentences, so S-numbers match every other analyser, G-038)."""
    require_supported_language(lang)
    textstat.set_lang("en_US")

    candidates = []
    for sent in sentences:
        words = sent["text"].split()
        if not words:
            continue
        polysyllabic = sum(1 for w in words if _syllable_count(w, lang) >= 3)
        density = round(polysyllabic / len(words), 2)
        candidates.append(
            {
                "sentence_idx": sent["idx"],
                "sentence": sent["text"],
                "triggered_by": [f"polysyllabic_density:{density}"],
                "contribution": density,
            }
        )

    if lang == "id":
        words_all = text.split()
        avg_sent_len = len(words_all) / max(1, len(sentences))
        avg_syl = sum(_count_id_syllables(w) for w in words_all) / max(
            1, len(words_all)
        )
        flesch = round(206.835 - 1.015 * avg_sent_len - 84.6 * avg_syl, 1)
    else:
        flesch = round(textstat.flesch_reading_ease(text), 1)

    fog = round(textstat.gunning_fog(text), 1)
    ari = round(textstat.automated_readability_index(text), 1)
    cl = round(textstat.coleman_liau_index(text), 1)

    fog_score = min(100.0, max(0.0, (fog - 6) / 12 * 100))
    ari_score = min(100.0, max(0.0, (ari - 5) / 11 * 100))
    cl_score = min(100.0, max(0.0, (cl - 5) / 11 * 100))
    flesch_score = min(100.0, max(0.0, 100 - flesch))

    score = round(
        fog_score * 0.35 + ari_score * 0.30 + cl_score * 0.20 + flesch_score * 0.15, 1
    )

    return {
        "flesch_reading_ease": flesch,
        "gunning_fog": fog,
        "ari": ari,
        "coleman_liau": cl,
        "score": score,
        "evidence": rank_evidence(candidates),
    }
