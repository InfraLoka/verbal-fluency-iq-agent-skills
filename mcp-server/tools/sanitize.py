# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Treat analysed text as untrusted data (G-014, G-037).

The analysed text is written by the person being assessed and is echoed back as
evidence to reviewers and to the AI agent that orchestrates the tools. Before it
appears in a report it is cleaned here: terminal control sequences are removed,
line breaks are flattened, and markdown that could fake a heading, link, table
or code block is neutralised. Phrases that look like instructions to an AI are
detected so the result can be flagged for human review.
"""

import re
import unicodedata

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f  ]")
_SPACES_RE = re.compile(r"\s+")
_MARKDOWN = str.maketrans({"`": "'", "[": "(", "]": ")", "|": "/", "<": "‹", ">": "›"})

POSSIBLE_PROMPT_INJECTION = "possible_prompt_injection"
INJECTION_PATTERNS = {
    "ignore previous instructions": r"\bignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
    "disregard previous instructions": r"\bdisregard\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+instructions?\b",
    "system prompt": r"\bsystem\s+prompt\b",
    "you are now": r"\byou\s+are\s+now\b",
    "abaikan instruksi": r"\babaikan\s+(?:semua\s+)?(?:instruksi|perintah)\b",
    "forget your instructions": r"\bforget\s+(?:all\s+)?(?:your|the|previous|prior)\s+instructions?\b",
    "disregard the system prompt": r"\bdisregard\s+(?:all\s+)?(?:the\s+|your\s+)?system\s+prompt\b",
    "lupakan instruksi": r"\blupakan\s+(?:semua\s+)?(?:instruksi|perintah)\b",
    "prompt sistem": r"\bprompt\s+sistem\b",
    "kamu sekarang adalah": r"\b(?:kamu|anda)\s+sekarang\s+adalah\b",
}
_INJECTION_RES = {
    k: re.compile(v, re.IGNORECASE) for k, v in INJECTION_PATTERNS.items()
}


def strip_format_chars(text: str) -> str:
    """Remove Unicode category Cf characters (zero-width, bidi override, BOM...)."""
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def clean_untrusted(text: str, max_len: int = 100) -> str:
    """One safe line: no control/ANSI characters, no active markdown, truncated."""
    cleaned = strip_format_chars(ANSI_RE.sub("", text or ""))
    cleaned = CONTROL_RE.sub(" ", cleaned)
    cleaned = _SPACES_RE.sub(" ", cleaned).strip()
    cleaned = cleaned.translate(_MARKDOWN).lstrip("#").strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip() + "…"
    return cleaned


def detect_injection_phrases(text: str) -> list[str]:
    """Labels of instruction-like phrases found in the text (en and id)."""
    folded = strip_format_chars(unicodedata.normalize("NFKC", text or ""))
    folded = _SPACES_RE.sub(" ", folded)
    return [label for label, rx in _INJECTION_RES.items() if rx.search(folded)]
