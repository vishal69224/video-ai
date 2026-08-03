"""Compose concise Kie.ai prompts from structured fashion analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from app.core.logger import get_logger
from app.services.kie_client import (
    SEEDANCE_2_MODELS,
    V1_PRO_FAST_MODEL,
    WAN_MODEL,
)

logger = get_logger()

# Preferred commercial shot order.
CANONICAL_SHOTS = [
    "Hero Wide Shot",
    "Model Walk",
    "Feature Close-up",
    "Fabric Macro",
    "Side Profile",
    "Back View",
    "Hero Pose",
]

DEFAULT_ACTIONS = [
    "Walk confidently",
    "Pause naturally",
    "Adjust garment detail",
    "Hand in pocket",
    "Slow turn",
    "Look away naturally",
    "Maintain elegant posture",
]

DEFAULT_CAMERAS = [
    "Wide Shot",
    "Tracking Shot",
    "Close-up",
    "Macro",
    "Medium Shot",
    "Orbit",
    "Low Angle",
]

DEFAULT_NEGATIVES = [
    "No dancing",
    "No jumping",
    "No running",
    "No exaggerated facial expressions",
    "No unnecessary hand waving",
    "No cartoon motion",
    "No unrealistic body deformation",
    "No clothing changes",
    "Preserve identity",
    "Preserve clothing exactly",
]

QUALITY_CLOSING = (
    "Ultra realistic. Photorealistic. Luxury commercial quality. 4K. "
    "Natural cloth physics. Realistic body movement. Professional fashion advertisement."
)


@dataclass
class PromptOptimizerService:
    """
    Turns structured fashion analysis into one optimized Kie.ai prompt.

    Provider-aware: Seedance = cinematic detail, Wan = motion-focused,
    V1 Pro Fast / Lite-style = short and concise.
    """

    def optimize(
        self,
        analysis: dict[str, Any],
        *,
        model: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> str:
        """Build a concise final cinematic prompt from structured analysis."""
        profile = self._provider_profile(model)
        seconds = self._normalize_duration(duration_seconds)
        max_shots = self._max_shots_for_duration(seconds)
        resolution_label = (resolution or "720p").strip() or "720p"

        product = self._clean_phrase(analysis.get("product") or "fashion garment")
        category = self._clean_phrase(analysis.get("category") or "apparel")
        gender = self._clean_phrase(analysis.get("gender") or "")
        fit = self._clean_phrase(analysis.get("fit") or "")
        fabric = self._clean_phrase(analysis.get("fabric") or "")
        texture = self._clean_phrase(analysis.get("texture") or "")
        material = self._clean_phrase(analysis.get("material") or "")
        primary = self._clean_phrase(analysis.get("primary_color") or "")
        secondary = self._clean_phrase(analysis.get("secondary_color") or "")
        lighting = self._clean_phrase(analysis.get("lighting") or "premium studio lighting")
        background = self._clean_phrase(analysis.get("background") or "clean commercial backdrop")

        hero_features = self._unique_phrases(analysis.get("hero_features"), limit=6)
        actions = self._unique_phrases(
            analysis.get("recommended_actions") or DEFAULT_ACTIONS,
            limit=max_shots,
        )
        cameras = self._unique_phrases(
            analysis.get("camera_suggestions") or DEFAULT_CAMERAS,
            limit=max_shots,
        )
        negatives = self._unique_phrases(
            list(analysis.get("negative_constraints") or []) + DEFAULT_NEGATIVES,
            limit=12,
        )
        views = self._unique_phrases(analysis.get("available_views"), limit=6)

        shots = self._build_shot_plan(
            max_shots=max_shots,
            hero_features=hero_features,
            actions=actions,
            cameras=cameras,
            views=views,
            profile=profile,
        )

        product_line = self._compose_product_line(
            product=product,
            category=category,
            gender=gender,
            fit=fit,
            fabric=fabric,
            texture=texture,
            material=material,
            primary=primary,
            secondary=secondary,
            hero_features=hero_features,
            profile=profile,
        )

        shot_line = self._compose_shot_line(shots, profile=profile)
        lighting_line = f"Lighting: {lighting}. Background: {background}."
        if profile == "concise":
            lighting_line = f"{lighting}; {background}."

        resolution_note = f"Output {resolution_label}."
        duration_note = f"{seconds}s commercial."

        if profile == "motion":
            body = (
                f"{product_line} Motion-led fashion commercial. {shot_line} "
                f"{lighting_line} {duration_note} {resolution_note} "
                "Keep movement elegant and fabric-driven."
            )
        elif profile == "cinematic":
            body = (
                f"{product_line} Detailed luxury fashion commercial. {shot_line} "
                f"{lighting_line} {duration_note} {resolution_note} "
                "Prioritize garment silhouette, texture, and premium framing."
            )
        else:
            body = (
                f"{product_line} {shot_line} {lighting_line} "
                f"{duration_note} {resolution_note}"
            )

        negative_section = "Negatives: " + "; ".join(negatives) + "."
        quality = QUALITY_CLOSING if profile != "concise" else (
            "Ultra realistic. Photorealistic. 4K. Professional fashion advertisement."
        )

        prompt = self._dedupe_sentences(f"{body} {negative_section} {quality}")
        logger.info(
            "Prompt optimized profile={} duration={}s shots={} chars={}",
            profile,
            seconds,
            len(shots),
            len(prompt),
        )
        return prompt

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
    def _max_shots_for_duration(seconds: int) -> int:
        if seconds <= 5:
            return 5
        if seconds <= 10:
            return 7
        if seconds <= 15:
            return 10
        if seconds <= 20:
            return 12
        return 15

    def _build_shot_plan(
        self,
        *,
        max_shots: int,
        hero_features: list[str],
        actions: list[str],
        cameras: list[str],
        views: list[str],
        profile: str,
    ) -> list[str]:
        """Build ordered shots with one camera move and one action each."""
        planned: list[str] = []
        feature_iter = iter(hero_features)
        action_iter = iter(actions)
        camera_iter = iter(cameras)

        view_hints = {self._normalize_key(item): item for item in views}
        has_back = any("back" in key for key in view_hints)
        has_side = any("side" in key or "profile" in key for key in view_hints)

        for index, shot_name in enumerate(CANONICAL_SHOTS):
            if len(planned) >= max_shots:
                break
            if shot_name == "Back View" and not has_back and index > 3:
                # Keep back view only when analysis saw a back reference, unless we need filler.
                if len(planned) + (len(CANONICAL_SHOTS) - index) > max_shots:
                    continue
            if shot_name == "Side Profile" and not has_side and len(planned) >= max_shots - 1:
                continue

            camera = next(camera_iter, None) or self._default_camera_for_shot(shot_name)
            camera = self._single_camera_move(camera)
            action = next(action_iter, None) or self._default_action_for_shot(shot_name)

            detail = ""
            if shot_name in {"Feature Close-up", "Fabric Macro"}:
                feature = next(feature_iter, None)
                if feature:
                    detail = f" on {feature}"

            if profile == "concise":
                planned.append(f"{shot_name}: {camera}, {action}{detail}")
            elif profile == "motion":
                planned.append(f"{shot_name}: {action}; camera {camera}{detail}")
            else:
                planned.append(f"{shot_name}: {camera}; model {action}{detail}")

        # Fill remaining budget with unused hero feature close-ups.
        while len(planned) < max_shots:
            feature = next(feature_iter, None)
            if not feature:
                break
            planned.append(f"Feature Close-up: Close-up, Pause naturally on {feature}")

        return planned[:max_shots]

    @staticmethod
    def _default_camera_for_shot(shot_name: str) -> str:
        mapping = {
            "Hero Wide Shot": "Wide Shot",
            "Model Walk": "Tracking Shot",
            "Feature Close-up": "Close-up",
            "Fabric Macro": "Macro",
            "Side Profile": "Medium Shot",
            "Back View": "Orbit",
            "Hero Pose": "Low Angle",
        }
        return mapping.get(shot_name, "Medium Shot")

    @staticmethod
    def _default_action_for_shot(shot_name: str) -> str:
        mapping = {
            "Hero Wide Shot": "Maintain elegant posture",
            "Model Walk": "Walk confidently",
            "Feature Close-up": "Adjust garment detail",
            "Fabric Macro": "Pause naturally",
            "Side Profile": "Slow turn",
            "Back View": "Slow turn",
            "Hero Pose": "Pause naturally",
        }
        return mapping.get(shot_name, "Pause naturally")

    @staticmethod
    def _single_camera_move(camera: str) -> str:
        """Keep one camera instruction per shot."""
        text = PromptOptimizerService._clean_phrase(camera)
        # If model returned compound moves, keep the first clause.
        for separator in (" then ", " and ", ",", "/"):
            if separator in text.lower():
                # case-preserving split on first separator occurrence
                lowered = text.lower()
                idx = lowered.find(separator)
                text = text[:idx].strip()
                break
        return text or "Medium Shot"

    def _compose_product_line(
        self,
        *,
        product: str,
        category: str,
        gender: str,
        fit: str,
        fabric: str,
        texture: str,
        material: str,
        primary: str,
        secondary: str,
        hero_features: list[str],
        profile: str,
    ) -> str:
        color = primary
        if secondary and secondary.lower() not in primary.lower():
            color = f"{primary} and {secondary}" if primary else secondary

        material_bits = self._unique_phrases([fabric, texture, material], limit=3)
        # Drop material tokens already covered by fabric/texture wording.
        filtered_materials: list[str] = []
        for bit in material_bits:
            key = self._normalize_key(bit)
            if any(
                key != self._normalize_key(other) and key in self._normalize_key(other)
                for other in material_bits
            ):
                continue
            filtered_materials.append(bit)
        material_text = ", ".join(filtered_materials)

        parts: list[str] = []
        subject = product if product else category
        if gender:
            parts.append(f"Showcase the {color + ' ' if color else ''}{subject} ({gender} {category})".strip())
        else:
            parts.append(f"Showcase the {color + ' ' if color else ''}{subject}".strip())

        if fit:
            parts.append(f"{fit} fit")
        if material_text:
            parts.append(material_text)
        if hero_features:
            # Mention each hero feature once.
            if profile == "concise":
                parts.append("highlight " + ", ".join(hero_features[:3]))
            else:
                parts.append("hero details: " + ", ".join(hero_features[:5]))

        line = ". ".join(self._unique_phrases(parts, limit=8))
        if not line.endswith("."):
            line += "."
        return line

    @staticmethod
    def _compose_shot_line(shots: list[str], *, profile: str) -> str:
        if not shots:
            return "Hero Wide Shot then Hero Pose."
        if profile == "concise":
            return "Shots: " + " | ".join(shots) + "."
        return "Shot sequence: " + "; ".join(shots) + "."

    @staticmethod
    def _unique_phrases(values: Any, *, limit: int = 10) -> list[str]:
        if values is None:
            return []
        if isinstance(values, str):
            items: Iterable[Any] = re.split(r"[,;/|]", values)
        elif isinstance(values, (list, tuple, set)):
            items = values
        else:
            items = [values]

        seen: set[str] = set()
        result: list[str] = []
        for raw in items:
            phrase = PromptOptimizerService._clean_phrase(raw)
            if not phrase:
                continue
            key = PromptOptimizerService._normalize_key(phrase)
            if key in seen:
                continue
            seen.add(key)
            result.append(phrase)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _clean_phrase(value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" .-;:")
        return text

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @staticmethod
    def _dedupe_sentences(text: str) -> str:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        seen: set[str] = set()
        kept: list[str] = []
        for part in parts:
            key = PromptOptimizerService._normalize_key(part)
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(part if part.endswith((".", "!", "?")) else f"{part}.")
        return " ".join(kept)


def get_prompt_optimizer_service() -> PromptOptimizerService:
    """FastAPI dependency factory for PromptOptimizerService."""
    return PromptOptimizerService()
