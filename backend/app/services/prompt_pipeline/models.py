"""Shared data models for the fashion commercial prompt pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageScene:
    index: int
    reference_type: str  # front / back / side / closeup / lifestyle / macro
    role: str  # Hero Front, Fabric Closeup, etc.
    visible_details: list[str] = field(default_factory=list)
    notes: str = ""
    # Products visibly present in THIS image only (fresh per request).
    detected_products: list[str] = field(default_factory=list)
    primary_product_in_image: str = ""
    # Approximate % of frame occupied by each detected product, e.g. {"shirt": 65, "pants": 25}
    product_areas: dict[str, float] = field(default_factory=dict)
    is_hero_image: bool = False


@dataclass
class ImageAnalysis:
    product_type: str = ""
    garment_category: str = ""
    gender: str = ""
    primary_color: str = ""
    secondary_colors: list[str] = field(default_factory=list)
    material: str = ""
    texture: str = ""
    fit: str = ""
    construction_details: list[str] = field(default_factory=list)
    visible_accessories: list[str] = field(default_factory=list)
    environment: str = ""
    lighting: str = ""
    background: str = ""
    mood: str = ""
    body_pose: str = ""
    face_direction: str = ""
    hand_position: str = ""
    confidence: float = 0.5
    # Vision's guess for the intended commercial hero product category.
    intended_commercial_subject: str = ""
    images: list[ImageScene] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_type": self.product_type,
            "garment_category": self.garment_category,
            "gender": self.gender,
            "primary_color": self.primary_color,
            "secondary_colors": list(self.secondary_colors),
            "material": self.material,
            "texture": self.texture,
            "fit": self.fit,
            "construction_details": list(self.construction_details),
            "visible_accessories": list(self.visible_accessories),
            "environment": self.environment,
            "lighting": self.lighting,
            "background": self.background,
            "mood": self.mood,
            "body_pose": self.body_pose,
            "face_direction": self.face_direction,
            "hand_position": self.hand_position,
            "confidence": self.confidence,
            "intended_commercial_subject": self.intended_commercial_subject,
            "images": [
                {
                    "index": img.index,
                    "reference_type": img.reference_type,
                    "role": img.role,
                    "visible_details": list(img.visible_details),
                    "notes": img.notes,
                    "detected_products": list(img.detected_products),
                    "primary_product_in_image": img.primary_product_in_image,
                    "product_areas": dict(img.product_areas),
                    "is_hero_image": img.is_hero_image,
                }
                for img in self.images
            ],
        }


@dataclass
class GarmentAnalysis:
    """Product understanding result for the current request only."""

    primary_product: str = ""
    secondary_product: str = ""
    visible_features: list[str] = field(default_factory=list)
    product_score: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    category_key: str = "apparel"  # shirt | pants | jacket | dress | apparel
    product_counts: dict[str, int] = field(default_factory=dict)
    product_scores: dict[str, float] = field(default_factory=dict)
    # Compatibility aliases used by planners/builders.
    hero_product: str = ""
    hero_features: list[str] = field(default_factory=list)
    forbidden_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_product": self.primary_product,
            "secondary_product": self.secondary_product,
            "visible_features": list(self.visible_features),
            "product_score": self.product_score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "category_key": self.category_key,
            "product_counts": dict(self.product_counts),
            "product_scores": dict(self.product_scores),
            "hero_product": self.hero_product,
            "hero_features": list(self.hero_features),
            "forbidden_features": list(self.forbidden_features),
        }


@dataclass
class DirectorBrief:
    """Fashion Director Engine briefing for planners."""

    garment_style: str = "apparel"  # oxford_shirt | linen_shirt | polo | blazer | ...
    personality: list[str] = field(default_factory=list)
    commercial_mood: str = "Luxury Editorial"
    pacing: str = "measured"  # measured | relaxed | brisk | architectural
    actions: list[str] = field(default_factory=list)
    cameras: list[str] = field(default_factory=list)
    scene_action_map: dict[str, str] = field(default_factory=dict)
    scene_camera_map: dict[str, str] = field(default_factory=dict)
    mood_notes: str = ""
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "garment_style": self.garment_style,
            "personality": list(self.personality),
            "commercial_mood": self.commercial_mood,
            "pacing": self.pacing,
            "actions": list(self.actions),
            "cameras": list(self.cameras),
            "scene_action_map": dict(self.scene_action_map),
            "scene_camera_map": dict(self.scene_camera_map),
            "mood_notes": self.mood_notes,
            "reasoning": self.reasoning,
        }


@dataclass
class StoryboardScene:
    scene_number: int
    beat: str  # beginning | middle | ending
    title: str
    purpose: str  # scene goal
    focus_feature: str = ""  # product focus
    source_image_index: int | None = None
    camera_movement: str = ""
    model_action: str = ""
    transition: str = ""

    @property
    def scene_goal(self) -> str:
        return self.purpose

    @property
    def product_focus(self) -> str:
        return self.focus_feature


@dataclass
class PlannedShot:
    scene_number: int
    beat: str
    title: str
    purpose: str
    action: str
    camera: str
    focus_feature: str = ""
    source_image_index: int | None = None
    transition: str = ""


@dataclass
class CommercialPlan:
    analysis: ImageAnalysis
    garment: GarmentAnalysis
    scenes: list[ImageScene]
    storyboard: list[StoryboardScene]
    shots: list[PlannedShot]
    duration_seconds: int = 10
    resolution: str = "720p"
    model: str | None = None
    director: DirectorBrief | None = None
