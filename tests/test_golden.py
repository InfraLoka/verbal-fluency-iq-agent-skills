# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from capture_golden import GOLDEN_SOURCES
from pipeline import run_pipeline

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "golden_scores.json"
RESULT_KEYS = {
    "status",
    "statuses",
    "reasons",
    "lang",
    "lang_confidence",
    "language_norm_unvalidated",
    "provenance",
    "text_type",
    "policy_version",
    "style_index",
    "style_index_label",
    "style_band",
    "components",
    "iq",
    "percentile",
    "classification",
    "range",
    "range_label",
    "withheld_reason",
    "mental_age",
    "text_complexity_band",
    "text_complexity_consistency",
    "word_count",
    "token_count",
    "low_reliability",
    "reliability_reasons",
}
COMPONENTS = ("lexical", "syntactic", "semantic", "readability")


def test_golden_sources_exclude_untracked_personal_corpus():
    assert GOLDEN_SOURCES
    assert all("example/rahmat" not in s for s in GOLDEN_SOURCES)


def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert set(out) == RESULT_KEYS
    assert out["status"] == "INSUFFICIENT_TEXT"
    assert out["iq"] is None
    assert out["range"] is None


@pytest.mark.parametrize("source", GOLDEN_SOURCES)
def test_golden_scores_match(source):
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))[source]
    text = (ROOT / source).read_text(encoding="utf-8")
    actual = run_pipeline(text)
    assert set(actual) == set(expected)
    for key in (
        "lang",
        "status",
        "statuses",
        "style_band",
        "iq",
        "percentile",
        "classification",
        "range",
        "mental_age",
        "text_complexity_band",
        "word_count",
        "token_count",
        "low_reliability",
    ):
        assert actual[key] == expected[key], key
    assert actual["style_index"] == pytest.approx(expected["style_index"], abs=0.5)
    for c in COMPONENTS:
        if expected["components"][c] is None:
            assert actual["components"][c] is None
        else:
            assert actual["components"][c] == pytest.approx(
                expected["components"][c], abs=0.5
            )
