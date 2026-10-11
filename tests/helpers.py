# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Shared test helpers: synthetic reference corpus and policy fixtures."""

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "tests" / "fixtures" / "reference_corpus"

sys.path.insert(0, str(ROOT / "mcp-server"))


def corpus_manifest() -> list[dict]:
    data = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    return data["passages"]


def corpus_text(name: str) -> str:
    return (CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def validated_policy() -> dict:
    """The shipped policy with every language marked validated.

    Only for unit tests of the computed (non-withheld) paths. Production code has
    no per-call override; validation is a config change backed by a study.
    """
    from tools.policy import load_policy

    pol = copy.deepcopy(load_policy())
    for flags in pol["languages"].values():
        flags["iq_validated"] = True
        flags["education_validated"] = True
    return pol


def ok_gate(lang: str = "en", policy: dict | None = None) -> dict:
    """A gate that passes every input check (status OK under validated_policy)."""
    from tools.policy import evaluate_gates

    return evaluate_gates(
        {"lang": lang, "confidence": 0.99, "mixed_language_share": 0.0},
        alpha_word_count=400,
        terminal_mark_count=20,
        provenance="supervised_unaided",
        text_type="formal_prose",
        policy=policy if policy is not None else validated_policy(),
    )
