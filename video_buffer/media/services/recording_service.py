"""
VideoRecordingService
=====================
Orchestrates the full pipeline:
    1. Generate MP4 from frames + timestamps
    2. Persist Video record with inline manifest
    3. Dispatch async cloud manifest upload

This is the single entry point callers should use — not generate_video directly.
"""

from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import cv2

from media.models import Video, get_media_path
from django.conf import settings
from common_utils.media.frame_manifest import FrameManifest
from common_utils.media.video_utils import generate_video, get_video_length
from common_utils.models.common import generate_unique_id

logger = logging.getLogger(__name__)


class VideoRecordingService:

    def create_video_from_images(
        self,
        images: list,               # queryset or list of Image model instances
        camera,                     # Camera model instance
        framerate: float,
        video_name: str,
        from_time: datetime,
        to_time: datetime,
        annotated_frames: Optional[list] = None,
        tenant=None,
        expires_at: Optional[datetime] = None,
        scale: float = 1.0,
    ) -> Optional["Video"]:
        """
        Full pipeline: images → MP4 → Video record with manifest.

        Parameters
        ----------
        images:
            Ordered list of Image model instances. Each must have:
              - image_file.path  (local path for cv2.imread)
              - timestamp        (timezone-aware datetime, wall-clock UTC)
        camera:
            Camera FK for the Video record.
        framerate:
            Playback framerate for the encoded video.
        video_name:
            Human-readable name stored on the Video record.
        from_time / to_time:
            Wall-clock window of the recording session.
        annotated_frames:
            Pre-annotated BGR numpy frames (same order/length as images).
            If None, raw frames are read from image.image_file.path.
        tenant:
            Tenant instance — used for multi-tenant context.
        expires_at:
            Optional expiry datetime for the Video record.
        scale:
            Resize factor applied to each frame before encoding.
        Returns
        -------
        Video instance with frame_manifest populated and manifest upload queued,
        or None if encoding failed.
        """
        from common_utils.models.common import generate_unique_id, get_video

        if not images:
            logger.warning("VideoRecordingService: no images provided")
            return None

        frames, timestamps = self._resolve_frames(images, annotated_frames)
        if not frames:
            logger.warning("VideoRecordingService: all frames failed to load")
            return None
        
        # ------------------------------------------------------------------
        # Create the Video DB record first to get a stable video_id and path
        # ------------------------------------------------------------------
        video_id = str(generate_unique_id())
        video_model = get_video(
            video_id=video_id,
            video_name=video_name,
            timestamp=datetime.now(tz=timezone.utc),
            from_time=from_time,
            to_time=to_time,
            expires_at=expires_at,
            camera_id=camera.id,
        )

        # ------------------------------------------------------------------
        # Resolve output path
        # ------------------------------------------------------------------
        video_file_rel = get_media_path(video_model, video_name)
        video_file_abs = f"{settings.MEDIA_ROOT}/{video_file_rel}"
        os.makedirs(os.path.dirname(video_file_abs), exist_ok=True)

        # ------------------------------------------------------------------
        # Encode — manifest is built frame-by-frame in lockstep with encoding
        # ------------------------------------------------------------------
        success, manifest = generate_video(
            frames=frames,
            frame_timestamps=timestamps,
            framerate=framerate,
            video_path=video_file_abs,
            video_id=video_id,
            scale=scale,
        )

        if not success or manifest is None:
            logger.error(
                "VideoRecordingService: encoding failed for video_id=%s", video_id
            )
            return None

        # ------------------------------------------------------------------
        # Persist — video file, manifest, timing, size
        # ------------------------------------------------------------------
        video_model.video_file = video_file_rel
        video_model.video_size = os.stat(video_file_abs).st_size


        # set_manifest populates: frame_manifest, framerate, start_time, end_time
        video_model.set_manifest(manifest)

        # Encoded video duration
        if manifest.video_duration_seconds is not None:
            video_model.duration = timedelta(seconds=manifest.video_duration_seconds)
        else:
            h, m, s = get_video_length(path=video_file_abs)
            video_model.duration = timedelta(hours=h, minutes=m, seconds=s)
 
        video_model.save()
 
        # Link source images
        video_model.images_used.set(images)
 
        logger.info(
            "VideoRecordingService: created Video %s | frames=%d | "
            "wall=%.1fs | video=%.1fs",
            video_id,
            manifest.frame_count,
            manifest.wall_duration_seconds or 0,
            manifest.video_duration_seconds or 0,
        )
 
        return video_model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_frames(
        self,
        images: list,
        annotated_frames: Optional[list],
    ) -> tuple[list, list[datetime]]:
        """
        Pair each frame with its wall-clock timestamp from the image record.
        If annotated_frames are provided they are used directly (task owns
        annotation); otherwise frames are read from disk.
 
        Skips unreadable disk frames with a warning.
        Raises if annotated_frames length mismatches images length.
        """
        frames, timestamps = [], []
 
        use_annotated = annotated_frames is not None
        if use_annotated and len(annotated_frames) != len(images):
            raise ValueError(
                f"annotated_frames length ({len(annotated_frames)}) must match "
                f"images length ({len(images)})"
            )
 
        for i, image in enumerate(images):
            if use_annotated:
                frame = annotated_frames[i]
            else:
                frame = cv2.imread(image.image_file.path)
                if frame is None:
                    logger.warning(
                        "VideoRecordingService: could not read %s — skipping",
                        image.image_file.path,
                    )
                    continue
 
            ts = image.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
 
            frames.append(frame)
            timestamps.append(ts)
 
        return frames, timestamps

    def _load_frames(
        self, images: list
    ) -> tuple[list, list[datetime]]:
        frames, timestamps = [], []
        for image in images:
            frame = cv2.imread(image.image_file.path)
            if frame is None:
                logger.warning(
                    "VideoRecordingService: could not read frame from %s, skipping",
                    image.image_file.path,
                )
                continue
            ts = image.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            frames.append(frame)
            timestamps.append(ts)
        return frames, timestamps

    def _create_video_record(
        self,
        video_id: str,
        video_name: str,
        video_path: str,
        manifest: FrameManifest,
        camera,
        images: list,
        tenant=None,
    ):
        from media.models import Video
        from django.core.files import File

        video = Video(
            video_id=video_id,
            video_name=video_name,
            camera=camera,
            timestamp=manifest.start_time or datetime.now(tz=timezone.utc),
        )

        # Populate manifest + timing fields
        video.set_manifest(manifest)

        # Encoded video duration
        if manifest.video_duration_seconds is not None:
            video.duration = timedelta(seconds=manifest.video_duration_seconds)

        video.save()

        # Link source images
        video.images_used.set(images)

        logger.info(
            "VideoRecordingService: created Video %s "
            "frames=%d wall=%.1fs video=%.1fs",
            video_id,
            manifest.frame_count,
            manifest.wall_duration_seconds or 0,
            manifest.video_duration_seconds or 0,
        )
        return video