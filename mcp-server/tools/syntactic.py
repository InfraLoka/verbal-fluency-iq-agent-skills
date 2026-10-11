# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re

import spacy

_nlp_cache: dict = {}

SUBORDINATE_DEPS = {"advcl", "relcl", "acl", "csubj", "ccomp", "xcomp"}
CLAUSE_DEPS = SUBORDINATE_DEPS | {"ROOT"}

# --- Indonesian rule-based resources (xx_ent_wiki_sm has no dependency parser) ---
# Konjungsi subordinatif (subordinating conjunctions).
ID_SUBORDINATORS = {
    "yang",
    "karena",
    "sehingga",
    "ketika",
    "meskipun",
    "walaupun",
    "jika",
    "kalau",
    "agar",
    "supaya",
    "sebab",
    "sejak",
    "setelah",
    "sebelum",
    "bahwa",
    "hingga",
    "sampai",
    "apabila",
    "bilamana",
    "seandainya",
    "andai",
    "tatkala",
    "seraya",
    "sambil",
    "selama",
    "sementara",
    "asalkan",
    "kecuali",
    "biarpun",
    "sekalipun",
    "daripada",
    "seolah",
    "seakan",
}
# Konjungsi koordinatif yang menghubungkan klausa (clause-joining coordinators).
ID_CLAUSE_COORDINATORS = {
    "dan",
    "atau",
    "tetapi",
    "tapi",
    "namun",
    "melainkan",
    "sedangkan",
    "lalu",
    "kemudian",
    "serta",
    "padahal",
}
# Morphological passive: di-/ter- verbal prefixes (e.g. ditipu, terlihat, dianggap).
# Requires >= 4 letters after the prefix so the locative preposition "di" (a separate
# 2-letter token) and short noise tokens are not counted.
_ID_PASSIVE_RE = re.compile(r"^(di|ter)[a-z]{4,}$")
# Words that match the di-/ter- pattern but are not passive verbs.
ID_PASSIVE_EXCLUSIONS = frozenset(
    {
        "terhadap",
        "tersebut",
        "terdapat",
        "terutama",
        "termasuk",
        "terakhir",
        "terlalu",
        "terus",
        "tertentu",
        "dirinya",
        "diri",
        "diskusi",
        "direktur",
        "dinamika",
        "distribusi",
        "diagram",
        "dimensi",
        "digital",
        "diploma",
        "diet",
        "dinas",
    }
)


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        _nlp_cache[lang] = spacy.load(model)
    return _nlp_cache[lang]


def _dep_depth(token) -> int:
    depth = 0
    seen = set()
    while token.head != token and id(token) not in seen:
        seen.add(id(token))
        token = token.head
        depth += 1
    return depth


def _analyze_syntactic_id(sentences: list[dict]) -> dict:
    """Parser-free Indonesian syntactic analysis.

    xx_ent_wiki_sm has no dependency parser, so the spaCy-dependency path collapses
    every structural metric to 0 for Indonesian. Here we compute the components that
    ARE validly measurable without a parse — clause density, subordination, and
    passive morphology — from a curated conjunction lexicon. Dependency depth is not
    measurable without a parser, so it is reported as None (not 0) and excluded from
    the weighted score, with the remaining weights renormalised.
    """
    lengths, clause_counts, sub_counts = [], [], []
    passive_count = 0
    evidence = []

    for sent_data in sentences:
        words = [w for w in sent_data["text"].split() if any(c.isalpha() for c in w)]
        lengths.append(len(words))
        lower = [re.sub(r"[^a-z\-]", "", w.lower()) for w in words]

        subs = sum(1 for w in lower if w in ID_SUBORDINATORS)
        coords = sum(1 for w in lower if w in ID_CLAUSE_COORDINATORS)
        sub_counts.append(subs)
        clause_counts.append(1 + subs + coords)

        passives = [
            w
            for w in lower
            if _ID_PASSIVE_RE.match(w) and w not in ID_PASSIVE_EXCLUSIONS
        ]
        is_passive = bool(passives)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 1:
            triggered.append(f"subordinators:{subs}")
        if is_passive:
            triggered.append(f"passive:{passives[0]}")
        if triggered:
            evidence.append(
                {
                    "sentence_idx": sent_data["idx"],
                    "sentence": sent_data["text"],
                    "triggered_by": triggered,
                }
            )

    n = len(sentences) or 1
    msl = round(sum(lengths) / n, 1)
    clause_density = round(sum(clause_counts) / n, 2)
    sub_index = round(sum(sub_counts) / n, 3)
    passive_ratio = round(passive_count / n, 3)

    # Reuse the SAME component-scoring curves as English so scales stay comparable.
    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    # Dependency depth (10% weight) is unmeasurable for id → drop it and renormalise
    # the remaining 0.30/0.35/0.25 weights (sum 0.90) to sum to 1.0.
    score = round(
        msl_score * (0.30 / 0.90) + cd_score * (0.35 / 0.90) + si_score * (0.25 / 0.90),
        1,
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": None,  # honest: not measurable without a parser
        "passive_ratio": passive_ratio,
        "score": score,
        "evidence": evidence[:3],
        "note": (
            "Indonesian syntactic metrics computed via rule-based morphology; "
            "dependency depth not measured (no parser for id)."
        ),
    }


def analyze_syntactic(sentences: list[dict], lang: str) -> dict:
    if lang == "id":
        return _analyze_syntactic_id(sentences)

    nlp = _get_nlp(lang)
    lengths, clause_counts, sub_counts, dep_depths = [], [], [], []
    passive_count = 0
    evidence = []

    for sent_data in sentences:
        doc = nlp(sent_data["text"])
        words = [t for t in doc if not t.is_space and not t.is_punct]
        lengths.append(len(words))

        clauses = sum(1 for t in doc if t.dep_ in CLAUSE_DEPS)
        clause_counts.append(max(1, clauses))

        subs = sum(1 for t in doc if t.dep_ in SUBORDINATE_DEPS)
        sub_counts.append(subs)

        max_depth = max((_dep_depth(t) for t in doc if not t.is_space), default=0)
        dep_depths.append(max_depth)

        is_passive = any(t.dep_ in {"nsubjpass", "auxpass", "aux:pass"} for t in doc)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 2:
            triggered.append(f"subordinate_clauses:{subs}")
        if max_depth >= 6:
            triggered.append(f"dep_depth:{max_depth}")
        if is_passive:
            triggered.append("passive_voice")
        if triggered:
            evidence.append(
                {
                    "sentence_idx": sent_data["idx"],
                    "sentence": sent_data["text"],
                    "triggered_by": triggered,
                }
            )

    n = len(sentences)
    msl = round(sum(lengths) / n, 1) if n else 0
    clause_density = round(sum(clause_counts) / n, 2) if n else 0
    sub_index = round(sum(sub_counts) / n, 3) if n else 0
    dep_depth = round(sum(dep_depths) / n, 1) if n else 0
    passive_ratio = round(passive_count / n, 3) if n else 0

    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    dd_score = min(100.0, max(0.0, (dep_depth - 2) / 8 * 100))

    score = round(
        msl_score * 0.30 + cd_score * 0.35 + si_score * 0.25 + dd_score * 0.10, 1
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": dep_depth,
        "passive_ratio": passive_ratio,
        "score": score,
        "evidence": evidence[:3],
    }
