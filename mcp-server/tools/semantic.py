from collections import defaultdict
from typing import List

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_model_cache: dict = {}
_nlp_cache: dict = {}

ABSTRACT_TYPES = {"LAW", "ORG", "NORP", "EVENT", "WORK_OF_ART", "LANGUAGE"}
CONCRETE_TYPES = {"PERSON", "GPE", "LOC", "FAC", "PRODUCT"}


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


def analyze_semantic(text: str, sentences: List[dict], lang: str) -> dict:
    if len(sentences) < 2:
        return {
            "argument_coherence": None,
            "topic_drift_index": None,
            "lexical_chain_density": 0.0,
            "entity_sophistication": "MINIMAL",
            "score": 50.0,
            "evidence": [],
            "note": "Too few sentences for full semantic analysis",
        }

    model = _get_model()
    texts = [s["text"] for s in sentences]
    embeddings = model.encode(texts)

    evidence = []
    coherence_vals = []
    for i in range(len(embeddings) - 1):
        sim = float(cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0])
        coherence_vals.append(sim)
        note = (
            "causal chain detected"
            if sim > 0.75
            else "slight drift"
            if sim < 0.50
            else "moderate transition"
        )
        evidence.append(
            {
                "sentence_idx_from": sentences[i]["idx"],
                "sentence_idx_to": sentences[i + 1]["idx"],
                "coherence": round(sim, 3),
                "note": note,
            }
        )

    argument_coherence = round(float(np.mean(coherence_vals)), 3)
    topic_drift_index = round(float(np.std(coherence_vals)), 3)

    nlp = _get_nlp(lang)
    doc = nlp(text)
    entity_types = {ent.label_ for ent in doc.ents}
    if entity_types & ABSTRACT_TYPES:
        entity_sophistication = "ABSTRACT"
    elif entity_types & CONCRETE_TYPES:
        entity_sophistication = "CONCRETE"
    else:
        entity_sophistication = "MINIMAL"

    word_positions: dict = defaultdict(set)
    for i, s in enumerate(sentences):
        for w in s["text"].lower().split():
            if len(w) > 4:
                word_positions[w].add(i)
    chained = sum(1 for pos in word_positions.values() if len(pos) > 1)
    total = len(word_positions)
    lexical_chain_density = round(chained / total, 3) if total else 0.0

    coh_score = min(100.0, max(0.0, (argument_coherence - 0.3) / 0.6 * 100))
    drift_score = min(100.0, max(0.0, (1 - topic_drift_index / 0.3) * 100))
    chain_score = min(100.0, max(0.0, (lexical_chain_density - 0.1) / 0.5 * 100))
    entity_score = {"ABSTRACT": 80.0, "CONCRETE": 50.0, "MINIMAL": 20.0}[
        entity_sophistication
    ]

    score = round(
        coh_score * 0.45
        + drift_score * 0.25
        + chain_score * 0.20
        + entity_score * 0.10,
        1,
    )

    return {
        "argument_coherence": argument_coherence,
        "topic_drift_index": topic_drift_index,
        "lexical_chain_density": lexical_chain_density,
        "entity_sophistication": entity_sophistication,
        "score": score,
        "evidence": evidence[:5],
    }
