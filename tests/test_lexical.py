# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import re
import sys

sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical
from tools.mapper import compute_verbal_fluency_score
from tools.preprocess import preprocess_text
from tools.readability import analyze_readability
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

from tests.helpers import corpus_text

RICH_TEXT = (
    "The epistemological underpinnings of this philosophical discourse "
    "traverse labyrinthine corridors of ontological ambiguity wherein "
    "conventional paradigms dissolve into hermeneutical uncertainty "
    "requiring unprecedented methodological innovation and interdisciplinary "
    "synthesis across divergent theoretical frameworks"
)
RICH_TOKENS = RICH_TEXT.split()
SIMPLE_TEXT = "the cat sat on the mat the cat sat the mat sat"
SIMPLE_TOKENS = SIMPLE_TEXT.split()

SENTENCES = [
    {"idx": 0, "text": "The cat sat on the mat."},
    {
        "idx": 1,
        "text": "The epistemological underpinnings dissolve into hermeneutical uncertainty.",
    },
]

CLEAN = (
    "The strongest argument for homework is practice. Skills such as reading "
    "fluently or solving equations improve with repetition, and the school day is "
    "short. Yet practice is only useful when students know how to do the task "
    "correctly. A child who misunderstood the lesson will simply repeat the "
    "mistake at home, often without anyone noticing until the next test. In that "
    "case homework does not reinforce learning; it reinforces errors. The "
    "discipline argument is weaker still. Students from calm homes with a quiet "
    "desk and an available parent can complete assignments easily. Students who "
    "share a small room with siblings cannot."
)
MISSPELLED = (
    "The strongset arguemnt for homewrok is practcie. Skills such as raeding "
    "fluetnly or solivng equations improve with repetiiton, and the school day is "
    "short. Yet practice is only usefull when studnets know how to do the task "
    "correclty. A child who misunderstood the lesosn will simply repaet the "
    "mistake at home, often without anyone noticing until the next test. In that "
    "case homework does not reinfroce learning; it reinforces erorrs. The "
    "discipline argument is weaker still. Students from calm homes with a quiet "
    "desk and an available parent can complete assignments easily. Students who "
    "share a small room with siblings cannot."
)


def _lex(text: str, lang: str = "en") -> dict:
    prep = preprocess_text(text, lang)
    return analyze_lexical(prep["tokens"], prep["sentences"], lang)


def test_analyze_lexical_returns_required_keys():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for key in (
        "mattr",
        "mtld",
        "vocd_d",
        "lexical_density",
        "avg_word_length",
        "token_unit",
        "oov_rate",
        "low_reliability",
        "reliability_reasons",
        "score_weights",
        "score",
        "evidence",
    ):
        assert key in result, f"Missing key: {key}"
    assert "hapax_ratio" not in result


def test_rich_vocabulary_scores_higher_than_simple():
    rich = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    simple = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert rich["score"] > simple["score"]


def test_mattr_between_0_and_1():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["mattr"] <= 1


def test_mtld_positive_for_ten_or_more_tokens():
    assert analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")["mtld"] > 0
    assert analyze_lexical(SIMPLE_TOKENS[:5], SENTENCES, "en")["mtld"] is None


def test_score_between_0_and_100():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_evidence_contains_sentence_idx_and_triggered_by():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert result["evidence"]
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert ev["triggered_by"]
        assert all(t.startswith("rare:") for t in ev["triggered_by"])


def test_empty_tokens_returns_error():
    result = analyze_lexical([], SENTENCES, "en")
    assert "error" in result
    assert result["score"] is None


def test_lexical_density_uses_content_words_not_length_threshold():
    en = analyze_lexical(
        [
            "the",
            "cat",
            "sat",
            "on",
            "the",
            "mat",
            "and",
            "the",
            "dog",
            "ran",
            "to",
            "the",
            "park",
        ],
        SENTENCES,
        "en",
    )
    assert en["lexical_density"] == round(6 / 13, 3)
    idn = analyze_lexical(
        [
            "rumah",
            "yang",
            "besar",
            "itu",
            "adalah",
            "milik",
            "dari",
            "keluarga",
            "dengan",
            "anak",
            "untuk",
            "mereka",
        ],
        SENTENCES,
        "id",
    )
    assert idn["lexical_density"] == round(4 / 12, 3)
    assert set(en["score_weights"]) == {"mattr", "mtld", "lexical_density"}
    assert "avg_word_length" not in en["score_weights"]


def test_lexical_diversity_metrics_use_same_token_unit_per_language():
    idn = analyze_lexical(["Membaca", "membaca", "dibaca", "pembaca"], SENTENCES, "id")
    en = analyze_lexical(["Reading", "reading", "read", "reader"], SENTENCES, "en")
    for result in (idn, en):
        assert result["token_unit"] == "lowercased_surface_form"
        # 3 surface types / 4 tokens; stemming would collapse the id case to 1/4.
        assert result["mattr"] == 0.75


def test_misspelled_text_not_scored_higher_than_clean_text_and_flagged_low_reliability():
    clean = _lex(CLEAN)
    noisy = _lex(MISSPELLED)
    assert noisy["score"] <= clean["score"]
    assert clean["low_reliability"] is False
    assert noisy["low_reliability"] is True
    assert noisy["oov_rate"] > 0.10
    assert noisy["reliability_reasons"]


def _truncate(text: str, n_words: int) -> str:
    out, count = [], 0
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        out.append(sentence)
        count += len(re.findall(r"[^\W\d_]+", sentence))
        if count >= n_words:
            break
    return " ".join(out)


def _style_index(text: str) -> tuple[float, dict]:
    prep = preprocess_text(text, "en")
    lex = analyze_lexical(prep["tokens"], prep["sentences"], "en")
    syn = analyze_syntactic(prep["sentences"], "en")
    sem = analyze_semantic(prep["text_clean"], prep["sentences"], "en")
    read = analyze_readability(prep["text_clean"], "en")
    vfs = compute_verbal_fluency_score(lex, syn, sem, read, prep["word_count"], "en")
    return vfs["style_index"], lex


def test_vfs_stable_across_truncation_lengths_within_tolerance():
    text = corpus_text("en_academic_essay")
    results = [_style_index(_truncate(text, n)) for n in (250, 400, 600)]
    indices = [r[0] for r in results]
    assert max(indices) - min(indices) <= 3.0, indices
    for _, lex in results:
        # The length-biased hapax ratio is gone; MTLD is the diversity measure.
        assert "hapax_ratio" not in lex
        assert lex["mtld"] is not None
