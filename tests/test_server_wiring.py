# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Drive server.py tool functions end to end with a stub FastMCP.

The installed ``mcp`` package may not ship ``mcp.server.fastmcp``; the stub keeps
this test about our wiring, not about the transport library.
"""

import importlib.util
import json
import pathlib
import sys
import types

import pytest

from tests.helpers import corpus_text

SERVER = pathlib.Path("mcp-server/server.py")


class _StubFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name

    def tool(self):
        return lambda fn: fn

    def run(self) -> None:  # pragma: no cover - never called in tests
        raise AssertionError("not used in tests")


@pytest.fixture(scope="module")
def server():
    stub = types.ModuleType("mcp.server.fastmcp")
    stub.FastMCP = _StubFastMCP
    saved = sys.modules.get("mcp.server.fastmcp")
    sys.modules["mcp.server.fastmcp"] = stub
    try:
        spec = importlib.util.spec_from_file_location("vf_server", SERVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        if saved is None:
            sys.modules.pop("mcp.server.fastmcp", None)
        else:
            sys.modules["mcp.server.fastmcp"] = saved


def _chain(server, text, provenance="unknown", text_type="unknown", gate=True):
    lang_json = server.tool_detect_language(text)
    lang = json.loads(lang_json)["lang"]
    prep_json = server.tool_preprocess_text(text, lang)
    prep = json.loads(prep_json)
    gate_json = (
        server.tool_evaluate_gates(
            lang_json,
            prep["word_count"],
            prep["terminal_mark_count"],
            provenance,
            text_type,
        )
        if gate
        else ""
    )
    sents = json.dumps(prep["sentences"])
    lex_json = server.tool_analyze_lexical(json.dumps(prep["tokens"]), sents, lang)
    syn_json = server.tool_analyze_syntactic(sents, lang)
    sem_json = server.tool_analyze_semantic(prep["text_clean"], sents, lang)
    read_json = server.tool_analyze_readability(prep["text_clean"], lang)
    vfs_json = server.tool_compute_verbal_fluency_score(
        lex_json, syn_json, sem_json, read_json, prep["word_count"], lang
    )
    vfs = json.loads(vfs_json)
    iq_json = server.tool_predict_iq(vfs["style_index"], lang, gate_json)
    iq = json.loads(iq_json)
    ma_json = server.tool_predict_mental_age(
        iq["point_estimate"] if iq["point_estimate"] is not None else -1.0,
        0,
        gate_json,
    )
    read = json.loads(read_json)
    band_json = server.tool_estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        json.loads(lex_json)["lexical_density"],
        lang,
        gate_json,
    )
    out = server.tool_generate_report(
        lang_json,
        prep_json,
        lex_json,
        syn_json,
        sem_json,
        read_json,
        vfs_json,
        iq_json,
        ma_json,
        band_json,
        "--both",
        0,
        False,
        gate_json,
    )
    return json.loads(out), iq


def test_server_chain_withholds_iq_and_reports_status(server):
    result, iq = _chain(server, corpus_text("en_news_report"))
    assert iq["point_estimate"] is None
    assert iq["style_band"].startswith("Style band")
    assert result["json"]["status"] == "UNVERIFIED_PROVENANCE"
    assert "Provenance      : unknown" in result["report"]


def test_server_chain_without_gate_refuses_iq(server):
    result, iq = _chain(server, corpus_text("en_news_report"), gate=False)
    assert iq["point_estimate"] is None
    assert "no gate" in iq["withheld_reason"]
    assert "Status: UNVERIFIED" in result["report"]


def test_server_has_no_education_level_tool(server):
    assert not hasattr(server, "tool_estimate_education_level")
    assert hasattr(server, "tool_estimate_text_complexity_band")
    assert hasattr(server, "tool_evaluate_gates")


def test_agent_tools_json_matches_server_signatures(server):
    import inspect

    spec = json.loads(pathlib.Path(".agent/tools.json").read_text(encoding="utf-8"))
    declared = {t["name"]: t for t in spec["tools"]}
    defined = {
        name: fn
        for name, fn in vars(server).items()
        if name.startswith("tool_") and callable(fn)
    }
    assert set(declared) == set(defined)
    for name, fn in defined.items():
        params = list(inspect.signature(fn).parameters)
        assert list(declared[name]["parameters"]) == params, name
    skill = pathlib.Path(".agent/SKILL.md").read_text(encoding="utf-8")
    for name in defined:
        assert f"  - {name}" in skill, name


def test_mental_age_requires_a_passing_gate(server):
    out = json.loads(server.tool_predict_mental_age(135.0, 12))
    assert out["mental_age"] is None
    assert "gate" in out["withheld_reason"]
