import re
import cv2
import logging
import subprocess
from PIL import Image
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from common_utils.media.image_utils import compress_image
from common_utils.media.frame_manifest import FrameManifest

logger = logging.getLogger(__name__)

def create_video_from_frames(output_filename, width, height, framerate=24):
    command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-f', 'rawvideo',
        '-s', f'{width}x{height}',  # Size of one frame
        '-pix_fmt', 'rgb24',
        '-r', str(framerate),  # Framerate
        '-i', '-',  # The input comes from a pipe
        '-an',  # No audio
        '-vcodec', 'libx264',  # Use H.264 codec
        '-preset', 'slow',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
        # '-b:v', '7000k',  # Bitrate
        '-movflags', '+faststart',  # Fast start for MP4 files
        output_filename
    ]

    # Open the FFmpeg process
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    return process

def convert_bgr_to_rgb(opencv_image):
    return cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)

def generate_video(
    frames: list, 
    framerate: float, 
    video_path: str, 
    video_id:str,
    frame_timestamps: list[datetime],
    scale: float = 1.0
) -> tuple[bool, Optional[FrameManifest]]:
    """
    Encode a list of OpenCV frames into an MP4 and produce a FrameManifest
    that maps every encoded frame to its real-world wall-clock timestamp.
 
    Parameters
    ----------
    frames:
        List of BGR OpenCV frames (numpy arrays), in capture order.
    framerate:
        Playback framerate for the encoded video (e.g. 24). This is NOT
        the capture rate — the encoded video will be shorter than real time.
    video_path:
        Output path for the MP4 file.
    video_id:
        Unique identifier for the video record (used in the manifest).
    frame_timestamps:
        Wall-clock UTC datetime for each frame. Must be the same length as
        `frames` and monotonically increasing. Must be timezone-aware.
    scale:
        Optional resize factor applied to each frame before encoding.
 
    Returns
    -------
    (success, manifest)
        success  — True if encoding completed without error.
        manifest — FrameManifest instance, or None on failure.
    """

    if not frames:
        logger.warning("generate_video: no frames provided for video_id=%s", video_id)('No data are found')
        return False, None
    
    if len(frames) != len(frame_timestamps):
        raise ValueError(
            f"frames ({len(frames)}) and frame_timestamps ({len(frame_timestamps)}) "
            "must have equal length"
        )

    h0, w0, _ = frames[0].shape
    h, w = int(h0 * scale), int(w0 * scale)

    manifest = FrameManifest(video_id=video_id, framerate=framerate)
    process = create_video_from_frames(video_path, width=w, height=h, framerate=framerate)

    try:
        for i, (frame, wall_time) in enumerate(zip(frames, frame_timestamps)):
            manifest.add_frame(frame_index=i, wall_time=wall_time)
            frame_resized = cv2.resize(frame, (w, h), interpolation=cv2.INTER_NEAREST)
            image = Image.fromarray(convert_bgr_to_rgb(frame_resized))
            process.stdin.write(image.tobytes())

        process.stdin.close()
        process.wait()

        if process.returncode != 0:
            logger.error(
                "generate_video: ffmpeg exited with code %d for video_id=%s",
                process.returncode, video_id
            )
            return False, None
    
    except Exception:
        logger.exception("generate_video: encoding failed for video_id=%s", video_id)
        try:
            process.stdin.close()
        except Exception:
            pass
        process.wait()
        return False, None
 
    logger.info(
        "generate_video: complete video_id=%s frames=%d "
        "wall_duration=%.1fs video_duration=%.1fs",
        video_id, manifest.frame_count,
        manifest.wall_duration_seconds or 0,
        manifest.video_duration_seconds or 0,
    )
    return True, manifest
    

def get_video_length(path):
    """
    Returns (hours, minutes, seconds) of the encoded video file duration.
    This is the video file duration — NOT the real-world recording span.
    Use FrameManifest.wall_duration_seconds for the real-world span.
    """
    process = subprocess.Popen(
        ['/usr/bin/ffmpeg', '-i', path], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT
    )
    stdout, stderr = process.communicate()
    matches = re.search(
        r"Duration:\s(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)", 
        stdout.decode('utf-8'), 
        re.DOTALL
    )

    if not matches:
        raise ValueError(f"Could not parse duration from ffmpeg output for: {path}")
    
    m = matches.groupdict()
    return float(m['hours']), float(m['minutes']), float(m['seconds'])


if __name__ == "__main__":
    from datetime import timedelta
    from common_utils.models.common import get_images
 
    now = datetime.now(tz=timezone.utc)
    from_time = now - timedelta(minutes=15)
    to_time = now
 
    images = get_images(from_time=from_time, to_time=to_time, camera_id=1)
 
    frames = []
    timestamps = []
    for image in images:
        frames.append(cv2.imread(image.image_file.path))
        timestamps.append(image.timestamp)  # wall-clock datetime from DB
 
    success, manifest = generate_video(
        frames=frames,
        frame_timestamps=timestamps,
        framerate=5,
        video_path="/media/videos/test.mp4",
        video_id="test-001",
    )
 
    if success and manifest:
        print(manifest)
        # Example query
        target = now - timedelta(minutes=1)
        pos = manifest.wall_time_to_video_position(target)
        if pos is not None: 
           print(f"Wall time {target.isoformat()} → video position {pos:.2f}s")