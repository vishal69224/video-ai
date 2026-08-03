"""Gemma Vision → structured fashion analysis JSON (stage 1 of prompt pipeline)."""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends
from ollama import ResponseError, chat

from app.core.config import Settings, get_settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger
from app.services.prompt_optimizer_service import (
    PromptOptimizerService,
    get_prompt_optimizer_service,
)

logger = get_logger()

ANALYSIS_SYSTEM_PROMPT = """You are a Fashion Product Analyst for AI video commercials.

You are NOT writing a cinematic prompt.
You are NOT captioning people as "a young man wearing...".

Analyze ALL attached reference images together.
Merge multi-view knowledge (front / side / back / fabric / detail close-ups)
into ONE structured product analysis.

Return ONLY one valid JSON object. No markdown. No preamble. No trailing text.
Use double quotes for all keys and string values. No trailing commas.

Required keys:
product, category, gender, fit, fabric, texture, material,
primary_color, secondary_color, hero_features, available_views,
recommended_actions, camera_suggestions, lighting, background,
negative_constraints, confidence

Rules:
- Use only what is visible. Do not invent logos, colors, or garments.
- hero_features = selling points (zip, pleats, embroidery, pocket, buckle, collar, etc.).
- available_views examples: front, side, back, fabric_closeup, detail_closeup.
- recommended_actions must be elegant fashion-commercial actions only
  (walk confidently, pause naturally, adjust waistband, slow turn, hand in pocket).
- Never recommend dancing, jumping, running, or exaggerated motion.
- camera_suggestions: Wide Shot, Medium Shot, Tracking Shot, Close-up, Macro, Orbit, Low Angle.
- confidence is a number from 0.0 to 1.0.
- Keep arrays short and unique (max 8 items each)."""

ANALYSIS_USER_PROMPT = (
    "Analyze all attached fashion reference images and return ONLY the JSON object "
    "defined in the system instructions."
)

REQUIRED_STRING_FIELDS = (
    "product",
    "category",
    "gender",
    "fit",
    "fabric",
    "texture",
    "material",
    "primary_color",
    "secondary_color",
    "lighting",
    "background",
)

REQUIRED_LIST_FIELDS = (
    "hero_features",
    "available_views",
    "recommended_actions",
    "camera_suggestions",
    "negative_constraints",
)

MAX_ANALYSIS_ATTEMPTS = 3


@dataclass
class ImagePromptService:
    """
    Stage 1: Gemma Vision → structured fashion JSON.
    Stage 2 (via PromptOptimizerService): JSON → concise Kie.ai prompt.
    """

    settings: Settings
    optimizer: PromptOptimizerService

    async def generate_prompt(
        self,
        image_paths: list[str],
        *,
        model: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> str:
        """
        Analyze images with Gemma, then optimize into one Kie.ai prompt.

        Returns:
            Final optimized cinematic prompt string.
        """
        analysis = await self.analyze_images(image_paths)
        prompt = self.optimizer.optimize(
            analysis,
            model=model,
            duration_seconds=duration_seconds,
            resolution=resolution,
        )
        if not prompt.strip():
            raise ImagePromptGenerationError(
                "Prompt optimizer returned an empty prompt",
                code="empty_response",
            )
        logger.info("Final optimized prompt ready ({} chars)", len(prompt))
        return prompt

    async def analyze_images(self, image_paths: list[str]) -> dict[str, Any]:
        """Run Gemma Vision and return normalized structured fashion analysis."""
        if not image_paths:
            raise ImagePromptGenerationError(
                "At least one image path is required",
                code="invalid_image",
            )

        resolved_paths = [self._resolve_image_path(path) for path in image_paths]
        logger.info(
            "Fashion analysis starting model={} images={}",
            self.settings.OLLAMA_MODEL,
            len(resolved_paths),
        )

        last_error: Exception | None = None
        for attempt in range(1, MAX_ANALYSIS_ATTEMPTS + 1):
            try:
                raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._chat_analysis,
                        resolved_paths,
                        attempt=attempt,
                    ),
                    timeout=self.settings.OLLAMA_TIMEOUT,
                )
            except TimeoutError as exc:
                logger.error(
                    "Fashion analysis timed out after {}s (attempt {}/{})",
                    self.settings.OLLAMA_TIMEOUT,
                    attempt,
                    MAX_ANALYSIS_ATTEMPTS,
                )
                last_error = ImagePromptGenerationError(
                    f"Prompt generation timed out after {self.settings.OLLAMA_TIMEOUT:.0f}s",
                    code="generation_timeout",
                )
                last_error.__cause__ = exc
                continue
            except ImagePromptGenerationError:
                raise
            except ResponseError as exc:
                message = str(exc).lower()
                if "not found" in message or "pull" in message:
                    raise ImagePromptGenerationError(
                        f"Ollama model '{self.settings.OLLAMA_MODEL}' is missing. "
                        f"Run: ollama pull {self.settings.OLLAMA_MODEL}",
                        code="model_missing",
                    ) from exc
                if "failed to load image" in message or "invalid_request_error" in message:
                    raise ImagePromptGenerationError(
                        f"Invalid image for vision model: {exc}",
                        code="invalid_image",
                    ) from exc
                raise ImagePromptGenerationError(
                    f"Ollama request failed: {exc}",
                    code="ollama_unavailable",
                ) from exc
            except ConnectionError as exc:
                raise ImagePromptGenerationError(
                    "Ollama is unavailable. Ensure the Ollama server is running.",
                    code="ollama_unavailable",
                ) from exc
            except OSError as exc:
                raise ImagePromptGenerationError(
                    f"Ollama is unavailable: {exc}",
                    code="ollama_unavailable",
                ) from exc
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected fashion analysis failure")
                raise ImagePromptGenerationError(
                    f"Prompt generation failed: {exc}",
                    code="prompt_generation_failed",
                ) from exc

            try:
                analysis = self._parse_analysis_json(raw)
            except ImagePromptGenerationError as exc:
                preview = (raw or "").replace("\n", " ")[:400]
                logger.warning(
                    "Fashion analysis JSON parse failed attempt={}/{} preview={!r}",
                    attempt,
                    MAX_ANALYSIS_ATTEMPTS,
                    preview,
                )
                last_error = exc
                continue

            logger.info(
                "Fashion analysis ready product={!r} features={} confidence={} attempt={}",
                analysis.get("product"),
                len(analysis.get("hero_features") or []),
                analysis.get("confidence"),
                attempt,
            )
            return analysis

        if isinstance(last_error, ImagePromptGenerationError):
            raise last_error
        raise ImagePromptGenerationError(
            "Failed to parse fashion analysis JSON",
            code="empty_response",
        )

    def _chat_analysis(self, image_paths: list[Path], *, attempt: int = 1) -> str:
        """Synchronous Gemma vision call that must return JSON text."""
        previous_host = os.environ.get("OLLAMA_HOST")
        os.environ["OLLAMA_HOST"] = self.settings.OLLAMA_HOST
        # Vary temperature on retries — temperature=0 often repeats the same broken JSON.
        temperature = 0.0 if attempt == 1 else min(0.2 * attempt, 0.6)
        try:
            response = chat(
                model=self.settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": ANALYSIS_USER_PROMPT,
                        "images": [str(path) for path in image_paths],
                    },
                ],
                format="json",
                options={"temperature": temperature, "num_predict": 700},
            )
        finally:
            if previous_host is None:
                os.environ.pop("OLLAMA_HOST", None)
            else:
                os.environ["OLLAMA_HOST"] = previous_host

        message = getattr(response, "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if content is None and isinstance(response, dict):
            content = response.get("message", {}).get("content")
        return str(content or "").strip()

    def _parse_analysis_json(self, raw: str) -> dict[str, Any]:
        """Parse and normalize Gemma JSON into the required analysis schema."""
        payload = self._extract_json_object(raw)
        if not isinstance(payload, dict):
            raise ImagePromptGenerationError(
                "Gemma did not return a JSON analysis object",
                code="empty_response",
            )
        return self._normalize_analysis(payload)

    def _normalize_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in REQUIRED_STRING_FIELDS:
            value = payload.get(field, "")
            if value is None:
                value = ""
            normalized[field] = str(value).strip()
            if normalized[field].lower() in {"none", "null", "n/a"}:
                normalized[field] = ""

        for field in REQUIRED_LIST_FIELDS:
            normalized[field] = self._as_string_list(payload.get(field))

        confidence = payload.get("confidence", 0.5)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.5
        normalized["confidence"] = max(0.0, min(1.0, confidence_value))

        if not normalized["product"] and not normalized["category"]:
            raise ImagePromptGenerationError(
                "Fashion analysis missing product/category",
                code="empty_response",
            )
        return normalized

    @classmethod
    def _extract_json_object(cls, raw: str) -> Any:
        text = cls._strip_code_fence((raw or "").strip())
        if not text:
            raise ImagePromptGenerationError(
                "Gemma returned an empty analysis",
                code="empty_response",
            )

        candidates = [text]
        balanced = cls._extract_balanced_object(text)
        if balanced and balanced not in candidates:
            candidates.append(balanced)
        # Also try cutting at the last complete closing brace.
        last_brace = text.rfind("}")
        if last_brace > 0:
            sliced = text[: last_brace + 1]
            if sliced not in candidates:
                candidates.append(sliced)

        last_error: Exception | None = None
        for candidate in candidates:
            for variant in cls._json_variants(candidate):
                try:
                    parsed = json.loads(variant)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError as exc:
                    last_error = exc
                    continue

        # Final fallback: salvage fields with regex from broken Gemma output.
        salvaged = cls._salvage_fields_from_text(text)
        if salvaged.get("product") or salvaged.get("category"):
            logger.warning(
                "Salvaged fashion analysis fields from broken JSON "
                "(product={!r}, features={})",
                salvaged.get("product"),
                len(salvaged.get("hero_features") or []),
            )
            return salvaged

        logger.warning(
            "JSON parse exhausted variants last_error={} raw_preview={!r}",
            last_error,
            text[:500],
        )
        raise ImagePromptGenerationError(
            "Failed to parse fashion analysis JSON",
            code="empty_response",
        ) from last_error

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
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

    @staticmethod
    def _extract_balanced_object(text: str) -> str | None:
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
        # Truncated object: close open braces/brackets best-effort.
        if depth > 0:
            open_brackets = text[start:].count("[") - text[start:].count("]")
            suffix = ("]" * max(0, open_brackets)) + ("}" * depth)
            return text[start:] + suffix
        return None

    @classmethod
    def _json_variants(cls, text: str) -> list[str]:
        """Generate increasingly repaired JSON candidates."""
        variants = [text]
        repaired = cls._repair_json_text(text)
        if repaired != text:
            variants.append(repaired)
        balanced = cls._extract_balanced_object(repaired)
        if balanced and balanced not in variants:
            variants.append(cls._repair_json_text(balanced))
        return variants

    @staticmethod
    def _repair_json_text(text: str) -> str:
        """Fix common Gemma JSON mistakes (trailing commas, smart quotes, etc.)."""
        fixed = text.strip()
        # Normalize fancy quotes.
        fixed = (
            fixed.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )
        # Remove BOM / zero-width chars.
        fixed = fixed.replace("\ufeff", "").replace("\u200b", "")
        # Python literals → JSON.
        fixed = re.sub(r"\bTrue\b", "true", fixed)
        fixed = re.sub(r"\bFalse\b", "false", fixed)
        fixed = re.sub(r"\bNone\b", "null", fixed)
        # Trailing commas before } or ].
        fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
        # Do NOT rewrite bare keys with a naive regex — it corrupts string values
        # that contain ", word:" patterns (e.g. lighting descriptions).
        return fixed.strip()

    @classmethod
    def _salvage_fields_from_text(cls, text: str) -> dict[str, Any]:
        """Best-effort field extraction when Gemma returns nearly-valid broken JSON."""
        payload: dict[str, Any] = {}
        for field in REQUIRED_STRING_FIELDS:
            match = re.search(
                rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"',
                text,
                flags=re.IGNORECASE,
            )
            if match:
                payload[field] = match.group(1).replace('\\"', '"').strip()
                continue
            # Unquoted / null-ish values.
            match = re.search(
                rf'"{field}"\s*:\s*(null|None|"")',
                text,
                flags=re.IGNORECASE,
            )
            if match:
                payload[field] = ""

        for field in REQUIRED_LIST_FIELDS:
            match = re.search(
                rf'"{field}"\s*:\s*\[(.*?)\]',
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                items = re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))
                payload[field] = [
                    item.replace('\\"', '"').strip() for item in items if item.strip()
                ]
                continue
            # Unclosed array — grab quoted strings after the key until next key/brace.
            match = re.search(
                rf'"{field}"\s*:\s*\[(.*?)(?="(?:[a-z_]+)"\s*:|\Z)',
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                items = re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))
                payload[field] = [
                    item.replace('\\"', '"').strip() for item in items if item.strip()
                ][:8]
                continue
            # Single string instead of array.
            match = re.search(
                rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"',
                text,
                flags=re.IGNORECASE,
            )
            if match:
                payload[field] = [match.group(1).replace('\\"', '"').strip()]

        conf = re.search(r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)', text, flags=re.IGNORECASE)
        if conf:
            try:
                payload["confidence"] = float(conf.group(1))
            except ValueError:
                payload["confidence"] = 0.5
        else:
            payload["confidence"] = 0.5

        return payload

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[,;/|]", value)
            return [part.strip() for part in parts if part.strip()][:8]
        if isinstance(value, (list, tuple)):
            items: list[str] = []
            for item in value:
                text = str(item or "").strip()
                if text:
                    items.append(text)
                if len(items) >= 8:
                    break
            return items
        text = str(value).strip()
        return [text] if text else []

    def _resolve_image_path(self, image_path: str) -> Path:
        """Map `/uploads/...` URLs or filesystem paths onto the uploads directory."""
        raw = image_path.strip()
        if not raw:
            raise ImagePromptGenerationError("Empty image path", code="invalid_image")

        upload_root = self.settings.upload_path.resolve()

        if raw.startswith("/uploads/"):
            relative = raw.removeprefix("/uploads/")
            candidate = (upload_root / relative).resolve()
        elif raw.startswith("uploads/"):
            relative = raw.removeprefix("uploads/")
            candidate = (upload_root / relative).resolve()
        else:
            candidate = Path(raw).expanduser().resolve()

        try:
            candidate.relative_to(upload_root)
        except ValueError as exc:
            raise ImagePromptGenerationError(
                f"Image path must be inside the uploads directory: {raw}",
                code="invalid_image",
            ) from exc

        if not candidate.is_file():
            raise ImagePromptGenerationError(
                f"Image file not found: {raw}",
                code="invalid_image",
            )

        extension = candidate.suffix.lower().lstrip(".")
        if extension not in self.settings.allowed_extensions:
            allowed = ", ".join(sorted(self.settings.allowed_extensions))
            raise ImagePromptGenerationError(
                f"Unsupported image type '.{extension}'. Allowed: {allowed}",
                code="invalid_image",
            )

        if candidate.stat().st_size <= 0:
            raise ImagePromptGenerationError(
                f"Image file is empty: {raw}",
                code="invalid_image",
            )

        return candidate


def get_image_prompt_service(
    settings: Settings = Depends(get_settings),
    optimizer: PromptOptimizerService = Depends(get_prompt_optimizer_service),
) -> ImagePromptService:
    """FastAPI dependency factory for ImagePromptService."""
    return ImagePromptService(settings=settings, optimizer=optimizer)
