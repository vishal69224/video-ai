"""Step 8 — Prompt Validator with self-healing storyboard repair."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger
from app.services.prompt_pipeline.models import CommercialPlan, PlannedShot
from app.services.prompt_pipeline.storyboard_repair import StoryboardRepair

logger = get_logger()

GENERIC_PHRASES = [
    "walk confidently",
    "pause naturally",
    "hand in pocket",
    "look away naturally",
    "maintain elegant posture",
    "adjust garment detail",
]

GENERIC_REPLACEMENTS = {
    "walk confidently": "Slow confident runway walk with natural arm swing",
    "pause naturally": "Settle into a calm standing pose",
    "hand in pocket": "Rest one hand lightly near the pocket seam",
    "look away naturally": "Look over the shoulder briefly",
    "maintain elegant posture": "Hold a confident final brand frame",
    "adjust garment detail": "Touch the hero construction detail once",
}


@dataclass
class PromptValidator:
    """
    Validate commercial plan + draft prompt.

    Missing commercial beats are repaired automatically.
    Only unrecoverable analysis failures raise errors.
    """

    repair_service: StoryboardRepair | None = None

    def __post_init__(self) -> None:
        if self.repair_service is None:
            self.repair_service = StoryboardRepair()

    def validate_plan(self, plan: CommercialPlan) -> CommercialPlan:
        """Repair missing beats, sanitize soft issues, then accept the plan."""
        logger.info("Pipeline stage=prompt_validator plan")
        self._assert_recoverable_subject(plan)

        plan = self.repair_service.repair(plan)
        plan = self._sanitize_features(plan)
        plan = self._sanitize_actions(plan)
        plan = self._dedupe_cameras_and_actions(plan)
        plan.shots = StoryboardRepair._renumber(plan.shots)
        plan.storyboard = StoryboardRepair._shots_to_storyboard(plan.shots)

        logger.info(
            "Plan validated after repair shots={} titles={}",
            len(plan.shots),
            [shot.title for shot in plan.shots],
        )
        return plan

    def validate_prompt(self, prompt: str, plan: CommercialPlan) -> None:
        """Soft prompt checks — only fail on empty/unusable output."""
        logger.info("Pipeline stage=prompt_validator prompt")
        text = (prompt or "").strip()
        if not text:
            raise ImagePromptGenerationError(
                "Generated prompt is empty",
                code="empty_response",
            )

        # Soft warnings only — never fail for missing beat wording in text.
        lowered = text.lower()
        if "negatives:" not in lowered and "negative" not in lowered:
            logger.warning("Prompt missing explicit negatives section; continuing")
        if len(text) < 80:
            logger.warning("Prompt is unusually short ({} chars); continuing", len(text))

        logger.info(
            "Prompt validated shots={} chars={}",
            len(plan.shots),
            len(text),
        )

    def _assert_recoverable_subject(self, plan: CommercialPlan) -> None:
        """Fail only when analysis has no usable subject/garment."""
        analysis = plan.analysis
        garment = plan.garment
        subject = (
            garment.primary_product
            or garment.hero_product
            or analysis.product_type
            or analysis.garment_category
        ).strip()
        if not subject:
            raise ImagePromptGenerationError(
                "No garment/subject detected in analysis",
                code="empty_response",
            )
        if not analysis.images and not analysis.product_type and not analysis.garment_category:
            raise ImagePromptGenerationError(
                "Empty fashion analysis",
                code="empty_response",
            )

    def _sanitize_features(self, plan: CommercialPlan) -> CommercialPlan:
        allowed_list = plan.garment.visible_features or plan.garment.hero_features
        allowed = {self._norm(feature) for feature in allowed_list}
        for shot in plan.shots:
            feature = self._norm(shot.focus_feature)
            if not feature or not allowed:
                continue
            # Keep descriptive walking/ending focus lines even if not a garment feature.
            if any(
                token in shot.title.lower()
                for token in ("walking", "ending", "opening hero", "hero")
            ):
                continue
            if feature in allowed or any(
                feature in allowed_item or allowed_item in feature for allowed_item in allowed
            ):
                continue
            logger.warning(
                "Clearing unverified focus feature {!r} from scene {}",
                shot.focus_feature,
                shot.scene_number,
            )
            shot.focus_feature = allowed_list[0] if allowed_list else ""
        return plan

    def _sanitize_actions(self, plan: CommercialPlan) -> CommercialPlan:
        banned_patterns = (
            r"\bjump(?:ing|s)?\b",
            r"\bdanc(?:e|ing|es)\b",
            r"\brunning\b",
            r"\brun\s+(?:away|forward|across the room|fast)\b",
            r"\bspin fast\b",
            r"\bcartwheel\b",
        )
        for shot in plan.shots:
            action_key = self._norm(shot.action)
            for generic, replacement in GENERIC_REPLACEMENTS.items():
                if action_key == self._norm(generic):
                    logger.warning(
                        "Replacing generic action {!r} with {!r}",
                        shot.action,
                        replacement,
                    )
                    shot.action = replacement
                    break

            blob = f"{shot.action} {shot.purpose}".lower()
            if any(re.search(pattern, blob) for pattern in banned_patterns):
                logger.warning(
                    "Replacing exaggerated action {!r}",
                    shot.action,
                )
                shot.action = "Settle into a calm standing pose"
        return plan

    def _dedupe_cameras_and_actions(self, plan: CommercialPlan) -> CommercialPlan:
        seen_actions: set[str] = set()
        seen_cameras: set[str] = set()
        alt_cameras = [
            "Slow push in",
            "Parallax",
            "Slider movement",
            "Rack focus",
            "Over shoulder reveal",
            "Low angle luxury shot",
        ]
        alt_actions = [
            "Settle into a calm standing pose",
            "Shift body weight naturally",
            "Touch the hero construction detail once",
            "Look over the shoulder briefly",
            "Hold a confident final brand frame",
            "Inhale slowly and soften the shoulders",
        ]
        camera_i = 0
        action_i = 0

        for shot in plan.shots:
            action_key = self._norm(shot.action)
            if action_key in seen_actions:
                while action_i < len(alt_actions) and self._norm(alt_actions[action_i]) in seen_actions:
                    action_i += 1
                if action_i < len(alt_actions):
                    shot.action = alt_actions[action_i]
                    action_i += 1
                    action_key = self._norm(shot.action)
            seen_actions.add(action_key)

            camera_key = self._norm(shot.camera)
            if camera_key in seen_cameras:
                while camera_i < len(alt_cameras) and self._norm(alt_cameras[camera_i]) in seen_cameras:
                    camera_i += 1
                if camera_i < len(alt_cameras):
                    shot.camera = alt_cameras[camera_i]
                    camera_i += 1
                    camera_key = self._norm(shot.camera)
            seen_cameras.add(camera_key)

        return plan

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())
