import re
import cv2
import logging
import subprocess
from PIL import Image
from decimal import Decimal
from common_utils.media.image_utils import compress_image

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

def generate_video(frames, framerate, video_path, scale=1.):
    success = False
    if not frames:
        print('No data are found')
        return success
    
    h0, w0, _ = frames[0].shape
    h, w = int(h0 * scale), int(w0 * scale)
    process = create_video_from_frames(video_path, width=w, height=h, framerate=framerate)
    for i, frame in enumerate(frames):
        frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_NEAREST)
        image = Image.fromarray(convert_bgr_to_rgb(frame))
        process.stdin.write(image.tobytes())

    process.stdin.close()
    process.wait()
    

def get_video_length(path):
    process = subprocess.Popen(['/usr/bin/ffmpeg', '-i', path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = process.communicate()
    matches = re.search(r"Duration:\s(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)", stdout.decode('utf-8'), re.DOTALL).groupdict()

    hours = float(matches['hours'])
    minutes = float(matches['minutes'])
    seconds =float(matches['seconds'])

    return hours, minutes, seconds


if __name__ == "__main__":
    from datetime import datetime, timezone, timedelta
    from common_utils.models.common import get_images
    now = datetime.now(tz=timezone.utc)
    from_time = now - timedelta(minutes=15)
    to_time = now
    
    images = get_images(
        from_time=from_time, to_time=to_time, camera_id=1
    )

    frames = []
    for image in images:
        frames.append(cv2.imread(image.image_file.path))

    generate_video(
    frames=frames,
    video_path=f"/media/videos/test.mp4",
    framerate=5,
)