# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import pathlib
import re
import sys

import pytest

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

import component_correlation

DOC = pathlib.Path("docs/validation/effective-weights.md")
COMPONENTS = ("lexical", "syntactic", "semantic", "readability")


@pytest.fixture(scope="module")
def result():
    return component_correlation.compute()


def test_cross_component_effective_weights_and_length_share_reported(result):
    assert result["n_passages"] == 12
    for a in COMPONENTS:
        assert result["correlation"][a][a] == pytest.approx(1.0)
        for b in COMPONENTS:
            assert result["correlation"][a][b] == pytest.approx(
                result["correlation"][b][a]
            )
    assert sum(result["effective_weights"].values()) == pytest.approx(1.0, abs=1e-6)
    assert 0.0 <= result["length_share"] <= 1.0

    text = DOC.read_text(encoding="utf-8")
    assert "## Correlation matrix" in text
    assert "## Effective weights" in text
    for c in COMPONENTS:
        assert f"| {c} |" in text
    match = re.search(r"length_share = (\d\.\d{3})", text)
    assert match is not None
    assert 0.0 <= float(match.group(1)) <= 1.0


def test_render_reports_length_share_and_weights():
    fixed = {
        "n_passages": 12,
        "passages": [],
        "nominal_weights": {
            "lexical": 0.30,
            "syntactic": 0.25,
            "semantic": 0.30,
            "readability": 0.15,
        },
        "correlation": {
            a: {b: 1.0 if a == b else 0.5 for b in COMPONENTS} for a in COMPONENTS
        },
        "effective_weights": {
            "lexical": 0.111,
            "syntactic": 0.222,
            "semantic": 0.333,
            "readability": 0.334,
        },
        "length_share": 0.6789,
    }
    text = component_correlation.render(fixed)
    assert "length_share = 0.679" in text
    assert "R² = 0.679" in text
    for c in COMPONENTS:
        assert f"| {c} | {fixed['nominal_weights'][c]:.2f} |" in text
        assert f"| {c} | {fixed['effective_weights'][c]:.3f} |" in text
    assert "No cap is enforced" in text
    assert "Largest divergence from nominal: lexical" in text
