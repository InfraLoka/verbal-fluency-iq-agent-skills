# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Result models for every tool output (G-040).

Each analysis function returns one of these TypedDicts. ``server.py`` adds
``input_sha256``, ``kind`` and ``_sig`` (``SignedFields``) to every output.
tests/test_result_types.py validates real outputs against these models with
pydantic (extra keys forbidden), so a renamed or missing key fails a test.
"""

from typing import Any, NotRequired, TypedDict


class SentenceRecord(TypedDict):
    idx: int
    text: str


class SentenceEvidence(TypedDict):
    sentence_idx: int
    sentence: str
    triggered_by: list[str]
    contribution: float
    rank: str


class TransitionEvidence(TypedDict):
    sentence_idx_from: int
    sentence_idx_to: int
    similarity: float
    note: str
    contribution: float
    rank: str


class LanguageResult(TypedDict):
    lang: str
    confidence: float
    supported: bool
    mixed_language_share: float | None
    regional_language: str | None
    regional_function_word_share: float | None


class PreprocessResult(TypedDict):
    lang: str
    tokens: list[str]
    sentences: list[SentenceRecord]
    word_count: int
    token_count: int
    terminal_mark_count: int
    sentence_count: int
    text_clean: str
    injection_phrases: list[str]


class GateResult(TypedDict):
    status: str
    statuses: list[str]
    reasons: list[str]
    iq_allowed: bool
    text_ok: bool
    education_allowed: bool
    language_norm_unvalidated: bool
    lang: str | None
    provenance: str
    text_type: str
    policy_version: str


class LexicalResult(TypedDict):
    mattr: float | None
    mtld: float | None
    vocd_d: float | None
    lexical_density: float | None
    avg_word_length: float | None
    token_unit: str
    alpha_token_count: int
    known_token_count: int
    oov_rate: float | None
    rare_word_share: float | None
    repeated_ngram_share: float | None
    low_reliability: bool
    reliability_reasons: list[str]
    score_weights: dict[str, float]
    score: float | None
    evidence: list[SentenceEvidence]
    warnings: list[str]
    error: str | None


class SyntacticResult(TypedDict):
    mean_sentence_length: float
    clause_density: float
    subordination_index: float
    dependency_depth: float | None
    passive_ratio: float
    colloquial_forms_normalised: NotRequired[int]
    comparable_across_languages: bool
    score: float
    evidence: list[SentenceEvidence]
    note: str


class SemanticResult(TypedDict):
    adjacent_sentence_similarity: float | None
    topic_drift_index: float | None
    lexical_chain_density: float | None
    entity_labels: list[str]
    transitions: int
    scaling_status: str | None
    duplicate_sentences_removed: int
    duplicate_sentence_ratio: float | None
    score: float | None
    evidence: list[TransitionEvidence]
    note: NotRequired[str]


class ReadabilityResult(TypedDict):
    flesch_reading_ease: float
    gunning_fog: float
    ari: float
    coleman_liau: float
    score: float
    evidence: list[SentenceEvidence]


class StyleIndexResult(TypedDict):
    vfs: float | None
    style_index: float | None
    style_index_label: str
    lexical: float | None
    syntactic: float | None
    semantic: float | None
    readability: float | None
    weights_used: dict[str, float]
    unavailable_components: list[str]
    confidence_label: str
    lang: str
    text_length_words: int
    review_flags: list[str]
    review_reasons: list[str]
    low_reliability: bool
    scoring_provenance: dict[str, Any]


class IQResult(TypedDict):
    style_index: float | None
    style_index_label: str
    style_band: str | None
    point_estimate: int | None
    range_low: int | None
    range_high: int | None
    range_label: str
    classification: str | None
    percentile: int | None
    withheld_reason: str | None
    language_norm_unvalidated: bool
    scoring_provenance: dict[str, Any]


class MentalAgeResult(TypedDict):
    mental_age: float | None
    based_on_chronological_age: int | None
    age_assumed: bool
    withheld_reason: str | None
    formula: str


class ComplexityBandResult(TypedDict):
    text_complexity_band: int | None
    label: str | None
    per_metric_bands: dict[str, int] | None
    consistency: str | None
    withheld_reason: str | None
    note: str


class ReportResult(TypedDict):
    json: dict[str, Any] | None
    report: str | None


class SignedFields(TypedDict):
    input_sha256: str
    kind: str
    _sig: str


class ToolError(TypedDict):
    error: str
    field: str | None
    message: str


# Server tool name -> result model of its output (before signing).
TOOL_RESULT_TYPES: dict[str, type] = {
    "tool_detect_language": LanguageResult,
    "tool_preprocess_text": PreprocessResult,
    "tool_evaluate_gates": GateResult,
    "tool_analyze_lexical": LexicalResult,
    "tool_analyze_syntactic": SyntacticResult,
    "tool_analyze_semantic": SemanticResult,
    "tool_analyze_readability": ReadabilityResult,
    "tool_compute_verbal_fluency_score": StyleIndexResult,
    "tool_predict_iq": IQResult,
    "tool_predict_mental_age": MentalAgeResult,
    "tool_estimate_text_complexity_band": ComplexityBandResult,
    "tool_generate_report": ReportResult,
}
