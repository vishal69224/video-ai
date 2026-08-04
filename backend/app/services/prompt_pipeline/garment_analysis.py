"""Step 2 — Product Understanding with weighted commercial importance scoring."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import GarmentAnalysis, ImageAnalysis, ImageScene

logger = get_logger()

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shirt": (
        "shirt",
        "blouse",
        "oxford",
        "polo",
        "tee",
        "t-shirt",
        "tshirt",
        "top",
        "button-down",
        "buttondown",
    ),
    "pants": (
        "pant",
        "pants",
        "trouser",
        "trousers",
        "chino",
        "chinos",
        "jogger",
        "jean",
        "jeans",
        "gurkha",
        "short",
        "shorts",
    ),
    "jacket": (
        "jacket",
        "blazer",
        "coat",
        "bomber",
        "hoodie",
        "cardigan",
        "overshirt",
    ),
    "dress": ("dress", "gown", "frock", "jumpsuit"),
    "skirt": ("skirt",),
    "shoes": ("shoe", "shoes", "sneaker", "boot", "loafer"),
    "bag": ("bag", "handbag", "tote"),
}

CATEGORY_FEATURE_HINTS: dict[str, tuple[str, ...]] = {
    "shirt": (
        "collar",
        "placket",
        "cuff",
        "cuffs",
        "chest pocket",
        "yoke",
        "rolled sleeve",
        "button-down",
    ),
    "pants": (
        "waistband",
        "pleat",
        "pleats",
        "belt loop",
        "belt loops",
        "side pocket",
        "zip fly",
        "gurkha",
        "crease",
        "inseam",
    ),
    "jacket": ("lapel", "lapels", "zipper", "lining", "shoulders"),
    "dress": ("neckline", "waist seam", "fabric fall"),
}

NOISE_FEATURES = {
    "full silhouette",
    "silhouette",
    "model",
    "person",
    "man",
    "woman",
    "fit",
    "look",
    "outfit",
    "clothing",
    "garment",
    "texture",
    "fabric texture",
    "soft matte",
}

# Weights calibrated so the example shirt (~freq5/hero/2 closeups/65%/0.95)
# scores ~9.7 and background pants (~freq3/25%/0.78) score ~3.6.
WEIGHT_FREQUENCY = 0.55         # per image occurrence
WEIGHT_AREA = 0.032             # per average % frame area (65% => 2.08)
WEIGHT_HERO = 1.5               # present in at least one hero frame
WEIGHT_CLOSEUP = 0.7            # per closeup/detail/macro image
WEIGHT_INTENDED_SUBJECT = 1.0   # vision says this is the commercial subject
WEIGHT_CONFIDENCE = 1.0         # vision confidence 0–1


@dataclass
class GarmentAnalysisStage:
    """
    Product Understanding with weighted commercial importance scoring.

    Stateless: every run starts with empty feature/product collections.
    """

    def run(self, analysis: ImageAnalysis) -> GarmentAnalysis:
        logger.info("Pipeline stage=product_understanding weighted_scoring")

        image_count = max(1, len(analysis.images))
        product_counts: Counter[str] = Counter()
        hero_hits: Counter[str] = Counter()
        closeup_hits: Counter[str] = Counter()
        area_totals: dict[str, list[float]] = defaultdict(list)

        for scene in analysis.images:
            categories = self._categories_in_scene(scene, analysis)
            for category in categories:
                product_counts[category] += 1
                area = self._area_for_category(scene, category)
                area_totals[category].append(area)
                if self._is_hero_scene(scene) and (
                    category == self._normalize_category(scene.primary_product_in_image)
                    or category == self._classify_text(scene.primary_product_in_image)
                    or len(categories) == 1
                    or area >= 40
                ):
                    hero_hits[category] += 1
                if self._is_detail_scene(scene) and (
                    category == self._normalize_category(scene.primary_product_in_image)
                    or category == self._classify_text(scene.primary_product_in_image)
                    or area >= 35
                    or self._details_match_category(scene, category)
                ):
                    closeup_hits[category] += 1

        if not product_counts:
            fallback = self._classify_text(
                f"{analysis.product_type} {analysis.garment_category}"
            )
            if fallback:
                product_counts[fallback] = image_count
                area_totals[fallback].append(60.0)

        intended = (
            self._normalize_category(analysis.intended_commercial_subject)
            or self._classify_text(analysis.intended_commercial_subject)
            or self._classify_text(f"{analysis.product_type} {analysis.garment_category}")
        )
        vision_confidence = max(0.0, min(1.0, float(analysis.confidence or 0.5)))

        scorecards: dict[str, dict[str, float | int | bool]] = {}
        product_scores: dict[str, float] = {}

        for category, frequency in product_counts.items():
            areas = area_totals.get(category) or [0.0]
            avg_area = sum(areas) / max(1, len(areas))
            hero = hero_hits.get(category, 0) > 0
            closeups = closeup_hits.get(category, 0)
            is_intended = category == intended

            # Confidence is applied per product; intended/hero products keep full
            # vision confidence, background garments use a mild discount.
            conf_factor = vision_confidence if (is_intended or hero) else vision_confidence * 0.85
            score = 0.0
            score += WEIGHT_FREQUENCY * frequency
            score += WEIGHT_AREA * avg_area
            score += WEIGHT_HERO if hero else 0.0
            score += WEIGHT_CLOSEUP * closeups
            score += WEIGHT_INTENDED_SUBJECT if is_intended else 0.0
            score += WEIGHT_CONFIDENCE * conf_factor
            score = round(score, 2)

            product_scores[category] = score
            scorecards[category] = {
                "frequency": frequency,
                "hero": hero,
                "closeups": closeups,
                "area": round(avg_area, 1),
                "intended": is_intended,
                "confidence": vision_confidence,
                "score": score,
            }

        ranked = sorted(
            product_scores.items(),
            key=lambda item: (-item[1], -product_counts.get(item[0], 0), item[0]),
        )
        primary_key = ranked[0][0] if ranked else "apparel"
        secondary_key = ranked[1][0] if len(ranked) > 1 else ""
        primary_score = float(product_scores.get(primary_key, 0.0))
        primary_card = scorecards.get(primary_key, {})

        primary_label = self._label_for(
            primary_key,
            analysis.product_type,
            analysis.garment_category,
        )
        secondary_label = self._label_for(secondary_key, "", "") if secondary_key else ""

        visible_features = self._collect_primary_features(analysis, primary_key=primary_key)
        forbidden_features = self._collect_foreign_features(analysis, primary_key=primary_key)
        confidence = self._score_confidence(primary_card, image_count=image_count)
        reasoning = self._build_reasoning(
            primary_key=primary_key,
            secondary_key=secondary_key,
            scorecards=scorecards,
            image_count=image_count,
        )

        result = GarmentAnalysis(
            primary_product=primary_label,
            secondary_product=secondary_label,
            visible_features=list(visible_features),
            product_score=primary_score,
            confidence=confidence,
            reasoning=reasoning,
            category_key=(
                primary_key
                if primary_key in CATEGORY_FEATURE_HINTS or primary_key in CATEGORY_KEYWORDS
                else "apparel"
            ),
            product_counts=dict(product_counts),
            product_scores=dict(product_scores),
            hero_product=primary_label,
            hero_features=list(visible_features),
            forbidden_features=list(forbidden_features),
        )

        logger.info(
            "Product understanding primary={!r} score={} secondary={!r} "
            "features={} confidence={:.2f}",
            result.primary_product,
            result.product_score,
            result.secondary_product,
            result.visible_features,
            result.confidence,
        )
        for category, card in sorted(
            scorecards.items(),
            key=lambda item: -float(item[1]["score"]),
        ):
            logger.info(
                "Scorecard {} frequency={} hero={} closeups={} area={}% "
                "intended={} confidence={:.2f} final_score={}",
                category,
                card["frequency"],
                card["hero"],
                card["closeups"],
                card["area"],
                card["intended"],
                card["confidence"],
                card["score"],
            )
        logger.info("Product reasoning: {}", reasoning)
        return result

    def _build_reasoning(
        self,
        *,
        primary_key: str,
        secondary_key: str,
        scorecards: dict[str, dict[str, float | int | bool]],
        image_count: int,
    ) -> str:
        primary = scorecards.get(primary_key, {})
        parts = [
            (
                f"{primary_key.title()} selected as primary with score "
                f"{primary.get('score', 0)} "
                f"(frequency {primary.get('frequency', 0)}/{image_count}, "
                f"hero={'yes' if primary.get('hero') else 'no'}, "
                f"closeups={primary.get('closeups', 0)}, "
                f"area={primary.get('area', 0)}%, "
                f"intended_subject={'yes' if primary.get('intended') else 'no'}, "
                f"vision_confidence={float(primary.get('confidence', 0)):.2f})."
            )
        ]
        if secondary_key and secondary_key in scorecards:
            secondary = scorecards[secondary_key]
            parts.append(
                f"{secondary_key.title()} is secondary background context "
                f"(score {secondary.get('score', 0)}, "
                f"frequency {secondary.get('frequency', 0)}/{image_count}, "
                f"area={secondary.get('area', 0)}%)."
            )
        parts.append(
            "Commercial focuses only on the primary product; "
            "secondary garments are not featured."
        )
        return " ".join(parts)

    def _score_confidence(
        self,
        primary_card: dict[str, float | int | bool],
        *,
        image_count: int,
    ) -> float:
        if not primary_card:
            return 0.0
        frequency = float(primary_card.get("frequency", 0))
        area = float(primary_card.get("area", 0))
        vision = float(primary_card.get("confidence", 0.5))
        hero_bonus = 0.1 if primary_card.get("hero") else 0.0
        closeup_bonus = min(0.15, 0.05 * float(primary_card.get("closeups", 0)))
        intended_bonus = 0.1 if primary_card.get("intended") else 0.0
        ratio = frequency / max(1, image_count)
        score = (
            0.35 * ratio
            + 0.25 * min(1.0, area / 70.0)
            + 0.20 * vision
            + hero_bonus
            + closeup_bonus
            + intended_bonus
        )
        return round(max(0.0, min(1.0, score)), 3)

    def _area_for_category(self, scene: ImageScene, category: str) -> float:
        for key, value in (scene.product_areas or {}).items():
            mapped = self._normalize_category(key) or self._classify_text(key)
            if mapped == category:
                try:
                    return max(0.0, min(100.0, float(value)))
                except (TypeError, ValueError):
                    return 0.0
        # Heuristic fallback when vision omits areas.
        if self._normalize_category(scene.primary_product_in_image) == category or self._classify_text(
            scene.primary_product_in_image
        ) == category:
            if self._is_detail_scene(scene):
                return 70.0
            if self._is_hero_scene(scene):
                return 60.0
            return 45.0
        if category in {
            self._normalize_category(p) or self._classify_text(p)
            for p in scene.detected_products
        }:
            return 25.0
        return 15.0 if self._details_match_category(scene, category) else 0.0

    def _is_hero_scene(self, scene: ImageScene) -> bool:
        return bool(scene.is_hero_image) or "hero" in (scene.role or "").lower()

    def _is_detail_scene(self, scene: ImageScene) -> bool:
        ref = (scene.reference_type or "").lower()
        role = (scene.role or "").lower()
        return ref in {"closeup", "macro"} or any(
            token in role for token in ("close", "detail", "macro", "fabric")
        )

    def _details_match_category(self, scene: ImageScene, category: str) -> bool:
        blob = self._norm(" ".join([scene.role, scene.notes, *scene.visible_details]))
        hints = CATEGORY_FEATURE_HINTS.get(category, ())
        return any(self._norm(hint) in blob for hint in hints)

    def _categories_in_scene(
        self,
        scene: ImageScene,
        analysis: ImageAnalysis,
    ) -> set[str]:
        found: set[str] = set()

        for product in scene.detected_products:
            key = self._normalize_category(product) or self._classify_text(product)
            if key:
                found.add(key)
        primary = self._normalize_category(scene.primary_product_in_image) or self._classify_text(
            scene.primary_product_in_image
        )
        if primary:
            found.add(primary)

        for key in scene.product_areas:
            mapped = self._normalize_category(key) or self._classify_text(key)
            if mapped:
                found.add(mapped)

        detail_blob = " ".join([scene.role, scene.notes, *scene.visible_details])
        found.update(self._classify_all(detail_blob))

        detail_norm = self._norm(detail_blob)
        for category, hints in CATEGORY_FEATURE_HINTS.items():
            if any(self._norm(hint) in detail_norm for hint in hints):
                found.add(category)

        return found

    def _collect_primary_features(
        self,
        analysis: ImageAnalysis,
        *,
        primary_key: str,
    ) -> list[str]:
        candidates: list[str] = []

        for detail in analysis.construction_details:
            if self._feature_belongs_to(detail, primary_key):
                candidates.append(detail.strip())

        for scene in analysis.images:
            scene_cats = self._categories_in_scene(scene, analysis)
            if primary_key not in scene_cats and scene_cats:
                continue
            for detail in scene.visible_details:
                if self._feature_belongs_to(detail, primary_key):
                    candidates.append(detail.strip())

        for accessory in analysis.visible_accessories:
            foreign = self._classify_text(accessory)
            if foreign and foreign != primary_key:
                continue
            if accessory.strip() and self._norm(accessory) not in NOISE_FEATURES:
                if self._feature_belongs_to(accessory, primary_key) or not foreign:
                    candidates.append(accessory.strip())

        return self._unique(candidates)[:8]

    def _collect_foreign_features(
        self,
        analysis: ImageAnalysis,
        *,
        primary_key: str,
    ) -> list[str]:
        foreign: list[str] = []
        pool = list(analysis.construction_details)
        for scene in analysis.images:
            pool.extend(scene.visible_details)
        for detail in pool:
            owner = self._feature_owner_category(detail)
            if owner and owner != primary_key:
                foreign.append(detail.strip())
        return self._unique(foreign)[:8]

    def _feature_belongs_to(self, detail: str, primary_key: str) -> bool:
        text = detail.strip()
        if not text:
            return False
        norm = self._norm(text)
        if norm in NOISE_FEATURES:
            return False
        owner = self._feature_owner_category(text)
        if owner and owner != primary_key:
            return False
        return True

    def _feature_owner_category(self, detail: str) -> str | None:
        norm = self._norm(detail)
        for category, hints in CATEGORY_FEATURE_HINTS.items():
            if any(self._norm(hint) in norm for hint in hints):
                return category
        return self._classify_text(detail)

    def _label_for(self, key: str, product_type: str, garment_category: str) -> str:
        if not key:
            return ""
        blob = f"{product_type} {garment_category}".strip()
        if blob and self._classify_text(blob) == key:
            return product_type or garment_category or key.title()
        pretty = {
            "shirt": "Shirt",
            "pants": "Pants",
            "jacket": "Jacket",
            "dress": "Dress",
            "skirt": "Skirt",
            "shoes": "Shoes",
            "bag": "Bag",
            "apparel": "Apparel",
        }
        return pretty.get(key, key.title())

    def _normalize_category(self, value: str) -> str | None:
        text = self._norm(value)
        if not text:
            return None
        aliases = {
            "t shirt": "shirt",
            "tshirt": "shirt",
            "trouser": "pants",
            "trousers": "pants",
            "chino": "pants",
            "jeans": "pants",
            "blazer": "jacket",
            "coat": "jacket",
            "accessory": "bag",
        }
        if text in aliases:
            return aliases[text]
        if text in CATEGORY_KEYWORDS:
            return text
        return None

    def _classify_text(self, text: str) -> str | None:
        matches = self._classify_all(text)
        if not matches:
            return None
        for key in ("shirt", "pants", "jacket", "dress", "skirt", "shoes", "bag"):
            if key in matches:
                return key
        return next(iter(matches))

    def _classify_all(self, text: str) -> set[str]:
        norm = f" {self._norm(text)} "
        found: set[str] = set()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                token = self._norm(keyword)
                if f" {token} " in norm or norm.strip() == token:
                    found.add(category)
                    break
        return found

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = GarmentAnalysisStage._norm(value)
            if not key or key in seen or key in NOISE_FEATURES:
                continue
            seen.add(key)
            result.append(value.strip())
        return result

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(
            "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        )
