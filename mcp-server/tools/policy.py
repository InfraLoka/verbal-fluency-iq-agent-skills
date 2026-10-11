# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Validity policy: decides which outputs may be emitted and why others are withheld.

All thresholds come from ``config/validation.json`` (or an injected dict of the same
shape, for unit tests). There is deliberately no per-call override: IQ output for a
language is enabled only by setting ``iq_validated`` in the config after the study in
``docs/validation/validation-protocol.md`` has passed.
"""

import copy
import json
import os
import re

OK = "OK"
UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
MIXED_LANGUAGE = "MIXED_LANGUAGE"
INSUFFICIENT_TEXT = "INSUFFICIENT_TEXT"
INSUFFICIENT_STRUCTURE = "INSUFFICIENT_STRUCTURE"
UNVERIFIED_PROVENANCE = "UNVERIFIED_PROVENANCE"
UNVALIDATED = "UNVALIDATED"

# Highest precedence first. ``status`` is the first triggered entry; every triggered
# status is listed in ``statuses`` and explained in ``reasons``.
STATUS_PRECEDENCE = (
    UNSUPPORTED_LANGUAGE,
    MIXED_LANGUAGE,
    INSUFFICIENT_TEXT,
    INSUFFICIENT_STRUCTURE,
    UNVERIFIED_PROVENANCE,
    UNVALIDATED,
)
# Statuses meaning the text itself cannot support the measurement.
TEXT_STATUSES = frozenset(
    {UNSUPPORTED_LANGUAGE, MIXED_LANGUAGE, INSUFFICIENT_TEXT, INSUFFICIENT_STRUCTURE}
)

PROVENANCE_VALUES = ("supervised_unaided", "unsupervised", "unknown")
TEXT_TYPE_VALUES = ("formal_prose", "informal", "unknown")

# Gunning Fog, ARI and Coleman-Liau were built for English. Other languages need
# ``education_validated`` before a text complexity band is shown (F-013).
READABILITY_NATIVE_LANGUAGES = frozenset({"en"})

STYLE_INDEX_LABEL = (
    "Writing-style index (lexical-syntactic complexity). Not an intelligence measure."
)
PROVENANCE_CAVEAT = (
    "Valid only for supervised, unaided writing produced for the same prompt. "
    "AI assistance, translation, dictation or editing change every score."
)
NO_INDIVIDUAL_DECISION_NOTICE = (
    "Not validated for decisions about individuals (hiring, admissions, "
    "clinical, legal). Human review is mandatory."
)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "validation.json"
)
_TERMINAL_MARK_RE = re.compile(r"[.!?…]+")
_cached: dict | None = None


class CrossLanguageComparisonError(ValueError):
    """Raised when results from different languages are compared or ranked."""


def load_policy(path: str | None = None) -> dict:
    """Return a fresh copy of the validation policy."""
    global _cached
    if path is not None:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    if _cached is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _cached = json.load(f)
    return copy.deepcopy(_cached)


def _resolve(policy: dict | None) -> dict:
    return policy if policy is not None else load_policy()


def iq_validated(lang: str | None, policy: dict | None = None) -> bool:
    flags = _resolve(policy)["languages"].get(lang or "", {})
    return bool(flags.get("iq_validated", False))


def education_validated(lang: str | None, policy: dict | None = None) -> bool:
    flags = _resolve(policy)["languages"].get(lang or "", {})
    return bool(flags.get("education_validated", False))


def count_terminal_marks(text: str) -> int:
    """Count runs of sentence-ending punctuation ('...' counts once)."""
    return len(_TERMINAL_MARK_RE.findall(text or ""))


def _require(value: str, allowed: tuple[str, ...], name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")


def evaluate_gates(
    lang_result: dict,
    alpha_word_count: int,
    terminal_mark_count: int,
    provenance: str = "unknown",
    text_type: str = "unknown",
    policy: dict | None = None,
) -> dict:
    """Apply every input gate and return the status that governs all outputs."""
    pol = _resolve(policy)
    _require(provenance, PROVENANCE_VALUES, "provenance")
    _require(text_type, TEXT_TYPE_VALUES, "text_type")

    lang = lang_result.get("lang")
    confidence = float(lang_result.get("confidence", 0.0))
    mixed = lang_result.get("mixed_language_share")
    issues: list[tuple[str, str]] = []

    if lang not in pol["languages"]:
        supported = ", ".join(sorted(pol["languages"]))
        issues.append(
            (UNSUPPORTED_LANGUAGE, f"language {lang!r} is not supported ({supported})")
        )
    elif mixed is not None and mixed > pol["max_mixed_language_share"]:
        issues.append(
            (
                MIXED_LANGUAGE,
                (
                    f"{mixed:.2f} of words are in a second language "
                    f"(max {pol['max_mixed_language_share']:.2f})"
                ),
            )
        )
    elif confidence < pol["min_lang_confidence"]:
        issues.append(
            (
                UNSUPPORTED_LANGUAGE,
                (
                    f"language detection confidence {confidence:.2f} is below "
                    f"{pol['min_lang_confidence']:.2f}"
                ),
            )
        )

    if alpha_word_count < pol["min_words"]:
        issues.append(
            (
                INSUFFICIENT_TEXT,
                f"{alpha_word_count} words; at least {pol['min_words']} are required",
            )
        )

    words_per_mark = alpha_word_count / max(1, terminal_mark_count)
    if alpha_word_count > 0 and words_per_mark > pol["max_words_per_terminal_mark"]:
        issues.append(
            (
                INSUFFICIENT_STRUCTURE,
                (
                    f"{words_per_mark:.1f} words per sentence-ending mark "
                    f"(max {pol['max_words_per_terminal_mark']}); punctuation is too "
                    "sparse for sentence-length metrics"
                ),
            )
        )

    if provenance != "supervised_unaided":
        issues.append(
            (
                UNVERIFIED_PROVENANCE,
                (
                    f"provenance {provenance!r}: authorship is not attested as "
                    "supervised and unaided"
                ),
            )
        )

    if text_type != "formal_prose":
        issues.append(
            (
                UNVALIDATED,
                (
                    f"text_type {text_type!r} is outside the formal-prose scope; "
                    "IQ is refused"
                ),
            )
        )

    if lang in pol["languages"] and not iq_validated(lang, pol):
        issues.append(
            (
                UNVALIDATED,
                (
                    f"IQ mapping is not validated for language {lang!r} "
                    "(config/validation.json)"
                ),
            )
        )

    triggered = {status for status, _ in issues}
    statuses = [s for s in STATUS_PRECEDENCE if s in triggered]
    status = statuses[0] if statuses else OK
    text_ok = not (triggered & TEXT_STATUSES)
    band_calibrated = lang in READABILITY_NATIVE_LANGUAGES or education_validated(
        lang, pol
    )
    return {
        "status": status,
        "statuses": statuses,
        "reasons": [f"{s}: {msg}" for s, msg in issues],
        "iq_allowed": status == OK,
        "text_ok": text_ok,
        "education_allowed": text_ok and band_calibrated,
        "language_norm_unvalidated": not iq_validated(lang, pol),
        "lang": lang,
        "provenance": provenance,
        "text_type": text_type,
        "policy_version": pol["version"],
    }


def withheld_reason(
    gate: dict | None, lang: str | None = None, policy: dict | None = None
) -> str | None:
    """Why IQ-bearing outputs are withheld, or None when they may be emitted.

    The gate is trusted only when it is a genuine OK evaluation for this language
    and the language is validated in the policy; a bare ``iq_allowed`` flag is not
    enough. With ``lang`` omitted, the gate's own language is used.
    """
    if gate is None:
        return "no gate evaluation supplied (tools.policy.evaluate_gates)"
    gate_lang = gate.get("lang")
    target = lang if lang is not None else gate_lang
    if gate.get("status") != OK or not gate.get("iq_allowed"):
        reasons = gate.get("reasons") or []
        return "; ".join(reasons) or "gate status is not OK"
    if gate_lang is None or gate_lang != target:
        return f"gate was evaluated for language {gate_lang!r}, not {target!r}"
    if not iq_validated(target, policy):
        return f"IQ mapping is not validated for language {target!r}"
    return None


def assert_same_language(results: list[dict]) -> str:
    """Return the shared language, or refuse a cross-language comparison (F-005)."""
    langs = {r.get("lang") for r in results}
    if len(langs) != 1 or None in langs:
        shown = sorted(repr(lang) for lang in langs)
        raise CrossLanguageComparisonError(
            f"refusing to compare results across languages {shown}: "
            "per-language norms are not equated"
        )
    return str(langs.pop())


def rank_by_style_index(results: list[dict]) -> list[dict]:
    """Order same-language results by style index (highest first)."""
    assert_same_language(results)
    scored = [r for r in results if r.get("style_index") is not None]
    return sorted(scored, key=lambda r: r["style_index"], reverse=True)
