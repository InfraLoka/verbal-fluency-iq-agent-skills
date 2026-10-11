# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Scores carry the scoring version, norms versions, config hashes and model versions."""

import hashlib
import importlib.metadata
import json
import pathlib
import re
import sys

sys.path.insert(0, "scripts")
sys.path.insert(0, "mcp-server")

from tools import models
from tools.mapper import compute_verbal_fluency_score, predict_iq
from tools.provenance import CONFIG_FILES, SCORING_VERSION, scoring_provenance

from tests.helpers import corpus_text
from tests.server_helpers import load_server, run_chain

CONFIG = pathlib.Path("mcp-server/config")


def _check(prov: dict) -> None:
    assert prov["scoring_version"] == SCORING_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", SCORING_VERSION)
    for name in CONFIG_FILES:
        expected = hashlib.sha256((CONFIG / name).read_bytes()).hexdigest()
        assert prov["config_sha256"][name] == expected, name
    for name in ("iq_norms.json", "edu_norms.json", "semantic_scaling.json"):
        data = json.loads((CONFIG / name).read_text(encoding="utf-8"))
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["version"]), name
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["effective_date"]), name
        assert prov["norms"][name] == {
            "version": data["version"],
            "effective_date": data["effective_date"],
        }
    for lib in ("spacy", "sentence-transformers", "textstat", "en_core_web_sm"):
        assert prov["libraries"][lib] == importlib.metadata.version(lib)
    assert prov["models"]["spacy"] == {"en": "en_core_web_sm", "id": "xx_ent_wiki_sm"}
    assert prov["models"]["sentence_transformer"] == {
        "name": models.SENTENCE_MODEL_NAME,
        "revision": models.SENTENCE_MODEL_REVISION,
    }


def test_report_includes_scoring_and_norms_version():
    _check(scoring_provenance())
    vfs = compute_verbal_fluency_score(
        {"score": 50.0}, {"score": 50.0}, {"score": 50.0}, {"score": 50.0}, 300, "en"
    )
    _check(vfs["scoring_provenance"])
    _check(predict_iq(50.0, "en")["scoring_provenance"])

    out = run_chain(load_server(), corpus_text("en_news_report"))
    report = json.loads(out["report"])
    _check(report["json"]["scoring_provenance"])
    text = report["report"]
    assert f"Scoring version : {SCORING_VERSION}" in text
    assert "iq_norms.json 2026-10-11" in text
    assert f"@{models.SENTENCE_MODEL_REVISION[:12]}" in text
    digest = scoring_provenance()["config_sha256"]["iq_norms.json"]
    assert f"iq_norms.json         : sha256 {digest[:16]}" in text
    slim = json.loads(
        load_server().tool_generate_report(
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
            "--scores-only",
        )
    )
    assert slim["json"]["scoring_version"] == SCORING_VERSION
