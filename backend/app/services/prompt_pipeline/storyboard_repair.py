"""Self-healing storyboard repair for missing commercial beats."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import (
    CommercialPlan,
    PlannedShot,
    StoryboardScene,
)

logger = get_logger()

# Canonical commercial order to preserve when repairing.
CANONICAL_ORDER = (
    "hero",
    "front",
    "feature",
    "walking",
    "fabric",
    "back",
    "ending",
)


@dataclass(frozen=True)
class CanonicalBeat:
    key: str
    match_tokens: tuple[str, ...]
    title: str
    beat: str
    camera: str
    action: str
    focus_feature: str
    purpose: str


CANONICAL_BEATS: tuple[CanonicalBeat, ...] = (
    CanonicalBeat(
        key="hero",
        match_tokens=("opening hero", "hero introduction", "hero shot", "hero"),
        title="Opening Hero",
        beat="beginning",
        camera="slow push in from medium-wide to medium",
        action="settle into a calm, tailored stance with quiet confidence",
        focus_feature="silhouette",
        purpose="Introduce the garment as the hero of a premium campaign frame",
    ),
    CanonicalBeat(
        key="front",
        match_tokens=("front reveal", "front view", "collar detail", "waistband"),
        title="Front Reveal",
        beat="middle",
        camera="slow dolly in",
        action="shift body weight to reveal fit",
        focus_feature="fit",
        purpose="Reveal silhouette and fit",
    ),
    CanonicalBeat(
        key="fabric",
        match_tokens=("fabric motion", "fabric stretch", "fabric macro", "macro"),
        title="Fabric Motion",
        beat="middle",
        camera="macro glide across the fabric",
        action="let the fabric shift with a soft breath",
        focus_feature="fabric texture",
        purpose="Celebrate weave, light fall, and cloth physics",
    ),
    CanonicalBeat(
        key="walking",
        match_tokens=("walking scene", "walking shot", "walking"),
        title="Walking Shot",
        beat="middle",
        camera="Waist Tracking",
        action="Slow confident runway walk with natural arm swing",
        focus_feature="Natural cloth movement, silhouette, premium drape",
        purpose="Demonstrate garment movement during motion.",
    ),
    CanonicalBeat(
        key="feature",
        match_tokens=(
            "feature",
            "button interaction",
            "pocket",
            "collar",
            "cuff",
            "lapel",
            "interaction",
        ),
        title="Feature Detail",
        beat="middle",
        camera="shoulder tracking into rack focus",
        action="touch the hero construction detail once",
        focus_feature="hero detail",
        purpose="Highlight a visible product feature as a craft moment",
    ),
    CanonicalBeat(
        key="back",
        match_tokens=("back view", "back reveal"),
        title="Back View",
        beat="middle",
        camera="orbit 45° to the back",
        action="look over the shoulder briefly",
        focus_feature="back construction",
        purpose="Complete the silhouette story with the rear view",
    ),
    CanonicalBeat(
        key="ending",
        match_tokens=("ending pose", "ending"),
        title="Ending Pose",
        beat="ending",
        camera="slow dolly out to hero frame",
        action="hold a confident final pose with settled shoulders",
        focus_feature="full look",
        purpose="Leave a memorable premium brand close",
    ),
)


@dataclass
class StoryboardRepair:
    """Insert missing commercial beats and renumber scenes."""

    def repair(self, plan: CommercialPlan) -> CommercialPlan:
        shots = list(plan.shots)
        present = self._present_keys(shots)
        missing = [beat for beat in CANONICAL_BEATS if beat.key not in present]

        if not missing:
            plan.shots = self._renumber(shots)
            plan.storyboard = self._shots_to_storyboard(plan.shots)
            return plan

        logger.info(
            "Storyboard repair inserting missing beats={}",
            [beat.key for beat in missing],
        )

        used_cameras = {self._norm(shot.camera) for shot in shots}
        used_actions = {self._norm(shot.action) for shot in shots}
        hero_feature = (
            plan.garment.hero_features[0] if plan.garment.hero_features else ""
        )

        for beat in missing:
            camera = beat.camera
            action = beat.action
            # Avoid creating immediate duplicates when repairing.
            if self._norm(camera) in used_cameras:
                camera = f"{beat.camera} (alt)"
            if self._norm(action) in used_actions:
                action = f"{beat.action} (alt)"

            focus = beat.focus_feature
            if beat.key == "feature" and hero_feature:
                focus = hero_feature
            elif beat.key == "fabric" and hero_feature:
                focus = hero_feature
            elif beat.key == "walking":
                focus = beat.focus_feature

            shot = PlannedShot(
                scene_number=0,
                beat=beat.beat,
                title=beat.title,
                purpose=beat.purpose,
                action=action,
                camera=camera,
                focus_feature=focus,
                source_image_index=self._guess_source_index(plan, beat.key),
                transition="continue the commercial story",
            )
            shots = self._insert_in_canonical_order(shots, shot, beat.key)
            used_cameras.add(self._norm(camera))
            used_actions.add(self._norm(action))

        plan.shots = self._renumber(shots)
        plan.storyboard = self._shots_to_storyboard(plan.shots)
        logger.info(
            "Storyboard repaired titles={}",
            [shot.title for shot in plan.shots],
        )
        return plan

    def _present_keys(self, shots: list[PlannedShot]) -> set[str]:
        present: set[str] = set()
        for shot in shots:
            title = shot.title.lower()
            for beat in CANONICAL_BEATS:
                if any(token in title for token in beat.match_tokens):
                    present.add(beat.key)
                    break
                # Walking can also be detected from action/purpose.
                if beat.key == "walking" and "walk" in f"{shot.action} {shot.purpose}".lower():
                    present.add("walking")
        return present

    def _insert_in_canonical_order(
        self,
        shots: list[PlannedShot],
        new_shot: PlannedShot,
        new_key: str,
    ) -> list[PlannedShot]:
        """Insert so overall order follows Hero→Front→Fabric→Walking→Feature→Back→Ending."""
        target_rank = {key: index for index, key in enumerate(CANONICAL_ORDER)}
        new_rank = target_rank[new_key]

        insert_at = len(shots)
        for index, shot in enumerate(shots):
            shot_key = self._shot_key(shot)
            if shot_key is None:
                continue
            if target_rank[shot_key] > new_rank:
                insert_at = index
                break
        result = list(shots)
        result.insert(insert_at, new_shot)
        return result

    def _shot_key(self, shot: PlannedShot) -> str | None:
        title = shot.title.lower()
        for beat in CANONICAL_BEATS:
            if any(token in title for token in beat.match_tokens):
                return beat.key
        if "walk" in f"{shot.action} {shot.purpose}".lower():
            return "walking"
        return None

    def _guess_source_index(self, plan: CommercialPlan, key: str) -> int | None:
        type_map = {
            "hero": "front",
            "front": "front",
            "fabric": "macro",
            "walking": "front",
            "feature": "closeup",
            "back": "back",
            "ending": "front",
        }
        wanted = type_map.get(key)
        if not wanted:
            return None
        for scene in plan.scenes:
            if scene.reference_type == wanted:
                return scene.index
            if key == "fabric" and scene.reference_type == "closeup":
                return scene.index
            if key == "feature" and scene.reference_type in {"closeup", "macro"}:
                return scene.index
        return plan.scenes[0].index if plan.scenes else None

    @staticmethod
    def _renumber(shots: list[PlannedShot]) -> list[PlannedShot]:
        for index, shot in enumerate(shots, start=1):
            shot.scene_number = index
            if index == 1:
                shot.beat = "beginning"
            elif index == len(shots):
                shot.beat = "ending"
            elif shot.beat not in {"beginning", "middle", "ending", "opening"}:
                shot.beat = "middle"
            elif shot.beat == "opening":
                shot.beat = "beginning"
        if shots:
            shots[0].beat = "beginning"
            shots[-1].beat = "ending"
        return shots

    @staticmethod
    def _shots_to_storyboard(shots: list[PlannedShot]) -> list[StoryboardScene]:
        return [
            StoryboardScene(
                scene_number=shot.scene_number,
                beat=shot.beat,
                title=shot.title,
                purpose=shot.purpose,
                focus_feature=shot.focus_feature,
                source_image_index=shot.source_image_index,
                camera_movement=shot.camera,
                model_action=shot.action,
                transition=shot.transition,
            )
            for shot in shots
        ]

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(
            "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        )
