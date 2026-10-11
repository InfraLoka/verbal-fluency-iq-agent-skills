# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Load and validate the norms files at first use (G-041).

``iq_norms.json`` bands must tile the style index range [0, 100] with half-open
bands and rising IQ ranges; ``edu_norms.json`` bands must be numbered 1..n with
thresholds rising with the band. A malformed file raises ``NormsConfigError``
when it is loaded instead of mis-scoring silently.
"""

import itertools
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
STYLE_INDEX_MIN = 0.0
STYLE_INDEX_MAX = 100.0

_iq_norms: dict | None = None
_edu_norms: dict | None = None

IQ_BAND_KEYS = ("vfs_min", "vfs_max", "iq_min", "iq_max", "label")
EDU_BAND_KEYS = ("band", "label", "fog_min", "ari_min", "lexical_density_min")
EDU_THRESHOLDS = ("fog_min", "ari_min", "lexical_density_min")


class NormsConfigError(ValueError):
    """A norms file is malformed: missing keys, gaps, overlaps or bad order."""


def _require_keys(obj: dict, keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise NormsConfigError(f"{where}: missing keys {missing}")


def validate_iq_norms(norms: dict) -> None:
    """Bands must tile [0, 100] without gaps or overlaps (G-007, G-041)."""
    _require_keys(
        norms, ("bands", "iq_mean", "iq_sd", "max_ratio_mental_age_years"), "iq_norms"
    )
    bands = norms["bands"]
    if not bands:
        raise NormsConfigError("iq_norms: no bands")
    for i, b in enumerate(bands):
        _require_keys(b, IQ_BAND_KEYS, f"iq_norms band {i}")
        if not b["vfs_min"] < b["vfs_max"] or not b["iq_min"] <= b["iq_max"]:
            raise NormsConfigError(f"iq_norms band {b['label']!r}: min not below max")
    ordered = sorted(bands, key=lambda b: b["vfs_min"])
    if ordered[0]["vfs_min"] != STYLE_INDEX_MIN:
        raise NormsConfigError("iq_norms: lowest band must start at 0")
    if ordered[-1]["vfs_max"] != STYLE_INDEX_MAX:
        raise NormsConfigError("iq_norms: highest band must end at 100")
    for low, high in itertools.pairwise(ordered):
        if low["vfs_max"] != high["vfs_min"]:
            raise NormsConfigError(
                f"iq_norms: bands {low['label']!r} and {high['label']!r} are not "
                f"contiguous ({low['vfs_max']} != {high['vfs_min']})"
            )
        if not low["iq_max"] < high["iq_min"]:
            raise NormsConfigError(
                f"iq_norms: IQ ranges of {low['label']!r} and {high['label']!r} "
                "are not increasing"
            )
    if norms["iq_sd"] <= 0:
        raise NormsConfigError("iq_norms: iq_sd must be positive")


def validate_edu_norms(norms: dict) -> None:
    """Bands numbered 1..n with thresholds rising with the band number."""
    _require_keys(norms, ("bands",), "edu_norms")
    bands = norms["bands"]
    if not bands:
        raise NormsConfigError("edu_norms: no bands")
    for i, b in enumerate(bands):
        _require_keys(b, EDU_BAND_KEYS, f"edu_norms band {i}")
    ordered = sorted(bands, key=lambda b: b["band"])
    if [b["band"] for b in ordered] != list(range(1, len(ordered) + 1)):
        raise NormsConfigError("edu_norms: bands must be numbered 1..n")
    for key in EDU_THRESHOLDS:
        values = [b[key] for b in ordered]
        if (
            values[0] != 0
            or values != sorted(values)
            or len(set(values)) != len(values)
        ):
            raise NormsConfigError(
                f"edu_norms: {key} must start at 0 and increase with the band"
            )


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data: dict = json.load(f)
    return data


def load_iq_norms(path: str | None = None) -> dict:
    """Validated IQ norms; the shipped file is read and checked once."""
    global _iq_norms
    if path is not None:
        norms = _read_json(path)
        validate_iq_norms(norms)
        return norms
    if _iq_norms is None:
        norms = _read_json(os.path.join(CONFIG_DIR, "iq_norms.json"))
        validate_iq_norms(norms)
        _iq_norms = norms
    return _iq_norms


def load_edu_norms(path: str | None = None) -> dict:
    """Validated text complexity bands; the shipped file is read once."""
    global _edu_norms
    if path is not None:
        norms = _read_json(path)
        validate_edu_norms(norms)
        return norms
    if _edu_norms is None:
        norms = _read_json(os.path.join(CONFIG_DIR, "edu_norms.json"))
        validate_edu_norms(norms)
        _edu_norms = norms
    return _edu_norms
