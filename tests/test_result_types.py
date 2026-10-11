# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Real tool outputs validate against the TypedDict result models (G-040)."""

import json
import sys

import pytest
from pydantic import ConfigDict, TypeAdapter, with_config

sys.path.insert(0, "mcp-server")

from tools import result_types

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain

SHORT = "The committee approved the new budget for the city library."
CHAIN_KEYS = {
    "lang": "tool_detect_language",
    "prep": "tool_preprocess_text",
    "gate": "tool_evaluate_gates",
    "lexical": "tool_analyze_lexical",
    "syntactic": "tool_analyze_syntactic",
    "semantic": "tool_analyze_semantic",
    "readability": "tool_analyze_readability",
    "vfs": "tool_compute_verbal_fluency_score",
    "iq": "tool_predict_iq",
    "mental_age": "tool_predict_mental_age",
    "band": "tool_estimate_text_complexity_band",
    "report": "tool_generate_report",
}


def _strict(model: type) -> TypeAdapter:
    """A validator that also rejects keys the model does not declare."""
    strict = with_config(ConfigDict(extra="forbid"))(model)
    return TypeAdapter(strict)


def _check(tool: str, raw: str) -> None:
    payload = json.loads(raw)
    signed = {k: payload.pop(k) for k in ("input_sha256", "kind", "_sig")}
    _strict(result_types.SignedFields).validate_python(signed)
    _strict(result_types.TOOL_RESULT_TYPES[tool]).validate_python(payload)


@pytest.mark.parametrize("passage", ["en_news_report", "id_news_report"])
def test_tool_results_validate_against_result_models(passage):
    server = load_server()
    assert set(result_types.TOOL_RESULT_TYPES) == {
        name for name in vars(server) if name.startswith("tool_")
    }
    out = run_chain(server, corpus_text(passage))
    for key, tool in CHAIN_KEYS.items():
        _check(tool, out[key])

    short = run_chain(server, SHORT)  # unavailable and withheld shapes
    for key, tool in CHAIN_KEYS.items():
        _check(tool, short[key])

    error = json.loads(server.tool_analyze_lexical("{bad", "en"))
    _strict(result_types.ToolError).validate_python(error)

    lexical = json.loads(out["lexical"])
    lexical["unexpected_key"] = 1
    with pytest.raises(ValueError):
        _strict(result_types.LexicalResult).validate_python(lexical)
