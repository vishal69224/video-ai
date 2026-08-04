"""Step 4 — Cinematic fashion commercial storyboard planner."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import (
    DirectorBrief,
    GarmentAnalysis,
    ImageScene,
    StoryboardScene,
)

logger = get_logger()


@dataclass(frozen=True)
class StoryBeatTemplate:
    """One narrative beat in a premium clothing commercial."""

    key: str
    title: str
    beat: str  # beginning | middle | ending
    scene_goal: str
    camera_movement: str
    model_action: str
    product_focus_fallback: str
    transition: str
    # Optional: only include if a matching visible feature exists.
    required_feature_tokens: tuple[str, ...] = ()
    preferred_image_types: tuple[str, ...] = ()


# Category-specific visual stories — not generic checklists.
SHIRT_STORY: tuple[StoryBeatTemplate, ...] = (
    StoryBeatTemplate(
        key="hero",
        title="Opening Hero",
        beat="beginning",
        scene_goal="Introduce the shirt as the hero of a premium campaign frame",
        camera_movement="slow push in from medium-wide to medium",
        model_action="settle into a calm, tailored stance with quiet confidence",
        product_focus_fallback="full shirt silhouette and clean fit",
        transition="dissolve into intimate garment detail",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="collar",
        title="Collar Detail",
        beat="middle",
        scene_goal="Draw the eye to collar craftsmanship and neckline polish",
        camera_movement="slow dolly in to collar close-up",
        model_action="straighten the collar with two fingers",
        product_focus_fallback="collar",
        transition="cut on hand movement to the placket",
        required_feature_tokens=("collar",),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="button",
        title="Button Interaction",
        beat="middle",
        scene_goal="Show tactile quality through a restrained button/placket moment",
        camera_movement="shoulder tracking into rack focus on the placket",
        model_action="button a cuff or smooth the placket once",
        product_focus_fallback="buttons and placket",
        transition="match-cut into walking motion",
        required_feature_tokens=("button", "placket", "cuff"),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="walking",
        title="Walking Shot",
        beat="middle",
        scene_goal="Prove drape and ease through a confident walk",
        camera_movement="waist tracking alongside the model",
        model_action="slow confident runway walk with natural arm swing",
        product_focus_fallback="shirt movement through the torso and sleeves",
        transition="glide into fabric texture",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="fabric",
        title="Fabric Motion",
        beat="middle",
        scene_goal="Celebrate weave, light fall, and cloth physics",
        camera_movement="macro glide across the fabric",
        model_action="let the sleeve and body fabric shift with a soft breath",
        product_focus_fallback="fabric weave and texture",
        transition="orbit reveal toward the back",
        preferred_image_types=("macro", "closeup"),
    ),
    StoryBeatTemplate(
        key="back",
        title="Back View",
        beat="middle",
        scene_goal="Complete the silhouette story with the rear view",
        camera_movement="orbit 45° to the back",
        model_action="look over the shoulder briefly",
        product_focus_fallback="back yoke and clean rear line",
        transition="hold, then pull back for the final frame",
        preferred_image_types=("back",),
    ),
    StoryBeatTemplate(
        key="ending",
        title="Ending Pose",
        beat="ending",
        scene_goal="Leave a memorable premium brand close",
        camera_movement="slow dolly out to hero frame",
        model_action="hold a confident final pose with settled shoulders",
        product_focus_fallback="complete shirt look",
        transition="fade to brand hold",
        preferred_image_types=("front", "lifestyle"),
    ),
)

PANTS_STORY: tuple[StoryBeatTemplate, ...] = (
    StoryBeatTemplate(
        key="hero",
        title="Hero",
        beat="beginning",
        scene_goal="Open on the trousers as the campaign hero",
        camera_movement="low angle luxury reveal into full-length frame",
        model_action="settle weight into a composed standing stance",
        product_focus_fallback="full trouser silhouette and fit",
        transition="rise into waistband craft",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="waistband",
        title="Waistband",
        beat="middle",
        scene_goal="Spotlight waist construction and premium finishing",
        camera_movement="slow push in to the waistband",
        model_action="adjust the waistband with one deliberate hand",
        product_focus_fallback="waistband",
        transition="slide down toward pocket detail",
        required_feature_tokens=("waist", "gurkha", "buckle", "belt"),
        preferred_image_types=("closeup", "macro", "front"),
    ),
    StoryBeatTemplate(
        key="pocket",
        title="Pocket",
        beat="middle",
        scene_goal="Show utility and clean pocket geometry without clutter",
        camera_movement="parallax close-up on the pocket seam",
        model_action="brush the pocket seam lightly",
        product_focus_fallback="side pockets",
        transition="step into walking rhythm",
        required_feature_tokens=("pocket",),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="walking",
        title="Walking",
        beat="middle",
        scene_goal="Reveal stride, drape, and leg line in motion",
        camera_movement="waist tracking with gentle forward energy",
        model_action="take a slow confident walk with natural stride",
        product_focus_fallback="drape through the leg and hem",
        transition="cut into fabric stretch under light",
        preferred_image_types=("front", "side", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="fabric",
        title="Fabric Stretch",
        beat="middle",
        scene_goal="Show how the cloth moves, recovers, and catches light",
        camera_movement="macro glide across the thigh fabric",
        model_action="shift body weight to create a soft fabric stretch",
        product_focus_fallback="fabric stretch and texture",
        transition="turn into the back reveal",
        preferred_image_types=("macro", "closeup"),
    ),
    StoryBeatTemplate(
        key="back",
        title="Back View",
        beat="middle",
        scene_goal="Confirm rear fit and construction honesty",
        camera_movement="orbit 30° around to the back",
        model_action="look over the shoulder while holding posture",
        product_focus_fallback="back fit and pocket geometry",
        transition="resolve into the closing pose",
        preferred_image_types=("back",),
    ),
    StoryBeatTemplate(
        key="ending",
        title="Ending",
        beat="ending",
        scene_goal="End on a quiet, premium trousers campaign frame",
        camera_movement="slow dolly out",
        model_action="hold a composed final stance",
        product_focus_fallback="full trousers look",
        transition="fade to brand hold",
        preferred_image_types=("front", "lifestyle"),
    ),
)

JACKET_STORY: tuple[StoryBeatTemplate, ...] = (
    StoryBeatTemplate(
        key="hero",
        title="Opening Hero",
        beat="beginning",
        scene_goal="Present the jacket as architectural hero outerwear",
        camera_movement="hero product reveal with slow push in",
        model_action="settle the shoulders into a tailored stance",
        product_focus_fallback="jacket silhouette and structure",
        transition="move into lapel craft",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="lapel",
        title="Lapel Detail",
        beat="middle",
        scene_goal="Highlight lapel shape and premium edge finishing",
        camera_movement="slow dolly in to lapels",
        model_action="smooth the lapel once",
        product_focus_fallback="lapels",
        transition="cut to closure interaction",
        required_feature_tokens=("lapel",),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="closure",
        title="Closure Interaction",
        beat="middle",
        scene_goal="Show the jacket living through a quiet button or zip moment",
        camera_movement="shoulder tracking",
        model_action="button the jacket slowly or ease the zipper",
        product_focus_fallback="buttons or zipper",
        transition="open into a walk",
        required_feature_tokens=("button", "zip", "closure"),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="walking",
        title="Walking Shot",
        beat="middle",
        scene_goal="Let the jacket move with controlled authority",
        camera_movement="shoulder tracking walk",
        model_action="slow confident walk with controlled arm swing",
        product_focus_fallback="jacket movement and drape",
        transition="texture hold",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="fabric",
        title="Fabric Motion",
        beat="middle",
        scene_goal="Capture cloth weight and light on the shell",
        camera_movement="macro glide",
        model_action="let the jacket body shift with a soft turn",
        product_focus_fallback="fabric texture",
        transition="orbit to the back",
        preferred_image_types=("macro", "closeup"),
    ),
    StoryBeatTemplate(
        key="back",
        title="Back View",
        beat="middle",
        scene_goal="Reveal back length and shoulder architecture",
        camera_movement="orbit 45°",
        model_action="look over the shoulder",
        product_focus_fallback="back panel and shoulders",
        transition="pull wide for the ending",
        preferred_image_types=("back",),
    ),
    StoryBeatTemplate(
        key="ending",
        title="Ending Pose",
        beat="ending",
        scene_goal="Close with a luxury outerwear brand frame",
        camera_movement="slow dolly out",
        model_action="hold a tailored final pose",
        product_focus_fallback="complete jacket look",
        transition="fade to brand hold",
        preferred_image_types=("front", "lifestyle"),
    ),
)

DRESS_STORY: tuple[StoryBeatTemplate, ...] = (
    StoryBeatTemplate(
        key="hero",
        title="Opening Hero",
        beat="beginning",
        scene_goal="Introduce the dress with graceful presence",
        camera_movement="slow push in",
        model_action="settle into an elegant standing pose",
        product_focus_fallback="dress silhouette",
        transition="float into neckline detail",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="neckline",
        title="Neckline Detail",
        beat="middle",
        scene_goal="Frame the neckline as a quiet luxury cue",
        camera_movement="slow dolly in",
        model_action="soften the shoulders and lift the chin slightly",
        product_focus_fallback="neckline",
        transition="descend toward the waist",
        required_feature_tokens=("neckline", "neck"),
        preferred_image_types=("closeup", "front"),
    ),
    StoryBeatTemplate(
        key="drape",
        title="Drape Motion",
        beat="middle",
        scene_goal="Show fabric fall and fluid movement",
        camera_movement="slider movement along the body line",
        model_action="shift weight to let the fabric fall naturally",
        product_focus_fallback="drape and fabric fall",
        transition="continue into a walk",
        preferred_image_types=("front", "side", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="walking",
        title="Walking Shot",
        beat="middle",
        scene_goal="Create a runway-soft motion beat",
        camera_movement="waist tracking",
        model_action="slow graceful walk",
        product_focus_fallback="hem movement",
        transition="texture close",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="fabric",
        title="Fabric Motion",
        beat="middle",
        scene_goal="Celebrate textile character in light",
        camera_movement="macro glide",
        model_action="touch the hem gently",
        product_focus_fallback="fabric texture",
        transition="turn for the back",
        preferred_image_types=("macro", "closeup"),
    ),
    StoryBeatTemplate(
        key="back",
        title="Back View",
        beat="middle",
        scene_goal="Reveal the back line of the dress",
        camera_movement="orbit 30°",
        model_action="look over the shoulder",
        product_focus_fallback="back line",
        transition="settle into the final pose",
        preferred_image_types=("back",),
    ),
    StoryBeatTemplate(
        key="ending",
        title="Ending Pose",
        beat="ending",
        scene_goal="End on an elevated fashion-house close",
        camera_movement="slow dolly out",
        model_action="hold a serene final pose",
        product_focus_fallback="complete dress look",
        transition="fade to brand hold",
        preferred_image_types=("front", "lifestyle"),
    ),
)

APPAREL_STORY: tuple[StoryBeatTemplate, ...] = (
    StoryBeatTemplate(
        key="hero",
        title="Opening Hero",
        beat="beginning",
        scene_goal="Introduce the garment as campaign hero",
        camera_movement="hero product reveal",
        model_action="settle into a calm commercial stance",
        product_focus_fallback="silhouette",
        transition="move into detail",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="feature",
        title="Feature Detail",
        beat="middle",
        scene_goal="Highlight the strongest visible construction detail",
        camera_movement="slow dolly in",
        model_action="touch the hero construction detail once",
        product_focus_fallback="hero detail",
        transition="step into motion",
        preferred_image_types=("closeup", "macro"),
    ),
    StoryBeatTemplate(
        key="walking",
        title="Walking Shot",
        beat="middle",
        scene_goal="Show the garment living in motion",
        camera_movement="waist tracking",
        model_action="slow confident runway walk with natural arm swing",
        product_focus_fallback="natural cloth movement",
        transition="texture beat",
        preferred_image_types=("front", "lifestyle"),
    ),
    StoryBeatTemplate(
        key="fabric",
        title="Fabric Motion",
        beat="middle",
        scene_goal="Capture fabric character and light",
        camera_movement="macro glide",
        model_action="run fingers across the fabric",
        product_focus_fallback="fabric texture",
        transition="optional back reveal",
        preferred_image_types=("macro", "closeup"),
    ),
    StoryBeatTemplate(
        key="back",
        title="Back View",
        beat="middle",
        scene_goal="Complete the 360 understanding of the piece",
        camera_movement="orbit 45°",
        model_action="look over the shoulder briefly",
        product_focus_fallback="back view",
        transition="resolve to ending",
        preferred_image_types=("back",),
    ),
    StoryBeatTemplate(
        key="ending",
        title="Ending Pose",
        beat="ending",
        scene_goal="Close with a premium advertisement hold",
        camera_movement="slow dolly out",
        model_action="hold a confident final brand frame",
        product_focus_fallback="full look",
        transition="fade to brand hold",
        preferred_image_types=("front", "lifestyle"),
    ),
)

CATEGORY_STORIES: dict[str, tuple[StoryBeatTemplate, ...]] = {
    "shirt": SHIRT_STORY,
    "pants": PANTS_STORY,
    "jacket": JACKET_STORY,
    "dress": DRESS_STORY,
    "apparel": APPAREL_STORY,
}


@dataclass
class StoryboardPlanner:
    """Generate a cinematic, category-aware fashion commercial storyboard."""

    def run(
        self,
        scenes: list[ImageScene],
        garment: GarmentAnalysis,
        *,
        duration_seconds: int,
        director: DirectorBrief | None = None,
    ) -> list[StoryboardScene]:
        logger.info(
            "Pipeline stage=storyboard_planner category={} style={} mood={} duration={}s",
            garment.category_key,
            director.garment_style if director else "n/a",
            director.commercial_mood if director else "n/a",
            duration_seconds,
        )

        templates = list(
            CATEGORY_STORIES.get(garment.category_key, CATEGORY_STORIES["apparel"])
        )
        visible_features = list(
            garment.visible_features or garment.hero_features or []
        )
        feature_blob = " ".join(visible_features).lower()
        max_scenes = self._max_scenes(duration_seconds)

        selected: list[StoryBeatTemplate] = []
        for template in templates:
            if template.required_feature_tokens:
                if not any(token in feature_blob for token in template.required_feature_tokens):
                    # Keep story flow for core narrative beats even without exact token.
                    if template.key not in {"collar", "button", "waistband", "pocket", "lapel", "closure", "neckline"}:
                        pass
                    else:
                        # Swap to a visible-feature beat when possible.
                        alt = self._feature_substitute(template, visible_features)
                        if alt is None:
                            continue
                        template = alt
            # Fashion Director overrides action/camera language per beat.
            if director:
                template = self._apply_director(template, director)
            selected.append(template)

        # Always keep beginning + ending; trim middle first if over budget.
        selected = self._fit_to_budget(selected, max_scenes)

        storyboard: list[StoryboardScene] = []
        for index, template in enumerate(selected, start=1):
            focus = self._resolve_focus(template, visible_features)
            source = self._pick_source_image(scenes, template.preferred_image_types)
            purpose = template.scene_goal
            if director and director.commercial_mood:
                purpose = f"{purpose} — {director.commercial_mood} mood"
            storyboard.append(
                StoryboardScene(
                    scene_number=index,
                    beat=template.beat,
                    title=template.title,
                    purpose=purpose,
                    focus_feature=focus,
                    source_image_index=source.index if source else None,
                    camera_movement=template.camera_movement,
                    model_action=template.model_action,
                    transition=template.transition,
                )
            )

        if storyboard:
            storyboard[0].beat = "beginning"
            storyboard[-1].beat = "ending"

        logger.info(
            "Cinematic storyboard titles={} director_style={}",
            [scene.title for scene in storyboard],
            director.garment_style if director else None,
        )
        return storyboard

    def _apply_director(
        self,
        template: StoryBeatTemplate,
        director: DirectorBrief,
    ) -> StoryBeatTemplate:
        action = director.scene_action_map.get(template.key) or template.model_action
        camera = director.scene_camera_map.get(template.key) or template.camera_movement
        # If beat-specific map missed, borrow from style banks by beat role.
        if template.key not in director.scene_action_map and director.actions:
            if template.beat == "ending" and director.actions:
                action = director.actions[-1]
            elif template.beat == "beginning" and director.actions:
                action = director.scene_action_map.get("hero") or action
        if template.key not in director.scene_camera_map and director.cameras:
            if template.beat == "ending":
                camera = next(
                    (cam for cam in director.cameras if "pull back" in cam.lower() or "dolly out" in cam.lower()),
                    director.cameras[-1],
                )
        return StoryBeatTemplate(
            key=template.key,
            title=template.title,
            beat=template.beat,
            scene_goal=template.scene_goal,
            camera_movement=camera,
            model_action=action,
            product_focus_fallback=template.product_focus_fallback,
            transition=template.transition,
            required_feature_tokens=template.required_feature_tokens,
            preferred_image_types=template.preferred_image_types,
        )

    def _feature_substitute(
        self,
        template: StoryBeatTemplate,
        visible_features: list[str],
    ) -> StoryBeatTemplate | None:
        if not visible_features:
            return None
        feature = visible_features[0]
        return StoryBeatTemplate(
            key=template.key,
            title=f"{feature.title()} Detail",
            beat="middle",
            scene_goal=f"Highlight the visible {feature} as a premium craft moment",
            camera_movement=template.camera_movement,
            model_action=f"acknowledge the {feature} with a restrained hand moment",
            product_focus_fallback=feature,
            transition=template.transition,
            preferred_image_types=template.preferred_image_types or ("closeup",),
        )

    def _fit_to_budget(
        self,
        templates: list[StoryBeatTemplate],
        max_scenes: int,
    ) -> list[StoryBeatTemplate]:
        if len(templates) <= max_scenes:
            return templates
        beginning = [t for t in templates if t.beat == "beginning"]
        ending = [t for t in templates if t.beat == "ending"]
        middle = [t for t in templates if t.beat == "middle"]
        # Preserve story spine: hero, walking, fabric/detail, ending.
        priority_middle = ["walking", "fabric", "collar", "waistband", "button", "pocket", "back", "feature", "drape", "lapel", "closure", "neckline"]
        middle_sorted = sorted(
            middle,
            key=lambda item: (
                priority_middle.index(item.key) if item.key in priority_middle else 50
            ),
        )
        keep_middle_n = max(0, max_scenes - len(beginning) - len(ending))
        kept_middle = middle_sorted[:keep_middle_n]
        # Restore original narrative order among kept beats.
        kept_keys = {item.key for item in beginning + kept_middle + ending}
        return [item for item in templates if item.key in kept_keys][:max_scenes]

    def _resolve_focus(
        self,
        template: StoryBeatTemplate,
        visible_features: list[str],
    ) -> str:
        for feature in visible_features:
            fl = feature.lower()
            if any(token in fl for token in template.required_feature_tokens):
                return feature
        # Fabric beats keep texture language unless a fabric-related feature exists.
        if template.key == "fabric":
            for feature in visible_features:
                fl = feature.lower()
                if any(token in fl for token in ("fabric", "texture", "weave", "pleat", "drape")):
                    return feature
            return template.product_focus_fallback
        # Detail beats can use the strongest visible construction feature.
        if template.key in {
            "collar",
            "button",
            "waistband",
            "pocket",
            "feature",
            "lapel",
            "closure",
            "neckline",
        }:
            if visible_features:
                return visible_features[0]
        return template.product_focus_fallback

    def _pick_source_image(
        self,
        scenes: list[ImageScene],
        preferred_types: tuple[str, ...],
    ) -> ImageScene | None:
        if not scenes:
            return None
        for ref_type in preferred_types:
            for scene in scenes:
                if scene.reference_type == ref_type:
                    return scene
                if ref_type == "closeup" and scene.reference_type == "macro":
                    return scene
        # Fall back to hero-ish first image.
        for scene in scenes:
            if "hero" in scene.role.lower():
                return scene
        return scenes[0]

    @staticmethod
    def _max_scenes(seconds: int) -> int:
        if seconds <= 5:
            return 5
        if seconds <= 10:
            return 7
        if seconds <= 15:
            return 8
        if seconds <= 20:
            return 9
        return 10
