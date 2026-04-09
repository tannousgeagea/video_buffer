"""
Tests for FrameManifest — bidirectional time lookup, serialisation, edge cases.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common_utils.media.frame_manifest import FrameManifest, FrameEntry


BASE_TIME = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)


def make_manifest(
    n_frames: int = 10,
    interval_seconds: float = 12.0,
    framerate: float = 24.0,
    video_id: str = "test-vid",
) -> FrameManifest:
    """Build a manifest with evenly-spaced wall-clock timestamps."""
    m = FrameManifest(video_id=video_id, framerate=framerate)
    for i in range(n_frames):
        wall = BASE_TIME + timedelta(seconds=i * interval_seconds)
        m.add_frame(frame_index=i, wall_time=wall)
    return m


class TestBuild:
    def test_basic_build(self):
        m = make_manifest(n_frames=5)
        assert m.frame_count == 5

    def test_requires_monotonic_frame_index(self):
        m = FrameManifest(video_id="x", framerate=24)
        m.add_frame(0, BASE_TIME)
        m.add_frame(1, BASE_TIME + timedelta(seconds=1))
        with pytest.raises(ValueError, match="monotonically increasing"):
            m.add_frame(1, BASE_TIME + timedelta(seconds=2))  # duplicate index

    def test_requires_aware_datetime(self):
        m = FrameManifest(video_id="x", framerate=24)
        with pytest.raises(ValueError, match="timezone-aware"):
            m.add_frame(0, datetime(2024, 1, 1))  # naive

    def test_invalid_framerate(self):
        with pytest.raises(ValueError, match="framerate must be positive"):
            FrameManifest(video_id="x", framerate=0)


class TestWallTimeToVideoPosition:
    def test_exact_first_frame(self):
        m = make_manifest(n_frames=10, interval_seconds=10.0, framerate=24.0)
        pos = m.wall_time_to_video_position(BASE_TIME)
        assert pos == pytest.approx(0.0)

    def test_exact_last_frame(self):
        m = make_manifest(n_frames=10, interval_seconds=10.0, framerate=24.0)
        last_time = BASE_TIME + timedelta(seconds=9 * 10.0)
        pos = m.wall_time_to_video_position(last_time)
        # last frame_index=9, video pos = 9/24
        assert pos == pytest.approx(9 / 24.0)

    def test_midpoint_interpolation(self):
        m = make_manifest(n_frames=2, interval_seconds=10.0, framerate=24.0)
        # Halfway between frame 0 (wall=BASE) and frame 1 (wall=BASE+10s)
        midpoint = BASE_TIME + timedelta(seconds=5.0)
        pos = m.wall_time_to_video_position(midpoint)
        # frame 0.5 → 0.5/24
        assert pos == pytest.approx(0.5 / 24.0, rel=1e-4)

    def test_out_of_range_returns_none(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0)
        before = BASE_TIME - timedelta(seconds=1)
        after  = BASE_TIME + timedelta(seconds=5 * 10.0 + 1)
        assert m.wall_time_to_video_position(before) is None
        assert m.wall_time_to_video_position(after) is None

    def test_requires_aware_datetime(self):
        m = make_manifest(n_frames=3)
        with pytest.raises(ValueError):
            m.wall_time_to_video_position(datetime(2024, 1, 15, 11, 0, 0))


class TestVideoPositionToWallTime:
    def test_position_zero(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0, framerate=24.0)
        wt = m.video_position_to_wall_time(0.0)
        assert wt == BASE_TIME

    def test_last_frame_position(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0, framerate=24.0)
        last_pos = 4 / 24.0
        wt = m.video_position_to_wall_time(last_pos)
        expected = BASE_TIME + timedelta(seconds=4 * 10.0)
        assert abs((wt - expected).total_seconds()) < 0.01

    def test_interpolated_position(self):
        m = make_manifest(n_frames=2, interval_seconds=10.0, framerate=24.0)
        # video pos 0.5/24 → frame 0.5 → halfway between frame 0 and 1
        pos = 0.5 / 24.0
        wt = m.video_position_to_wall_time(pos)
        expected = BASE_TIME + timedelta(seconds=5.0)
        assert abs((wt - expected).total_seconds()) < 0.01

    def test_out_of_range_returns_none(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0, framerate=24.0)
        assert m.video_position_to_wall_time(-0.1) is None
        assert m.video_position_to_wall_time(1000.0) is None


class TestRoundTrip:
    def test_wall_to_video_to_wall(self):
        m = make_manifest(n_frames=20, interval_seconds=8.0, framerate=24.0)
        original = BASE_TIME + timedelta(seconds=50.0)
        pos = m.wall_time_to_video_position(original)
        recovered = m.video_position_to_wall_time(pos)
        assert abs((recovered - original).total_seconds()) < 0.1

    def test_video_to_wall_to_video(self):
        m = make_manifest(n_frames=20, interval_seconds=8.0, framerate=24.0)
        original_pos = 5 / 24.0
        wt = m.video_position_to_wall_time(original_pos)
        recovered_pos = m.wall_time_to_video_position(wt)
        assert abs(recovered_pos - original_pos) < 0.001


class TestSerialisation:
    def test_to_dict_keys(self):
        m = make_manifest(n_frames=3)
        d = m.to_dict()
        assert "video_id" in d
        assert "framerate" in d
        assert "frame_count" in d
        assert "entries" in d
        assert d["frame_count"] == 3

    def test_round_trip_dict(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0, framerate=24.0)
        d = m.to_dict()
        m2 = FrameManifest.from_dict(d)
        assert m2.frame_count == m.frame_count
        assert m2.framerate == m.framerate
        assert m2.entries[0].wall_ts == m.entries[0].wall_ts

    def test_round_trip_json(self):
        m = make_manifest(n_frames=5)
        raw = m.to_json()
        m2 = FrameManifest.from_json(raw)
        # Queries should still work after deserialisation
        pos = m2.wall_time_to_video_position(BASE_TIME)
        assert pos == pytest.approx(0.0)

    def test_queries_work_after_deserialisation(self):
        m = make_manifest(n_frames=10, interval_seconds=12.0, framerate=5.0)
        m2 = FrameManifest.from_dict(m.to_dict())
        target = BASE_TIME + timedelta(seconds=60.0)
        pos_original = m.wall_time_to_video_position(target)
        pos_restored  = m2.wall_time_to_video_position(target)
        assert pos_original == pytest.approx(pos_restored)


class TestProperties:
    def test_wall_duration(self):
        m = make_manifest(n_frames=10, interval_seconds=10.0)
        # 0..9 frames × 10s = 90s
        assert m.wall_duration_seconds == pytest.approx(90.0)

    def test_video_duration(self):
        m = make_manifest(n_frames=10, interval_seconds=10.0, framerate=24.0)
        # last frame_index=9, 9/24
        assert m.video_duration_seconds == pytest.approx(9 / 24.0)

    def test_start_end_time(self):
        m = make_manifest(n_frames=5, interval_seconds=10.0)
        assert m.start_time == BASE_TIME
        assert m.end_time == BASE_TIME + timedelta(seconds=40.0)

    def test_empty_manifest_properties(self):
        m = FrameManifest(video_id="x", framerate=24)
        assert m.frame_count == 0
        assert m.wall_duration_seconds is None
        assert m.video_duration_seconds is None
        assert m.start_time is None
        assert m.end_time is None


if __name__ == "__main__":
    pytest.main([__file__])