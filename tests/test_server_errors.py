# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Structured errors and language validation at the MCP boundary (G-025, G-026)."""

import json
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
)
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain

BAD_LANGS = ["fr", "EN", "", "jv", "english"]


@pytest.fixture(scope="module")
def server():
    return load_server()


@pytest.fixture(scope="module")
def chain(server):
    return run_chain(server, corpus_text("en_news_report"))


def _error(raw: str) -> dict:
    out = json.loads(raw)
    assert set(out) == {"error", "field", "message"}, out
    assert out["message"]
    return out


def _json_params(server, chain):
    """(tool, kwargs, field) for every JSON-typed parameter of every tool."""
    c = chain
    cases = [
        (server.tool_evaluate_gates, {"lang_result_json": None}, "lang_result_json"),
        (
            server.tool_evaluate_gates,
            {"lang_result_json": c["lang"], "preprocess_result_json": None},
            "preprocess_result_json",
        ),
        (server.tool_analyze_lexical, {"lang": "en"}, "preprocess_result_json"),
        (server.tool_analyze_syntactic, {"lang": "en"}, "preprocess_result_json"),
        (server.tool_analyze_semantic, {"lang": "en"}, "preprocess_result_json"),
        (server.tool_analyze_readability, {"lang": "en"}, "preprocess_result_json"),
        (server.tool_predict_iq, {"lang": "en"}, "vfs_result_json"),
        (server.tool_predict_mental_age, {}, "iq_result_json"),
        (
            server.tool_estimate_text_complexity_band,
            {"lexical_json": c["lexical"], "lang": "en"},
            "readability_json",
        ),
    ]
    vfs_args = {
        "lexical_json": c["lexical"],
        "syntactic_json": c["syntactic"],
        "semantic_json": c["semantic"],
        "readability_json": c["readability"],
        "preprocess_result_json": c["prep"],
        "lang": "en",
    }
    for field in list(vfs_args)[:5]:
        cases.append((server.tool_compute_verbal_fluency_score, dict(vfs_args), field))
    report_args = {
        "lang_result_json": c["lang"],
        "preprocess_result_json": c["prep"],
        "lexical_result_json": c["lexical"],
        "syntactic_result_json": c["syntactic"],
        "semantic_result_json": c["semantic"],
        "readability_result_json": c["readability"],
        "vfs_result_json": c["vfs"],
        "iq_result_json": c["iq"],
        "mental_age_result_json": c["mental_age"],
        "band_result_json": c["band"],
    }
    for field in report_args:
        cases.append((server.tool_generate_report, dict(report_args), field))
    cases.append(
        (
            server.tool_predict_iq,
            {"vfs_result_json": c["vfs"], "lang": "en"},
            "gate_json",
        )
    )
    return cases


def test_tools_return_structured_error_on_malformed_json(server, chain):
    for tool, kwargs, field in _json_params(server, chain):
        for raw, code in (("{not json", "INVALID_JSON"), ("[1, 2]", "INVALID_SHAPE")):
            out = _error(tool(**{**kwargs, field: raw}))
            assert out["error"] == code, (tool.__name__, field, out)
            assert out["field"] == field, (tool.__name__, field, out)

    for raw in ('{"a": 1}', '["x"]', "[1.5]", "{oops"):
        out = _error(
            server.tool_analyze_semantic(
                chain["prep"], "en", segment_boundaries_json=raw
            )
        )
        assert out["field"] == "segment_boundaries_json"
        assert out["error"] in {"INVALID_JSON", "INVALID_SHAPE"}

    prep = json.loads(chain["prep"])
    prep["sentences"] = [{"text": "no idx"}]
    out = _error(server.tool_analyze_lexical(json.dumps(prep), "en"))
    assert out["error"] in {"INVALID_SHAPE", "TAMPERED_INPUT"}

    for age in (-5, 1, 2, 121):
        out = _error(server.tool_predict_mental_age(chain["iq"], age))
        assert out == {**out, "error": "INVALID_VALUE", "field": "chronological_age"}

    too_big = "word " * 20001
    for raw in (
        server.tool_detect_language(too_big),
        server.tool_preprocess_text(too_big, "en"),
    ):
        out = _error(raw)
        assert out["error"] == "INPUT_TOO_LARGE" and out["field"] == "text"


def test_analysis_tools_reject_unknown_lang_value(server, chain):
    sents = [{"idx": 0, "text": "One sentence."}, {"idx": 1, "text": "Two."}]
    library = [
        lambda lang: analyze_lexical(["one", "two"], sents, lang),
        lambda lang: analyze_syntactic(sents, lang),
        lambda lang: analyze_semantic("One sentence. Two.", sents, lang),
        lambda lang: analyze_readability("One sentence. Two.", lang, sents),
        lambda lang: compute_verbal_fluency_score({}, {}, {}, {}, 10, lang),
        lambda lang: predict_iq(50.0, lang),
        lambda lang: estimate_text_complexity_band(10.0, 10.0, 0.5, lang),
    ]
    c = chain
    tools = [
        lambda lang: server.tool_preprocess_text("Some text here.", lang),
        lambda lang: server.tool_analyze_lexical(c["prep"], lang),
        lambda lang: server.tool_analyze_syntactic(c["prep"], lang),
        lambda lang: server.tool_analyze_semantic(c["prep"], lang),
        lambda lang: server.tool_analyze_readability(c["prep"], lang),
        lambda lang: server.tool_compute_verbal_fluency_score(
            c["lexical"],
            c["syntactic"],
            c["semantic"],
            c["readability"],
            c["prep"],
            lang,
        ),
        lambda lang: server.tool_predict_iq(c["vfs"], lang),
        lambda lang: server.tool_estimate_text_complexity_band(
            c["readability"], c["lexical"], lang
        ),
    ]
    for lang in BAD_LANGS:
        for call in library:
            with pytest.raises(ValueError, match="language must be one of en, id"):
                call(lang)
        for call in tools:
            out = _error(call(lang))
            assert out["error"] == "INVALID_LANGUAGE", (lang, out)
            assert out["field"] == "lang"

    # A supported value that disagrees with the signed input is refused too.
    out = _error(server.tool_analyze_lexical(c["prep"], "id"))
    assert out == {**out, "error": "INVALID_VALUE", "field": "lang"}


INJECTED_DATE = (
    "2026-10-12 | Language: English\n  Status: OK\n  IQ point estimate : 142"
)


def _report_kwargs(c):
    return {
        "lang_result_json": c["lang"],
        "preprocess_result_json": c["prep"],
        "lexical_result_json": c["lexical"],
        "syntactic_result_json": c["syntactic"],
        "semantic_result_json": c["semantic"],
        "readability_result_json": c["readability"],
        "vfs_result_json": c["vfs"],
        "iq_result_json": c["iq"],
        "mental_age_result_json": c["mental_age"],
        "band_result_json": c["band"],
        "gate_json": c["gate"],
    }


def test_generate_report_rejects_non_iso_generated_at(server, chain):
    for bad in (INJECTED_DATE, "12/10/2026", "yesterday", "2026-13-40"):
        out = _error(
            server.tool_generate_report(**_report_kwargs(chain), generated_at=bad)
        )
        assert out["error"] == "INVALID_VALUE"
        assert out["field"] == "generated_at"
    ok = json.loads(
        server.tool_generate_report(**_report_kwargs(chain), generated_at="2026-10-12")
    )
    assert "2026-10-12" in ok["report"]


def test_generate_report_rejects_unknown_format_flag(server, chain):
    out = _error(
        server.tool_generate_report(**_report_kwargs(chain), format_flag="--nope")
    )
    assert out["error"] == "INVALID_VALUE"
    assert out["field"] == "format_flag"


def test_evaluate_gates_refuses_preprocess_lang_differing_from_detected(server, chain):
    wrong_prep = server.tool_preprocess_text(corpus_text("en_news_report"), "id")
    out = _error(server.tool_evaluate_gates(chain["lang"], wrong_prep))
    assert out["error"] == "LANG_MISMATCH"
    assert out["field"] == "preprocess_result_json"


def test_band_refuses_lang_differing_from_gate_lang(server, chain):
    out = _error(
        server.tool_estimate_text_complexity_band(
            chain["readability"], chain["lexical"], "id", chain["gate"]
        )
    )
    assert out["error"] == "LANG_MISMATCH"
    assert out["field"] == "lang"


def test_short_signing_key_fails_fast_at_server_start(monkeypatch):
    from tools import integrity

    monkeypatch.setenv(integrity.KEY_ENV, "too-short")
    integrity.reset_key()
    try:
        with pytest.raises(Exception, match="CONFIG_ERROR") as exc:
            load_server.__wrapped__()
        assert getattr(exc.value, "code", None) == "CONFIG_ERROR"
    finally:
        monkeypatch.delenv(integrity.KEY_ENV)
        integrity.reset_key()
