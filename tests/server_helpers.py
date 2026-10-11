# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Load the real server module once and run the full MCP tool chain."""

import functools
import importlib.util
import json
import pathlib
from types import ModuleType

SERVER = pathlib.Path(__file__).resolve().parent.parent / "mcp-server" / "server.py"


@functools.cache
def load_server() -> ModuleType:
    spec = importlib.util.spec_from_file_location("vf_server", SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_chain(
    server: ModuleType,
    text: str,
    provenance: str = "unknown",
    text_type: str = "unknown",
    gate: bool = True,
    chronological_age: int = 0,
) -> dict[str, str]:
    """Call every tool in SKILL.md order; return each tool's raw JSON string."""
    out: dict[str, str] = {}
    out["lang"] = server.tool_detect_language(text)
    lang = json.loads(out["lang"])["lang"]
    out["prep"] = server.tool_preprocess_text(text, lang)
    out["gate"] = (
        server.tool_evaluate_gates(out["lang"], out["prep"], provenance, text_type)
        if gate
        else ""
    )
    out["lexical"] = server.tool_analyze_lexical(out["prep"], lang)
    out["syntactic"] = server.tool_analyze_syntactic(out["prep"], lang)
    out["semantic"] = server.tool_analyze_semantic(out["prep"], lang)
    out["readability"] = server.tool_analyze_readability(out["prep"], lang)
    out["vfs"] = server.tool_compute_verbal_fluency_score(
        out["lexical"],
        out["syntactic"],
        out["semantic"],
        out["readability"],
        out["prep"],
        lang,
    )
    out["iq"] = server.tool_predict_iq(out["vfs"], lang, out["gate"])
    out["mental_age"] = server.tool_predict_mental_age(
        out["iq"], chronological_age, out["gate"]
    )
    out["band"] = server.tool_estimate_text_complexity_band(
        out["readability"], out["lexical"], lang, out["gate"]
    )
    out["report"] = server.tool_generate_report(
        out["lang"],
        out["prep"],
        out["lexical"],
        out["syntactic"],
        out["semantic"],
        out["readability"],
        out["vfs"],
        out["iq"],
        out["mental_age"],
        out["band"],
        "--both",
        chronological_age,
        False,
        out["gate"],
    )
    return out
