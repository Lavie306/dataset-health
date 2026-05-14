"""Shared medical terminology normalization helpers."""

from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache
from typing import Any

ROOT = pathlib.Path(__file__).parent.parent.parent
DEFAULT_GLOSSARY = ROOT / "src" / "processing" / "medical_dict.json"


def _needs_boundary(char: str) -> bool:
    return char.isalnum() or char == "_"


def _compile_term(term: str) -> re.Pattern:
    prefix = r"(?<!\w)" if term and _needs_boundary(term[0]) else ""
    suffix = r"(?!\w)" if term and _needs_boundary(term[-1]) else ""
    return re.compile(prefix + re.escape(term) + suffix, re.IGNORECASE)


@lru_cache(maxsize=1)
def load_glossary(path: str | None = None) -> dict[str, str]:
    """Load the project medical dictionary, longest terms first."""
    glossary_path = pathlib.Path(path) if path else DEFAULT_GLOSSARY
    if not glossary_path.exists():
        return {}

    with open(glossary_path, encoding="utf-8") as f:
        data = json.load(f)

    cleaned = {
        str(src).strip(): str(dst).strip()
        for src, dst in data.items()
        if str(src).strip() and str(dst).strip()
    }
    return dict(sorted(cleaned.items(), key=lambda item: len(item[0]), reverse=True))


@lru_cache(maxsize=1)
def _compiled_glossary() -> tuple[tuple[re.Pattern, str, str], ...]:
    return tuple((_compile_term(src), src, dst) for src, dst in load_glossary().items())


def apply_glossary(text: str) -> str:
    """Normalize known medical terms in a text string."""
    if not text:
        return text

    normalized = text
    for pattern, _src, dst in _compiled_glossary():
        dst_lower = dst.lower()

        def replace(match: re.Match) -> str:
            # Some accepted terms intentionally contain the alias
            # (e.g. "ho gà" -> "bệnh ho gà"). Avoid repeated re-normalization.
            start = max(0, match.start() - len(dst) - 2)
            end = min(len(normalized), match.end() + len(dst) + 2)
            if dst_lower in normalized[start:end].lower():
                return match.group(0)
            return dst

        normalized = pattern.sub(replace, normalized)
    return collapse_repeated_glossary_targets(normalized)


def collapse_repeated_glossary_targets(text: str) -> str:
    """Clean repeated words caused by older glossary passes."""
    if not text:
        return text

    cleaned = text
    for repeated_first, repeated_last, dst in _compiled_cleanup_patterns():
        cleaned = repeated_first.sub(dst, cleaned)
        cleaned = repeated_last.sub(dst, cleaned)

    return cleaned


@lru_cache(maxsize=1)
def _compiled_cleanup_patterns() -> tuple[tuple[re.Pattern, re.Pattern, str], ...]:
    patterns = []
    risky_targets = {
        dst
        for src, dst in load_glossary().items()
        if src.lower() != dst.lower() and src.lower() in dst.lower()
    }
    for dst in risky_targets:
        words = dst.split()
        if len(words) < 2:
            continue

        first, last = words[0], words[-1]
        rest = " ".join(words[1:])
        repeated_first = re.compile(
            r"(?<!\w)(?:" + re.escape(first) + r"\s+)+" + re.escape(rest) + r"(?!\w)",
            re.IGNORECASE,
        )
        repeated_last = re.compile(
            r"(?<!\w)" + re.escape(dst) + r"(?:\s+" + re.escape(last) + r")+(?!\w)",
            re.IGNORECASE,
        )
        patterns.append((repeated_first, repeated_last, dst))
    return tuple(patterns)


def apply_glossary_to_record(record: dict[str, Any], fields: list[str] | tuple[str, ...]) -> tuple[dict[str, Any], int]:
    """Apply glossary to selected string fields and return changed-field count."""
    changed = 0
    for field in fields:
        val = record.get(field)
        if not isinstance(val, str) or not val:
            continue
        new_val = apply_glossary(val)
        if new_val != val:
            record[field] = new_val
            changed += 1
    return record, changed


def glossary_remaining_hits(text: str) -> list[str]:
    """Return source glossary terms that still appear in text after normalization."""
    if not text:
        return []
    hits = []
    for pattern, src, _dst in _compiled_glossary():
        if src.lower() in _dst.lower():
            continue
        if pattern.search(text):
            hits.append(src)
    return hits
