"""Step 6 — Camera Planner (cinematic, non-repeating movements)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import DirectorBrief, StoryboardScene

logger = get_logger()

GENERIC_CAMERAS = {
    "wide shot",
    "medium shot",
    "tracking shot",
    "close-up",
    "close up",
    "macro",
    "orbit",
    "low angle",
}

CAMERA_BANK = [
    "slow push in",
    "slow dolly in",
    "slow dolly out",
    "orbit 30°",
    "orbit 45°",
    "waist tracking",
    "shoulder tracking",
    "slider movement",
    "macro glide",
    "low angle luxury shot",
    "rack focus",
    "parallax",
    "over shoulder reveal",
    "hero product reveal",
]

SCENE_CAMERA_PREFERENCE: dict[str, list[str]] = {
    "hero introduction": ["hero product reveal", "slow push in", "low angle luxury shot"],
    "front reveal": ["slow dolly in", "parallax", "slider movement"],
    "fabric macro": ["macro glide", "rack focus"],
    "interaction": ["shoulder tracking", "slow push in", "rack focus"],
    "back reveal": ["orbit 45°", "over shoulder reveal", "orbit 30°"],
    "side profile": ["orbit 30°", "slider movement", "parallax"],
    "walking shot": ["waist tracking", "shoulder tracking", "slow dolly out"],
    "ending pose": ["slow dolly out", "low angle luxury shot", "hero product reveal"],
}


@dataclass
class CameraPlanner:
    """Assign a different cinematic camera move to every scene."""

    def run(
        self,
        storyboard: list[StoryboardScene],
        director: DirectorBrief | None = None,
    ) -> list[str]:
        logger.info(
            "Pipeline stage=camera_planner director_style={}",
            director.garment_style if director else "n/a",
        )
        used: set[str] = set()
        cameras: list[str] = []
        director_bank = list(director.cameras) if director else []

        for scene in storyboard:
            mapped = self._director_scene_camera(scene, director)
            if mapped and self._norm(mapped) not in used:
                camera = mapped
            else:
                camera = self._pick_for_scene(scene, used, director_bank=director_bank)
            cameras.append(camera)
            used.add(self._norm(camera))

        logger.info("Cameras planned={}", cameras)
        return cameras

    def _director_scene_camera(
        self,
        scene: StoryboardScene,
        director: DirectorBrief | None,
    ) -> str | None:
        if not director:
            return None
        title = scene.title.lower()
        for key, camera in director.scene_camera_map.items():
            if key.replace("_", " ") in title or key in title:
                return camera
        aliases = {
            "opening": "hero",
            "hero": "hero",
            "collar": "collar",
            "button": "button",
            "walking": "walking",
            "walk": "walking",
            "fabric": "fabric",
            "back": "back",
            "ending": "ending",
            "waistband": "waistband",
            "pocket": "pocket",
            "lapel": "lapel",
            "closure": "closure",
            "neckline": "neckline",
            "drape": "drape",
            "feature": "feature",
        }
        for needle, key in aliases.items():
            if needle in title and key in director.scene_camera_map:
                return director.scene_camera_map[key]
        return None

    def _pick_for_scene(
        self,
        scene: StoryboardScene,
        used: set[str],
        *,
        director_bank: list[str] | None = None,
    ) -> str:
        title = scene.title.lower()
        preferred: list[str] = []
        for key, cams in SCENE_CAMERA_PREFERENCE.items():
            if key in title or (
                key == "interaction" and "interaction" in title
            ):
                preferred.extend(cams)

        bank = list(director_bank or []) + CAMERA_BANK
        for camera in preferred + bank:
            key = self._norm(camera)
            if key in used or key in GENERIC_CAMERAS:
                continue
            return camera

        for index, camera in enumerate(bank, start=1):
            candidate = f"{camera} variant {index}"
            key = self._norm(candidate)
            if key not in used:
                return camera
        return "slow push in"

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())
