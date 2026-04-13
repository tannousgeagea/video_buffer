from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field, field_validator, model_validator

class FrameManifestPayload(BaseModel):
    """
    Embedded frame manifest transferred alongside the video archive request.
    Mirrors the FrameManifest.to_dict() schema so the receiving service can
    deserialise it directly into a FrameManifest instance without a separate
    sidecar fetch.
    """
    video_id: str
    framerate: float
    frame_count: int
    start_time_iso: Optional[str] = None
    end_time_iso: Optional[str] = None
    wall_duration_seconds: Optional[float] = None
    video_duration_seconds: Optional[float] = None
    entries: List[Dict[str, Any]] = Field(default_factory=list)


class VideoArchiveRequest(BaseModel):
    # ------------------------------------------------------------------
    # Routing / identity
    # ------------------------------------------------------------------
    tenant_domain: str
    location: str
    sensor_box_location: str
    camera_id: str
    video_id: str

    # ------------------------------------------------------------------
    # Media reference
    # ------------------------------------------------------------------
    media_id: str
    media_name: str
    media_url: str
    media_type: str = Field(default="video", description="MIME category, e.g. 'video'")
    media_format: Optional[str] = Field(
        default=None,
        description="Container format, e.g. 'mp4', 'mkv'",
    )
    media_size_bytes: Optional[int] = Field(
        default=None,
        description="Encoded video file size in bytes",
        ge=0,
    )

    # ------------------------------------------------------------------
    # Real-world timing  (wall-clock, not video file position)
    # ------------------------------------------------------------------
    start_time: Optional[datetime] = Field(
        default=None,
        description="Wall-clock UTC start of the recording session",
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="Wall-clock UTC end of the recording session",
    )
    wall_duration_seconds: Optional[float] = Field(
        default=None,
        description="Real-world recording span in seconds (end_time - start_time)",
        ge=0,
    )

    # ------------------------------------------------------------------
    # Encoded video timing  (video file position, not real-world time)
    # ------------------------------------------------------------------
    framerate: Optional[float] = Field(
        default=None,
        description="Playback framerate of the encoded video file",
        gt=0,
    )
    video_duration_seconds: Optional[float] = Field(
        default=None,
        description="Encoded video file duration in seconds",
        ge=0,
    )

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------
    manifest: Optional[FrameManifestPayload] = Field(
        default=None,
        description=(
            "Inline frame manifest. Present when the manifest is small enough "
            "to embed directly. Takes precedence over manifest_url when both are set."
        ),
    )
    manifest_url: Optional[str] = Field(
        default=None,
        description="Cloud storage URL for the sidecar manifest JSON",
    )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    expires_at: Optional[datetime] = Field(
        default=None,
        description="UTC datetime after which this archive entry may be purged",
    )

    # ------------------------------------------------------------------
    # Extensible metadata
    # ------------------------------------------------------------------
    meta_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, v: str) -> str:
        allowed = {"video", "timelapse", "clip"}
        if v not in allowed:
            raise ValueError(f"media_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("framerate")
    @classmethod
    def validate_framerate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("framerate must be positive")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "VideoArchiveRequest":
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
        return self

    @model_validator(mode="after")
    def derive_wall_duration(self) -> "VideoArchiveRequest":
        """
        Auto-derive wall_duration_seconds from start/end if not explicitly set.
        """
        if self.wall_duration_seconds is None and self.start_time and self.end_time:
            delta = (self.end_time - self.start_time).total_seconds()
            object.__setattr__(self, "wall_duration_seconds", delta)
        return self

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def from_video_model(cls, video, media_url: str) -> "VideoArchiveRequest":
        """
        Build a VideoArchiveRequest directly from a Video model instance.
        Convenience factory so callers don't manually map fields.
        """
        camera   = video.camera
        entity   = camera.sensor_box.plant_entity
        tenant   = entity.entity_type.tenant

        manifest_payload = None
        if video.frame_manifest:
            manifest_payload = FrameManifestPayload(**video.frame_manifest)

        return cls(
            tenant_domain=tenant.domain,
            location=entity.entity_uid,
            sensor_box_location=camera.sensor_box.sensor_box_location,
            camera_id=str(camera.camera_id),
            video_id=video.video_id,
            media_id=video.video_id,
            media_name=video.video_name,
            media_url=media_url,
            media_type="video",
            media_format=video.video_format,
            media_size_bytes=video.video_size,
            start_time=video.start_time,
            end_time=video.end_time,
            framerate=video.framerate,
            video_duration_seconds=(
                video.duration.total_seconds() if video.duration else None
            ),
            manifest=manifest_payload,
            manifest_url=video.manifest_url,
            expires_at=video.expires_at,
            meta_info=video.meta_info or {},
        )