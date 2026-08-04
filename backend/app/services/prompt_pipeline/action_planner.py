"""Step 5 — Action Planner (context-aware, non-generic actions)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import (
    DirectorBrief,
    GarmentAnalysis,
    ImageAnalysis,
    StoryboardScene,
)

logger = get_logger()

GENERIC_BANNED = {
    "walk confidently",
    "pause naturally",
    "hand in pocket",
    "slow turn",
    "look away naturally",
    "maintain elegant posture",
    "adjust garment detail",
}

CATEGORY_ACTIONS: dict[str, list[str]] = {
    "shirt": [
        "straighten the collar with two fingers",
        "button the cuff deliberately",
        "touch the chest pocket lightly",
        "roll and settle a sleeve",
        "smooth the placket once",
        "shift weight into a relaxed stance",
        "look over the shoulder briefly",
        "slow confident walk with natural arm swing",
        "inhale slowly and settle the shoulders",
    ],
    "pants": [
        "adjust the waistband with one hand",
        "check the belt loop naturally",
        "run fingers across the fabric at the thigh",
        "shift body weight to show drape",
        "take a slow confident walk",
        "pause with relaxed standing posture",
        "look over the shoulder to reveal the back",
        "settle the hem with a soft step",
        "place one hand lightly near the pocket seam",
    ],
    "jacket": [
        "smooth the lapel once",
        "button the jacket slowly",
        "hold the jacket edge near the hip",
        "adjust the cuff",
        "settle the shoulders",
        "look over the shoulder",
        "slow confident walk with controlled arm swing",
        "open then close the front softly",
        "shift weight into a tailored stance",
    ],
    "dress": [
        "smooth the waist seam lightly",
        "let the fabric fall naturally",
        "shift weight to reveal drape",
        "slow graceful walk",
        "look over the shoulder",
        "settle into a calm standing pose",
        "touch the hem gently",
        "turn with restrained elegance",
    ],
    "apparel": [
        "settle into a calm standing pose",
        "shift body weight naturally",
        "slow confident walk",
        "look over the shoulder",
        "touch the hero detail once",
        "inhale slowly and soften the shoulders",
        "hold a quiet ending stance",
    ],
}

SCENE_ACTION_PREFERENCE: dict[str, list[str]] = {
    "hero introduction": ["settle", "stance", "inhale", "shoulders"],
    "front reveal": ["shift", "weight", "silhouette", "stance"],
    "fabric macro": ["fingers", "fabric", "touch", "run"],
    "interaction": ["adjust", "button", "collar", "cuff", "waistband", "lapel", "pocket"],
    "back reveal": ["shoulder", "look over"],
    "side profile": ["turn", "profile", "weight"],
    "walking": ["walk"],
    "ending": ["stance", "pose", "settle", "hold"],
}


@dataclass
class ActionPlanner:
    """Choose unique, image-aware actions — never generic loops."""

    def run(
        self,
        storyboard: list[StoryboardScene],
        garment: GarmentAnalysis,
        analysis: ImageAnalysis,
        director: DirectorBrief | None = None,
    ) -> list[str]:
        logger.info(
            "Pipeline stage=action_planner director_style={}",
            director.garment_style if director else "n/a",
        )
        bank = list(CATEGORY_ACTIONS.get(garment.category_key, CATEGORY_ACTIONS["apparel"]))
        feature_actions = self._feature_actions(garment)
        # Fashion Director actions lead the pool when available.
        director_actions = list(director.actions) if director else []
        pool = director_actions + feature_actions + bank

        env = f"{analysis.environment} {analysis.mood} {analysis.background}".lower()
        if "cafe" in env or "coffee" in env:
            pool.insert(0, "pick up a coffee cup naturally")
        if "book" in env or "reading" in env:
            pool.insert(0, "hold a book with a quiet gaze")
        if "window" in env or "outside" in env:
            pool.insert(0, "look outside with a calm expression")
        if analysis.hand_position:
            pool.insert(0, f"keep hands {analysis.hand_position.lower()}")

        used: set[str] = set()
        actions: list[str] = []
        for scene in storyboard:
            mapped = self._director_scene_action(scene, director)
            if mapped and self._norm(mapped) not in used:
                action = mapped
            else:
                action = self._pick_for_scene(scene, pool, used)
            actions.append(action)
            used.add(self._norm(action))

        logger.info("Actions planned={}", actions)
        return actions

    def _director_scene_action(
        self,
        scene: StoryboardScene,
        director: DirectorBrief | None,
    ) -> str | None:
        if not director:
            return None
        title = scene.title.lower()
        # Map storyboard titles back to director beat keys.
        for key, action in director.scene_action_map.items():
            if key.replace("_", " ") in title or key in title:
                return action
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
            if needle in title and key in director.scene_action_map:
                return director.scene_action_map[key]
        return None

    def _pick_for_scene(
        self,
        scene: StoryboardScene,
        pool: list[str],
        used: set[str],
    ) -> str:
        title = scene.title.lower()
        prefs: list[str] = []
        for key, needles in SCENE_ACTION_PREFERENCE.items():
            if key in title or (key == "interaction" and "interaction" in title):
                prefs.extend(needles)
            if key == "walking" and "walk" in title:
                prefs.extend(needles)
            if key == "ending" and "ending" in title:
                prefs.extend(needles)

        # Prefer unused actions matching scene preferences.
        for action in pool:
            key = self._norm(action)
            if key in used or key in GENERIC_BANNED:
                continue
            if prefs and any(needle in key for needle in prefs):
                return action

        for action in pool:
            key = self._norm(action)
            if key not in used and key not in GENERIC_BANNED:
                return action

        # Last resort unique wording.
        fallback = f"hold a restrained commercial pause for {scene.title.lower()}"
        return fallback

    def _feature_actions(self, garment: GarmentAnalysis) -> list[str]:
        actions: list[str] = []
        for feature in garment.hero_features:
            fl = feature.lower()
            if "collar" in fl:
                actions.append("straighten the collar with two fingers")
            elif "cuff" in fl:
                actions.append("button the cuff deliberately")
            elif "pocket" in fl:
                actions.append("touch the chest pocket lightly" if garment.category_key == "shirt" else "brush the pocket seam lightly")
            elif "waist" in fl or "gurkha" in fl or "buckle" in fl:
                actions.append("adjust the waistband with one hand")
            elif "pleat" in fl:
                actions.append("shift weight to reveal the pleats")
            elif "lapel" in fl:
                actions.append("smooth the lapel once")
            elif "button" in fl or "placket" in fl:
                actions.append("smooth the placket once")
            elif "sleeve" in fl:
                actions.append("adjust the sleeve naturally")
            elif "fabric" in fl or "texture" in fl or "weave" in fl:
                actions.append("run fingers across the fabric")
        return self._unique(actions)

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = ActionPlanner._norm(value)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())
