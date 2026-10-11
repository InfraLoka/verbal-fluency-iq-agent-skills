# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Evidence is ranked by contribution and cites preprocess sentence idx (G-038, G-043)."""

import sys

sys.path.insert(0, "mcp-server")

from tools.evidence import rank_evidence
from tools.lexical import analyze_lexical
from tools.preprocess import preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

# Plain sentences first; the most complex sentence comes last.
TEXT = (
    "The cat sat on the mat. The dog ran to the park. We ate bread at noon. "
    "The sun was warm today. "
    "Notwithstanding considerable epistemological heterogeneity, the committee, "
    "which had deliberated extensively, concluded that the jurisprudential "
    "ramifications were unprecedented because the legislation was ambiguous."
)
# "Dr." and "3.5" would split sentences under a naive '.' split.
ABBREVIATED = (
    "Dr. Smith measured a pH of 3.5 in the sample. "
    "Interdisciplinary methodological considerations necessitate comprehensive "
    "reevaluation. The cat sat."
)


def test_evidence_ranked_by_contribution_not_position():
    items = [{"contribution": c, "n": i} for i, c in enumerate([0.1, 0.5, 0.0, 0.9])]
    ranked = rank_evidence(items)
    assert [(r["n"], r["rank"]) for r in ranked] == [
        (3, "strongest"),
        (1, "strongest"),
        (2, "weakest"),
        (0, "weakest"),
    ]
    assert rank_evidence(items[:1]) == [{**items[0], "rank": "strongest"}]

    prep = preprocess_text(TEXT, "en")
    last = prep["sentences"][-1]["idx"]
    sents = prep["sentences"]
    for result in (
        analyze_lexical(prep["tokens"], sents, "en"),
        analyze_syntactic(sents, "en"),
        analyze_readability(prep["text_clean"], "en", sents),
    ):
        evidence = result["evidence"]
        assert evidence[0]["sentence_idx"] == last
        assert evidence[0]["rank"] == "strongest"
        strongest = [e["contribution"] for e in evidence if e["rank"] == "strongest"]
        weakest = [e["contribution"] for e in evidence if e["rank"] == "weakest"]
        assert strongest == sorted(strongest, reverse=True)
        assert weakest == sorted(weakest)
        assert max(weakest) <= min(strongest)
        assert len(evidence) == 4

    sem = analyze_semantic(prep["text_clean"], sents, "en")
    sims = [e["similarity"] for e in sem["evidence"]]
    assert sem["evidence"][0]["rank"] == "strongest"
    assert sims[0] == max(sims) and sims[-1] != max(sims)
    assert any(e["rank"] == "weakest" for e in sem["evidence"])


def test_readability_evidence_idx_matches_preprocess_sentences():
    prep = preprocess_text(ABBREVIATED, "en")
    by_idx = {s["idx"]: s["text"] for s in prep["sentences"]}
    result = analyze_readability(prep["text_clean"], "en", prep["sentences"])
    assert result["evidence"]
    for ev in result["evidence"]:
        assert by_idx[ev["sentence_idx"]] == ev["sentence"]
    cited = {ev["sentence_idx"] for ev in result["evidence"]}
    assert cited == set(by_idx)
    top = result["evidence"][0]
    assert top["sentence"].startswith("Interdisciplinary")
