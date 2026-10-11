# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Import the real server module (real FastMCP) and drive every tool end to end."""

import asyncio
import inspect
import json
import pathlib

import pytest

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain


@pytest.fixture(scope="module")
def server():
    return load_server()


def test_server_module_imports_and_registers_all_tools(server):
    from fastmcp import FastMCP

    assert isinstance(server.mcp, FastMCP)
    registered = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    defined = {
        name
        for name, fn in vars(server).items()
        if name.startswith("tool_") and callable(fn)
    }
    assert len(defined) == 12
    assert registered == defined


def test_server_chain_withholds_iq_and_reports_status(server):
    out = run_chain(server, corpus_text("en_news_report"))
    iq = json.loads(out["iq"])
    result = json.loads(out["report"])
    assert iq["point_estimate"] is None
    assert iq["style_band"].startswith("Style band")
    assert result["json"]["status"] == "UNVERIFIED_PROVENANCE"
    assert "Provenance      : unknown" in result["report"]


def test_server_chain_without_gate_refuses_iq(server):
    out = run_chain(server, corpus_text("en_news_report"), gate=False)
    iq = json.loads(out["iq"])
    assert iq["point_estimate"] is None
    assert "no gate" in iq["withheld_reason"]
    assert "Status: UNVERIFIED" in json.loads(out["report"])["report"]


def test_server_has_no_education_level_tool(server):
    assert not hasattr(server, "tool_estimate_education_level")
    assert hasattr(server, "tool_estimate_text_complexity_band")
    assert hasattr(server, "tool_evaluate_gates")


def test_agent_tools_json_matches_server_signatures(server):
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
    out = run_chain(server, corpus_text("en_news_report"), chronological_age=12)
    mental = json.loads(out["mental_age"])
    assert mental["mental_age"] is None
    assert "withheld" in mental["withheld_reason"]
