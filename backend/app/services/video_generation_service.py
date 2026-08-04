"""Orchestrate prompt generation, Kie.ai submission, and status polling."""

from __future__ import annotations

import asyncio
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

# Stage → (start%, end%) for smooth progress. Update BEFORE long work starts.
STAGE_RANGES: dict[str, tuple[int, int]] = {
    "queued": (5, 5),
    "uploading_images": (10, 20),
    "analyzing_images": (20, 35),
    "generating_prompt": (35, 50),
    "uploading_assets": (50, 65),
    "submitting_to_kie": (65, 75),
    "waiting_queue": (75, 80),
    "rendering": (80, 95),
    "finalizing": (95, 99),
    "completed": (100, 100),
    "failed": (100, 100),
}

# Legacy alias used by older call sites / failed markers.
STAGE_PROGRESS = {stage: bounds[0] for stage, bounds in STAGE_RANGES.items()}


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
        """
        Create a job immediately and run the pipeline in the background so the
        progress page can poll live stage/progress updates.
        """
        logger.info("Production Mode active — Kie.ai submission enabled (async job)")

        title = (project_name or "").strip() or "Product Film"
        resolved_model = self.validation_service.resolve_model(api_model)
        resolved_resolution = self.validation_service.resolve_resolution(resolution)
        resolved_seconds = self.validation_service.resolve_duration_seconds(
            duration_seconds
        )
        table_credits = self.validation_service.estimate_credits(
            model=resolved_model,
            resolution=resolved_resolution,
            duration_seconds=resolved_seconds,
            client_estimate=estimated_credits,
            model_ui_id=model_id,
        )
        display_duration = self._format_duration(resolved_seconds)
        display_resolution = self._format_resolution(resolved_resolution)
        job_id = f"job-{uuid4()}"

        video_store.create(
            task_id=job_id,
            prompt="",
            title=title,
            image_paths=list(image_paths),
            image_urls=[],
            status="processing",
            stage="queued",
            progress=STAGE_RANGES["queued"][0],
            duration=display_duration,
            resolution=display_resolution,
            model=resolved_model,
            credits_used=table_credits,
        )
        video_store.update(
            job_id,
            status_message="Job queued — starting pipeline…",
        )

        asyncio.create_task(
            self._run_production_pipeline(
                job_id=job_id,
                image_paths=list(image_paths),
                api_model=api_model,
                resolved_model=resolved_model,
                resolution=resolution,
                resolved_resolution=resolved_resolution,
                duration_seconds=duration_seconds,
                resolved_seconds=resolved_seconds,
            ),
            name=f"video-pipeline-{job_id}",
        )

        return VideoGenerationResponse(
            success=True,
            status="processing",
            task_id=job_id,
            prompt=None,
            message="Video generation started. Poll /api/video/status for live progress.",
            development_mode=False,
        )

    async def _run_production_pipeline(
        self,
        *,
        job_id: str,
        image_paths: list[str],
        api_model: str | None,
        resolved_model: str,
        resolution: str | None,
        resolved_resolution: str,
        duration_seconds: int | None,
        resolved_seconds: int,
    ) -> None:
        """Background pipeline — updates stage/progress before each long step."""
        pulse: asyncio.Task[None] | None = None
        try:
            self._set_stage(
                job_id,
                "uploading_images",
                message="Preparing uploaded images…",
            )
            validated_paths = self._validate_images(image_paths)
            total_images = len(validated_paths)
            for index, path in enumerate(validated_paths, start=1):
                start, end = STAGE_RANGES["uploading_images"]
                pct = start + int((end - start) * (index / max(total_images, 1)))
                self._set_stage(
                    job_id,
                    "uploading_images",
                    progress=pct,
                    message=f"Preparing image {index}/{total_images}",
                )
                await asyncio.sleep(0)  # yield so status polls can read updates

            thumbnail_url = self._local_upload_url(validated_paths[0])
            video_store.update(
                job_id,
                image_paths=validated_paths,
                thumbnail_url=thumbnail_url,
            )

            self._set_stage(
                job_id,
                "analyzing_images",
                message="Analyzing product images…",
            )
            pulse = self._start_progress_pulse(job_id, "analyzing_images")
            # Hold analyzing long enough for the UI to poll it before prompt work.
            await asyncio.sleep(1.2)
            if pulse:
                pulse.cancel()

            self._set_stage(
                job_id,
                "generating_prompt",
                message="Generating cinematic prompt…",
            )
            pulse = self._start_progress_pulse(job_id, "generating_prompt")

            try:
                prompt = await self.prompt_service.generate_prompt(
                    validated_paths,
                    model=resolved_model,
                    duration_seconds=resolved_seconds,
                    resolution=resolved_resolution,
                )
            except ImagePromptGenerationError as exc:
                self._fail_job(job_id, exc.message)
                return

            if pulse:
                pulse.cancel()
                pulse = None

            video_store.update(job_id, prompt=prompt)
            logger.info("Prompt generation completed job_id={} length={}", job_id, len(prompt))

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
                self._fail_job(job_id, exc.message)
                return

            self._set_stage(
                job_id,
                "uploading_assets",
                message="Uploading assets to Kie.ai…",
            )

            async def _on_asset_upload(index: int, total: int) -> None:
                start, end = STAGE_RANGES["uploading_assets"]
                pct = start + int((end - start) * ((index - 1) / max(total, 1)))
                self._set_stage(
                    job_id,
                    "uploading_assets",
                    progress=min(end - 1, max(start, pct)),
                    message=f"Uploading image {index}/{total} to Kie.ai",
                )

            try:
                image_urls = await self.kie_client.ensure_remote_image_urls(
                    validated_paths,
                    on_progress=_on_asset_upload,
                )
            except KieGenerationError as exc:
                self._fail_job(job_id, exc.message)
                return

            video_store.update(job_id, image_urls=image_urls)
            self._set_stage(
                job_id,
                "uploading_assets",
                progress=STAGE_RANGES["uploading_assets"][1],
                message=f"Uploaded {len(image_urls)} asset(s) to Kie.ai",
            )

            url_check = await self.validation_service.urls_are_accessible(image_urls)
            model_checks = self.validation_service.validate_prompt_and_settings(
                prompt=prompt,
                model=api_model,
                resolution=resolution,
                duration_seconds=duration_seconds,
                image_urls=image_urls,
                require_public_urls=True,
            )
            final_checks = [item for item in model_checks if item.name != "public_image_url"]
            final_checks.append(url_check)
            try:
                self.validation_service.ensure_valid(final_checks)
            except VideoGenerationError as exc:
                self._fail_job(job_id, exc.message)
                return

            self._set_stage(
                job_id,
                "submitting_to_kie",
                message="Submitting generation request to Kie.ai…",
            )
            try:
                kie_task_id = await self.kie_client.generate_video(
                    prompt=prompt,
                    image_urls=image_urls,
                    model=api_model,
                    resolution=resolution,
                    duration_seconds=duration_seconds,
                )
            except KieGenerationError as exc:
                self._fail_job(job_id, exc.message)
                return
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected Kie.ai failure job_id={}", job_id)
                self._fail_job(job_id, f"Video generation failed: {exc}")
                return

            # Keep client task_id stable; store provider id for polling.
            video_store.update(job_id, provider_task_id=kie_task_id)
            self._set_stage(
                job_id,
                "waiting_queue",
                message="Waiting in Kie.ai queue…",
            )
            logger.info(
                "Kie.ai task submitted job_id={} provider_task_id={}",
                job_id,
                kie_task_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected pipeline failure job_id={}", job_id)
            self._fail_job(job_id, f"Video generation failed: {exc}")
        finally:
            if pulse and not pulse.done():
                pulse.cancel()

    async def get_status(self, task_id: str) -> VideoStatusResponse:
        """Return local task state, refreshing from Kie.ai when a provider id exists."""
        record = video_store.get_by_task_id(task_id)
        if record is None:
            raise VideoGenerationError(
                f"Task not found: {task_id}",
                code="task_not_found",
            )

        if record.status in {"completed", "failed"}:
            return self._to_status_response(record)

        provider_task_id = (record.provider_task_id or "").strip()
        if not provider_task_id:
            # Still in local pipeline — nudge progress within the active stage band.
            self._nudge_stage_progress(task_id, record.stage)
            refreshed = video_store.get_by_task_id(task_id) or record
            return self._to_status_response(refreshed)

        try:
            remote = await self.kie_client.get_task_status(provider_task_id)
        except KieGenerationError as exc:
            logger.warning(
                "Kie status poll failed job_id={} provider_task_id={} error={}",
                task_id,
                provider_task_id,
                exc.message,
            )
            return self._to_status_response(record, message=exc.message)

        updated = self._apply_kie_status(task_id, remote) or record
        if updated.status == "completed" and (updated.video_url or "").strip():
            actual_credits = self._extract_credits_used(remote)
            expected_credits = updated.credits_used
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
                updated = video_store.update(task_id, credits_used=credits) or updated
            try:
                await self.library_service.save_completed_from_task(
                    updated,
                    credits_used=credits,
                    model=updated.model,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Failed to persist completed video task_id={}",
                    task_id,
                )
        return self._to_status_response(updated)

    def _set_stage(
        self,
        task_id: str,
        stage: str,
        *,
        progress: int | None = None,
        message: str | None = None,
    ) -> VideoTaskRecord | None:
        """Update stage immediately; never decrease progress."""
        record = video_store.get_by_task_id(task_id)
        if record is None:
            return None
        start, _end = STAGE_RANGES.get(stage, (record.progress, record.progress))
        next_progress = start if progress is None else progress
        next_progress = max(int(record.progress), int(next_progress))
        logger.info(
            "Progress update job_id={} stage={} progress={}% message={!r}",
            task_id,
            stage,
            next_progress,
            message,
        )
        return video_store.update(
            task_id,
            status="processing",
            stage=stage,
            progress=next_progress,
            status_message=message if message is not None else record.status_message,
            error_message=None,
        )

    def _fail_job(self, task_id: str, message: str) -> None:
        video_store.update(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            status_message=message,
            error_message=message,
        )

    def _start_progress_pulse(self, task_id: str, stage: str) -> asyncio.Task[None]:
        """Slowly advance progress inside a stage band during long operations."""

        async def _pulse() -> None:
            start, end = STAGE_RANGES.get(stage, (0, 0))
            ceiling = max(start, end - 1)
            while True:
                await asyncio.sleep(2.0)
                record = video_store.get_by_task_id(task_id)
                if record is None or record.stage != stage:
                    return
                if record.progress >= ceiling:
                    continue
                video_store.update(
                    task_id,
                    progress=min(ceiling, int(record.progress) + 1),
                )

        return asyncio.create_task(_pulse(), name=f"progress-pulse-{task_id}-{stage}")

    def _nudge_stage_progress(self, task_id: str, stage: str) -> None:
        """On each status poll, inch progress forward within the active band."""
        if stage not in STAGE_RANGES or stage in {"queued", "completed", "failed"}:
            return
        record = video_store.get_by_task_id(task_id)
        if record is None or record.stage != stage:
            return
        _start, end = STAGE_RANGES[stage]
        ceiling = max(_start, end - 1)
        if record.progress >= ceiling:
            return
        video_store.update(task_id, progress=min(ceiling, int(record.progress) + 1))

    def _apply_kie_status(self, task_id: str, remote: dict[str, Any]) -> VideoTaskRecord | None:
        """Map Kie.ai recordInfo into local stage/progress (never regress)."""
        state = str(remote.get("state") or "").strip().lower()
        fail_msg = remote.get("failMsg") or remote.get("fail_msg")
        record = video_store.get_by_task_id(task_id)
        current = int(record.progress) if record else 0

        def _bump(stage: str, progress: int, message: str) -> VideoTaskRecord | None:
            start, end = STAGE_RANGES[stage]
            target = max(current, min(end, max(start, progress)))
            return video_store.update(
                task_id,
                status="processing",
                stage=stage,
                progress=target,
                status_message=message,
                error_message=None,
            )

        if state in {"waiting", "queuing", "queueing"}:
            start, end = STAGE_RANGES["waiting_queue"]
            # Creep within 75–80 while queued at provider.
            target = min(end, max(start, current + 1 if current >= start else start))
            return _bump("waiting_queue", target, "Waiting in Kie.ai queue…")

        if state == "generating":
            start, end = STAGE_RANGES["rendering"]
            target = min(end - 1, max(start, current + 1 if current >= start else start))
            return _bump("rendering", target, "Rendering video…")

        if state == "success":
            video_url = self._extract_video_url(remote)
            if not video_url:
                return _bump(
                    "finalizing",
                    STAGE_RANGES["finalizing"][0],
                    "Finalizing video output…",
                )
            return video_store.update(
                task_id,
                status="completed",
                stage="completed",
                progress=100,
                video_url=video_url,
                status_message="Video generation completed.",
                error_message=None,
            )

        if state == "fail":
            message = str(fail_msg or "Kie.ai generation failed")
            return video_store.update(
                task_id,
                status="failed",
                stage="failed",
                progress=100,
                status_message=message,
                error_message=message,
            )

        if state in {"successing", "finalizing"}:
            return _bump(
                "finalizing",
                STAGE_RANGES["finalizing"][0],
                "Finalizing video output…",
            )

        # Unknown provider state — keep advancing render band, never rewind.
        start, end = STAGE_RANGES["rendering"]
        target = min(end - 1, max(start, current if current >= start else start))
        return _bump("rendering", target, "Rendering video…")

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
            progress=int(record.progress),
            prompt=record.prompt or None,
            video_url=record.video_url,
            thumbnail_url=record.thumbnail_url,
            created_at=record.created_at,
            duration=record.duration,
            resolution=record.resolution,
            title=record.title,
            message=message
            or record.status_message
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
