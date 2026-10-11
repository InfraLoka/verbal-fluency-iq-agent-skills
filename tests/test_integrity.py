# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Signed tool outputs: unsigned, tampered and mixed-text inputs are refused (G-015)."""

import json
import sys

import pytest

sys.path.insert(0, "mcp-server")

from tools import integrity

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain


@pytest.fixture(scope="module")
def server():
    return load_server()


@pytest.fixture(scope="module")
def chain(server):
    return run_chain(server, corpus_text("en_news_report"))


def _error(raw: str) -> dict:
    out = json.loads(raw)
    assert set(out) == {"error", "field", "message"}, out
    return out


def _tamper(raw: str, **changes) -> str:
    payload = json.loads(raw)
    payload.update(changes)
    return json.dumps(payload)


def test_predict_iq_rejects_unsigned_vfs_input(server, chain):
    vfs = json.loads(chain["vfs"])
    unsigned = {k: v for k, v in vfs.items() if k not in ("_sig", "input_sha256")}
    unsigned["style_index"] = 100.0
    out = _error(server.tool_predict_iq(json.dumps(unsigned), "en"))
    assert out["error"] == "UNSIGNED_INPUT"
    assert out["field"] == "vfs_result_json"

    out = _error(server.tool_predict_iq(_tamper(chain["vfs"], style_index=99.9), "en"))
    assert out["error"] == "TAMPERED_INPUT"
    assert out["field"] == "vfs_result_json"

    forged = _tamper(chain["vfs"], _sig="0" * 64)
    assert _error(server.tool_predict_iq(forged, "en"))["error"] == "TAMPERED_INPUT"

    valid = json.loads(server.tool_predict_iq(chain["vfs"], "en", chain["gate"]))
    assert "error" not in valid
    assert valid["style_band"].startswith("Style band")
    assert valid["input_sha256"] == integrity.text_sha256(corpus_text("en_news_report"))
    assert len(valid["_sig"]) == 64


def test_downstream_tools_refuse_tampered_or_mixed_inputs(server, chain):
    c = chain
    lex_up = _tamper(c["lexical"], score=100.0)
    out = _error(
        server.tool_compute_verbal_fluency_score(
            lex_up, c["syntactic"], c["semantic"], c["readability"], c["prep"], "en"
        )
    )
    assert (out["error"], out["field"]) == ("TAMPERED_INPUT", "lexical_json")

    out = _error(
        server.tool_predict_mental_age(_tamper(c["iq"], point_estimate=140), 12)
    )
    assert (out["error"], out["field"]) == ("TAMPERED_INPUT", "iq_result_json")

    out = _error(
        server.tool_estimate_text_complexity_band(
            _tamper(c["readability"], gunning_fog=30.0), c["lexical"], "en"
        )
    )
    assert out["error"] == "TAMPERED_INPUT"

    forged_gate = _tamper(c["gate"], status="OK", iq_allowed=True, reasons=[])
    out = _error(server.tool_predict_iq(c["vfs"], "en", forged_gate))
    assert (out["error"], out["field"]) == ("TAMPERED_INPUT", "gate_json")

    other = run_chain(server, corpus_text("en_opinion"))
    out = _error(server.tool_predict_iq(c["vfs"], "en", other["gate"]))
    assert (out["error"], out["field"]) == ("INPUT_MISMATCH", "gate_json")
    out = _error(
        server.tool_compute_verbal_fluency_score(
            c["lexical"],
            other["syntactic"],
            c["semantic"],
            c["readability"],
            c["prep"],
            "en",
        )
    )
    assert (out["error"], out["field"]) == ("INPUT_MISMATCH", "syntactic_json")

    report_args = [
        c["lang"],
        c["prep"],
        c["lexical"],
        c["syntactic"],
        c["semantic"],
        c["readability"],
        _tamper(c["vfs"], style_index=99.0),
        c["iq"],
        c["mental_age"],
        c["band"],
    ]
    out = _error(server.tool_generate_report(*report_args))
    assert (out["error"], out["field"]) == ("TAMPERED_INPUT", "vfs_result_json")

    report = json.loads(c["report"])
    assert report["json"]["input_sha256"] == integrity.text_sha256(
        corpus_text("en_news_report")
    )
    assert "_sig" not in json.dumps(report["json"]["metrics"])


def test_signing_key_from_env_survives_restart_and_ephemeral_key_does_not(
    server, monkeypatch
):
    text = corpus_text("en_news_report")
    monkeypatch.delenv(integrity.KEY_ENV, raising=False)
    integrity.reset_key()
    assert integrity.key_source() == "ephemeral"
    lang = server.tool_detect_language(text)
    integrity.reset_key()  # simulates a server restart
    assert _error(server.tool_evaluate_gates(lang))["error"] == "TAMPERED_INPUT"

    monkeypatch.setenv(integrity.KEY_ENV, "test-only-signing-key-0123456789-abcdef")
    integrity.reset_key()
    assert integrity.key_source() == "env"
    lang = server.tool_detect_language(text)
    integrity.reset_key()
    gate = json.loads(server.tool_evaluate_gates(lang))
    assert gate["status"] == "INSUFFICIENT_TEXT"  # no preprocess result: 0 words

    monkeypatch.delenv(integrity.KEY_ENV)
    integrity.reset_key()


def test_signed_output_of_wrong_kind_is_rejected(server):
    chain = run_chain(server, corpus_text("en_news_report"))
    out = _error(
        server.tool_compute_verbal_fluency_score(
            chain["semantic"],  # a real signed output, but not a lexical one
            chain["syntactic"],
            chain["semantic"],
            chain["readability"],
            chain["prep"],
            "en",
        )
    )
    assert out["error"] == "WRONG_KIND" and out["field"] == "lexical_json"
    assert json.loads(chain["semantic"])["kind"] == "analyze_semantic"
    assert (
        json.loads(
            server.tool_compute_verbal_fluency_score(
                chain["lexical"],
                chain["syntactic"],
                chain["semantic"],
                chain["readability"],
                chain["prep"],
                "en",
            )
        )["kind"]
        == "compute_verbal_fluency_score"
    )


def test_kind_is_inside_the_mac(chain):
    payload = json.loads(chain["lexical"])
    payload["kind"] = "analyze_semantic"
    with pytest.raises(integrity.IntegrityError) as exc:
        integrity.verify(payload, "x")
    assert exc.value.code == "TAMPERED_INPUT"


def test_short_signing_key_is_a_configuration_error(monkeypatch):
    monkeypatch.setenv(integrity.KEY_ENV, "too-short")
    integrity.reset_key()
    try:
        with pytest.raises(integrity.SigningKeyError, match="32"):
            integrity.sign({"a": 1}, "h", "k")
    finally:
        monkeypatch.delenv(integrity.KEY_ENV)
        integrity.reset_key()


def test_unset_or_empty_key_warns_once_without_key_material(monkeypatch, caplog):
    from tools.oplog import logger

    for value in (None, ""):
        if value is None:
            monkeypatch.delenv(integrity.KEY_ENV, raising=False)
        else:
            monkeypatch.setenv(integrity.KEY_ENV, value)
        integrity.reset_key()
        with caplog.at_level("WARNING", logger=logger.name):
            caplog.clear()
            integrity.sign({"a": 1}, "h", "k")
            integrity.sign({"a": 2}, "h", "k")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "ephemeral" in warnings[0].getMessage()
    integrity.reset_key()
