# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.policy import evaluate_gates, withheld_reason
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

mcp = FastMCP("verbal-fluency-mcp")


def _gate(gate_json: str) -> dict | None:
    """Empty string means no gate: every screening output is then withheld."""
    return json.loads(gate_json) if gate_json else None


def _age(chronological_age: int) -> int | None:
    return chronological_age if chronological_age > 0 else None


@mcp.tool()
def tool_detect_language(text: str) -> str:
    """Detect language. Returns lang, confidence (heuristic agreement index, not a
    probability), supported, mixed_language_share."""
    return json.dumps(detect_language(text))


@mcp.tool()
def tool_preprocess_text(text: str, lang: str) -> str:
    """Clean and tokenize text. Returns tokens, sentences (with idx), word_count
    (alphabetic words), token_count, terminal_mark_count."""
    return json.dumps(preprocess_text(text, lang))


@mcp.tool()
def tool_evaluate_gates(
    lang_result_json: str,
    word_count: int,
    terminal_mark_count: int,
    provenance: str = "unknown",
    text_type: str = "unknown",
) -> str:
    """Apply validity gates. provenance: supervised_unaided | unsupervised | unknown.
    text_type: formal_prose | informal | unknown. Returns status, reasons and the
    gate JSON that predict_iq, the complexity band and the report require."""
    return json.dumps(
        evaluate_gates(
            json.loads(lang_result_json),
            word_count,
            terminal_mark_count,
            provenance,
            text_type,
        )
    )


@mcp.tool()
def tool_analyze_lexical(tokens_json: str, sentences_json: str, lang: str) -> str:
    """Compute MATTR, MTLD, content-word density, out-of-dictionary rate."""
    return json.dumps(
        analyze_lexical(json.loads(tokens_json), json.loads(sentences_json), lang)
    )


@mcp.tool()
def tool_analyze_syntactic(sentences_json: str, lang: str) -> str:
    """Compute clause density, subordination index, dependency depth (en only).
    Scores are not comparable across languages."""
    return json.dumps(analyze_syntactic(json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_semantic(
    text: str, sentences_json: str, lang: str, segment_boundaries_json: str = ""
) -> str:
    """Compute adjacent-sentence similarity, topic drift, lexical chain density.

    segment_boundaries_json: optional JSON array of sentence idx values where a new
    document begins; cross-document transitions are excluded. Empty string = none.
    """
    boundaries = (
        json.loads(segment_boundaries_json) if segment_boundaries_json else None
    )
    return json.dumps(
        analyze_semantic(text, json.loads(sentences_json), lang, boundaries)
    )


@mcp.tool()
def tool_analyze_readability(text: str, lang: str) -> str:
    """Compute Flesch, Gunning Fog, ARI, Coleman-Liau. Returns score and evidence."""
    return json.dumps(analyze_readability(text, lang))


@mcp.tool()
def tool_compute_verbal_fluency_score(
    lexical_json: str,
    syntactic_json: str,
    semantic_json: str,
    readability_json: str,
    word_count: int,
    lang: str,
) -> str:
    """Combine component scores into the style index (0-100). Unavailable
    components are dropped and weights renormalised."""
    return json.dumps(
        compute_verbal_fluency_score(
            json.loads(lexical_json),
            json.loads(syntactic_json),
            json.loads(semantic_json),
            json.loads(readability_json),
            word_count,
            lang,
        )
    )


@mcp.tool()
def tool_predict_iq(style_index: float, lang: str, gate_json: str = "") -> str:
    """Neutral style band always; experimental IQ only when gate status is OK and
    the language is validated in config/validation.json. Otherwise IQ fields are
    null with withheld_reason."""
    return json.dumps(predict_iq(style_index, lang, gate=_gate(gate_json)))


@mcp.tool()
def tool_predict_mental_age(
    iq_estimate: float = -1.0, chronological_age: int = 0, gate_json: str = ""
) -> str:
    """Ratio mental age only for a supplied age <= 16, an emitted IQ and a gate
    that allows IQ. Pass iq_estimate=-1 when IQ was withheld; age is never assumed."""
    block = withheld_reason(_gate(gate_json))
    iq = iq_estimate if iq_estimate >= 0 and block is None else None
    result = predict_mental_age(iq, _age(chronological_age))
    if block is not None:
        result["withheld_reason"] = f"withheld: {block}"
    return json.dumps(result)


@mcp.tool()
def tool_estimate_text_complexity_band(
    gunning_fog: float,
    ari: float,
    lexical_density: float,
    lang: str,
    gate_json: str = "",
) -> str:
    """Text complexity band (describes the text, not the writer's education).
    Unavailable for languages without calibrated readability norms."""
    return json.dumps(
        estimate_text_complexity_band(
            gunning_fog, ari, lexical_density, lang, gate=_gate(gate_json)
        )
    )


@mcp.tool()
def tool_generate_report(
    lang_result_json: str,
    preprocess_result_json: str,
    lexical_result_json: str,
    syntactic_result_json: str,
    semantic_result_json: str,
    readability_result_json: str,
    vfs_result_json: str,
    iq_result_json: str,
    mental_age_result_json: str,
    band_result_json: str,
    format_flag: str = "--both",
    chronological_age: int = 0,
    verbose_caveats: bool = False,
    gate_json: str = "",
) -> str:
    """Generate JSON and/or report with status, provenance caveat and evidence."""
    result = generate_report(
        json.loads(lang_result_json),
        json.loads(preprocess_result_json),
        json.loads(lexical_result_json),
        json.loads(syntactic_result_json),
        json.loads(semantic_result_json),
        json.loads(readability_result_json),
        json.loads(vfs_result_json),
        json.loads(iq_result_json),
        json.loads(mental_age_result_json),
        json.loads(band_result_json),
        format_flag,
        _age(chronological_age),
        verbose_caveats,
        gate=_gate(gate_json),
    )
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
