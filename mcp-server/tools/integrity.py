# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Run integrity for tool outputs: input hash plus HMAC-SHA256 signature (G-015).

The analysis functions in ``tools/*.py`` stay pure; ``server.py`` signs every
tool output here and verifies the signed outputs that downstream tools receive,
so a caller cannot hand ``predict_iq`` a made-up style index or edit a score
between tools.

Key: the ``VF_SIGNING_KEY`` environment variable (UTF-8 text). Without it a
random key is generated per server process, and signatures are then valid only
within that one process: restarting the server invalidates earlier outputs.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from typing import Any

KEY_ENV = "VF_SIGNING_KEY"
MIN_KEY_BYTES = 32
KIND_FIELD = "kind"
SIG_FIELD = "_sig"
HASH_FIELD = "input_sha256"

UNSIGNED_INPUT = "UNSIGNED_INPUT"
TAMPERED_INPUT = "TAMPERED_INPUT"
INPUT_MISMATCH = "INPUT_MISMATCH"
INVALID_SHAPE = "INVALID_SHAPE"
WRONG_KIND = "WRONG_KIND"

_log = logging.getLogger("verbal_fluency.integrity")
_lock = threading.Lock()
_key: dict[str, bytes] = {}


class IntegrityError(ValueError):
    """A tool input is unsigned, tampered with, or from a different text."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


class SigningKeyError(ValueError):
    """VF_SIGNING_KEY is set but too short to be a safe HMAC key."""


def text_sha256(text: str) -> str:
    """SHA-256 of the analysed text (UTF-8), hex encoded."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def key_source() -> str:
    """'env' when VF_SIGNING_KEY is set, otherwise 'ephemeral'."""
    return "env" if os.environ.get(KEY_ENV) else "ephemeral"


def _signing_key() -> bytes:
    with _lock:
        if "key" not in _key:
            configured = os.environ.get(KEY_ENV)
            if configured:
                raw = configured.encode("utf-8")
                if len(raw) < MIN_KEY_BYTES:
                    raise SigningKeyError(
                        f"{KEY_ENV} must be at least {MIN_KEY_BYTES} bytes long "
                        f"(got {len(raw)}); set a longer random value or unset it"
                    )
                _key["key"] = raw
            else:
                _log.warning(
                    "%s is not set: using an ephemeral random per-process signing key; "
                    "signed outputs stop being valid when the server restarts",
                    KEY_ENV,
                )
                _key["key"] = secrets.token_bytes(32)
        return _key["key"]


def ensure_signing_key() -> None:
    """Resolve the signing key now so a bad VF_SIGNING_KEY fails at start-up."""
    _signing_key()


def reset_key() -> None:
    """Forget the cached key, as a server restart would (tests only)."""
    with _lock:
        _key.clear()


def canonical(payload: dict[str, Any]) -> bytes:
    """Sorted-key compact JSON of everything except the signature."""
    unsigned = {k: v for k, v in payload.items() if k != SIG_FIELD}
    return json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _mac(payload: dict[str, Any]) -> str:
    return hmac.new(_signing_key(), canonical(payload), hashlib.sha256).hexdigest()


def sign(payload: dict[str, Any], input_sha256: str, kind: str) -> dict[str, Any]:
    """Return a copy carrying ``input_sha256``, the producing tool ``kind`` and
    ``_sig`` (the MAC covers all three)."""
    out = {k: v for k, v in payload.items() if k != SIG_FIELD}
    out[HASH_FIELD] = input_sha256
    out[KIND_FIELD] = kind
    out[SIG_FIELD] = _mac(out)
    return out


def verify(
    payload: Any, field: str, expected_kind: str | None = None
) -> dict[str, Any]:
    """Return ``payload`` if its signature is valid (and, when given, it was
    produced by the ``expected_kind`` tool), else raise IntegrityError."""
    if not isinstance(payload, dict):
        raise IntegrityError(INVALID_SHAPE, field, f"{field} must be a JSON object")
    sig = payload.get(SIG_FIELD)
    if not isinstance(sig, str) or not isinstance(payload.get(HASH_FIELD), str):
        raise IntegrityError(
            UNSIGNED_INPUT,
            field,
            f"{field} is not a signed output of this server; pass the JSON the "
            "previous tool returned, unchanged",
        )
    if not hmac.compare_digest(sig, _mac(payload)):
        raise IntegrityError(
            TAMPERED_INPUT,
            field,
            f"{field} was modified after this server produced it, or was signed "
            "by another server process",
        )
    if expected_kind is not None and payload.get(KIND_FIELD) != expected_kind:
        raise IntegrityError(
            WRONG_KIND,
            field,
            f"{field} must be the output of {expected_kind}, not "
            f"{payload.get(KIND_FIELD)!r}",
        )
    return payload


def same_input(payloads: dict[str, dict[str, Any]]) -> str:
    """The shared ``input_sha256`` of verified payloads, or INPUT_MISMATCH."""
    hashes = {name: p[HASH_FIELD] for name, p in payloads.items()}
    first = next(iter(hashes.values()))
    odd = [name for name, value in hashes.items() if value != first]
    if odd:
        raise IntegrityError(
            INPUT_MISMATCH,
            odd[0],
            f"{odd[0]} comes from a different text than {next(iter(hashes))}; "
            "run every tool on the same text",
        )
    return first
