# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Shared, thread-safe model loading (G-028).

Every spaCy pipeline and the sentence-embedding model are loaded once per
process through this module, under one lock. A missing model raises
``ModelUnavailableError`` naming the command that installs it, instead of a raw
``OSError`` or a network error in the middle of a request.

Model names and the embedding model revision are pinned here (G-029) so a
score can be tied to the exact weights that produced it.
"""

import logging
import threading
import time
from collections import Counter
from typing import Any

SPACY_MODELS = {"en": "en_core_web_sm", "id": "xx_ent_wiki_sm"}
SENTENCE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SENTENCE_MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
ENCODE_BATCH_SIZE = 32
SPACY_INSTALL_HINT = "pip install -r requirements-models.txt"

logger = logging.getLogger("verbal_fluency.models")
_lock = threading.RLock()
_spacy: dict[str, Any] = {}
_sentence: dict[str, Any] = {}
# Number of times each model was actually loaded in this process (tests assert 1).
LOAD_COUNTS: Counter[str] = Counter()


class ModelUnavailableError(RuntimeError):
    """A required model is not installed or cannot be loaded."""

    code = "MODEL_UNAVAILABLE"


def _log_load(name: str, revision: str | None, started: float) -> None:
    fields = {
        "model": name,
        "revision": revision,
        "seconds": round(time.perf_counter() - started, 2),
    }
    logger.info("model_loaded", extra={"fields": fields})


def get_spacy(lang: str) -> Any:
    """The shared spaCy pipeline for ``lang`` (with sentence boundaries)."""
    if lang not in SPACY_MODELS:
        raise ValueError(f"no spaCy model configured for language {lang!r}")
    with _lock:
        if lang not in _spacy:
            import spacy

            started = time.perf_counter()
            name = SPACY_MODELS[lang]
            try:
                nlp = spacy.load(name)
            except OSError as exc:
                raise ModelUnavailableError(
                    f"spaCy model {name!r} is not installed; run: {SPACY_INSTALL_HINT}"
                ) from exc
            # xx_ent_wiki_sm has no parser or sentencizer; add one so doc.sents
            # works for Indonesian. NER is unaffected.
            if not {"sentencizer", "parser", "senter"} & set(nlp.pipe_names):
                nlp.add_pipe("sentencizer", first=True)
            _spacy[lang] = nlp
            LOAD_COUNTS[name] += 1
            _log_load(name, None, started)
        return _spacy[lang]


def get_sentence_model() -> Any:
    """The shared sentence-embedding model at the pinned revision."""
    with _lock:
        if "model" not in _sentence:
            from sentence_transformers import SentenceTransformer

            started = time.perf_counter()
            try:
                model = SentenceTransformer(
                    SENTENCE_MODEL_NAME, revision=SENTENCE_MODEL_REVISION
                )
            except Exception as exc:  # network, cache and file errors alike
                raise ModelUnavailableError(
                    f"sentence model {SENTENCE_MODEL_NAME!r} at revision "
                    f"{SENTENCE_MODEL_REVISION} could not be loaded ({exc}); "
                    "download it once with network access or restore the "
                    "Hugging Face cache"
                ) from exc
            _sentence["model"] = model
            LOAD_COUNTS[SENTENCE_MODEL_NAME] += 1
            _log_load(SENTENCE_MODEL_NAME, SENTENCE_MODEL_REVISION, started)
        return _sentence["model"]


def reset_cache() -> None:
    """Forget loaded models and load counts (tests only)."""
    with _lock:
        _spacy.clear()
        _sentence.clear()
        LOAD_COUNTS.clear()
