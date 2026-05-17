from typing import List
import spacy

_nlp_cache: dict = {}

SUBORDINATE_DEPS = {"advcl", "relcl", "acl", "csubj", "ccomp", "xcomp"}
CLAUSE_DEPS = SUBORDINATE_DEPS | {"ROOT"}


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


def analyze_syntactic(sentences: List[dict], lang: str) -> dict:
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
            evidence.append({
                "sentence_idx": sent_data["idx"],
                "sentence": sent_data["text"],
                "triggered_by": triggered,
            })

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

    score = round(msl_score * 0.30 + cd_score * 0.35 + si_score * 0.25 + dd_score * 0.10, 1)

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": dep_depth,
        "passive_ratio": passive_ratio,
        "score": score,
        "evidence": evidence[:3],
    }
