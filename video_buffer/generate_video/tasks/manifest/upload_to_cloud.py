"""
Video manifest tasks
====================
Async Celery tasks that upload the frame manifest sidecar to cloud storage
and backfill manifest_url on the Video record.

The inline frame_manifest (JSONField) is written synchronously at encode time
and serves as the fallback. These tasks run in the background to populate the
durable cloud copy (manifest_url).
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# Retry policy: 3 attempts, exponential backoff (60s, 120s, 240s)
MANIFEST_UPLOAD_MAX_RETRIES = 3
MANIFEST_UPLOAD_RETRY_BACKOFF = 60  # seconds


@shared_task(
    bind=True,
    max_retries=MANIFEST_UPLOAD_MAX_RETRIES,
    default_retry_delay=MANIFEST_UPLOAD_RETRY_BACKOFF,
)
def upload_manifest_to_cloud(self, video_id: int) -> None:
    """
    Upload the inline frame_manifest JSON to cloud storage and backfill
    manifest_url on the Video record.

    Idempotent: safe to retry or call multiple times.
    """
    from media.models import Video  # local import to avoid circular deps

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error("upload_manifest_to_cloud: Video id=%d not found", video_id)
        return

    if not video.frame_manifest:
        logger.warning(
            "upload_manifest_to_cloud: Video %s has no inline manifest, skipping",
            video.video_id,
        )
        return

    if video.manifest_url:
        logger.info(
            "upload_manifest_to_cloud: Video %s already has manifest_url, skipping",
            video.video_id,
        )
        return

    try:
        sidecar_key = _sidecar_key_from_video(video)
        manifest_json = json.dumps(video.frame_manifest, indent=2).encode("utf-8")

        # Save to Django's configured storage backend (S3, GCS, Azure, etc.)
        saved_path = default_storage.save(sidecar_key, ContentFile(manifest_json))
        manifest_url = default_storage.url(saved_path)

        video.manifest_url = manifest_url
        video.save(update_fields=["manifest_url"])

        logger.info(
            "upload_manifest_to_cloud: Video %s manifest uploaded → %s",
            video.video_id, manifest_url,
        )

    except Exception as exc:
        logger.exception(
            "upload_manifest_to_cloud: failed for Video %s (attempt %d/%d)",
            video.video_id,
            self.request.retries + 1,
            MANIFEST_UPLOAD_MAX_RETRIES + 1,
        )
        raise self.retry(exc=exc, countdown=MANIFEST_UPLOAD_RETRY_BACKOFF * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=MANIFEST_UPLOAD_MAX_RETRIES,
    default_retry_delay=MANIFEST_UPLOAD_RETRY_BACKOFF,
)
def regenerate_manifest(self, video_id: int, manifest_dict: dict) -> None:
    """
    Replace both inline and cloud manifest with a new version.
    Used when a manifest needs to be recomputed (e.g. framerate correction).

    Clears manifest_url first so the inline copy is always the fallback
    during the upload window.
    """
    from media.models import Video

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error("regenerate_manifest: Video id=%d not found", video_id)
        return

    try:
        # 1. Atomically update inline copy and clear stale cloud URL
        video.frame_manifest = manifest_dict
        video.manifest_url   = None
        video.save(update_fields=["frame_manifest", "manifest_url"])

        # 2. Re-upload to cloud
        upload_manifest_to_cloud.delay(video_id)

    except Exception as exc:
        logger.exception("regenerate_manifest: failed for Video id=%d", video_id)
        raise self.retry(exc=exc)


def _sidecar_key_from_video(video) -> str:
    """
    Derive a deterministic storage key for the manifest sidecar.
    Mirrors the video file path with a .manifest.json suffix.

    e.g. videos/cam1/abc123/video.mp4 → videos/cam1/abc123/video.manifest.json
    """
    video_name = video.video_file.name  # e.g. "videos/cam1/abc123/video.mp4"
    base = video_name.rsplit(".", 1)[0] if "." in video_name else video_name
    return f"{base}.manifest.json"