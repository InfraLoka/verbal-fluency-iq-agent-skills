# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re

from tests.helpers import CORPUS_DIR, corpus_manifest, corpus_text

WORD_RE = re.compile(r"[^\W\d_]+")


def test_manifest_lists_twelve_synthetic_passages_in_both_languages():
    passages = corpus_manifest()
    assert len(passages) == 12
    assert {p["lang"] for p in passages} == {"en", "id"}
    assert sum(p["lang"] == "en" for p in passages) == 6
    assert len({p["genre"] for p in passages}) >= 6


def test_every_manifest_entry_has_a_file_and_every_file_is_listed():
    names = {p["name"] for p in corpus_manifest()}
    files = {p.stem for p in CORPUS_DIR.glob("*.txt")}
    assert names == files


def test_formal_passages_meet_minimum_length_for_scoring():
    for p in corpus_manifest():
        n_words = len(WORD_RE.findall(corpus_text(p["name"])))
        if p["text_type"] == "formal_prose":
            assert n_words >= 260, p["name"]
        assert n_words >= 200, p["name"]


def test_long_passage_supports_truncation_to_600_words():
    assert len(WORD_RE.findall(corpus_text("en_academic_essay"))) >= 600
