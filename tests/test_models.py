# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Shared model loader, batched model calls and determinism (G-027, G-028, G-029)."""

import sys
import threading

import numpy as np
import pytest

sys.path.insert(0, "mcp-server")

from tools import models, preprocess, semantic, syntactic
from tools.preprocess import preprocess_text
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

from tests.helpers import corpus_text


@pytest.fixture
def fresh_models():
    models.reset_cache()
    yield models
    models.reset_cache()


def test_models_loaded_once_via_shared_loader(fresh_models, monkeypatch):
    text = corpus_text("en_news_report")
    prep = preprocess_text(text, "en")
    analyze_syntactic(prep["sentences"], "en")
    analyze_semantic(prep["text_clean"], prep["sentences"], "en")
    preprocess_text(text, "en")
    assert models.LOAD_COUNTS["en_core_web_sm"] == 1
    assert models.LOAD_COUNTS[models.SENTENCE_MODEL_NAME] == 1
    for module in (preprocess, syntactic, semantic):
        assert not hasattr(module, "_nlp_cache"), module.__name__
        assert not hasattr(module, "_get_nlp"), module.__name__

    models.reset_cache()
    threads = [
        threading.Thread(target=models.get_spacy, args=("id",)) for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert models.LOAD_COUNTS["xx_ent_wiki_sm"] == 1
    assert "sentencizer" in models.get_spacy("id").pipe_names

    monkeypatch.setitem(models.SPACY_MODELS, "en", "no_such_model_installed")
    models.reset_cache()
    with pytest.raises(models.ModelUnavailableError) as excinfo:
        models.get_spacy("en")
    assert "requirements-models.txt" in str(excinfo.value)
    assert excinfo.value.code == "MODEL_UNAVAILABLE"


def test_semantic_scores_stable_across_repeated_runs(fresh_models):
    prep = preprocess_text(corpus_text("id_news_report"), "id")
    runs = [
        analyze_semantic(prep["text_clean"], prep["sentences"], "id") for _ in range(3)
    ]
    models.reset_cache()  # a fresh model load must give the same numbers
    runs.append(analyze_semantic(prep["text_clean"], prep["sentences"], "id"))
    assert all(run == runs[0] for run in runs)
    assert models.SENTENCE_MODEL_REVISION == "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


class _SpyPipeline:
    """Wraps a spaCy pipeline: allows nlp.pipe, forbids per-sentence nlp()."""

    def __init__(self, nlp):
        self._nlp = nlp
        self.pipe_calls = 0

    def pipe(self, texts, **kwargs):
        self.pipe_calls += 1
        return self._nlp.pipe(texts, **kwargs)

    def __call__(self, text):
        raise AssertionError("per-sentence nlp() call; use nlp.pipe")


class _SpyModel:
    def __init__(self, model):
        self._model = model
        self.calls: list[dict] = []

    def encode(self, texts, **kwargs):
        self.calls.append({"n": len(texts), **kwargs})
        return self._model.encode(texts, **kwargs)


def test_syntactic_and_semantic_batch_model_calls(monkeypatch):
    prep = preprocess_text(corpus_text("en_academic_essay"), "en")
    sentences = prep["sentences"]
    spy_nlp = _SpyPipeline(models.get_spacy("en"))
    monkeypatch.setattr(models, "get_spacy", lambda lang: spy_nlp)
    result = analyze_syntactic(sentences, "en")
    assert spy_nlp.pipe_calls == 1
    assert result["score"] is not None

    spy_model = _SpyModel(models.get_sentence_model())
    monkeypatch.setattr(models, "get_sentence_model", lambda: spy_model)
    monkeypatch.setattr(semantic, "_entity_labels", lambda text, lang: [])
    sem = analyze_semantic(prep["text_clean"], sentences, "en")
    assert len(spy_model.calls) == 1
    assert spy_model.calls[0]["n"] == len(sentences)
    assert spy_model.calls[0]["batch_size"] == models.ENCODE_BATCH_SIZE

    emb = models.get_sentence_model().encode([s["text"] for s in sentences])
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    expected = float(np.mean(np.sum(emb[:-1] * emb[1:], axis=1)))
    assert sem["adjacent_sentence_similarity"] == pytest.approx(expected, abs=1e-3)
