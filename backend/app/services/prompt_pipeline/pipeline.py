"""End-to-end fashion commercial director prompt pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends

from app.ai.orchestrator import AIOrchestrator, get_ai_orchestrator
from app.core.config import Settings, get_settings
from app.core.exceptions import ImagePromptGenerationError
from app.core.logger import get_logger
from app.services.prompt_builder_service import (
    PromptBuilderService,
    get_prompt_builder_service,
)
from app.services.prompt_optimizer_service import (
    PromptOptimizerService,
    get_prompt_optimizer_service,
)
from app.services.prompt_pipeline.action_planner import ActionPlanner
from app.services.prompt_pipeline.camera_planner import CameraPlanner
from app.services.prompt_pipeline.fashion_director import FashionDirectorEngine
from app.services.prompt_pipeline.garment_analysis import GarmentAnalysisStage
from app.services.prompt_pipeline.image_analysis import ImageAnalysisStage
from app.services.prompt_pipeline.models import CommercialPlan, PlannedShot
from app.services.prompt_pipeline.prompt_validator import PromptValidator
from app.services.prompt_pipeline.scene_analysis import SceneAnalysisStage
from app.services.prompt_pipeline.storyboard_planner import StoryboardPlanner

logger = get_logger()


@dataclass
class FashionPromptPipeline:
    """
    Images → Image Analysis → Garment Analysis → Fashion Director →
    Scene Analysis → Storyboard → Action → Camera →
    Prompt Builder → Validator → Optimizer
    """

    settings: Settings
    orchestrator: AIOrchestrator
    builder: PromptBuilderService
    optimizer: PromptOptimizerService

    def __post_init__(self) -> None:
        self.image_analysis = ImageAnalysisStage(orchestrator=self.orchestrator)
        self.garment_analysis = GarmentAnalysisStage()
        self.fashion_director = FashionDirectorEngine()
        self.scene_analysis = SceneAnalysisStage()
        self.storyboard_planner = StoryboardPlanner()
        self.action_planner = ActionPlanner()
        self.camera_planner = CameraPlanner()
        self.validator = PromptValidator()

    async def generate(
        self,
        image_paths: list[Path],
        *,
        model: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> str:
        if not image_paths:
            raise ImagePromptGenerationError(
                "At least one image path is required",
                code="invalid_image",
            )

        seconds = self._normalize_duration(duration_seconds)
        resolution_label = (resolution or "720p").strip() or "720p"

        analysis = await self.image_analysis.run(image_paths)
        garment = self.garment_analysis.run(analysis)
        director = self.fashion_director.run(garment, analysis)
        scenes = self.scene_analysis.run(analysis)
        storyboard = self.storyboard_planner.run(
            scenes,
            garment,
            duration_seconds=seconds,
            director=director,
        )
        # Fallback planners only fill gaps; cinematic storyboard owns the narrative.
        # Both are directed by the Fashion Director Engine when available.
        fallback_actions = self.action_planner.run(
            storyboard, garment, analysis, director=director
        )
        fallback_cameras = self.camera_planner.run(storyboard, director=director)

        shots: list[PlannedShot] = []
        for index, scene in enumerate(storyboard):
            shots.append(
                PlannedShot(
                    scene_number=scene.scene_number,
                    beat=scene.beat,
                    title=scene.title,
                    purpose=scene.scene_goal,
                    action=scene.model_action or fallback_actions[index],
                    camera=scene.camera_movement or fallback_cameras[index],
                    focus_feature=scene.product_focus or scene.focus_feature,
                    source_image_index=scene.source_image_index,
                    transition=scene.transition,
                )
            )

        plan = CommercialPlan(
            analysis=analysis,
            garment=garment,
            scenes=scenes,
            storyboard=storyboard,
            shots=shots,
            duration_seconds=seconds,
            resolution=resolution_label,
            model=model,
            director=director,
        )

        plan = self.validator.validate_plan(plan)
        draft = self.builder.build_from_plan(plan)
        prompt = self.optimizer.optimize(
            draft,
            model=model,
            duration_seconds=seconds,
            resolution=resolution_label,
        )
        self.validator.validate_prompt(prompt, plan)

        if not prompt.strip():
            raise ImagePromptGenerationError(
                "Prompt pipeline returned an empty prompt",
                code="empty_response",
            )

        logger.info(
            "Fashion commercial prompt ready product={!r} style={} mood={} scenes={} chars={}",
            garment.hero_product,
            director.garment_style,
            director.commercial_mood,
            len(plan.shots),
            len(prompt),
        )
        return prompt

    @staticmethod
    def _normalize_duration(duration_seconds: int | None) -> int:
        try:
            seconds = int(duration_seconds) if duration_seconds is not None else 5
        except (TypeError, ValueError):
            seconds = 5
        return max(1, min(seconds, 30))


def get_fashion_prompt_pipeline(
    settings: Settings = Depends(get_settings),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    builder: PromptBuilderService = Depends(get_prompt_builder_service),
    optimizer: PromptOptimizerService = Depends(get_prompt_optimizer_service),
) -> FashionPromptPipeline:
    """FastAPI dependency factory for FashionPromptPipeline."""
    return FashionPromptPipeline(
        settings=settings,
        orchestrator=orchestrator,
        builder=builder,
        optimizer=optimizer,
    )
