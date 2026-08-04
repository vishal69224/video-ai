"""
Seedance pricing — single source of truth.

Config: app/data/seedance_pricing.json
Formula: credits = credits_per_second × duration
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger()

PRICING_FILE = Path(__file__).resolve().parent.parent / "data" / "seedance_pricing.json"


@dataclass(frozen=True)
class CreditQuote:
    model: str
    model_id: str
    model_name: str
    resolution: str
    duration: int
    credits: float
    credits_per_second: float


class SeedancePricingEngine:
    """estimateCredits(model, resolution, duration) — only credit calculator."""

    def __init__(self, catalog: dict[str, Any]) -> None:
        self.catalog = catalog
        self._by_key: dict[str, dict[str, Any]] = {}
        for model in catalog.get("models") or []:
            for key in (model.get("id"), model.get("model_id")):
                text = str(key or "").strip()
                if text:
                    self._by_key[text] = model

    @classmethod
    def from_file(cls, path: Path | None = None) -> SeedancePricingEngine:
        pricing_path = path or PRICING_FILE
        payload = json.loads(pricing_path.read_text(encoding="utf-8"))
        logger.info(
            "Loaded Seedance pricing version={} models={}",
            payload.get("version"),
            len(payload.get("models") or []),
        )
        return cls(payload)

    def list_models(self, *, ui_only: bool = False) -> list[dict[str, Any]]:
        models = list(self.catalog.get("models") or [])
        if ui_only:
            models = [m for m in models if m.get("ui_visible", True)]
        return models

    def get_catalog(self, *, ui_only: bool = False) -> dict[str, Any]:
        models = []
        for model in self.list_models(ui_only=ui_only):
            item = dict(model)
            quote = self.estimateCredits(
                str(model.get("id") or ""),
                str(model.get("default_resolution") or "720p"),
                int(model.get("default_duration") or 5),
            )
            item["example_credits"] = quote.credits if quote else None
            item["pricing_available"] = quote is not None
            models.append(item)
        return {
            "version": self.catalog.get("version"),
            "formula": self.catalog.get("formula"),
            "billing_mode": self.catalog.get("billing_mode"),
            "models": models,
        }

    def find_model(self, model: str | None) -> dict[str, Any] | None:
        key = (model or "").strip()
        return self._by_key.get(key) if key else None

    def estimateCredits(
        self,
        model: str,
        resolution: str,
        duration: int | float | str,
    ) -> CreditQuote | None:
        """credits = credits_per_second × duration"""
        config = self.find_model(model)
        if not config:
            return None

        res = _normalize_resolution(resolution)
        seconds = _normalize_duration(duration)
        if res not in (config.get("resolutions") or []):
            return None

        dmin = int(config.get("duration_min") or min(config.get("durations") or [1]))
        dmax = int(config.get("duration_max") or max(config.get("durations") or [1]))
        if seconds < dmin or seconds > dmax:
            return None

        rate = (config.get("credits_per_second") or {}).get(res)
        if rate is None:
            return None

        credits_per_second = float(rate)
        credits = round(credits_per_second * seconds, 4)
        return CreditQuote(
            model=str(config.get("id") or ""),
            model_id=str(config.get("model_id") or ""),
            model_name=str(config.get("name") or ""),
            resolution=res,
            duration=seconds,
            credits=credits,
            credits_per_second=credits_per_second,
        )

    # Alias for Python call sites.
    estimate_credits = estimateCredits


def _normalize_resolution(value: str) -> str:
    raw = (value or "").strip().lower()
    return {
        "480": "480p",
        "720": "720p",
        "1080": "1080p",
        "2160": "4k",
        "2160p": "4k",
    }.get(raw, raw)


def _normalize_duration(value: int | float | str) -> int:
    try:
        return max(0, int(math.floor(float(value))))
    except (TypeError, ValueError):
        return 0


@lru_cache(maxsize=1)
def _cached_engine() -> SeedancePricingEngine:
    return SeedancePricingEngine.from_file()


def get_seedance_pricing_engine() -> SeedancePricingEngine:
    return _cached_engine()


def reload_seedance_pricing_engine() -> SeedancePricingEngine:
    _cached_engine.cache_clear()
    return _cached_engine()
