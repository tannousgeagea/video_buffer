"""
Frame Manifest
==============
Maps every encoded video frame to its real-world wall-clock timestamp.

Because videos are generated at a higher playback framerate than the capture
rate, the video duration does not correspond to real time. This manifest is
the authoritative index that resolves:
    wall_time  → video position (seconds)
    video pos  → wall_time

Lifecycle
---------
1. Built incrementally during frame collection  (add_frame)
2. Serialised to dict/JSON before upload        (to_dict / to_json)
3. Persisted as both JSONField and cloud sidecar
4. Deserialised at query time                   (from_dict / from_json)
5. Queried bidirectionally                      (wall_time_to_video_position /
                                                 video_position_to_wall_time)
"""

from __future__ import annotations

import json
import bisect
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FrameEntry:
    frame_index: int
    wall_ts: float      # UTC unix timestamp (float, sub-second precision)
    wall_ts_iso: str    # ISO-8601 string — human-readable / external consumers


@dataclass
class ManifestQueryResult:
    frame_index: int
    wall_time: datetime
    video_position_seconds: float
    interpolated: bool  # True when result is between two recorded frames


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class FrameManifest:
    """
    Immutable once built. Thread-safe for reads.
    """

    def __init__(self, video_id: str, framerate: float) -> None:
        if framerate <= 0:
            raise ValueError(f"framerate must be positive, got {framerate}")
        self.video_id: str = video_id
        self.framerate: float = framerate
        self.entries: list[FrameEntry] = []

        # Sorted index caches — built lazily on first query
        self._wall_ts_index: list[float] = []
        self._frame_index_index: list[int] = []
        self._index_dirty: bool = True

    # ------------------------------------------------------------------
    # Build phase
    # ------------------------------------------------------------------

    def add_frame(self, frame_index: int, wall_time: datetime) -> None:
        """
        Register a frame. Must be called in frame_index order.
        wall_time must be timezone-aware.
        """
        if wall_time.tzinfo is None:
            raise ValueError("wall_time must be timezone-aware (use UTC)")
        if self.entries and frame_index <= self.entries[-1].frame_index:
            raise ValueError(
                f"frame_index must be monotonically increasing. "
                f"Got {frame_index}, last was {self.entries[-1].frame_index}"
            )
        ts = wall_time.timestamp()
        self.entries.append(FrameEntry(
            frame_index=frame_index,
            wall_ts=ts,
            wall_ts_iso=wall_time.isoformat(),
        ))
        self._index_dirty = True

    # ------------------------------------------------------------------
    # Internal index
    # ------------------------------------------------------------------

    def _rebuild_index(self) -> None:
        self._wall_ts_index = [e.wall_ts for e in self.entries]
        self._frame_index_index = [e.frame_index for e in self.entries]
        self._index_dirty = False

    def _ensure_index(self) -> None:
        if self._index_dirty:
            self._rebuild_index()

    # ------------------------------------------------------------------
    # Query: wall time → video position
    # ------------------------------------------------------------------

    def wall_time_to_video_position(self, wall_time: datetime) -> Optional[float]:
        """
        Returns the video position in seconds for a given wall-clock time,
        or None if the time is outside the recorded range.

        Uses linear interpolation between surrounding frames.
        """
        if not self.entries:
            return None
        if wall_time.tzinfo is None:
            raise ValueError("wall_time must be timezone-aware")

        self._ensure_index()
        target_ts = wall_time.timestamp()

        first_ts = self._wall_ts_index[0]
        last_ts = self._wall_ts_index[-1]

        if target_ts < first_ts or target_ts > last_ts:
            logger.debug(
                "wall_time_to_video_position: %s is outside manifest range "
                "[%s, %s]", wall_time.isoformat(),
                self.entries[0].wall_ts_iso, self.entries[-1].wall_ts_iso
            )
            return None

        idx = bisect.bisect_left(self._wall_ts_index, target_ts)
        idx = min(max(idx, 1), len(self.entries) - 1)

        before = self.entries[idx - 1]
        after = self.entries[idx]
        span_ts = after.wall_ts - before.wall_ts

        if span_ts > 0:
            frac = (target_ts - before.wall_ts) / span_ts
            interpolated_frame = before.frame_index + frac * (after.frame_index - before.frame_index)
        else:
            interpolated_frame = float(before.frame_index)

        return interpolated_frame / self.framerate

    # ------------------------------------------------------------------
    # Query: video position → wall time
    # ------------------------------------------------------------------

    def video_position_to_wall_time(self, video_seconds: float) -> Optional[datetime]:
        """
        Returns the wall-clock time for a given video position (seconds),
        or None if the position is outside the encoded range.

        Uses linear interpolation between surrounding frames.
        """
        if not self.entries:
            return None

        self._ensure_index()
        target_frame = video_seconds * self.framerate

        first_frame = self._frame_index_index[0]
        last_frame = self._frame_index_index[-1]

        if target_frame < first_frame or target_frame > last_frame:
            logger.debug(
                "video_position_to_wall_time: frame %.2f is outside manifest range "
                "[%d, %d]", target_frame, first_frame, last_frame
            )
            return None

        idx = bisect.bisect_left(self._frame_index_index, target_frame)
        idx = min(max(idx, 1), len(self.entries) - 1)

        before = self.entries[idx - 1]
        after = self.entries[idx]
        span_frames = after.frame_index - before.frame_index

        if span_frames > 0:
            frac = (target_frame - before.frame_index) / span_frames
            interpolated_ts = before.wall_ts + frac * (after.wall_ts - before.wall_ts)
        else:
            interpolated_ts = before.wall_ts

        return datetime.fromtimestamp(interpolated_ts, tz=timezone.utc)

    # ------------------------------------------------------------------
    # Rich query: returns full context
    # ------------------------------------------------------------------

    def query(self, wall_time: datetime) -> Optional[ManifestQueryResult]:
        """
        Full query returning both video position and nearest frame metadata.
        Returns None if wall_time is out of range.
        """
        video_pos = self.wall_time_to_video_position(wall_time)
        if video_pos is None:
            return None

        frame_index = round(video_pos * self.framerate)
        resolved_wall_time = self.video_position_to_wall_time(video_pos)

        return ManifestQueryResult(
            frame_index=frame_index,
            wall_time=resolved_wall_time,
            video_position_seconds=video_pos,
            interpolated=True,  # always interpolated unless exact hit
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        return len(self.entries)

    @property
    def wall_duration_seconds(self) -> Optional[float]:
        """Real-world time span covered by this manifest."""
        if len(self.entries) < 2:
            return None
        return self.entries[-1].wall_ts - self.entries[0].wall_ts

    @property
    def video_duration_seconds(self) -> Optional[float]:
        """Encoded video duration based on frame count and framerate."""
        if not self.entries:
            return None
        return self.entries[-1].frame_index / self.framerate

    @property
    def start_time(self) -> Optional[datetime]:
        if not self.entries:
            return None
        return datetime.fromtimestamp(self.entries[0].wall_ts, tz=timezone.utc)

    @property
    def end_time(self) -> Optional[datetime]:
        if not self.entries:
            return None
        return datetime.fromtimestamp(self.entries[-1].wall_ts, tz=timezone.utc)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "framerate": self.framerate,
            "frame_count": len(self.entries),
            "start_time_iso": self.start_time.isoformat() if self.start_time else None,
            "end_time_iso": self.end_time.isoformat() if self.end_time else None,
            "wall_duration_seconds": self.wall_duration_seconds,
            "video_duration_seconds": self.video_duration_seconds,
            "entries": [asdict(e) for e in self.entries],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "FrameManifest":
        manifest = cls(video_id=data["video_id"], framerate=data["framerate"])
        manifest.entries = [FrameEntry(**e) for e in data["entries"]]
        manifest._index_dirty = True
        return manifest

    @classmethod
    def from_json(cls, raw: str) -> "FrameManifest":
        return cls.from_dict(json.loads(raw))

    def __repr__(self) -> str:
        return (
            f"<FrameManifest video_id={self.video_id!r} "
            f"frames={self.frame_count} "
            f"wall_duration={self.wall_duration_seconds:.1f}s "
            f"video_duration={self.video_duration_seconds:.1f}s>"
        )