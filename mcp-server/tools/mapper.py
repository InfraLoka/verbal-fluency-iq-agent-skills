# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
import json
import math
import os
import statistics

from tools.policy import (
    STYLE_INDEX_LABEL,
    iq_validated,
    load_policy,
    withheld_reason,
)

_iq_norms = None
_edu_norms = None

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

# Nominal component weights of the style index (hand-set; see
# docs/validation/effective-weights.md for what actually drives the index).
NOMINAL_WEIGHTS = {
    "lexical": 0.35,
    "syntactic": 0.25,
    "semantic": 0.25,
    "readability": 0.15,
}
RANGE_LABEL = "uncalibrated heuristic range"
MIN_RANGE_HALF_WIDTH = 25
TEXT_COMPLEXITY_NOTE = (
    "Describes how difficult this text is to read, not the writer's education. "
    "Education cannot be inferred from text."
)


def _load_iq_norms() -> dict:
    global _iq_norms
    if _iq_norms is None:
        with open(os.path.join(_CONFIG_DIR, "iq_norms.json"), encoding="utf-8") as f:
            _iq_norms = json.load(f)
    return _iq_norms


def _load_edu_norms() -> dict:
    global _edu_norms
    if _edu_norms is None:
        with open(os.path.join(_CONFIG_DIR, "edu_norms.json"), encoding="utf-8") as f:
            _edu_norms = json.load(f)
    return _edu_norms


def _length_label(word_count: int) -> str:
    """Ordinal text-length reliability label (no numeric pseudo-probability)."""
    if word_count < 30:
        return "VERY LOW"
    if word_count < 100:
        return "LOW"
    if word_count < 300:
        return "MEDIUM"
    return "HIGH"


def compute_verbal_fluency_score(
    lexical: dict,
    syntactic: dict,
    semantic: dict,
    readability: dict,
    word_count: int,
    lang: str,
) -> dict:
    """Weighted style index. Unavailable components (score None) are dropped and
    the remaining nominal weights renormalised (F-016), never imputed."""
    scores = {
        "lexical": lexical.get("score"),
        "syntactic": syntactic.get("score"),
        "semantic": semantic.get("score"),
        "readability": readability.get("score"),
    }
    available = {k: v for k, v in scores.items() if v is not None}
    unavailable = sorted(k for k, v in scores.items() if v is None)
    if available:
        total = sum(NOMINAL_WEIGHTS[k] for k in available)
        weights_used = {k: round(NOMINAL_WEIGHTS[k] / total, 4) for k in available}
        vfs: float | None = round(
            sum(available[k] * NOMINAL_WEIGHTS[k] for k in available) / total, 1
        )
    else:
        weights_used = {}
        vfs = None

    return {
        "vfs": vfs,
        "style_index": vfs,
        "style_index_label": STYLE_INDEX_LABEL,
        **scores,
        "weights_used": weights_used,
        "unavailable_components": unavailable,
        "confidence_label": _length_label(word_count),
        "lang": lang,
        "text_length_words": word_count,
    }


def _band_for(style_index: float) -> dict:
    bands = _load_iq_norms()["bands"]
    for b in bands:
        if b["vfs_min"] <= style_index <= b["vfs_max"]:
            return b
    return bands[0] if style_index > bands[0]["vfs_max"] else bands[-1]


def iq_percentile(iq: float) -> int:
    """Percentile of an IQ point under N(100, 15), clamped to 1..99 (F-004)."""
    norms = _load_iq_norms()
    z = (iq - norms["iq_mean"]) / norms["iq_sd"]
    pct = 50.0 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return int(min(99, max(1, round(pct))))


def predict_iq(
    style_index: float | None,
    lang: str,
    gate: dict | None = None,
    policy: dict | None = None,
) -> dict:
    """Style band always; IQ only when the gate allows it (F-001, F-003, F-009).

    ``gate`` is the dict from ``tools.policy.evaluate_gates``. Without a gate,
    IQ is withheld: there is no way to request IQ without passing every check.
    """
    pol = policy if policy is not None else load_policy()
    half_width = max(MIN_RANGE_HALF_WIDTH, int(pol["uncalibrated_range_half_width"]))
    result: dict = {
        "style_index": style_index,
        "style_index_label": STYLE_INDEX_LABEL,
        "style_band": None,
        "point_estimate": None,
        "range_low": None,
        "range_high": None,
        "range_label": RANGE_LABEL,
        "classification": None,
        "percentile": None,
        "withheld_reason": None,
        "language_norm_unvalidated": not iq_validated(lang, pol),
    }
    if style_index is None:
        result["withheld_reason"] = "style index unavailable"
        return result

    band = _band_for(style_index)
    result["style_band"] = band["label"]

    reason = withheld_reason(gate, lang, pol)
    if reason is not None:
        result["withheld_reason"] = reason
        return result

    band_range = band["vfs_max"] - band["vfs_min"]
    position = (style_index - band["vfs_min"]) / band_range if band_range > 0 else 0.5
    iq_point = round(band["iq_min"] + position * (band["iq_max"] - band["iq_min"]))
    result.update(
        {
            "point_estimate": iq_point,
            "range_low": iq_point - half_width,
            "range_high": iq_point + half_width,
            "classification": band["label"],
            "percentile": iq_percentile(iq_point),
        }
    )
    return result


def predict_mental_age(
    iq_estimate: float | None, chronological_age: int | None = None
) -> dict:
    """Ratio mental age, only for a supplied age <= 16 (F-017). Never assumed."""
    max_age = _load_iq_norms()["max_ratio_mental_age_years"]
    result: dict = {
        "mental_age": None,
        "based_on_chronological_age": chronological_age,
        "age_assumed": False,
        "withheld_reason": None,
        "formula": "mental_age = (iq / 100) * chronological_age",
    }
    if iq_estimate is None:
        result["withheld_reason"] = "IQ estimate withheld"
    elif chronological_age is None:
        result["withheld_reason"] = "chronological age not supplied; never assumed"
    elif chronological_age > max_age:
        result["withheld_reason"] = (
            f"ratio mental age is undefined beyond age {max_age}"
        )
    else:
        result["mental_age"] = round((iq_estimate / 100) * chronological_age, 1)
    return result


def _metric_band(value: float, key: str, bands: list[dict]) -> int:
    matched = bands[0]["band"]
    for b in bands:
        if value >= b[key]:
            matched = b["band"]
    return matched


def estimate_text_complexity_band(
    gunning_fog: float,
    ari: float,
    lexical_density: float | None,
    lang: str,
    gate: dict | None = None,
    policy: dict | None = None,
) -> dict:
    """Median of per-metric complexity bands (F-014). Describes the text, not the
    writer's education (F-019); unavailable for uncalibrated languages (F-013)."""
    result: dict = {
        "text_complexity_band": None,
        "label": None,
        "per_metric_bands": None,
        "consistency": None,
        "withheld_reason": None,
        "note": TEXT_COMPLEXITY_NOTE,
    }
    if gate is None:
        result["withheld_reason"] = "no gate evaluation supplied"
        return result
    if not gate["text_ok"]:
        result["withheld_reason"] = "; ".join(gate["reasons"])
        return result
    if not gate["education_allowed"]:
        result["withheld_reason"] = (
            f"text complexity bands are not calibrated for language {lang!r}"
        )
        return result

    bands = sorted(_load_edu_norms()["bands"], key=lambda b: b["band"])
    per_metric = {
        "gunning_fog": _metric_band(gunning_fog, "fog_min", bands),
        "ari": _metric_band(ari, "ari_min", bands),
    }
    if lexical_density is not None:
        per_metric["lexical_density"] = _metric_band(
            lexical_density, "lexical_density_min", bands
        )
    values = list(per_metric.values())
    band = int(statistics.median_low(values))
    result.update(
        {
            "text_complexity_band": band,
            "label": next(b["label"] for b in bands if b["band"] == band),
            "per_metric_bands": per_metric,
            "consistency": "CONSISTENT"
            if max(values) - min(values) <= 1
            else "CONFLICTING",
        }
    )
    return result
