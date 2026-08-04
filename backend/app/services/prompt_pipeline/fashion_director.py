"""Fashion Director Engine — garment personality, mood, actions, camera language."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import (
    DirectorBrief,
    GarmentAnalysis,
    ImageAnalysis,
)

logger = get_logger()


@dataclass(frozen=True)
class GarmentStyleProfile:
    """Director language unique to a garment personality."""

    style_key: str
    match_tokens: tuple[str, ...]
    personality: tuple[str, ...]
    commercial_mood: str
    pacing: str
    mood_notes: str
    actions: tuple[str, ...]
    cameras: tuple[str, ...]
    # Beat-key → preferred action / camera for storyboard injection.
    scene_actions: dict[str, str] = field(default_factory=dict)
    scene_cameras: dict[str, str] = field(default_factory=dict)
    # Prefer this mood when analysis environment matches these tokens.
    environment_mood_overrides: tuple[tuple[str, str], ...] = ()


# Style profiles ordered from most specific → most general within a category.
STYLE_PROFILES: tuple[GarmentStyleProfile, ...] = (
    GarmentStyleProfile(
        style_key="oxford_shirt",
        match_tokens=("oxford", "button-down", "buttondown", "dress shirt", "formal shirt"),
        personality=("Elegant", "Professional", "Confident", "Smart Casual"),
        commercial_mood="Business Campaign",
        pacing="measured",
        mood_notes="Clean power dressing with quiet confidence and tailored precision.",
        actions=(
            "adjust the cuff with deliberate calm",
            "button the collar cleanly",
            "check the watch once",
            "walk toward camera with restrained stride",
            "pause in a composed stance",
            "look sideways with quiet authority",
            "smooth the placket once",
            "settle the shoulders into a tailored line",
        ),
        cameras=(
            "collar macro",
            "cuff macro",
            "shoulder tracking",
            "eye level follow",
            "slow push in from mid shot",
            "placket rack focus",
            "slow pull back to hero frame",
        ),
        scene_actions={
            "hero": "settle into a composed tailored stance with quiet confidence",
            "collar": "button the collar cleanly",
            "button": "adjust the cuff with deliberate calm",
            "walking": "walk toward camera with restrained stride",
            "fabric": "let the oxford cloth shift with a soft breath",
            "back": "look sideways with quiet authority",
            "ending": "pause in a composed stance, then hold the final brand frame",
        },
        scene_cameras={
            "hero": "slow push in from mid shot at eye level",
            "collar": "collar macro",
            "button": "cuff macro",
            "walking": "eye level follow",
            "fabric": "shoulder tracking into fabric texture",
            "back": "shoulder tracking arc to the rear",
            "ending": "slow pull back to hero frame",
        },
        environment_mood_overrides=(
            ("office", "Business Campaign"),
            ("studio", "Minimal Studio"),
            ("loft", "Modern Loft"),
            ("editorial", "Luxury Editorial"),
        ),
    ),
    GarmentStyleProfile(
        style_key="linen_shirt",
        match_tokens=("linen", "resort shirt", "camp collar", "cuban collar"),
        personality=("Relaxed", "Summer", "Resort", "Breathable", "Natural"),
        commercial_mood="Summer Lifestyle",
        pacing="relaxed",
        mood_notes="Sunlit ease, breathable cloth, and unforced resort elegance.",
        actions=(
            "touch the linen fabric lightly",
            "walk through a soft breeze",
            "relax the shoulders",
            "hold a coffee with easy calm",
            "breathe naturally and let the cloth move",
            "look into the distance",
            "roll a sleeve loosely",
            "shift weight into a soft standing ease",
        ),
        cameras=(
            "fabric macro",
            "soft handheld",
            "natural tracking",
            "backlit push in",
            "gentle slider through golden light",
            "slow dolly out into open air",
        ),
        scene_actions={
            "hero": "relax the shoulders and breathe into an easy standing presence",
            "collar": "touch the open collar with a light natural hand",
            "button": "roll a sleeve loosely",
            "walking": "walk through a soft breeze with unhurried ease",
            "fabric": "touch the linen fabric lightly and let it breathe",
            "back": "look into the distance over the shoulder",
            "ending": "hold coffee or empty hands in calm stillness for the final frame",
        },
        scene_cameras={
            "hero": "backlit push in",
            "collar": "fabric macro on the collar",
            "button": "soft handheld on the sleeve",
            "walking": "natural tracking",
            "fabric": "fabric macro",
            "back": "soft handheld orbit to the back",
            "ending": "slow dolly out into open air",
        },
        environment_mood_overrides=(
            ("beach", "Resort"),
            ("resort", "Resort"),
            ("cafe", "Weekend Casual"),
            ("travel", "Travel"),
            ("terrace", "Summer Lifestyle"),
            ("outdoor", "Summer Lifestyle"),
        ),
    ),
    GarmentStyleProfile(
        style_key="polo_shirt",
        match_tokens=("polo", "piqué", "pique"),
        personality=("Sport Luxury", "Weekend", "Modern Casual"),
        commercial_mood="Weekend Casual",
        pacing="brisk",
        mood_notes="Modern leisure polish — athletic ease without looking sporty-generic.",
        actions=(
            "adjust the polo placket lightly",
            "settle the collar points",
            "walk with easy weekend energy",
            "pause with one hand near the hem",
            "look off-camera with modern calm",
            "shift weight into a relaxed athletic stance",
            "smooth the sleeve band once",
        ),
        cameras=(
            "collar close tracking",
            "waist-level lifestyle follow",
            "clean push in on the placket",
            "side profile slider",
            "slow pull back weekend hero",
        ),
        scene_actions={
            "hero": "settle into a modern casual stance with soft athletic ease",
            "collar": "settle the collar points",
            "button": "adjust the polo placket lightly",
            "walking": "walk with easy weekend energy",
            "fabric": "smooth the sleeve band once",
            "back": "look off-camera with modern calm",
            "ending": "pause in a clean weekend hero stance",
        },
        scene_cameras={
            "hero": "clean push in on the placket",
            "collar": "collar close tracking",
            "button": "collar close tracking",
            "walking": "waist-level lifestyle follow",
            "fabric": "side profile slider",
            "back": "side profile slider to the rear",
            "ending": "slow pull back weekend hero",
        },
        environment_mood_overrides=(
            ("club", "Weekend Casual"),
            ("court", "Weekend Casual"),
            ("loft", "Modern Loft"),
            ("travel", "Travel"),
        ),
    ),
    GarmentStyleProfile(
        style_key="blazer",
        match_tokens=("blazer", "suit jacket", "sport coat", "sports coat"),
        personality=("Executive", "Premium", "Luxury", "Power Dressing"),
        commercial_mood="Business Campaign",
        pacing="architectural",
        mood_notes="Executive architecture — sharp lines, controlled power, premium stillness.",
        actions=(
            "smooth the lapel with one precise motion",
            "button the blazer slowly",
            "adjust the cuff beneath the sleeve",
            "walk with controlled executive stride",
            "settle the shoulders into structured power",
            "look over the shoulder with authority",
            "hold a still final power pose",
        ),
        cameras=(
            "lapel macro",
            "structured shoulder tracking",
            "low angle power reveal",
            "slow architectural push in",
            "orbit to the back with precision",
            "slow pull back executive hero",
        ),
        scene_actions={
            "hero": "settle the shoulders into structured power",
            "lapel": "smooth the lapel with one precise motion",
            "closure": "button the blazer slowly",
            "walking": "walk with controlled executive stride",
            "fabric": "adjust the cuff beneath the sleeve",
            "back": "look over the shoulder with authority",
            "ending": "hold a still final power pose",
        },
        scene_cameras={
            "hero": "low angle power reveal",
            "lapel": "lapel macro",
            "closure": "slow architectural push in",
            "walking": "structured shoulder tracking",
            "fabric": "lapel macro into fabric texture",
            "back": "orbit to the back with precision",
            "ending": "slow pull back executive hero",
        },
        environment_mood_overrides=(
            ("boardroom", "Business Campaign"),
            ("office", "Business Campaign"),
            ("studio", "Minimal Studio"),
            ("editorial", "Luxury Editorial"),
            ("loft", "Modern Loft"),
        ),
    ),
    GarmentStyleProfile(
        style_key="bomber_jacket",
        match_tokens=("bomber", "flight jacket", "ma-1", "ma1"),
        personality=("Urban", "Street Luxury", "Confident"),
        commercial_mood="Modern Loft",
        pacing="brisk",
        mood_notes="Urban confidence with street-luxury edge and kinetic framing.",
        actions=(
            "zip the bomber halfway with intention",
            "settle the ribbed cuff",
            "walk with urban confidence",
            "adjust the collar of the bomber",
            "turn with sharp street energy",
            "hold a confident final urban pose",
            "let the jacket shell shift with a short step",
        ),
        cameras=(
            "zipper tracking macro",
            "urban shoulder follow",
            "handheld-confident push in",
            "street-level tracking",
            "orbit with city energy",
            "slow pull back loft hero",
        ),
        scene_actions={
            "hero": "settle into an urban confident stance",
            "lapel": "adjust the collar of the bomber",
            "closure": "zip the bomber halfway with intention",
            "walking": "walk with urban confidence",
            "fabric": "let the jacket shell shift with a short step",
            "back": "turn with sharp street energy",
            "ending": "hold a confident final urban pose",
        },
        scene_cameras={
            "hero": "handheld-confident push in",
            "lapel": "zipper tracking macro",
            "closure": "zipper tracking macro",
            "walking": "street-level tracking",
            "fabric": "urban shoulder follow",
            "back": "orbit with city energy",
            "ending": "slow pull back loft hero",
        },
        environment_mood_overrides=(
            ("street", "Modern Loft"),
            ("city", "Modern Loft"),
            ("loft", "Modern Loft"),
            ("night", "Modern Loft"),
            ("editorial", "Luxury Editorial"),
        ),
    ),
    GarmentStyleProfile(
        style_key="gurkha_pants",
        match_tokens=("gurkha", "gurkha pant", "gurkha trouser"),
        personality=("Tailored", "Craftsmanship", "Structure", "Premium Fit"),
        commercial_mood="Luxury Editorial",
        pacing="measured",
        mood_notes="Craft-led trousers storytelling — waist architecture, structure, premium fit.",
        actions=(
            "adjust the Gurkha buckle with deliberate craft focus",
            "smooth the waistband once",
            "brush the pleat line lightly",
            "take a structured tailored walk",
            "shift weight to reveal premium drape",
            "look over the shoulder to confirm the back fit",
            "hold a composed craftsmanship ending stance",
        ),
        cameras=(
            "waistband craft macro",
            "pleat tracking close-up",
            "low angle tailored reveal",
            "waist tracking with structure",
            "thigh fabric glide",
            "slow pull back editorial hero",
        ),
        scene_actions={
            "hero": "settle weight into a composed tailored stance",
            "waistband": "adjust the Gurkha buckle with deliberate craft focus",
            "pocket": "brush the pocket seam lightly",
            "walking": "take a structured tailored walk",
            "fabric": "shift weight to reveal premium drape and pleat structure",
            "back": "look over the shoulder to confirm the back fit",
            "ending": "hold a composed craftsmanship ending stance",
        },
        scene_cameras={
            "hero": "low angle tailored reveal",
            "waistband": "waistband craft macro",
            "pocket": "pleat tracking close-up",
            "walking": "waist tracking with structure",
            "fabric": "thigh fabric glide",
            "back": "orbit 30° with editorial precision",
            "ending": "slow pull back editorial hero",
        },
        environment_mood_overrides=(
            ("studio", "Minimal Studio"),
            ("editorial", "Luxury Editorial"),
            ("loft", "Modern Loft"),
            ("travel", "Travel"),
        ),
    ),
    # Broader category fallbacks when no subtype matches.
    GarmentStyleProfile(
        style_key="shirt",
        match_tokens=("shirt", "blouse", "top"),
        personality=("Elegant", "Confident", "Smart Casual"),
        commercial_mood="Luxury Editorial",
        pacing="measured",
        mood_notes="Elevated shirt commercial with clean silhouette focus.",
        actions=(
            "straighten the collar with two fingers",
            "button the cuff deliberately",
            "slow confident walk with natural arm swing",
            "smooth the placket once",
            "look over the shoulder briefly",
            "hold a confident final pose",
        ),
        cameras=(
            "collar macro",
            "shoulder tracking",
            "eye level follow",
            "macro glide across the fabric",
            "slow pull back to hero frame",
        ),
        scene_actions={
            "hero": "settle into a calm, tailored stance with quiet confidence",
            "collar": "straighten the collar with two fingers",
            "button": "button the cuff deliberately",
            "walking": "slow confident walk with natural arm swing",
            "fabric": "let the sleeve and body fabric shift with a soft breath",
            "back": "look over the shoulder briefly",
            "ending": "hold a confident final pose with settled shoulders",
        },
        scene_cameras={
            "hero": "slow push in from medium-wide to medium",
            "collar": "collar macro",
            "button": "shoulder tracking into rack focus on the placket",
            "walking": "eye level follow",
            "fabric": "macro glide across the fabric",
            "back": "orbit 45° to the back",
            "ending": "slow pull back to hero frame",
        },
    ),
    GarmentStyleProfile(
        style_key="pants",
        match_tokens=("pant", "trouser", "chino", "jean"),
        personality=("Tailored", "Premium Fit", "Confident"),
        commercial_mood="Luxury Editorial",
        pacing="measured",
        mood_notes="Trouser-led commercial focused on fit, drape, and craft.",
        actions=(
            "adjust the waistband with one hand",
            "take a slow confident walk",
            "shift body weight to show drape",
            "brush the pocket seam lightly",
            "look over the shoulder to reveal the back",
            "hold a composed final stance",
        ),
        cameras=(
            "waistband craft macro",
            "waist tracking with gentle forward energy",
            "low angle luxury reveal into full-length frame",
            "thigh fabric glide",
            "slow pull back editorial hero",
        ),
        scene_actions={
            "hero": "settle weight into a composed standing stance",
            "waistband": "adjust the waistband with one hand",
            "pocket": "brush the pocket seam lightly",
            "walking": "take a slow confident walk with natural stride",
            "fabric": "shift body weight to create a soft fabric stretch",
            "back": "look over the shoulder while holding posture",
            "ending": "hold a composed final stance",
        },
        scene_cameras={
            "hero": "low angle luxury reveal into full-length frame",
            "waistband": "waistband craft macro",
            "pocket": "parallax close-up on the pocket seam",
            "walking": "waist tracking with gentle forward energy",
            "fabric": "thigh fabric glide",
            "back": "orbit 30° around to the back",
            "ending": "slow pull back editorial hero",
        },
    ),
    GarmentStyleProfile(
        style_key="jacket",
        match_tokens=("jacket", "coat", "outerwear", "hoodie", "cardigan"),
        personality=("Premium", "Confident", "Structured"),
        commercial_mood="Luxury Editorial",
        pacing="architectural",
        mood_notes="Outerwear commercial with structure, motion, and silhouette authority.",
        actions=(
            "smooth the lapel once",
            "button the jacket slowly or ease the zipper",
            "slow confident walk with controlled arm swing",
            "settle the shoulders",
            "look over the shoulder",
            "hold a tailored final pose",
        ),
        cameras=(
            "hero product reveal with slow push in",
            "structured shoulder tracking",
            "macro glide",
            "orbit 45°",
            "slow pull back to hero frame",
        ),
        scene_actions={
            "hero": "settle the shoulders into a tailored stance",
            "lapel": "smooth the lapel once",
            "closure": "button the jacket slowly or ease the zipper",
            "walking": "slow confident walk with controlled arm swing",
            "fabric": "let the jacket body shift with a soft turn",
            "back": "look over the shoulder",
            "ending": "hold a tailored final pose",
        },
        scene_cameras={
            "hero": "hero product reveal with slow push in",
            "lapel": "slow dolly in to lapels",
            "closure": "structured shoulder tracking",
            "walking": "structured shoulder tracking walk",
            "fabric": "macro glide",
            "back": "orbit 45°",
            "ending": "slow pull back to hero frame",
        },
    ),
    GarmentStyleProfile(
        style_key="dress",
        match_tokens=("dress", "gown", "jumpsuit"),
        personality=("Elegant", "Fluid", "Luxury"),
        commercial_mood="Luxury Editorial",
        pacing="relaxed",
        mood_notes="Graceful dress storytelling with fabric fall and elevated calm.",
        actions=(
            "settle into an elegant standing pose",
            "let the fabric fall naturally",
            "slow graceful walk",
            "touch the hem gently",
            "look over the shoulder",
            "hold a serene final pose",
        ),
        cameras=(
            "slow push in",
            "slider movement along the body line",
            "macro glide",
            "orbit 30°",
            "slow dolly out",
        ),
        scene_actions={
            "hero": "settle into an elegant standing pose",
            "neckline": "soften the shoulders and lift the chin slightly",
            "drape": "shift weight to let the fabric fall naturally",
            "walking": "slow graceful walk",
            "fabric": "touch the hem gently",
            "back": "look over the shoulder",
            "ending": "hold a serene final pose",
        },
        scene_cameras={
            "hero": "slow push in",
            "neckline": "slow dolly in",
            "drape": "slider movement along the body line",
            "walking": "waist tracking",
            "fabric": "macro glide",
            "back": "orbit 30°",
            "ending": "slow dolly out",
        },
    ),
    GarmentStyleProfile(
        style_key="apparel",
        match_tokens=(),
        personality=("Premium", "Confident", "Modern"),
        commercial_mood="Luxury Editorial",
        pacing="measured",
        mood_notes="Premium apparel commercial with clean campaign pacing.",
        actions=(
            "settle into a calm commercial stance",
            "slow confident walk",
            "touch the hero detail once",
            "look over the shoulder",
            "hold a quiet ending stance",
        ),
        cameras=(
            "hero product reveal",
            "slow push in",
            "waist tracking",
            "macro glide",
            "slow dolly out",
        ),
        scene_actions={
            "hero": "settle into a calm commercial stance",
            "feature": "touch the hero detail once",
            "walking": "slow confident walk",
            "fabric": "run fingers across the fabric",
            "back": "look over the shoulder briefly",
            "ending": "hold a quiet ending stance",
        },
        scene_cameras={
            "hero": "hero product reveal",
            "feature": "slow dolly in",
            "walking": "waist tracking",
            "fabric": "macro glide",
            "back": "orbit 45°",
            "ending": "slow dolly out",
        },
    ),
)


@dataclass
class FashionDirectorEngine:
    """
    Determines garment personality, commercial mood, and director language
    for Storyboard / Action / Camera planners.
    """

    def run(
        self,
        garment: GarmentAnalysis,
        analysis: ImageAnalysis,
    ) -> DirectorBrief:
        logger.info("Pipeline stage=fashion_director")
        profile = self._select_profile(garment, analysis)
        mood = self._resolve_mood(profile, analysis)
        brief = DirectorBrief(
            garment_style=profile.style_key,
            personality=list(profile.personality),
            commercial_mood=mood,
            pacing=profile.pacing,
            actions=list(profile.actions),
            cameras=list(profile.cameras),
            scene_action_map=dict(profile.scene_actions),
            scene_camera_map=dict(profile.scene_cameras),
            mood_notes=profile.mood_notes,
            reasoning=self._reasoning(profile, mood, garment),
        )
        logger.info(
            "Director brief style={} mood={} personality={} pacing={}",
            brief.garment_style,
            brief.commercial_mood,
            brief.personality,
            brief.pacing,
        )
        logger.info("Director reasoning: {}", brief.reasoning)
        return brief

    def _select_profile(
        self,
        garment: GarmentAnalysis,
        analysis: ImageAnalysis,
    ) -> GarmentStyleProfile:
        blob = self._norm(
            " ".join(
                [
                    garment.primary_product,
                    garment.hero_product,
                    garment.category_key,
                    analysis.product_type,
                    analysis.garment_category,
                    analysis.material,
                    analysis.texture,
                    analysis.fit,
                    " ".join(garment.visible_features or []),
                    " ".join(analysis.construction_details or []),
                ]
            )
        )

        # Specific subtype profiles first (non-empty match tokens, excluding
        # broad category keys that appear later in STYLE_PROFILES).
        for profile in STYLE_PROFILES:
            if not profile.match_tokens:
                continue
            if profile.style_key in {"shirt", "pants", "jacket", "dress"}:
                continue
            if any(self._norm(token) in blob for token in profile.match_tokens):
                return profile

        # Category fallbacks.
        category = (garment.category_key or "apparel").lower()
        for profile in STYLE_PROFILES:
            if profile.style_key == category:
                return profile

        return STYLE_PROFILES[-1]  # apparel

    def _resolve_mood(
        self,
        profile: GarmentStyleProfile,
        analysis: ImageAnalysis,
    ) -> str:
        env_blob = self._norm(
            " ".join(
                [
                    analysis.environment,
                    analysis.background,
                    analysis.mood,
                    analysis.lighting,
                ]
            )
        )
        for token, mood in profile.environment_mood_overrides:
            if self._norm(token) in env_blob:
                return mood

        # Global environment cues when profile has no override hit.
        global_cues = (
            ("beach", "Resort"),
            ("resort", "Resort"),
            ("travel", "Travel"),
            ("airport", "Travel"),
            ("cafe", "Weekend Casual"),
            ("weekend", "Weekend Casual"),
            ("office", "Business Campaign"),
            ("boardroom", "Business Campaign"),
            ("studio", "Minimal Studio"),
            ("loft", "Modern Loft"),
            ("summer", "Summer Lifestyle"),
            ("editorial", "Luxury Editorial"),
        )
        for token, mood in global_cues:
            if token in env_blob:
                return mood
        return profile.commercial_mood

    def _reasoning(
        self,
        profile: GarmentStyleProfile,
        mood: str,
        garment: GarmentAnalysis,
    ) -> str:
        product = garment.primary_product or garment.hero_product or profile.style_key
        traits = ", ".join(profile.personality)
        return (
            f"{product} directed as {profile.style_key.replace('_', ' ')} with "
            f"personality [{traits}], commercial mood '{mood}', and "
            f"{profile.pacing} pacing. Actions and camera language are "
            f"style-specific, not generic category defaults."
        )

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(
            "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        )
