# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Scoring provenance: which algorithm, norms, libraries and models made a score.

Every style index, IQ result and report carries ``scoring_provenance`` so a stored
score can be tied to the code and data that produced it (G-011).

Bump ``SCORING_VERSION`` whenever a weight, threshold, norm or scoring rule
changes; the config hashes change automatically with any config edit.
"""

import functools
import hashlib
import importlib.metadata
import json
import os
from typing import Any

from tools import models

SCORING_VERSION = "3.0.0"
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CONFIG_FILES = (
    "validation.json",
    "iq_norms.json",
    "edu_norms.json",
    "semantic_scaling.json",
    "id_syllables.json",
    "robustness.json",
)
NORMS_FILES = ("iq_norms.json", "edu_norms.json", "semantic_scaling.json")
LIBRARIES = (
    "spacy",
    "sentence-transformers",
    "transformers",
    "torch",
    "textstat",
    "lexicalrichness",
    "wordfreq",
    "langid",
    "langdetect",
    "PySastrawi",
    "numpy",
    "en_core_web_sm",
    "xx_ent_wiki_sm",
)


def _version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def config_sha256() -> dict[str, str]:
    """SHA-256 of each config file's bytes."""
    out = {}
    for name in CONFIG_FILES:
        with open(os.path.join(CONFIG_DIR, name), "rb") as f:
            out[name] = hashlib.sha256(f.read()).hexdigest()
    return out


def norms_versions() -> dict[str, dict[str, Any]]:
    """``version`` and ``effective_date`` declared by each norms file."""
    out = {}
    for name in NORMS_FILES:
        with open(os.path.join(CONFIG_DIR, name), encoding="utf-8") as f:
            data = json.load(f)
        out[name] = {
            "version": data.get("version"),
            "effective_date": data.get("effective_date"),
        }
    return out


@functools.cache
def scoring_provenance() -> dict[str, Any]:
    """Computed once per process; copy before mutating."""
    return {
        "scoring_version": SCORING_VERSION,
        "config_sha256": config_sha256(),
        "norms": norms_versions(),
        "libraries": {name: _version(name) for name in LIBRARIES},
        "models": {
            "spacy": dict(models.SPACY_MODELS),
            "sentence_transformer": {
                "name": models.SENTENCE_MODEL_NAME,
                "revision": models.SENTENCE_MODEL_REVISION,
            },
        },
    }
