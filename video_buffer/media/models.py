
from __future__ import annotations
from django.db import models
from tenants.models import (
    SensorBox, Camera
)

import httpx
import logging
from datetime import timezone
from typing import Optional
from common_utils.media.frame_manifest import FrameManifest

logger = logging.getLogger(__name__)

def get_image_path(instance, filename):
    return f"images/{instance.camera_id}/{filename}"

def get_media_path(instance, filename):
    return f"videos/{filename}"

# Create your models here.
class Image(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name="images")
    image_id = models.CharField(max_length=255, unique=True)
    image_name = models.CharField(max_length=255)
    image_file = models.ImageField(upload_to=get_image_path)
    image_size = models.IntegerField(null=True, blank=True)
    image_format = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        db_table = 'image'
        verbose_name = 'Image'
        verbose_name_plural = "Images"

    def __str__(self) -> str:
        return f"Image: {self.image_id} created at {self.created_at}"

    
class Video(models.Model):
    camera = models.ForeignKey(
        Camera, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="videos",
    )
    video_id = models.CharField(max_length=255, unique=True)
    video_name = models.CharField(max_length=255)
    video_file = models.FileField(upload_to=get_media_path)
    video_size = models.IntegerField(null=True, blank=True)
    video_format = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # ------------------------------------------------------------------ #
    # Timing fields
    # ------------------------------------------------------------------ #
    # Wall-clock UTC boundaries of the real-world recording session.
    # These represent actual time — NOT positions in the encoded video file.
    start_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Wall-clock UTC start time of the recording session. "
                  "Represents the real-world time when the first frame was captured."
    )
    end_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Wall-clock UTC end time of the recording session. "
                  "Represents the real-world time when the last frame was captured."
    )

    # Encoded video file duration (typically much shorter than the real session).
    duration = models.DurationField(
        null=True, blank=True,
        help_text="Duration of the encoded video file. "
                  "Typically much shorter than the real-world recording session."
    )

    # ------------------------------------------------------------------ #
    # Manifest fields
    # ------------------------------------------------------------------ #
    # Playback framerate used when encoding. Required to convert
    # frame_index → video_seconds (video_seconds = frame_index / framerate).
    framerate = models.FloatField(
        null=True, blank=True,
        help_text="Playback framerate of the encoded video file.",
    )
 
    # Inline manifest — written immediately after encoding completes.
    # Acts as the fallback when manifest_url is not yet available.
    # Schema: {video_id, framerate, frame_count, entries: [{frame_index, wall_ts, wall_ts_iso}]}
    frame_manifest = models.JSONField(
        null=True, blank=True,
        help_text="Inline frame→wall-time manifest. Kept in sync with manifest_url.",
    )
 
    # Cloud sidecar URL — written asynchronously after cloud upload.
    # Takes precedence over frame_manifest when both are present.
    manifest_url = models.URLField(
        null=True, blank=True,
        help_text="Cloud storage URL for the sidecar manifest JSON.",
    )

    # ------------------------------------------------------------------ #
    # Other fields
    # ------------------------------------------------------------------ #
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    images_used = models.ManyToManyField(Image, related_name="videos")

    class Meta:
        db_table = 'video'
        verbose_name = 'Video'
        verbose_name_plural = "Videos"

    def __str__(self) -> str:
        return f"Video {self.video_id} ({self.start_time} - {self.end_time})"


    # ------------------------------------------------------------------ #
    # Manifest resolution
    # ------------------------------------------------------------------ #
 
    def get_manifest(self, timeout: float = 10.0) -> Optional[FrameManifest]:
        """
        Resolve and deserialise the FrameManifest for this video.
 
        Resolution order:
            1. manifest_url  — durable cloud copy (preferred)
            2. frame_manifest — inline DB copy (fallback during upload window)
 
        Returns None if neither source is available.
        """
        data = self._fetch_manifest_data(timeout=timeout)
        if data is None:
            return None
        return FrameManifest.from_dict(data)
    
    def _fetch_manifest_data(self, timeout: float = 10.0) -> Optional[dict]:
        if self.manifest_url:
            try:
                response = httpx.get(self.manifest_url, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except Exception:
                logger.exception(
                    "Video %s: failed to fetch manifest from URL %s — "
                    "falling back to inline copy",
                    self.video_id, self.manifest_url,
                )
 
        if self.frame_manifest:
            return self.frame_manifest
 
        logger.warning("Video %s: no manifest available", self.video_id)
        return None
 
    def set_manifest(self, manifest: FrameManifest) -> None:
        """
        Write the inline manifest and sync timing fields.
        Does NOT touch manifest_url — that is handled by the Celery task.
        Call save() after this method.
        """
        self.frame_manifest = manifest.to_dict()
        self.framerate      = manifest.framerate
        self.start_time     = manifest.start_time
        self.end_time       = manifest.end_time
 
    def clear_manifest_url(self) -> None:
        """
        Clear the cloud URL before a manifest regeneration.
        Ensures resolved_manifest falls back to the inline copy during
        the re-upload window. Call save() after this method.
        """
        self.manifest_url = None
 
    # ------------------------------------------------------------------ #
    # Convenience query shortcuts
    # ------------------------------------------------------------------ #
 
    def wall_time_to_video_position(self, wall_time) -> Optional[float]:
        """Shortcut: resolve manifest and query in one call."""
        manifest = self.get_manifest()
        if manifest is None:
            return None
        return manifest.wall_time_to_video_position(wall_time)
 
    def video_position_to_wall_time(self, video_seconds: float):
        """Shortcut: resolve manifest and query in one call."""
        manifest = self.get_manifest()
        if manifest is None:
            return None
        return manifest.video_position_to_wall_time(video_seconds)