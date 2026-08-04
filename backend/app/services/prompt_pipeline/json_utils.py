"""Shared JSON repair/salvage helpers for vision responses."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger

logger = get_logger()


def strip_code_fence(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    body = "\n".join(lines).strip()
    if body.lower().startswith("json"):
        body = body[4:].strip()
    return body


def extract_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    if depth > 0:
        open_brackets = text[start:].count("[") - text[start:].count("]")
        return text[start:] + ("]" * max(0, open_brackets)) + ("}" * depth)
    return None


def repair_json_text(text: str) -> str:
    fixed = text.strip()
    fixed = (
        fixed.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    fixed = fixed.replace("\ufeff", "").replace("\u200b", "")
    fixed = re.sub(r"\bTrue\b", "true", fixed)
    fixed = re.sub(r"\bFalse\b", "false", fixed)
    fixed = re.sub(r"\bNone\b", "null", fixed)
    fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
    return fixed.strip()


def parse_json_object(raw: str) -> dict[str, Any]:
    text = strip_code_fence(raw)
    if not text:
        raise ImagePromptGenerationError(
            "Vision model returned an empty analysis",
            code="empty_response",
        )

    candidates = [text]
    balanced = extract_balanced_object(text)
    if balanced and balanced not in candidates:
        candidates.append(balanced)
    last_brace = text.rfind("}")
    if last_brace > 0:
        sliced = text[: last_brace + 1]
        if sliced not in candidates:
            candidates.append(sliced)

    last_error: Exception | None = None
    for candidate in candidates:
        for variant in (candidate, repair_json_text(candidate)):
            try:
                parsed = json.loads(variant)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as exc:
                last_error = exc
                continue

    logger.warning(
        "JSON parse failed for fashion pipeline preview={!r}",
        text[:400],
    )
    raise ImagePromptGenerationError(
        "Failed to parse fashion analysis JSON",
        code="empty_response",
    ) from last_error


def as_string_list(value: Any, *, limit: int = 12) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,;/|]", value)
        return [part.strip() for part in parts if part.strip()][:limit]
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text.lower() not in {"none", "null", "n/a"}:
                items.append(text)
            if len(items) >= limit:
                break
        return items
    text = str(value).strip()
    return [text] if text and text.lower() not in {"none", "null", "n/a"} else []


def clean_str(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"none", "null", "n/a", ""}:
        return ""
    return re.sub(r"\s+", " ", text)
