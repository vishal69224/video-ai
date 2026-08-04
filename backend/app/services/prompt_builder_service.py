"""Step 7 — Prompt Builder (Kie.ai-optimized director shot list)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.prompt_pipeline.models import CommercialPlan, PlannedShot

logger = get_logger()

DEFAULT_NEGATIVES = [
    "No dancing.",
    "No jumping.",
    "No running.",
    "No exaggerated expressions.",
    "Preserve identity.",
    "Preserve clothing.",
]

# Phrases that waste tokens and hurt Kie.ai efficiency.
BANNED_PHRASES = (
    "drawing the eye to",
    "drawing the eye",
    "minimal studio mood",
    "premium campaign",
    "premium framing",
    "premium campaign frame",
    "cloth physics",
    "hero garment",
    "luxury campaign",
    "unmistakably fashion-film",
    "celebrates craftsmanship",
    "celebrate craftsmanship",
    "to celebrate",
    "to reveal premium",
    "sophisticated mood",
    "fashion-film",
    "fabric truth",
    "quiet background presence",
    "sole hero of the film",
    "bathed in",
)

# Map freeform planner camera text → compact cinematography vocabulary.
CAMERA_NORMALIZE = (
    (r"\bslow\s+push[-\s]?in\b.*", "Slow push-in"),
    (r"\bpush[-\s]?in\b", "Slow push-in"),
    (r"\bslow\s+pull[-\s]?back\b.*", "Slow pull-back"),
    (r"\bpull[-\s]?back\b", "Slow pull-back"),
    (r"\bdolly\s+out\b", "Slow pull-back"),
    (r"\bdolly\s+in\b", "Slow push-in"),
    (r"\borbit\s*45", "Orbit 45°"),
    (r"\borbit\s*30", "Orbit 30°"),
    (r"\borbit.*\bright\b", "Orbit right"),
    (r"\borbit.*\bleft\b", "Orbit left"),
    (r"\borbit\b", "Orbit 45°"),
    (r"\bwaist[-\s]?level\s+tracking\b|\bwaist\s+tracking\b", "Waist tracking"),
    (r"\bshoulder\s+tracking\b", "Shoulder tracking"),
    (r"\bmacro\s+glide\b", "Macro glide"),
    (r"\bclose\s+macro\b|\bmacro\b", "Close macro"),
    (r"\bcrane\s+rise\b", "Crane rise"),
    (r"\beye[-\s]?level\s+follow\b|\beye\s+level\s+follow\b", "Eye-level follow"),
    (r"\bhandheld\s+follow\b|\bsoft\s+handheld\b|\bhandheld\b", "Handheld follow"),
    (r"\bside\s+tracking\b|\bside\s+profile\s+slider\b", "Side tracking"),
    (r"\bparallax\b", "Parallax move"),
    (r"\bover[-\s]?shoulder\b", "Over-shoulder reveal"),
    (r"\bnatural\s+tracking\b|\btracking\b", "Eye-level follow"),
    (r"\bbacklit\s+push\b", "Slow push-in"),
    (r"\blow\s+angle\b", "Slow push-in"),
    (r"\brack\s+focus\b", "Close macro"),
    (r"\bslider\b", "Side tracking"),
)


@dataclass
class PromptBuilderService:
    """Builds a concise Kie.ai production brief from the commercial plan."""

    def build_from_plan(self, plan: CommercialPlan) -> str:
        logger.info("Pipeline stage=prompt_builder kie_optimized shots={}", len(plan.shots))
        analysis = plan.analysis
        garment = plan.garment
        director = plan.director
        seconds = max(1, int(plan.duration_seconds or 10))
        target_min, target_max = self._word_budget(seconds)
        max_shots = self._shot_budget(seconds, len(plan.shots))

        style = (
            (director.commercial_mood if director and director.commercial_mood else "")
            or analysis.mood
            or "Luxury Editorial"
        )
        subject = self._subject(plan)
        environment = (analysis.environment or analysis.background or "clean studio").strip()
        lighting = (analysis.lighting or "soft directional light").strip()
        features = list(garment.visible_features or garment.hero_features or [])

        header = [
            f"Style: {self._compact(style)}.",
            f"Subject: {subject}.",
            f"Environment: {self._compact(environment)}.",
            f"Lighting: {self._compact(lighting)}.",
        ]

        shot_lines = self._build_shots(
            plan.shots,
            features=features,
            max_shots=max_shots,
        )
        ending = self._ending_line(plan.shots, features=features)
        negatives = " ".join(DEFAULT_NEGATIVES)

        prompt = " ".join([*header, *shot_lines, f"Ending: {ending}", negatives])
        prompt = self._strip_banned(prompt)
        prompt = self._enforce_word_limit(prompt, target_max)
        words = len(prompt.split())
        logger.info(
            "Kie prompt ready words={} target={}-{} shots={}",
            words,
            target_min,
            target_max,
            len(shot_lines),
        )
        return prompt

    def _subject(self, plan: CommercialPlan) -> str:
        analysis = plan.analysis
        garment = plan.garment
        color = analysis.primary_color
        product = (
            garment.primary_product
            or garment.hero_product
            or analysis.product_type
            or "fashion garment"
        )
        if color and color.lower() not in product.lower():
            product = f"{color} {product}".strip()
        bits = [product]
        if analysis.fit:
            bits.append(analysis.fit)
        material = ", ".join(
            b for b in [analysis.material, analysis.texture] if b
        )
        if material:
            bits.append(material)
        features = garment.visible_features or garment.hero_features
        if features:
            bits.append("features: " + ", ".join(features[:4]))
        if analysis.gender and analysis.gender.lower() not in product.lower():
            bits.append(analysis.gender)
        return self._compact("; ".join(bits))

    def _build_shots(
        self,
        shots: list[PlannedShot],
        *,
        features: list[str],
        max_shots: int,
    ) -> list[str]:
        if not shots:
            return [
                "Slow push-in as the model stands confidently, emphasizing the garment silhouette.",
                "Macro glide across the key construction detail while the model adjusts it.",
                "Eye-level follow as the model walks forward with relaxed confidence.",
                "Orbit 45° to reveal the back construction.",
                "Slow pull-back into the final hero pose.",
            ][:max_shots]

        lines: list[str] = []
        used_cameras: set[str] = set()
        used_focus: set[str] = set()
        feature_i = 0

        # Reserve the final storyboard beat for the Ending line.
        body_shots = [s for s in shots if s.beat != "ending"]
        if not body_shots:
            body_shots = list(shots[:-1] if len(shots) > 1 else shots)
        selected = self._select_shots(body_shots, max_shots)
        for index, shot in enumerate(selected):
            camera = self._normalize_camera(shot.camera, is_ending=False)
            if self._norm(camera) in used_cameras:
                camera = self._alternate_camera(index, is_ending=False)
            used_cameras.add(self._norm(camera))

            action = self._normalize_action(shot.action)
            focus, feature_i = self._normalize_focus(
                shot.focus_feature,
                features,
                feature_i,
                used_focus,
                allow_feature_fallback=shot.beat != "beginning"
                and "hero" not in (shot.title or "").lower(),
            )
            if focus:
                used_focus.add(self._norm(focus))

            line = self._format_shot(camera=camera, action=action, focus=focus)
            if line:
                lines.append(line)
        return lines

    def _select_shots(self, shots: list[PlannedShot], max_shots: int) -> list[PlannedShot]:
        if len(shots) <= max_shots:
            return list(shots)
        if max_shots <= 1:
            return [shots[0]]
        # Keep opening + evenly spaced middle beats (ending handled separately).
        opening = shots[0]
        middle = shots[1:]
        keep_middle = max_shots - 1
        if keep_middle >= len(middle):
            return list(shots[:max_shots])
        step = len(middle) / keep_middle
        picked = [middle[min(len(middle) - 1, int(i * step))] for i in range(keep_middle)]
        return [opening, *picked]

    def _format_shot(self, *, camera: str, action: str, focus: str) -> str:
        cam = camera.rstrip(".")
        act = action.rstrip(".")
        if not cam:
            cam = "Eye-level follow"
        if not act:
            act = "the model holds a calm stance"

        # Camera → Action → Feature. Emphasize silhouette only when no concrete focus.
        if focus:
            line = f"{cam} as {act}, focus on the {focus}."
        elif "stance" in act or "stands" in act or "pose" in act:
            line = f"{cam} as {act}, emphasizing the garment silhouette."
        else:
            line = f"{cam} as {act}."
        return self._capitalize(self._strip_banned(line))

    def _ending_line(self, shots: list[PlannedShot], *, features: list[str]) -> str:
        action = "the model holds a confident final pose"
        if shots:
            last = shots[-1]
            if last.action:
                action = self._normalize_action(last.action)
        return self._capitalize(f"Slow pull-back as {action}.")

    def _normalize_camera(self, value: str, *, is_ending: bool = False) -> str:
        text = self._clean(value)
        if is_ending:
            lower = text.lower()
            if any(token in lower for token in ("pull", "dolly out", "wide", "hero frame")):
                return "Slow pull-back"
            return "Slow pull-back"
        if not text:
            return "Eye-level follow"
        lower = text.lower()
        for pattern, label in CAMERA_NORMALIZE:
            if re.search(pattern, lower):
                return label
        # Keep short camera phrases; truncate long prose.
        words = text.split()
        if len(words) > 6:
            text = " ".join(words[:5])
        return self._capitalize(text)

    def _alternate_camera(self, index: int, *, is_ending: bool) -> str:
        if is_ending:
            return "Slow pull-back"
        bank = [
            "Slow push-in",
            "Macro glide",
            "Waist tracking",
            "Shoulder tracking",
            "Orbit 45°",
            "Eye-level follow",
            "Side tracking",
            "Parallax move",
            "Close macro",
            "Over-shoulder reveal",
        ]
        return bank[index % len(bank)]

    def _normalize_action(self, value: str) -> str:
        text = self._clean(value)
        if not text:
            return "the model holds a calm stance"
        # Drop purpose tails before banned-phrase cleanup.
        text = re.split(r"\s+[—–]\s+", text)[0]
        text = re.sub(
            r"\s+to\s+(reveal|celebrate|establish|show|prove|confirm|highlight|spotlight)\b.*$",
            "",
            text,
            flags=re.I,
        )
        text = re.sub(r",\s*to\s+.*$", "", text, flags=re.I)
        text = self._strip_banned(text)
        lower = text.lower()
        if lower.startswith("model "):
            text = "the " + self._uncapitalize(text)
        elif not lower.startswith(
            ("the model ", "model ", "he ", "she ", "they ", "fingers ", "hands ")
        ):
            head, _, tail = self._uncapitalize(text).partition(" ")
            text = f"the model {self._third_person(head)}{(' ' + tail) if tail else ''}"
        words = text.split()
        if len(words) > 14:
            text = " ".join(words[:14])
        return self._uncapitalize(text)

    def _normalize_focus(
        self,
        focus: str,
        features: list[str],
        feature_i: int,
        used: set[str],
        *,
        allow_feature_fallback: bool = True,
    ) -> tuple[str, int]:
        text = self._clean(focus)
        text = re.sub(
            r"\b(full|complete|hero)\s+(shirt|pants|jacket|dress|look|silhouette)\b",
            "",
            text,
            flags=re.I,
        ).strip(" ,.")
        if text and self._norm(text) not in used and not self._is_vague_focus(text):
            return " ".join(text.split()[:6]), feature_i
        if not allow_feature_fallback:
            return "", feature_i
        idx = feature_i
        while idx < len(features):
            candidate = features[idx].strip()
            idx += 1
            if candidate and self._norm(candidate) not in used and not self._is_vague_focus(candidate):
                return candidate, idx
        return "", idx

    @staticmethod
    def _is_vague_focus(value: str) -> bool:
        norm = PromptBuilderService._norm(value)
        if not norm:
            return True
        if norm in {
            "silhouette",
            "full silhouette",
            "natural cloth movement",
            "fabric weave and texture",
            "fabric stretch",
            "complete shirt look",
            "complete jacket look",
            "full look",
            "full trousers look",
        }:
            return True
        # "full trouser silhouette", "complete dress look", etc.
        if norm.endswith("silhouette") or norm.endswith(" look"):
            return True
        return False

    @staticmethod
    def _word_budget(seconds: int) -> tuple[int, int]:
        if seconds <= 8:
            return 120, 180
        if seconds <= 12:
            return 180, 260
        return 250, 350

    @staticmethod
    def _shot_budget(seconds: int, available: int) -> int:
        if seconds <= 8:
            n = 5
        elif seconds <= 12:
            n = 6
        else:
            n = 7
        return max(3, min(n, available or n, 7))

    def _enforce_word_limit(self, prompt: str, max_words: int) -> str:
        words = prompt.split()
        if len(words) <= max_words:
            return " ".join(words)
        # Never drop negatives; trim from the middle shot block if oversized.
        neg_start = None
        for index, word in enumerate(words):
            if word.startswith("No") and index + 1 < len(words):
                # Heuristic: negatives block starts at first "No dancing."
                joined = " ".join(words[index:])
                if joined.startswith("No dancing"):
                    neg_start = index
                    break
        if neg_start is None:
            return " ".join(words[:max_words])
        negatives = words[neg_start:]
        headroom = max_words - len(negatives)
        if headroom < 40:
            headroom = max(40, max_words // 2)
            negatives = negatives[: max_words - headroom]
        return " ".join(words[:headroom] + negatives)

    def _strip_banned(self, text: str) -> str:
        cleaned = text
        for phrase in BANNED_PHRASES:
            cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.I)
        # Remove em/en-dash mood tails only (keep hyphens in push-in, eye-level).
        cleaned = re.sub(r"\s*[—–]\s*(mood\b)?\s*", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
        return cleaned.strip()

    @staticmethod
    def _compact(value: str) -> str:
        text = " ".join((value or "").split())
        # Drop duplicated mood suffix like "calm confidence mood".
        text = re.sub(r"\bmood\b", "", text, flags=re.I).strip()
        return text

    @staticmethod
    def _clean(value: str) -> str:
        text = " ".join((value or "").split()).strip(" .;,:")
        for label in (
            "Scene Goal:",
            "Camera Movement:",
            "Model Action:",
            "Product Focus:",
            "Transition:",
            "Camera:",
            "Action:",
            "Focus:",
        ):
            if text.lower().startswith(label.lower()):
                text = text[len(label) :].strip(" .;,:")
        return text

    @staticmethod
    def _third_person(verb: str) -> str:
        if not verb:
            return verb
        lower = verb.lower()
        if lower.endswith(("s", "ed", "ing")):
            return verb
        if lower.endswith(("x", "z", "ch", "sh")):
            return verb + "es"
        if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
            return verb[:-1] + "ies"
        return verb + "s"

    @staticmethod
    def _uncapitalize(value: str) -> str:
        if not value:
            return value
        if len(value) > 1 and value[0].isupper() and value[1].isupper():
            return value
        return value[0].lower() + value[1:]

    @staticmethod
    def _capitalize(value: str) -> str:
        if not value:
            return value
        return value[0].upper() + value[1:]

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(
            "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        )

    async def build_prompt(self, analysis: dict, project_name: str | None = None) -> str:
        raise NotImplementedError(
            "Use FashionPromptPipeline / build_from_plan for commercial prompts"
        )

    async def build_negative_prompt(self, analysis: dict | None = None) -> str:
        return " ".join(DEFAULT_NEGATIVES)


def get_prompt_builder_service() -> PromptBuilderService:
    """FastAPI dependency factory for PromptBuilderService."""
    return PromptBuilderService()
