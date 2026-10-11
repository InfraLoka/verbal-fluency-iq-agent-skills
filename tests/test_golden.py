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


def test_golden_sources_exclude_untracked_personal_corpus():
    assert GOLDEN_SOURCES
    assert all("example/rahmat" not in s for s in GOLDEN_SOURCES)


def test_run_pipeline_shape():
    out = run_pipeline("The cat sat on the mat. " * 20)
    assert set(out) == {"lang", "vfs", "iq", "ci", "edu", "word_count"}
    assert len(out["ci"]) == 2


@pytest.mark.parametrize("source", GOLDEN_SOURCES)
def test_golden_scores_match(source):
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))[source]
    text = (ROOT / source).read_text(encoding="utf-8")
    actual = run_pipeline(text)
    assert actual["lang"] == expected["lang"]
    assert actual["vfs"] == pytest.approx(expected["vfs"], abs=0.5)
    assert abs(actual["iq"] - expected["iq"]) <= 1
    assert actual["edu"] == expected["edu"]
    assert actual["word_count"] == expected["word_count"]
    assert len(actual["ci"]) == len(expected["ci"]) == 2
    for a, e in zip(actual["ci"], expected["ci"]):
        assert abs(a - e) <= 1
