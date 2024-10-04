import os
import cv2
import uuid
import django
django.setup()

import time
import logging
import numpy as np
from celery import Celery
from celery import shared_task
from datetime import datetime, timedelta, timezone
from common_utils.media.video_utils import generate_video as gen_video
from common_utils.media.video_utils import get_video_length
from common_utils.models.common import get_images, get_video, generate_unique_id
from database.models import get_media_path
from django.conf import settings

@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, ignore_result=True,
             name='generate_video.tasks.video.core.generate_video')
def generate_video(self, **kwargs):
    try:
        now = datetime.now(tz=timezone.utc)
        from_time = now - timedelta(minutes=5)
        to_time = now
        
        images = get_images(
            from_time=from_time, to_time=to_time
        )
        
        if len(images) < 100:
            data = {
                "action": "ignored",
                "time": datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
                "results": f"Not enough images: {len(images)}"
            }
            
            return data
        
        frames = []
        for image in images:
            frames.append(
                cv2.imread(image.image_file.path)
            )
            
        video_name = f"video_{from_time.strftime('%Y-%m-%d_%H-%M-%S')}_{to_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        # video_path = f"{settings.MEDIA_ROOT}/{}"
        
        video_model = get_video(
            video_id=str(generate_unique_id()),
            video_name=video_name,
            timestamp=datetime.now(tz=timezone.utc),
            from_time=from_time,
            to_time=to_time,
            expires_at=(datetime.now(tz=timezone.utc) + timedelta(hours=6)).replace(tzinfo=timezone.utc), 
        )
        
        video_file = get_media_path(video_model, video_name)
        if not os.path.exists(
            os.path.dirname(
                f"{settings.MEDIA_ROOT}/{video_file}"
            )
        ):
            os.makedirs(
                os.path.dirname(
                    f"{settings.MEDIA_ROOT}/{video_file}"
                )
            )
            
        gen_video(
            frames=frames,
            video_path=f"{settings.MEDIA_ROOT}/{video_file}",
            framerate=5,
        )
        
        video_model.video_size = os.stat(f"{settings.MEDIA_ROOT}/{video_file}").st_size
        h, m, s = get_video_length(path=f"{settings.MEDIA_ROOT}/{video_file}")
        video_model.duration = timedelta(hours=h, minutes=m, seconds=s)
        video_model.video_file = video_file
        video_model.save()
        
        data = {
            "action": "done",
            "time": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        }
        
        return data
    except Exception as err:
        raise ValueError(f"Error generating video: {err}")