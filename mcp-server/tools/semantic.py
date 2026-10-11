# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Adjacent-sentence semantic metrics.

``adjacent_sentence_similarity`` is the mean cosine similarity of neighbouring
sentence embeddings from a paraphrase model. It measures topical overlap, not
argument quality (F-030). Its 0-100 scaling is read per language from
``config/semantic_scaling.json`` and is uncalibrated.

Named entities are reported for information only and never scored (F-012).
"""

import json
import os
from collections import defaultdict

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from tools.policy import load_policy

_model_cache: dict = {}
_nlp_cache: dict = {}
_scaling_cache: dict = {}

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

# Nominal sub-weights; unavailable parts are dropped and the rest renormalised.
SUB_WEIGHTS = {"similarity": 0.45, "drift": 0.25, "chain": 0.20}
DRIFT_SCALE_MAX = 0.3


def _get_model():
    if "model" not in _model_cache:
        _model_cache["model"] = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _model_cache["model"]


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        _nlp_cache[lang] = spacy.load(
            "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        )
    return _nlp_cache[lang]


def _load_scaling() -> dict:
    if "scaling" not in _scaling_cache:
        path = os.path.join(_CONFIG_DIR, "semantic_scaling.json")
        with open(path, encoding="utf-8") as f:
            _scaling_cache["scaling"] = json.load(f)
    return _scaling_cache["scaling"]


def _scaling_for(lang: str) -> dict:
    return _load_scaling()["languages"][lang]


def _entity_labels(text: str, lang: str) -> list[str]:
    """Sorted distinct NER labels; label sets differ per model (informational)."""
    return sorted({ent.label_ for ent in _get_nlp(lang)(text).ents})


def _unavailable(note: str) -> dict:
    return {
        "adjacent_sentence_similarity": None,
        "topic_drift_index": None,
        "lexical_chain_density": None,
        "entity_labels": [],
        "transitions": 0,
        "scaling_status": None,
        "score": None,
        "evidence": [],
        "note": note,
    }


def analyze_semantic(
    text: str,
    sentences: list[dict],
    lang: str,
    segment_boundaries: list[int] | None = None,
    policy: dict | None = None,
) -> dict:
    """Semantic metrics over adjacent sentences.

    segment_boundaries: optional list of sentence ``idx`` values at which a NEW
    document begins. Adjacent pairs whose target sentence starts a new document
    are skipped, so multi-file subjects are not penalised for spurious drift at
    document seams. Default None => all adjacent pairs are scored.

    The score is None (not an imputed 50) when it cannot be measured (F-016).
    """
    pol = policy if policy is not None else load_policy()
    if len(sentences) < 2:
        return _unavailable("Too few sentences for semantic analysis")

    boundaries = set(segment_boundaries or [])

    model = _get_model()
    texts = [s["text"] for s in sentences]
    embeddings = model.encode(texts)

    evidence = []
    similarities = []
    for i in range(len(embeddings) - 1):
        # Skip transitions that straddle a document boundary.
        if sentences[i + 1]["idx"] in boundaries:
            continue
        sim = float(cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0])
        similarities.append(sim)
        note = (
            "high overlap"
            if sim > 0.75
            else "low overlap"
            if sim < 0.50
            else "moderate overlap"
        )
        evidence.append(
            {
                "sentence_idx_from": sentences[i]["idx"],
                "sentence_idx_to": sentences[i + 1]["idx"],
                "similarity": round(sim, 3),
                "note": note,
            }
        )

    if not similarities:
        # Every adjacent pair straddled a document boundary.
        return _unavailable(
            "No within-document transitions available for semantic analysis"
        )

    similarity = round(float(np.mean(similarities)), 3)
    # Drift is the spread of similarities; with too few transitions it is 0 by
    # construction, so it is not measured at all (F-028).
    topic_drift_index = None
    if len(similarities) >= pol["min_drift_transitions"]:
        topic_drift_index = round(float(np.std(similarities)), 3)

    word_positions: dict = defaultdict(set)
    for i, s in enumerate(sentences):
        for w in s["text"].lower().split():
            if len(w) > 4:
                word_positions[w].add(i)
    chained = sum(1 for pos in word_positions.values() if len(pos) > 1)
    total = len(word_positions)
    lexical_chain_density = round(chained / total, 3) if total else 0.0

    scaling = _scaling_for(lang)
    low, high = scaling["similarity_min"], scaling["similarity_max"]
    parts = {
        "similarity": min(100.0, max(0.0, (similarity - low) / (high - low) * 100)),
        "chain": min(100.0, max(0.0, (lexical_chain_density - 0.1) / 0.5 * 100)),
    }
    if topic_drift_index is not None:
        parts["drift"] = min(
            100.0, max(0.0, (1 - topic_drift_index / DRIFT_SCALE_MAX) * 100)
        )
    weight_total = sum(SUB_WEIGHTS[k] for k in parts)
    score = round(sum(parts[k] * SUB_WEIGHTS[k] for k in parts) / weight_total, 1)

    return {
        "adjacent_sentence_similarity": similarity,
        "topic_drift_index": topic_drift_index,
        "lexical_chain_density": lexical_chain_density,
        "entity_labels": _entity_labels(text, lang),
        "transitions": len(similarities),
        "scaling_status": _load_scaling()["status"],
        "score": score,
        "evidence": evidence[:5],
    }
