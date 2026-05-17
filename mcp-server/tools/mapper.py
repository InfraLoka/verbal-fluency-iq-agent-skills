import json
import os
from typing import Optional

_iq_norms = None
_edu_norms = None

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")


def _load_iq_norms() -> dict:
    global _iq_norms
    if _iq_norms is None:
        with open(os.path.join(_CONFIG_DIR, "iq_norms.json")) as f:
            _iq_norms = json.load(f)
    return _iq_norms


def _load_edu_norms() -> dict:
    global _edu_norms
    if _edu_norms is None:
        with open(os.path.join(_CONFIG_DIR, "edu_norms.json")) as f:
            _edu_norms = json.load(f)
    return _edu_norms


def compute_verbal_fluency_score(
    lexical: dict,
    syntactic: dict,
    semantic: dict,
    readability: dict,
    word_count: int,
    lang: str,
) -> dict:
    vfs = round(
        lexical["score"] * 0.35
        + syntactic["score"] * 0.25
        + semantic["score"] * 0.25
        + readability["score"] * 0.15,
        1,
    )

    if word_count < 30:
        confidence, label = 0.30, "VERY LOW"
    elif word_count < 100:
        confidence, label = 0.55, "LOW"
    elif word_count < 300:
        confidence, label = 0.70, "MEDIUM"
    else:
        extra = min(0.13, (word_count - 300) / 1000 * 0.13)
        confidence, label = round(0.82 + extra, 2), "HIGH"

    return {
        "vfs": vfs,
        "lexical": lexical["score"],
        "syntactic": syntactic["score"],
        "semantic": semantic["score"],
        "readability": readability["score"],
        "confidence": confidence,
        "confidence_label": label,
        "lang": lang,
        "text_length_words": word_count,
    }


def predict_iq(vfs: float, confidence: float) -> dict:
    norms = _load_iq_norms()

    band = norms["bands"][-1]
    for b in norms["bands"]:
        if b["vfs_min"] <= vfs <= b["vfs_max"]:
            band = b
            break

    band_range = band["vfs_max"] - band["vfs_min"]
    position = (vfs - band["vfs_min"]) / band_range if band_range > 0 else 0.5
    iq_point = round(band["iq_min"] + position * (band["iq_max"] - band["iq_min"]))

    ci_half = round(15 - confidence * 10)
    percentile = round(
        band["percentile_min"] + position * (95 - band["percentile_min"])
    )

    return {
        "point_estimate": iq_point,
        "ci_low": iq_point - ci_half,
        "ci_high": iq_point + ci_half,
        "classification": band["label"],
        "percentile": percentile,
    }


def predict_mental_age(
    iq_estimate: float, chronological_age: Optional[int] = None
) -> dict:
    norms = _load_iq_norms()
    assumed = chronological_age is None
    age = (
        chronological_age
        if chronological_age is not None
        else norms["default_chronological_age"]
    )
    return {
        "mental_age": round((iq_estimate / 100) * age, 1),
        "based_on_chronological_age": age,
        "age_assumed": assumed,
        "formula": "mental_age = (iq / 100) * chronological_age",
    }


def estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> dict:
    norms = _load_edu_norms()
    matched = norms["levels"][-1]
    for level in norms["levels"]:
        if (
            gunning_fog >= level["fog_min"]
            and ari >= level["ari_min"]
            and lexical_density >= level["lexical_density_min"]
        ):
            matched = level
            break

    thresholds_met = sum(
        [
            gunning_fog >= matched["fog_min"] + 1,
            ari >= matched["ari_min"] + 1,
            lexical_density >= matched["lexical_density_min"] + 0.05,
        ]
    )

    if thresholds_met == 3:
        confidence, conf_label = 0.82, "HIGH"
    elif thresholds_met == 2:
        confidence, conf_label = 0.68, "MEDIUM"
    else:
        confidence, conf_label = 0.50, "LOW"

    return {
        "level_en": matched["level_en"],
        "level_id": matched["level_id"],
        "level_code": matched["code"],
        "confidence": confidence,
        "confidence_label": conf_label,
    }
