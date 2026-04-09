

import django
django.setup()

from media.models import Video
from common_utils.media.frame_manifest import FrameManifest
from datetime import datetime, timezone

def main():
    
    try:
        video = Video.objects.get(video_id=50075127)
    except Video.DoesNotExists:
        raise ValueError(f"Video not found")
    
    manifest = video.get_manifest()

    ts = datetime(year=2026, month=4, day=9, hour=14, minute=34, second=7).replace(tzinfo=timezone.utc)
    pos = manifest.wall_time_to_video_position(ts)

    print(pos)

if __name__ == "__main__":
    main()
