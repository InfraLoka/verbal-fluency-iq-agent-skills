from collections import Counter
from typing import List

from lexicalrichness import LexicalRichness


def _mattr(tokens: List[str], window: int = 50) -> float:
    if len(tokens) < window:
        return len(set(tokens)) / len(tokens) if tokens else 0.0
    ttrs = [
        len(set(tokens[i : i + window])) / window
        for i in range(len(tokens) - window + 1)
    ]
    return sum(ttrs) / len(ttrs)


def analyze_lexical(tokens: List[str], sentences: List[dict], lang: str) -> dict:
    alpha = [t for t in tokens if t.isalpha()]
    if not alpha:
        return {"score": 0.0, "error": "No alphabetic tokens found"}

    lower = [t.lower() for t in alpha]

    if lang == "id":
        try:
            from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

            stemmer = StemmerFactory().create_stemmer()
            mattr_tokens = [stemmer.stem(t) for t in lower]
        except ImportError:
            mattr_tokens = lower
    else:
        mattr_tokens = lower

    mattr = round(_mattr(mattr_tokens), 3)

    vocd_d = None
    if len(alpha) >= 50:
        try:
            lex = LexicalRichness(" ".join(alpha))
            vocd_d = round(lex.vocd(), 1)
        except Exception:
            vocd_d = None

    freq = Counter(lower)
    hapax_count = sum(1 for f in freq.values() if f == 1)
    hapax_ratio = round(hapax_count / len(freq), 3) if freq else 0.0

    avg_word_length = round(sum(len(t) for t in alpha) / len(alpha), 1)

    content_words = [t for t in alpha if len(t) > 3]
    lexical_density = round(len(content_words) / len(alpha), 3)

    mattr_score = min(100.0, max(0.0, (mattr - 0.3) / 0.6 * 100))
    hapax_score = min(100.0, max(0.0, (hapax_ratio - 0.2) / 0.5 * 100))
    awl_score = min(100.0, max(0.0, (avg_word_length - 3.5) / 4.0 * 100))
    ld_score = min(100.0, max(0.0, (lexical_density - 0.3) / 0.4 * 100))

    score = round(
        mattr_score * 0.40 + hapax_score * 0.30 + awl_score * 0.15 + ld_score * 0.15, 1
    )

    evidence = []
    for sent in sentences:
        words = [w for w in sent["text"].split() if w.isalpha()]
        rare = [w for w in words if freq.get(w.lower(), 0) == 1 and len(w) > 5]
        if rare:
            evidence.append(
                {
                    "sentence_idx": sent["idx"],
                    "sentence": sent["text"],
                    "triggered_by": [f"hapax:{w}" for w in rare[:3]],
                }
            )

    return {
        "mattr": mattr,
        "vocd_d": vocd_d,
        "hapax_ratio": hapax_ratio,
        "lexical_density": lexical_density,
        "avg_word_length": avg_word_length,
        "score": score,
        "evidence": evidence[:3],
    }
