# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""One JSON log line per tool call, with hashes and codes but never the text (G-032)."""

import io
import json
import logging
import sys

sys.path.insert(0, "mcp-server")

from tools.integrity import text_sha256
from tools.oplog import LOGGER_NAME, JsonLineFormatter
from tools.provenance import SCORING_VERSION

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain

MARKER = "Quixotic marmalade zebras 7731 hum softly."
FRENCH = (
    "Bonjour le monde, comment ca va aujourd'hui? Je voudrais acheter du pain et "
    "du fromage pour le diner de ce soir avec mes amis."
)


def test_server_logs_tool_errors_and_language_coercion_without_raw_text():
    server = load_server()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLineFormatter())
    root = logging.getLogger(LOGGER_NAME)
    root.addHandler(handler)
    try:
        text = corpus_text("en_news_report") + " " + MARKER
        out = run_chain(server, text)
        server.tool_detect_language(FRENCH)
        server.tool_preprocess_text(text, "fr")
        tampered = json.loads(out["vfs"])
        tampered["style_index"] = 99.0
        server.tool_predict_iq(json.dumps(tampered), "en")
        server.tool_analyze_lexical("{broken", "en")
    finally:
        root.removeHandler(handler)

    raw = stream.getvalue()
    lines = [json.loads(line) for line in raw.splitlines()]
    calls = [r for r in lines if r["event"] == "tool_call"]
    assert len(calls) == 16  # 12 chain calls + 4 extra
    for record in calls:
        assert record["scoring_version"] == SCORING_VERSION
        assert record["outcome"] in {"ok", "error"}
        assert record["tool"].startswith("tool_")
        assert isinstance(record["duration_ms"], float)

    digest = text_sha256(text)
    for record in (r for r in calls if r["outcome"] == "ok"):
        french = record.get("lang_decision", {}).get("lang") == "fr"
        assert record["input_sha256"] == (text_sha256(FRENCH) if french else digest)
    detect = [r for r in calls if r["tool"] == "tool_detect_language"]
    assert detect[0]["lang_decision"]["lang"] == "en"
    assert detect[1]["lang_decision"]["lang"] == "fr"
    assert detect[1]["lang_decision"]["supported"] is False
    gate = next(r for r in calls if r["tool"] == "tool_evaluate_gates")
    assert "UNVERIFIED_PROVENANCE" in gate["statuses"]

    errors = {
        (r["tool"], r["error"], r["field"]) for r in calls if r["outcome"] == "error"
    }
    assert errors == {
        ("tool_preprocess_text", "INVALID_LANGUAGE", "lang"),
        ("tool_predict_iq", "TAMPERED_INPUT", "vfs_result_json"),
        ("tool_analyze_lexical", "INVALID_JSON", "preprocess_result_json"),
    }
    bad_lang = next(r for r in calls if r.get("error") == "INVALID_LANGUAGE")
    assert bad_lang["input_sha256"] == digest

    for fragment in (MARKER, "marmalade", "Quixotic", FRENCH[:20], "fromage"):
        assert fragment not in raw, fragment
    sentence = corpus_text("en_news_report").split(".")[0]
    assert sentence not in raw
