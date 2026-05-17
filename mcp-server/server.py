import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from tools.preprocess import detect_language, preprocess_text
from tools.lexical import analyze_lexical
from tools.syntactic import analyze_syntactic
from tools.semantic import analyze_semantic
from tools.readability import analyze_readability
from tools.mapper import (
    compute_verbal_fluency_score,
    predict_iq,
    predict_mental_age,
    estimate_education_level,
)
from tools.reporter import generate_report

mcp = FastMCP("verbal-fluency-mcp")


@mcp.tool()
def tool_detect_language(text: str) -> str:
    """Detect language of input text. Returns lang (en|id) and confidence."""
    return json.dumps(detect_language(text))


@mcp.tool()
def tool_preprocess_text(text: str, lang: str) -> str:
    """Clean and tokenize text. Returns tokens, sentences (with idx), word_count."""
    return json.dumps(preprocess_text(text, lang))


@mcp.tool()
def tool_analyze_lexical(tokens_json: str, sentences_json: str, lang: str) -> str:
    """Compute MATTR, VOCD-D, hapax ratio, lexical density. Returns score and evidence."""
    return json.dumps(analyze_lexical(json.loads(tokens_json), json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_syntactic(sentences_json: str, lang: str) -> str:
    """Compute clause density, subordination index, dependency depth. Returns score and evidence."""
    return json.dumps(analyze_syntactic(json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_semantic(text: str, sentences_json: str, lang: str) -> str:
    """Compute argument coherence, topic drift, lexical chain density. Returns score and evidence."""
    return json.dumps(analyze_semantic(text, json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_readability(text: str, lang: str) -> str:
    """Compute Flesch, Gunning Fog, ARI, Coleman-Liau. Returns score and evidence."""
    return json.dumps(analyze_readability(text, lang))


@mcp.tool()
def tool_compute_verbal_fluency_score(
    lexical_json: str, syntactic_json: str, semantic_json: str,
    readability_json: str, word_count: int, lang: str
) -> str:
    """Combine metric scores into weighted VFS (0-100) with confidence label."""
    return json.dumps(compute_verbal_fluency_score(
        json.loads(lexical_json), json.loads(syntactic_json),
        json.loads(semantic_json), json.loads(readability_json),
        word_count, lang,
    ))


@mcp.tool()
def tool_predict_iq(vfs: float, confidence: float) -> str:
    """Map VFS to IQ point estimate, 95% CI, classification, and percentile."""
    return json.dumps(predict_iq(vfs, confidence))


@mcp.tool()
def tool_predict_mental_age(iq_estimate: float, chronological_age: int = 0) -> str:
    """Compute mental age from IQ. Pass chronological_age=0 to use population default (30)."""
    age = chronological_age if chronological_age > 0 else None
    return json.dumps(predict_mental_age(iq_estimate, age))


@mcp.tool()
def tool_estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> str:
    """Map readability metrics to education level with EN and ID labels."""
    return json.dumps(estimate_education_level(gunning_fog, ari, lexical_density, clause_density))


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
    edu_result_json: str,
    format_flag: str = "--both",
    chronological_age: int = 0,
    verbose_caveats: bool = False,
) -> str:
    """Generate JSON scores and/or structured report with sentence-level citation evidence."""
    age = chronological_age if chronological_age > 0 else None
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
        json.loads(edu_result_json),
        format_flag,
        age,
        verbose_caveats,
    )
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
