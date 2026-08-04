"""Orchestrate prompt generation, Kie.ai submission, and status polling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ImagePromptGenerationError,
    KieGenerationError,
    VideoGenerationError,
)
from app.core.logger import get_logger
from app.schemas.video_schema import (
    VideoGenerationResponse,
    VideoStatusResponse,
)
from app.services.generation_validation_service import (
    GenerationValidationService,
    get_generation_validation_service,
)
from app.services.image_prompt_service import ImagePromptService, get_image_prompt_service
from app.services.kie_client import KieClient, get_kie_client
from app.services.video_library_service import VideoLibraryService, get_video_library_service
from app.services.video_store import VideoTaskRecord, video_store

logger = get_logger()

STAGE_PROGRESS = {
    "queued": 5,
    "analyzing_images": 15,
    "generating_prompt": 30,
    "submitting_to_ai": 45,
    "rendering": 70,
    "finalizing": 90,
    "completed": 100,
    "failed": 100,
}


@dataclass
class VideoGenerationService:
    """Coordinates Gemma prompt generation and Kie.ai video submission."""

    settings: Settings
    prompt_service: ImagePromptService
    kie_client: KieClient
    library_service: VideoLibraryService
    validation_service: GenerationValidationService

    async def generate(
        self,
        image_paths: list[str],
        project_name: str | None = None,
        *,
        model_id: str | None = None,
        api_model: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
        estimated_credits: float | None = None,
    ) -> VideoGenerationResponse:
        """
        Validate images → generate prompt → (dev stop | validate → Kie.ai).
        """
        mode_label = "Development Mode" if self.settings.DEVELOPMENT_MODE else "Production Mode"
        logger.info(
            "Generation Mode: {} | image_count={} model_id={} resolution={} duration={} estimated_credits={}",
            mode_label,
            len(image_paths),
            model_id,
            resolution,
            duration_seconds,
            estimated_credits,
        )

        if self.settings.DEVELOPMENT_MODE:
            return await self._generate_development(
                image_paths,
                model_id=model_id,
                api_model=api_model,
                resolution=resolution,
                duration_seconds=duration_seconds,
                estimated_credits=estimated_credits,
            )

        return await self._generate_production(
            image_paths,
            project_name=project_name,
            model_id=model_id,
            api_model=api_model,
            resolution=resolution,
            duration_seconds=duration_seconds,
            estimated_credits=estimated_credits,
        )

    async def preview_prompt(
        self,
        image_paths: list[str],
        *,
        api_model: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
        estimated_credits: float | None = None,
    ) -> dict[str, Any]:
        """
        Credit-safe preview: Gemma prompt + validation only. Never calls Kie.ai.
        """
        logger.info("Generation Mode: Development Mode (prompt preview) — Kie.ai will not be called")
        validated_paths = self._validate_images(image_paths)

        model = self.validation_service.resolve_model(api_model)
        resolved_resolution = self.validation_service.resolve_resolution(resolution)
        seconds = self.validation_service.resolve_duration_seconds(duration_seconds)
        prompt = await self.prompt_service.generate_prompt(
            validated_paths,
            model=model,
            duration_seconds=seconds,
            resolution=resolved_resolution,
        )
        credits = self.validation_service.estimate_credits(
            model=model,
            resolution=resolved_resolution,
            duration_seconds=seconds,
            client_estimate=estimated_credits,
            model_ui_id=None,
        )

        checks = self.validation_service.validate_prompt_and_settings(
            prompt=prompt,
            model=model,
            resolution=resolved_resolution,
            duration_seconds=seconds,
            local_image_paths=validated_paths,
            require_public_urls=False,
        )
        valid = all(item.ok for item in checks)

        return {
            "success": valid,
            "development_mode": True,
            "generated_prompt": prompt,
            "estimated_model": model,
            "estimated_resolution": resolved_resolution,
            "estimated_duration": self._format_duration(seconds),
            "estimated_credits": credits,
            "validation": {
                "valid": valid,
                "checks": self.validation_service.checks_as_dicts(checks),
            },
            "message": (
                "Prompt preview completed. Kie.ai was not called."
                if valid
                else "Prompt preview completed with validation errors. Kie.ai was not called."
            ),
        }

    async def _generate_development(
        self,
        image_paths: list[str],
        *,
        model_id: str | None,
        api_model: str | None,
        resolution: str | None,
        duration_seconds: int | None,
        estimated_credits: float | None,
    ) -> VideoGenerationResponse:
        """Upload → Gemma → validate → return prompt. Never call Kie.ai."""
        logger.info("Development Mode active — stopping before Kie.ai (no credits used)")
        validated_paths = self._validate_images(image_paths)

        model = self.validation_service.resolve_model(api_model)
        resolved_resolution = self.validation_service.resolve_resolution(resolution)
        seconds = self.validation_service.resolve_duration_seconds(duration_seconds)

        try:
            prompt = await self.prompt_service.generate_prompt(
                validated_paths,
                model=model,
                duration_seconds=seconds,
                resolution=resolved_resolution,
            )
        except ImagePromptGenerationError as exc:
            raise VideoGenerationError(exc.message, code=exc.code) from exc

        credits = self.validation_service.estimate_credits(
            model=model,
            resolution=resolved_resolution,
            duration_seconds=seconds,
            client_estimate=estimated_credits,
            model_ui_id=model_id,
        )

        checks = self.validation_service.validate_prompt_and_settings(
            prompt=prompt,
            model=model,
            resolution=resolved_resolution,
            duration_seconds=seconds,
            local_image_paths=validated_paths,
            require_public_urls=False,
        )
        self.validation_service.ensure_valid(checks)

        logger.info(
            "Development Mode complete — prompt ready ({} chars), Kie.ai skipped",
            len(prompt),
        )
        return VideoGenerationResponse(
            success=True,
            status="development_preview",
            task_id=None,
            prompt=prompt,
            message="Development Mode: prompt generated. Kie.ai was not called.",
            development_mode=True,
            generated_prompt=prompt,
            estimated_model=model,
            estimated_resolution=resolved_resolution,
            estimated_duration=self._format_duration(seconds),
            estimated_credits=credits,
        )

    async def _generate_production(
        self,
        image_paths: list[str],
        *,
        project_name: str | None,
        model_id: str | None,
        api_model: str | None,
        resolution: str | None,
        duration_seconds: int | None,
        estimated_credits: float | None,
    ) -> VideoGenerationResponse:
        """Full production pipeline including Kie.ai + MongoDB persistence."""
        logger.info("Production Mode active — Kie.ai submission enabled")

        title = (project_name or "").strip() or "Product Film"
        resolved_model = self.validation_service.resolve_model(api_model)
        resolved_resolution = self.validation_service.resolve_resolution(resolution)
        resolved_seconds = self.validation_service.resolve_duration_seconds(
            duration_seconds
        )
        # Always price from the centralized table before any Kie call.
        table_credits = self.validation_service.estimate_credits(
            model=resolved_model,
            resolution=resolved_resolution,
            duration_seconds=resolved_seconds,
            client_estimate=estimated_credits,
            model_ui_id=model_id,
        )
        display_duration = self._format_duration(resolved_seconds)
        display_resolution = self._format_resolution(resolved_resolution)
        pending_task_id = f"pending-{uuid4()}"
        video_store.create(
            task_id=pending_task_id,
            prompt="",
            title=title,
            image_paths=[],
            image_urls=[],
            status="processing",
            stage="queued",
            progress=STAGE_PROGRESS["queued"],
            duration=display_duration,
            resolution=display_resolution,
            model=resolved_model,
            credits_used=table_credits,
        )

        try:
            video_store.update(
                pending_task_id,
                stage="analyzing_images",
                progress=STAGE_PROGRESS["analyzing_images"],
            )
            validated_paths = self._validate_images(image_paths)
            thumbnail_url = self._local_upload_url(validated_paths[0])
            video_store.update(
                pending_task_id,
                image_paths=validated_paths,
                thumbnail_url=thumbnail_url,
            )
            logger.info("Image validation completed for {} path(s)", len(validated_paths))

            video_store.update(
                pending_task_id,
                stage="generating_prompt",
                progress=STAGE_PROGRESS["generating_prompt"],
            )
            logger.info("Prompt generation started")
            try:
                prompt = await self.prompt_service.generate_prompt(
                    validated_paths,
                    model=resolved_model,
                    duration_seconds=resolved_seconds,
                    resolution=resolved_resolution,
                )
            except ImagePromptGenerationError as exc:
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=exc.message,
                )
                raise VideoGenerationError(exc.message, code=exc.code) from exc

            logger.info("Prompt generation completed length={}", len(prompt))
            video_store.update(pending_task_id, prompt=prompt)

            # Validate prompt + settings before any Kie credit spend.
            pre_checks = self.validation_service.validate_prompt_and_settings(
                prompt=prompt,
                model=api_model,
                resolution=resolution,
                duration_seconds=duration_seconds,
                local_image_paths=validated_paths,
                require_public_urls=False,
            )
            try:
                self.validation_service.ensure_valid(pre_checks)
            except VideoGenerationError as exc:
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=exc.message,
                )
                raise

            video_store.update(
                pending_task_id,
                stage="submitting_to_ai",
                progress=STAGE_PROGRESS["submitting_to_ai"],
            )
            # Upload local images to Kie File API so createTask gets a public downloadUrl.
            logger.info("Uploading {} image(s) to Kie File API", len(validated_paths))
            try:
                image_urls = await self.kie_client.ensure_remote_image_urls(validated_paths)
            except KieGenerationError as exc:
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=exc.message,
                )
                raise
            video_store.update(pending_task_id, image_urls=image_urls)
            logger.info("Kie-hosted image URLs ready count={}", len(image_urls))

            url_check = await self.validation_service.urls_are_accessible(image_urls)
            model_checks = self.validation_service.validate_prompt_and_settings(
                prompt=prompt,
                model=api_model,
                resolution=resolution,
                duration_seconds=duration_seconds,
                image_urls=image_urls,
                require_public_urls=True,
            )
            # Replace the local-file URL check with the live accessibility probe.
            final_checks = [item for item in model_checks if item.name != "public_image_url"]
            final_checks.append(url_check)
            try:
                self.validation_service.ensure_valid(final_checks)
            except VideoGenerationError as exc:
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=exc.message,
                )
                raise

            logger.info("Calling Kie.ai createTask (Production Mode)")
            try:
                kie_task_id = await self.kie_client.generate_video(
                    prompt=prompt,
                    image_urls=image_urls,
                    model=api_model,
                    resolution=resolution,
                    duration_seconds=duration_seconds,
                )
            except KieGenerationError as exc:
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=exc.message,
                )
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected Kie.ai failure")
                message = f"Video generation failed: {exc}"
                video_store.update(
                    pending_task_id,
                    status="failed",
                    stage="failed",
                    progress=STAGE_PROGRESS["failed"],
                    error_message=message,
                )
                raise VideoGenerationError(
                    message,
                    code="video_generation_failed",
                ) from exc

            video_store.rebind_task_id(
                pending_task_id,
                kie_task_id,
                status="processing",
                stage="rendering",
                progress=STAGE_PROGRESS["rendering"],
            )

            logger.info("Kie.ai task_id received task_id={}", kie_task_id)
            return VideoGenerationResponse(
                success=True,
                status="processing",
                task_id=kie_task_id,
                prompt=prompt,
                message="Video generation started successfully.",
                development_mode=False,
            )
        except (VideoGenerationError, KieGenerationError):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected video generation failure")
            video_store.update(
                pending_task_id,
                status="failed",
                stage="failed",
                progress=STAGE_PROGRESS["failed"],
                error_message=str(exc),
            )
            raise VideoGenerationError(
                f"Video generation failed: {exc}",
                code="video_generation_failed",
            ) from exc

    async def get_status(self, task_id: str) -> VideoStatusResponse:
        """Return local task state, refreshing from Kie.ai when still processing."""
        record = video_store.get_by_task_id(task_id)
        if record is None:
            raise VideoGenerationError(
                f"Task not found: {task_id}",
                code="task_not_found",
            )

        if record.status in {"completed", "failed"}:
            return self._to_status_response(record)

        try:
            remote = await self.kie_client.get_task_status(task_id)
        except KieGenerationError as exc:
            logger.warning("Kie status poll failed task_id={} error={}", task_id, exc.message)
            return self._to_status_response(
                record,
                message=exc.message,
            )

        updated = self._apply_kie_status(task_id, remote) or record
        if (
            updated.status == "completed"
            and (updated.video_url or "").strip()
        ):
            actual_credits = self._extract_credits_used(remote)
            expected_credits = updated.credits_used
            # Prefer Kie.ai-reported credits whenever present.
            credits = (
                actual_credits if actual_credits is not None else expected_credits
            )
            if (
                expected_credits is not None
                and actual_credits is not None
                and abs(float(expected_credits) - float(actual_credits)) > 1e-6
            ):
                logger.warning(
                    "CREDIT MISMATCH model={} resolution={} duration={} "
                    "expected_credits={} actual_credits={}",
                    updated.model,
                    updated.resolution,
                    updated.duration,
                    expected_credits,
                    actual_credits,
                )
            if credits is not None:
                updated = (
                    video_store.update(task_id, credits_used=credits) or updated
                )
            try:
                await self.library_service.save_completed_from_task(
                    updated,
                    credits_used=credits,
                    model=updated.model,
                )
            except Exception:  # noqa: BLE001 — status polling must still succeed
                logger.exception(
                    "Failed to persist completed video task_id={}",
                    task_id,
                )
        return self._to_status_response(updated)

    def _apply_kie_status(self, task_id: str, remote: dict[str, Any]) -> VideoTaskRecord | None:
        """Map Kie.ai recordInfo into local stage/progress fields."""
        state = str(remote.get("state") or "").strip().lower()
        fail_msg = remote.get("failMsg") or remote.get("fail_msg")

        if state in {"waiting", "queuing", "queueing"}:
            return video_store.update(
                task_id,
                status="processing",
                stage="queued" if state == "waiting" else "rendering",
                progress=(
                    STAGE_PROGRESS["queued"]
                    if state == "waiting"
                    else STAGE_PROGRESS["rendering"]
                ),
                error_message=None,
            )

        if state == "generating":
            return video_store.update(
                task_id,
                status="processing",
                stage="rendering",
                progress=STAGE_PROGRESS["rendering"],
                error_message=None,
            )

        if state == "success":
            video_url = self._extract_video_url(remote)
            # Only mark completed (and later persist) when a real video URL exists.
            if not video_url:
                return video_store.update(
                    task_id,
                    status="processing",
                    stage="finalizing",
                    progress=STAGE_PROGRESS["finalizing"],
                    error_message=None,
                )
            return video_store.update(
                task_id,
                status="completed",
                stage="completed",
                progress=STAGE_PROGRESS["completed"],
                video_url=video_url,
                error_message=None,
            )

        if state == "fail":
            message = str(fail_msg or "Kie.ai generation failed")
            return video_store.update(
                task_id,
                status="failed",
                stage="failed",
                progress=STAGE_PROGRESS["failed"],
                error_message=message,
            )

        # Unknown state — keep rendering while provider works.
        return video_store.update(
            task_id,
            status="processing",
            stage="finalizing" if state in {"successing", "finalizing"} else "rendering",
            progress=STAGE_PROGRESS.get("finalizing", STAGE_PROGRESS["rendering"]),
        )

    @staticmethod
    def _extract_credits_used(remote: dict[str, Any]) -> int | None:
        # Prefer any cost field Kie.ai may return.
        for key in (
            "creditsConsumed",
            "credits_consumed",
            "consumeCredits",
            "creditCost",
            "credits",
            "cost",
        ):
            raw = remote.get(key)
            if raw is None and isinstance(remote.get("data"), dict):
                raw = remote["data"].get(key)
            if raw is None:
                continue
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _parse_duration_seconds(value: str | int | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip().lower().rstrip("s")
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    def _extract_video_url(self, remote: dict[str, Any]) -> str | None:
        """Parse resultJson / resultUrls from Kie.ai success payload."""
        result_json = remote.get("resultJson") or remote.get("result_json")
        payload: Any = result_json
        if isinstance(result_json, str) and result_json.strip():
            try:
                payload = json.loads(result_json)
            except json.JSONDecodeError:
                payload = None

        if isinstance(payload, dict):
            urls = payload.get("resultUrls") or payload.get("result_urls") or []
            if isinstance(urls, list) and urls:
                return str(urls[0])
            for key in ("videoUrl", "video_url", "url"):
                if payload.get(key):
                    return str(payload[key])

        for key in ("resultUrls", "result_urls", "videoUrl", "video_url"):
            value = remote.get(key)
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str) and value.startswith("http"):
                return value
        return None

    def _to_status_response(
        self,
        record: VideoTaskRecord,
        message: str | None = None,
    ) -> VideoStatusResponse:
        stage = record.stage
        if record.status == "completed":
            stage = "completed"
        elif record.status == "failed":
            stage = "failed"

        return VideoStatusResponse(
            success=record.status != "failed",
            task_id=record.task_id,
            status=record.status,
            stage=stage,
            progress=record.progress,
            prompt=record.prompt or None,
            video_url=record.video_url,
            thumbnail_url=record.thumbnail_url,
            created_at=record.created_at,
            duration=record.duration,
            resolution=record.resolution,
            title=record.title,
            message=message
            or (
                "Video generation completed."
                if record.status == "completed"
                else record.error_message
            ),
            error_message=record.error_message,
        )

    def _local_upload_url(self, absolute_path: str) -> str:
        upload_root = self.settings.upload_path.resolve()
        candidate = Path(absolute_path).resolve()
        relative = candidate.relative_to(upload_root).as_posix()
        return f"/uploads/{relative}"

    def _format_duration(self, duration_seconds: int | None) -> str:
        if duration_seconds is None:
            return self.settings.display_duration
        try:
            seconds = max(1, int(duration_seconds))
        except (TypeError, ValueError):
            return self.settings.display_duration
        minutes, rem = divmod(seconds, 60)
        return f"{minutes}:{rem:02d}"

    def _format_resolution(self, resolution: str | None) -> str:
        if not resolution:
            return self.settings.display_resolution
        raw = resolution.strip().lower()
        mapping = {
            "480p": "480 × 854",
            "720p": "720 × 1280",
            "1080p": "1080 × 1920",
            "4k": "2160 × 3840",
        }
        return mapping.get(raw, resolution)

    def _validate_images(self, image_paths: list[str]) -> list[str]:
        """Ensure every image path exists and is an allowed upload file."""
        if not image_paths:
            raise VideoGenerationError(
                "At least one image path is required",
                code="missing_images",
            )

        upload_root = self.settings.upload_path.resolve()
        resolved: list[str] = []

        for raw_path in image_paths:
            raw = raw_path.strip()
            if not raw:
                raise VideoGenerationError(
                    "Empty image path is not allowed",
                    code="invalid_image",
                )

            if raw.startswith("/uploads/"):
                candidate = (upload_root / raw.removeprefix("/uploads/")).resolve()
            elif raw.startswith("uploads/"):
                candidate = (upload_root / raw.removeprefix("uploads/")).resolve()
            else:
                candidate = Path(raw).expanduser().resolve()

            try:
                candidate.relative_to(upload_root)
            except ValueError as exc:
                raise VideoGenerationError(
                    f"Image path must be inside the uploads directory: {raw}",
                    code="invalid_image",
                ) from exc

            if not candidate.is_file():
                raise VideoGenerationError(
                    f"Image file not found: {raw}",
                    code="missing_images",
                )

            extension = candidate.suffix.lower().lstrip(".")
            if extension not in self.settings.allowed_extensions:
                allowed = ", ".join(sorted(self.settings.allowed_extensions))
                raise VideoGenerationError(
                    f"Unsupported image type '.{extension}'. Allowed: {allowed}",
                    code="invalid_image",
                )

            if candidate.stat().st_size <= 0:
                raise VideoGenerationError(
                    f"Image file is empty: {raw}",
                    code="invalid_image",
                )

            resolved.append(str(candidate))

        return resolved


def get_video_generation_service(
    settings: Settings = Depends(get_settings),
    prompt_service: ImagePromptService = Depends(get_image_prompt_service),
    kie_client: KieClient = Depends(get_kie_client),
    library_service: VideoLibraryService = Depends(get_video_library_service),
    validation_service: GenerationValidationService = Depends(
        get_generation_validation_service
    ),
) -> VideoGenerationService:
    """FastAPI dependency factory for VideoGenerationService."""
    return VideoGenerationService(
        settings=settings,
        prompt_service=prompt_service,
        kie_client=kie_client,
        library_service=library_service,
        validation_service=validation_service,
    )
