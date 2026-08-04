"""Step 1 — Image Analysis (vision → structured JSON)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.ai.orchestrator import AIOrchestrator
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger
from app.services.prompt_pipeline.json_utils import (
    as_string_list,
    clean_str,
    parse_json_object,
)
from app.services.prompt_pipeline.models import ImageAnalysis, ImageScene

logger = get_logger()

IMAGE_ANALYSIS_SYSTEM = """You are a Fashion Commercial Image Analyst.

You are NOT writing a video prompt.
You are NOT captioning people.

Analyze ALL attached reference images together.
Preserve upload order: Image 1 is first attached, Image 2 second, etc.

Return ONLY one valid JSON object. No markdown. No preamble.

Schema:
{
  "product_type": "string",
  "garment_category": "string",
  "gender": "string",
  "primary_color": "string",
  "secondary_colors": ["string"],
  "material": "string",
  "texture": "string",
  "fit": "string",
  "construction_details": ["string"],
  "visible_accessories": ["string"],
  "environment": "string",
  "lighting": "string",
  "background": "string",
  "mood": "string",
  "body_pose": "string",
  "face_direction": "string",
  "hand_position": "string",
  "intended_commercial_subject": "shirt",
  "images": [
    {
      "index": 1,
      "reference_type": "front|back|side|closeup|lifestyle|macro",
      "role": "Hero Front|Fabric Closeup|Full Body|Shoulder Detail|Back View|Side Profile|Lifestyle|Macro Detail",
      "is_hero_image": true,
      "detected_products": ["shirt", "pants"],
      "primary_product_in_image": "shirt",
      "product_areas": {"shirt": 65, "pants": 25},
      "visible_details": ["string"],
      "notes": "string"
    }
  ],
  "confidence": 0.0
}

Rules:
- Use ONLY what is visible in THE CURRENT images. Never invent logos, colors, pockets, or garments.
- Do NOT carry over products or features from previous requests or memory.
- For EACH image, list every garment category visibly present in detected_products
  using only: shirt, pants, jacket, dress, skirt, shoes, bag, accessory.
- primary_product_in_image = the dominant garment in that specific image.
- product_areas = approximate percent of the frame occupied by each detected product (0–100). Values may sum over 100 if overlapping.
- is_hero_image = true for the strongest full-product campaign/hero frame.
- intended_commercial_subject = the garment most likely meant to be sold in this shoot.
- construction_details / visible_details must belong to garments actually visible.
- Never list shirt features when only pants are shown (and vice versa).
- Classify EVERY uploaded image in upload order.
- reference_type must be one of: front, back, side, closeup, lifestyle, macro.
- Keep arrays short and unique.
- confidence is 0.0–1.0."""

IMAGE_ANALYSIS_USER = (
    "Analyze all attached fashion reference images in upload order and return "
    "ONLY the JSON object defined in the system instructions."
)

MAX_ATTEMPTS = 3


@dataclass
class ImageAnalysisStage:
    """Vision stage: extract structured commercial image analysis."""

    orchestrator: AIOrchestrator

    async def run(self, image_paths: list[Path]) -> ImageAnalysis:
        logger.info("Pipeline stage=image_analysis images={}", len(image_paths))
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            temperature = 0.0 if attempt == 1 else min(0.2 * attempt, 0.5)
            try:
                raw = await self.orchestrator.analyze_images(
                    image_paths,
                    IMAGE_ANALYSIS_SYSTEM,
                    IMAGE_ANALYSIS_USER,
                    temperature=temperature,
                )
                analysis = self._normalize(raw, expected_count=len(image_paths))
                logger.info(
                    "Image analysis ready product={!r} images={} attempt={}",
                    analysis.product_type or analysis.garment_category,
                    len(analysis.images),
                    attempt,
                )
                return analysis
            except ImagePromptGenerationError as exc:
                if exc.code in {"invalid_api_key", "invalid_image", "model_missing"}:
                    raise
                logger.warning(
                    "Image analysis failed attempt={}/{} code={}",
                    attempt,
                    MAX_ATTEMPTS,
                    exc.code,
                )
                last_error = exc
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected image analysis failure")
                last_error = ImagePromptGenerationError(
                    f"Image analysis failed: {exc}",
                    code="prompt_generation_failed",
                )

        if isinstance(last_error, ImagePromptGenerationError):
            raise last_error
        raise ImagePromptGenerationError(
            "Image analysis failed",
            code="empty_response",
        )

    def _normalize(self, raw: str, *, expected_count: int) -> ImageAnalysis:
        payload = parse_json_object(raw)
        secondary = as_string_list(
            payload.get("secondary_colors") or payload.get("secondary_color"),
            limit=4,
        )
        images = self._normalize_images(payload.get("images"), expected_count)

        confidence = payload.get("confidence", 0.5)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.5

        analysis = ImageAnalysis(
            product_type=clean_str(payload.get("product_type") or payload.get("product")),
            garment_category=clean_str(
                payload.get("garment_category") or payload.get("category")
            ),
            gender=clean_str(payload.get("gender")),
            primary_color=clean_str(payload.get("primary_color")),
            secondary_colors=secondary,
            material=clean_str(payload.get("material") or payload.get("fabric")),
            texture=clean_str(payload.get("texture")),
            fit=clean_str(payload.get("fit")),
            construction_details=as_string_list(payload.get("construction_details"), limit=10),
            visible_accessories=as_string_list(payload.get("visible_accessories"), limit=8),
            environment=clean_str(payload.get("environment")),
            lighting=clean_str(payload.get("lighting")) or "soft luxury studio lighting",
            background=clean_str(payload.get("background")) or "clean commercial backdrop",
            mood=clean_str(payload.get("mood")) or "premium calm",
            body_pose=clean_str(payload.get("body_pose")),
            face_direction=clean_str(payload.get("face_direction")),
            hand_position=clean_str(payload.get("hand_position")),
            confidence=max(0.0, min(1.0, confidence_value)),
            intended_commercial_subject=clean_str(
                payload.get("intended_commercial_subject")
                or payload.get("commercial_subject")
            ),
            images=images,
        )

        if not analysis.product_type and not analysis.garment_category:
            raise ImagePromptGenerationError(
                "Image analysis missing product/category",
                code="empty_response",
            )
        return analysis

    def _normalize_images(self, value: Any, expected_count: int) -> list[ImageScene]:
        scenes: list[ImageScene] = []
        if isinstance(value, list):
            for idx, item in enumerate(value, start=1):
                if not isinstance(item, dict):
                    continue
                ref = clean_str(item.get("reference_type")).lower()
                if ref not in {"front", "back", "side", "closeup", "lifestyle", "macro"}:
                    role_hint = clean_str(item.get("role")).lower()
                    ref = self._infer_reference_type(role_hint) or "front"
                role = clean_str(item.get("role")) or self._default_role(ref, idx)
                detected = as_string_list(
                    item.get("detected_products") or item.get("products"),
                    limit=6,
                )
                primary_in_image = clean_str(
                    item.get("primary_product_in_image") or item.get("primary_product")
                )
                areas = self._normalize_product_areas(item.get("product_areas"))
                is_hero = bool(item.get("is_hero_image"))
                if not is_hero and "hero" in role.lower():
                    is_hero = True
                scenes.append(
                    ImageScene(
                        index=int(item.get("index") or idx),
                        reference_type=ref,
                        role=role,
                        visible_details=as_string_list(item.get("visible_details"), limit=8),
                        notes=clean_str(item.get("notes")),
                        detected_products=detected,
                        primary_product_in_image=primary_in_image,
                        product_areas=areas,
                        is_hero_image=is_hero,
                    )
                )

        # Ensure one scene slot per uploaded image (upload order).
        while len(scenes) < expected_count:
            idx = len(scenes) + 1
            scenes.append(
                ImageScene(
                    index=idx,
                    reference_type="front" if idx == 1 else "closeup",
                    role="Hero Front" if idx == 1 else "Detail Closeup",
                )
            )
        return scenes[:expected_count]

    @staticmethod
    def _normalize_product_areas(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        areas: dict[str, float] = {}
        for key, raw in value.items():
            label = clean_str(key).lower()
            if not label:
                continue
            try:
                amount = float(raw)
            except (TypeError, ValueError):
                continue
            # Accept 0–1 ratios or 0–100 percentages.
            if 0.0 < amount <= 1.0:
                amount *= 100.0
            areas[label] = max(0.0, min(100.0, amount))
        return areas

    @staticmethod
    def _infer_reference_type(role_hint: str) -> str | None:
        mapping = [
            ("back", "back"),
            ("side", "side"),
            ("profile", "side"),
            ("macro", "macro"),
            ("fabric", "macro"),
            ("close", "closeup"),
            ("detail", "closeup"),
            ("lifestyle", "lifestyle"),
            ("front", "front"),
            ("hero", "front"),
            ("full", "front"),
        ]
        for needle, value in mapping:
            if needle in role_hint:
                return value
        return None

    @staticmethod
    def _default_role(reference_type: str, index: int) -> str:
        defaults = {
            "front": "Hero Front" if index == 1 else "Front View",
            "back": "Back View",
            "side": "Side Profile",
            "closeup": "Detail Closeup",
            "macro": "Fabric Closeup",
            "lifestyle": "Lifestyle",
        }
        return defaults.get(reference_type, f"Reference {index}")
