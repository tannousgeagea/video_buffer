import os
import cv2
import uuid
import django
django.setup()
import json
import time
import logging
import numpy as np
from celery import Celery
from celery import shared_task
from datetime import datetime, timedelta, timezone
from common_utils.media.video_utils import generate_video as gen_video
from common_utils.media.video_utils import get_video_length
from common_utils.annotate.core import Annotator
from common_utils.models.common import get_images, get_video, generate_unique_id
from configure.client import ConfigManager
from media.models import get_media_path
from django.conf import settings

from common_utils.media.edge_to_cloud import sync

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, ignore_result=True,
             name='generate_video.tasks.video.core.generate_video')
def generate_video(self, camera_id, **kwargs):
    try:
        now = datetime.now(tz=timezone.utc)
        from_time = now - timedelta(minutes=15)
        to_time = now
        
        images = get_images(
            from_time=from_time, to_time=to_time, camera_id=camera_id
        )

        if len(images) < 10:
            data = {
                "action": "ignored",
                "time": datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
                "results": f"Not enough images: {len(images)}"
            }
            
            return data

        frames = []
        camera = images.first().camera
        tenant = camera.sensor_box.plant_entity.entity_type.tenant
        entity = camera.sensor_box.plant_entity
        for image in images:
            timestamp_str = (image.timestamp + timedelta(hours=2)).strftime(DATETIME_FORMAT) + f" | {entity.description}"
            annotator = Annotator(
                    im=cv2.imread(image.image_file.path)
                )
            annotator.add_legend(
                    legend_text=timestamp_str, font=1, font_scale=1, font_thickness=1,
                )
            frames.append(
                annotator.im.data
            )
            
        video_name = (
            f"{tenant.tenant_name}_"
            f"{entity.entity_uid}_"
            f"{camera.camera_position}_"
            f"{from_time.strftime('%Y-%m-%d_%H-%M-%S')}_{to_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        )
    
        video_model = get_video(
            video_id=str(generate_unique_id()),
            video_name=video_name,
            timestamp=datetime.now(tz=timezone.utc),
            from_time=from_time,
            to_time=to_time,
            expires_at=(datetime.now(tz=timezone.utc) + timedelta(hours=6)).replace(tzinfo=timezone.utc),
            camera_id=camera_id,
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
            framerate=3,
        )
        
        video_model.video_size = os.stat(f"{settings.MEDIA_ROOT}/{video_file}").st_size
        h, m, s = get_video_length(path=f"{settings.MEDIA_ROOT}/{video_file}")
        video_model.duration = timedelta(hours=h, minutes=m, seconds=s)
        video_model.video_file = video_file
        video_model.save()
        

        sync(
            url=f"http://{os.getenv('EDGE_CLOUD_SYNC_HOST', '0.0.0.0')}:{os.getenv('EDGE_CLOUD_SYNC_PORT', '27092')}/api/v1/event/media",
            media_file=f"{video_model.video_file.path}",
            params={   
                'event_id': video_model.video_id,
                'source_id': "video-archive",
                'blob_name': os.path.basename(video_model.video_file.path),
                'container_name': "video_archive",
                'target': "video_archive",
                'data': json.dumps(
                    {
                        "tenant_domain": tenant.domain,
                        "location": entity.entity_uid,
                        "sensor_box_location": camera.sensor_box.sensor_box_location,
                        "camera_id": camera.camera_id,
                        "video_id": video_model.video_id,
                        "media_id": video_model.video_id,
                        "media_name": video_model.video_name,
                        "media_url": video_model.video_file.url,
                        "media_type": "video",
                        "start_time": video_model.start_time.strftime(DATETIME_FORMAT),
                        "end_time": video_model.end_time.strftime(DATETIME_FORMAT),
                    }
                )
            },
        )

        data = {
            "action": "done",
            "time": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        }
        
        return data
    except Exception as err:
        raise ValueError(f"Error generating video: {err}")


@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, ignore_result=True,
             name='generate_video.tasks.video.core.generate_video_for_available_source')
def generate_video_for_available_source(self, **kwargs):
    try:
        active_sources = ConfigManager.get_active_data_sources()
        for source in active_sources:
            camera_info = source.get("camera")
            if not camera_info:
                logging.warning("Camera Info not found!")
                return
            
            camera_id = camera_info.get('id')
            if not camera_id:
                logging.warning(f"Camera ID not found! Camera Info Provided: {camera_info}")
            
            generate_video.apply_async(args=(camera_id,))

    except Exception as err:
        raise ValueError(f"Error generating video fow available source: {err}")