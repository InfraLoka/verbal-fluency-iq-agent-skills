# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""MCP server: every tool returns JSON; failures are structured, never raised.

Each output is signed (``tools.integrity``) and carries the SHA-256 of the
analysed text. Tools that consume earlier outputs verify those signatures and
refuse unsigned, edited or mixed-text inputs with a structured error
``{"error": CODE, "field": NAME, "message": TEXT}``.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import FastMCP
from tools.boundary import (
    CONFIG_ERROR,
    INVALID_SHAPE,
    LANG_MISMATCH,
    ToolInputError,
    checked_age,
    parse_json,
    require_format_flag,
    require_iso_date,
    require_lang,
    require_same_gate_lang,
    require_same_lang,
    signed_input,
    signed_output,
    structured,
    verified_gate,
    verified_prep,
)
from tools.integrity import (
    SigningKeyError,
    ensure_signing_key,
    same_input,
    text_sha256,
)
from tools.lexical import analyze_lexical
from tools.mapper import (
    compute_verbal_fluency_score,
    estimate_text_complexity_band,
    predict_iq,
    predict_mental_age,
)
from tools.oplog import configure_logging
from tools.policy import evaluate_gates, withheld_reason
from tools.preprocess import detect_language, preprocess_text
from tools.readability import analyze_readability
from tools.reporter import generate_report
from tools.semantic import analyze_semantic
from tools.syntactic import analyze_syntactic

KINDS = {
    "lang_result_json": "detect_language",
    "preprocess_result_json": "preprocess_text",
    "lexical_result_json": "analyze_lexical",
    "syntactic_result_json": "analyze_syntactic",
    "semantic_result_json": "analyze_semantic",
    "readability_result_json": "analyze_readability",
    "vfs_result_json": "compute_verbal_fluency_score",
    "iq_result_json": "predict_iq",
    "mental_age_result_json": "predict_mental_age",
    "band_result_json": "estimate_text_complexity_band",
}


class ConfigurationError(RuntimeError):
    """The server is misconfigured; it refuses to start (CONFIG_ERROR)."""

    code = CONFIG_ERROR


def validate_configuration() -> None:
    """Fail fast, before any analysis, on an unusable VF_SIGNING_KEY."""
    try:
        ensure_signing_key()
    except SigningKeyError as exc:
        raise ConfigurationError(f"{CONFIG_ERROR}: {exc}") from exc


configure_logging()
validate_configuration()
mcp = FastMCP("verbal-fluency-mcp")


@mcp.tool()
@structured
def tool_detect_language(text: str) -> str:
    """Detect language. Returns lang, confidence (heuristic agreement index, not a
    probability), supported, mixed_language_share."""
    return signed_output(detect_language(text), text_sha256(text), "detect_language")


@mcp.tool()
@structured
def tool_preprocess_text(text: str, lang: str) -> str:
    """Clean and tokenize text. Returns lang, tokens, sentences (with idx),
    word_count (alphabetic words), token_count, terminal_mark_count."""
    return signed_output(
        preprocess_text(text, require_lang(lang)), text_sha256(text), "preprocess_text"
    )


@mcp.tool()
@structured
def tool_evaluate_gates(
    lang_result_json: str,
    preprocess_result_json: str = "",
    provenance: str = "unknown",
    text_type: str = "unknown",
) -> str:
    """Apply validity gates. preprocess_result_json may be empty only when the
    language is unsupported. provenance: supervised_unaided | unsupervised |
    unknown. text_type: formal_prose | informal | unknown. Returns the gate JSON
    that predict_iq, the complexity band and the report require."""
    lang_r = signed_input(lang_result_json, "lang_result_json", "detect_language")
    if preprocess_result_json:
        prep = signed_input(
            preprocess_result_json, "preprocess_result_json", "preprocess_text"
        )
        if prep.get("lang") != lang_r.get("lang"):
            raise ToolInputError(
                LANG_MISMATCH,
                "preprocess_result_json",
                f"preprocess lang {prep.get('lang')!r} does not match detected "
                f"lang {lang_r.get('lang')!r}",
            )
        digest = same_input(
            {"lang_result_json": lang_r, "preprocess_result_json": prep}
        )
        counts = (prep["word_count"], prep["terminal_mark_count"])
    else:
        digest, counts = lang_r["input_sha256"], (0, 0)
    gate = evaluate_gates(lang_r, counts[0], counts[1], provenance, text_type)
    return signed_output(gate, digest, "evaluate_gates")


@mcp.tool()
@structured
def tool_analyze_lexical(preprocess_result_json: str, lang: str) -> str:
    """Compute MATTR, MTLD, content-word density, out-of-dictionary rate."""
    prep = verified_prep(preprocess_result_json, require_lang(lang))
    result = analyze_lexical(prep["tokens"], prep["sentences"], lang)
    return signed_output(result, prep["input_sha256"], "analyze_lexical")


@mcp.tool()
@structured
def tool_analyze_syntactic(preprocess_result_json: str, lang: str) -> str:
    """Compute clause density, subordination index, dependency depth (en only).
    Scores are not comparable across languages."""
    prep = verified_prep(preprocess_result_json, require_lang(lang))
    return signed_output(
        analyze_syntactic(prep["sentences"], lang),
        prep["input_sha256"],
        "analyze_syntactic",
    )


@mcp.tool()
@structured
def tool_analyze_semantic(
    preprocess_result_json: str, lang: str, segment_boundaries_json: str = ""
) -> str:
    """Compute adjacent-sentence similarity, topic drift, lexical chain density.

    segment_boundaries_json: optional JSON array of sentence idx values where a new
    document begins; cross-document transitions are excluded. Empty string = none.
    """
    prep = verified_prep(preprocess_result_json, require_lang(lang))
    boundaries = None
    if segment_boundaries_json:
        boundaries = parse_json(
            segment_boundaries_json, "segment_boundaries_json", list
        )
        if not all(isinstance(b, int) and not isinstance(b, bool) for b in boundaries):
            raise ToolInputError(
                INVALID_SHAPE,
                "segment_boundaries_json",
                "segment_boundaries_json must be an array of sentence idx integers",
            )
    result = analyze_semantic(prep["text_clean"], prep["sentences"], lang, boundaries)
    return signed_output(result, prep["input_sha256"], "analyze_semantic")


@mcp.tool()
@structured
def tool_analyze_readability(preprocess_result_json: str, lang: str) -> str:
    """Compute Flesch, Gunning Fog, ARI, Coleman-Liau. Returns score and evidence."""
    prep = verified_prep(preprocess_result_json, require_lang(lang))
    return signed_output(
        analyze_readability(prep["text_clean"], lang, prep["sentences"]),
        prep["input_sha256"],
        "analyze_readability",
    )


@mcp.tool()
@structured
def tool_compute_verbal_fluency_score(
    lexical_json: str,
    syntactic_json: str,
    semantic_json: str,
    readability_json: str,
    preprocess_result_json: str,
    lang: str,
) -> str:
    """Combine component scores into the style index (0-100). Unavailable
    components are dropped and weights renormalised. Every input must be the
    unmodified output of this server for the same text."""
    prep = verified_prep(preprocess_result_json, require_lang(lang))
    parts = {
        "lexical_json": signed_input(lexical_json, "lexical_json", "analyze_lexical"),
        "syntactic_json": signed_input(
            syntactic_json, "syntactic_json", "analyze_syntactic"
        ),
        "semantic_json": signed_input(
            semantic_json, "semantic_json", "analyze_semantic"
        ),
        "readability_json": signed_input(
            readability_json, "readability_json", "analyze_readability"
        ),
    }
    digest = same_input({"preprocess_result_json": prep, **parts})
    result = compute_verbal_fluency_score(
        parts["lexical_json"],
        parts["syntactic_json"],
        parts["semantic_json"],
        parts["readability_json"],
        prep["word_count"],
        lang,
    )
    return signed_output(result, digest, "compute_verbal_fluency_score")


@mcp.tool()
@structured
def tool_predict_iq(vfs_result_json: str, lang: str, gate_json: str = "") -> str:
    """Neutral style band always; experimental IQ only when gate status is OK and
    the language is validated in config/validation.json. Otherwise IQ fields are
    null with withheld_reason. vfs_result_json must be the signed output of
    tool_compute_verbal_fluency_score."""
    vfs = signed_input(
        vfs_result_json, "vfs_result_json", "compute_verbal_fluency_score"
    )
    require_same_lang(vfs, require_lang(lang), "vfs_result_json")
    gate = verified_gate(gate_json, vfs["input_sha256"])
    result = predict_iq(vfs["style_index"], lang, gate=gate)
    return signed_output(result, vfs["input_sha256"], "predict_iq")


@mcp.tool()
@structured
def tool_predict_mental_age(
    iq_result_json: str, chronological_age: int = 0, gate_json: str = ""
) -> str:
    """Ratio mental age only for a supplied age <= 16, an emitted IQ and a gate
    that allows IQ. chronological_age 0 means not supplied (never assumed);
    otherwise it must be 3-120."""
    iq = signed_input(iq_result_json, "iq_result_json", "predict_iq")
    age = checked_age(chronological_age)
    gate = verified_gate(gate_json, iq["input_sha256"])
    block = withheld_reason(gate)
    point = iq.get("point_estimate") if block is None else None
    result = predict_mental_age(point, age)
    if block is not None:
        result["withheld_reason"] = f"withheld: {block}"
    return signed_output(result, iq["input_sha256"], "predict_mental_age")


@mcp.tool()
@structured
def tool_estimate_text_complexity_band(
    readability_json: str, lexical_json: str, lang: str, gate_json: str = ""
) -> str:
    """Text complexity band (describes the text, not the writer's education).
    Unavailable for languages without calibrated readability norms."""
    require_lang(lang)
    read = signed_input(readability_json, "readability_json", "analyze_readability")
    lex = signed_input(lexical_json, "lexical_json", "analyze_lexical")
    digest = same_input({"readability_json": read, "lexical_json": lex})
    gate = verified_gate(gate_json, digest)
    require_same_gate_lang(gate, lang)
    result = estimate_text_complexity_band(
        read["gunning_fog"],
        read["ari"],
        lex.get("lexical_density"),
        lang,
        gate=gate,
    )
    return signed_output(result, digest, "estimate_text_complexity_band")


@mcp.tool()
@structured
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
    generated_at: str = "",
) -> str:
    """Generate JSON and/or report with status, provenance caveat and evidence.
    Every *_json input must be the unmodified output of this server for one text."""
    require_format_flag(format_flag)
    generated = require_iso_date(generated_at, "generated_at")
    inputs = {
        "lang_result_json": lang_result_json,
        "preprocess_result_json": preprocess_result_json,
        "lexical_result_json": lexical_result_json,
        "syntactic_result_json": syntactic_result_json,
        "semantic_result_json": semantic_result_json,
        "readability_result_json": readability_result_json,
        "vfs_result_json": vfs_result_json,
        "iq_result_json": iq_result_json,
        "mental_age_result_json": mental_age_result_json,
        "band_result_json": band_result_json,
    }
    p = {name: signed_input(raw, name, KINDS[name]) for name, raw in inputs.items()}
    digest = same_input(p)
    result = generate_report(
        p["lang_result_json"],
        p["preprocess_result_json"],
        p["lexical_result_json"],
        p["syntactic_result_json"],
        p["semantic_result_json"],
        p["readability_result_json"],
        p["vfs_result_json"],
        p["iq_result_json"],
        p["mental_age_result_json"],
        p["band_result_json"],
        format_flag,
        checked_age(chronological_age),
        verbose_caveats,
        gate=verified_gate(gate_json, digest),
        generated_at=generated or None,
    )
    return signed_output(result, digest, "generate_report")


if __name__ == "__main__":
    mcp.run()
