"""Step 3 — Scene Analysis (classify every uploaded image)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import ImageAnalysis, ImageScene

logger = get_logger()


@dataclass
class SceneAnalysisStage:
    """Normalize and order per-image commercial roles."""

    def run(self, analysis: ImageAnalysis) -> list[ImageScene]:
        logger.info("Pipeline stage=scene_analysis images={}", len(analysis.images))
        scenes = sorted(analysis.images, key=lambda item: item.index)

        # Promote first front/lifestyle image as hero if none marked.
        has_hero = any("hero" in scene.role.lower() for scene in scenes)
        if scenes and not has_hero:
            preferred = next(
                (
                    scene
                    for scene in scenes
                    if scene.reference_type in {"front", "lifestyle"}
                ),
                scenes[0],
            )
            preferred.role = "Hero Front"

        # Ensure macro/closeup naming is consistent.
        for scene in scenes:
            if scene.reference_type == "macro" and "macro" not in scene.role.lower():
                scene.role = "Fabric Closeup"
            elif scene.reference_type == "back" and "back" not in scene.role.lower():
                scene.role = "Back View"
            elif scene.reference_type == "side" and "side" not in scene.role.lower():
                scene.role = "Side Profile"

        for scene in scenes:
            logger.info(
                "Scene image={} type={} role={}",
                scene.index,
                scene.reference_type,
                scene.role,
            )
        return scenes
