# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""MCP boundary helpers used by ``server.py`` (G-015, G-025, G-026).

Argument parsing with structured errors, language checks, and the glue that
signs tool outputs and verifies signed inputs. The analysis modules never
import this module, so they stay pure functions of their arguments.
"""

import datetime
import functools
import inspect
import json
import time
from collections.abc import Callable
from typing import Any

from tools.integrity import SIG_FIELD, IntegrityError, same_input, sign, verify
from tools.mapper import MAX_AGE, MIN_AGE
from tools.models import ModelUnavailableError
from tools.oplog import log_tool_call
from tools.policy import SUPPORTED_LANGUAGES
from tools.preprocess import InputTooLargeError
from tools.reporter import FORMAT_FLAGS

INVALID_JSON = "INVALID_JSON"
INVALID_SHAPE = "INVALID_SHAPE"
INVALID_LANGUAGE = "INVALID_LANGUAGE"
INVALID_VALUE = "INVALID_VALUE"
LANG_MISMATCH = "LANG_MISMATCH"
CONFIG_ERROR = "CONFIG_ERROR"


class ToolInputError(ValueError):
    """A caller-supplied argument is malformed; reported, never raised to MCP."""

    def __init__(self, code: str, field: str | None, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def error_json(code: str, field: str | None, message: str) -> str:
    return json.dumps({"error": code, "field": field, "message": message})


def _call(fn: Callable[..., str], *args: Any, **kwargs: Any) -> str:
    try:
        return fn(*args, **kwargs)
    except (ToolInputError, IntegrityError) as exc:
        return error_json(exc.code, exc.field, str(exc))
    except InputTooLargeError as exc:
        return error_json(exc.code, "text", str(exc))
    except ModelUnavailableError as exc:
        return error_json(exc.code, None, str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        return error_json(INVALID_VALUE, None, f"{type(exc).__name__}: {exc}")


def structured(fn: Callable[..., str]) -> Callable[..., str]:
    """Structured error JSON for every expected failure (G-025), and one JSON log
    line per call without the analysed text (G-032)."""
    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        started = time.perf_counter()
        bound = signature.bind_partial(*args, **kwargs).arguments
        try:
            result = _call(fn, *args, **kwargs)
        except Exception as exc:
            log_tool_call(fn.__name__, bound, None, started, crash=exc)
            raise
        log_tool_call(fn.__name__, bound, result, started)
        return result

    return wrapper


def parse_json(raw: str, field: str, expected: type = dict) -> Any:
    """json.loads with a structured INVALID_JSON / INVALID_SHAPE error."""
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ToolInputError(
            INVALID_JSON, field, f"{field} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(value, expected):
        kind = "object" if expected is dict else "array"
        raise ToolInputError(INVALID_SHAPE, field, f"{field} must be a JSON {kind}")
    return value


def signed_input(raw: str, field: str, expected_kind: str) -> dict[str, Any]:
    """A verified earlier output of the ``expected_kind`` tool, without its
    signature (keeps input_sha256)."""
    payload = verify(parse_json(raw, field), field, expected_kind)
    return {k: v for k, v in payload.items() if k != SIG_FIELD}


def checked_age(chronological_age: int) -> int | None:
    """0 means not supplied (never assumed); otherwise MIN_AGE..MAX_AGE."""
    if chronological_age == 0:
        return None
    if not MIN_AGE <= chronological_age <= MAX_AGE:
        raise ToolInputError(
            INVALID_VALUE,
            "chronological_age",
            f"chronological_age must be 0 (not supplied) or {MIN_AGE}-{MAX_AGE}, "
            f"got {chronological_age!r}",
        )
    return chronological_age


def require_lang(lang: str) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        raise ToolInputError(
            INVALID_LANGUAGE,
            "lang",
            f"lang must be one of {', '.join(SUPPORTED_LANGUAGES)}, got {lang!r}",
        )
    return lang


def require_same_lang(payload: dict[str, Any], lang: str, field: str) -> None:
    if payload.get("lang") != lang:
        raise ToolInputError(
            INVALID_VALUE,
            "lang",
            f"lang {lang!r} does not match {field} (lang {payload.get('lang')!r})",
        )


def require_iso_date(value: str, field: str) -> str:
    """ "" or a YYYY-MM-DD calendar date; anything else could inject report lines."""
    if value:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ToolInputError(
                INVALID_VALUE, field, f"{field} must be empty or an ISO date YYYY-MM-DD"
            ) from None
    return value


def require_format_flag(value: str) -> str:
    if value not in FORMAT_FLAGS:
        raise ToolInputError(
            INVALID_VALUE,
            "format_flag",
            f"format_flag must be one of {', '.join(FORMAT_FLAGS)}, got {value!r}",
        )
    return value


def require_same_gate_lang(gate: dict[str, Any] | None, lang: str) -> None:
    if gate is not None and gate.get("lang") != lang:
        raise ToolInputError(
            LANG_MISMATCH,
            "lang",
            f"lang {lang!r} does not match gate_json (lang {gate.get('lang')!r})",
        )


def verified_prep(raw: str, lang: str) -> dict[str, Any]:
    """A verified preprocess result for ``lang`` with a well-formed shape."""
    prep = signed_input(raw, "preprocess_result_json", "preprocess_text")
    require_same_lang(prep, lang, "preprocess_result_json")
    sentences = prep.get("sentences")
    if not isinstance(sentences, list) or not all(
        isinstance(s, dict) and isinstance(s.get("idx"), int) and "text" in s
        for s in sentences
    ):
        raise ToolInputError(
            INVALID_SHAPE,
            "preprocess_result_json",
            "sentences must be a list of {idx, text} objects",
        )
    return prep


def verified_gate(gate_json: str, input_sha256: str) -> dict[str, Any] | None:
    """Empty string means no gate: every screening output is then withheld."""
    if not gate_json:
        return None
    gate = signed_input(gate_json, "gate_json", "evaluate_gates")
    same_input({"input": {"input_sha256": input_sha256}, "gate_json": gate})
    return gate


def signed_output(result: dict[str, Any], input_sha256: str, kind: str) -> str:
    return json.dumps(sign(result, input_sha256, kind))
