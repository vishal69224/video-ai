"""Step 9 — Prompt Optimizer (polish, dedupe, provider-aware shaping)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.kie_client import (
    SEEDANCE_2_MODELS,
    V1_PRO_FAST_MODEL,
    WAN_MODEL,
)

logger = get_logger()


@dataclass
class PromptOptimizerService:
    """
    Final polish pass for director-built prompts.

    Does NOT fill templates from captions. It only:
    - removes duplicate sentences
    - trims generic filler
    - shapes length/tone per video provider
    """

    def optimize(
        self,
        prompt: str,
        *,
        model: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> str:
        profile = self._provider_profile(model)
        text = " ".join((prompt or "").split())
        text = self._dedupe_sentences(text)
        text = self._strip_generic_filler(text)

        if profile == "concise":
            text = self._tighten(text, max_chars=1400)
        elif profile == "motion":
            if "motion" not in text.lower() and "walk" in text.lower():
                text = text.replace(
                    "Luxury fashion commercial.",
                    "Luxury fashion commercial. Keep movement fabric-driven.",
                    1,
                )
        elif profile == "cinematic":
            if "premium framing" not in text.lower():
                text = text.rstrip(".") + ". Emphasize premium framing and texture."

        # Ensure resolution/duration notes survive tightening.
        seconds = self._normalize_duration(duration_seconds)
        resolution_label = (resolution or "720p").strip() or "720p"
        if f"{seconds}s" not in text:
            text = f"{text} {seconds}s commercial."
        if resolution_label.lower() not in text.lower():
            text = f"{text} Output {resolution_label}."

        text = self._dedupe_sentences(text)
        logger.info(
            "Prompt optimized profile={} duration={}s chars={}",
            profile,
            seconds,
            len(text),
        )
        return text.strip()

    def _provider_profile(self, model: str | None) -> str:
        slug = (model or "").strip().lower()
        if slug in {m.lower() for m in SEEDANCE_2_MODELS} or "seedance-2" in slug:
            return "cinematic"
        if slug == WAN_MODEL.lower() or slug.startswith("wan/"):
            return "motion"
        if "v1-pro-fast" in slug or "v1-lite" in slug or slug == V1_PRO_FAST_MODEL.lower():
            return "concise"
        return "concise"

    @staticmethod
    def _normalize_duration(duration_seconds: int | None) -> int:
        try:
            seconds = int(duration_seconds) if duration_seconds is not None else 5
        except (TypeError, ValueError):
            seconds = 5
        return max(1, min(seconds, 30))

    @staticmethod
    def _strip_generic_filler(text: str) -> str:
        banned = [
            r"\bwalk confidently\b",
            r"\bpause naturally\b",
            r"\bhand in pocket\b",
            r"\blook away naturally\b",
            r"\bmaintain elegant posture\b",
            r"\badjust garment detail\b",
        ]
        cleaned = text
        for pattern in banned:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
        return cleaned.strip()

    @staticmethod
    def _tighten(text: str, *, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
        if not parts:
            return text

        # Always preserve negatives + closing quality lines.
        reserved = [
            part
            for part in parts
            if part.lower().startswith("negatives:")
            or part.lower().startswith("ultra realistic")
            or "cloth physics" in part.lower()
        ]
        body = [part for part in parts if part not in reserved]
        if not body:
            return " ".join(reserved)

        kept: list[str] = []
        # Prefer opening + scene lines; drop from the middle if needed.
        for part in body:
            candidate = " ".join(kept + [part] + reserved).strip()
            if len(candidate) > max_chars and kept:
                continue
            kept.append(part)
        result = " ".join(kept + reserved).strip()
        if len(result) > max_chars + 80:
            # Hard fallback: opening + first scenes + reserved.
            result = " ".join(body[:4] + reserved).strip()
        return result

    @staticmethod
    def _dedupe_sentences(text: str) -> str:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        seen: set[str] = set()
        kept: list[str] = []
        for part in parts:
            key = re.sub(r"[^a-z0-9]+", "", part.lower())
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(part if part.endswith((".", "!", "?")) else f"{part}.")
        return " ".join(kept)


def get_prompt_optimizer_service() -> PromptOptimizerService:
    """FastAPI dependency factory for PromptOptimizerService."""
    return PromptOptimizerService()
