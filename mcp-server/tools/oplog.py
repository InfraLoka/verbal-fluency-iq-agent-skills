# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Operational logging: one JSON line per tool call on stderr (G-032).

Records the tool, outcome, error code, input SHA-256, language decision,
statuses, warnings and the scoring version. It never records the analysed text,
tokens, sentences or error messages (which can quote caller input): only
hashes, codes and numbers.
"""

import json
import logging
import sys
import time
from typing import Any, TextIO

from tools.integrity import text_sha256
from tools.provenance import SCORING_VERSION

LOGGER_NAME = "verbal_fluency"
logger = logging.getLogger(f"{LOGGER_NAME}.server")
_HANDLER_FLAG = "_verbal_fluency_jsonl"


class JsonLineFormatter(logging.Formatter):
    """Render ``record.fields`` as one sorted JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(stream: TextIO | None = None) -> logging.Handler:
    """Attach the JSON-lines handler to the package logger once (idempotent)."""
    root = logging.getLogger(LOGGER_NAME)
    for handler in root.handlers:
        if getattr(handler, _HANDLER_FLAG, False):
            return handler
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonLineFormatter())
    setattr(handler, _HANDLER_FLAG, True)
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


def _summary(output: dict[str, Any]) -> dict[str, Any]:
    """Numbers, codes and flags from a tool output; never text."""
    fields: dict[str, Any] = {}
    if "confidence" in output and "supported" in output:
        fields["lang_decision"] = {
            "lang": output.get("lang"),
            "confidence": output.get("confidence"),
            "supported": output.get("supported"),
            "mixed_language_share": output.get("mixed_language_share"),
        }
    elif isinstance(output.get("lang"), str):
        fields["lang"] = output["lang"]
    if "statuses" in output:
        fields["statuses"] = output["statuses"]
    warnings = [w.split(":", 1)[0] for w in output.get("warnings") or []]
    if warnings:
        fields["warnings"] = warnings
    if output.get("review_flags"):
        fields["review_flags"] = output["review_flags"]
    return fields


def log_tool_call(
    tool: str,
    kwargs: dict[str, Any],
    result: str | None,
    started: float,
    crash: BaseException | None = None,
) -> None:
    """Log one call. ``result`` is the JSON string the tool returned."""
    fields: dict[str, Any] = {
        "tool": tool,
        "scoring_version": SCORING_VERSION,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    text = kwargs.get("text")
    if isinstance(text, str):
        fields["input_sha256"] = text_sha256(text)
        fields["input_chars"] = len(text)
    output: Any = None
    if result is not None:
        try:
            output = json.loads(result)
        except json.JSONDecodeError:
            output = None
    if crash is not None:
        fields.update(outcome="crash", error=type(crash).__name__)
        logger.error("tool_call", extra={"fields": fields})
        return
    if isinstance(output, dict) and "error" in output and "field" in output:
        fields.update(outcome="error", error=output["error"], field=output["field"])
        logger.warning("tool_call", extra={"fields": fields})
        return
    fields["outcome"] = "ok"
    if isinstance(output, dict):
        if isinstance(output.get("input_sha256"), str):
            fields["input_sha256"] = output["input_sha256"]
        fields.update(_summary(output))
    logger.info("tool_call", extra={"fields": fields})
