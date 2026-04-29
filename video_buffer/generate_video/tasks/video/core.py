import os
import cv2
import pytz
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
from django.db import close_old_connections

from common_utils.media.edge_to_cloud import sync
from media.services.recording_service import VideoRecordingService
from common_utils.schemas.video_archive_request import VideoArchiveRequest

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, ignore_result=True,
             name='generate_video.tasks.video.core.generate_video')
def generate_video(self, camera_id, **kwargs):
    close_old_connections()  # Ensure we don't have stale DB connections in the worker process
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
        
        # ------------------------------------------------------------------
        # Tenant / entity context
        # ------------------------------------------------------------------
        camera     = images.first().camera
        tenant     = camera.sensor_box.plant_entity.entity_type.tenant
        tenant_tz  = pytz.timezone(tenant.timezone)
        entity     = camera.sensor_box.plant_entity

        # ------------------------------------------------------------------
        # Annotate frames — preserve timestamps on each frame as before
        # ------------------------------------------------------------------
        annotated_frames = []
        for image in images:
            timestamp_str = (
                image.timestamp.astimezone(tenant_tz).strftime(DATETIME_FORMAT)
                + f" | {entity.description}"
            )
            annotator = Annotator(im=cv2.imread(image.image_file.path))
            annotator.add_legendV2(
                legend_text=timestamp_str,
                font=1,
                font_scale=1,
                font_thickness=1,
                pos=os.getenv("TIMESTAMP_POSITION", "top-left"),
                bg_color=(
                    int(os.getenv("TIMESTAMP_BG_COLOR_R", 0)),
                    int(os.getenv("TIMESTAMP_BG_COLOR_G", 0)),
                    int(os.getenv("TIMESTAMP_BG_COLOR_B", 0)),
                ),
                alpha=float(os.getenv("TIMESTAMP_BG_ALPHA", 0.6)),
            )
            annotated_frames.append(annotator.im.data)

        # ------------------------------------------------------------------
        # Build video name (same convention as before)
        # ------------------------------------------------------------------
        video_name = (
            f"{tenant.tenant_name}_"
            f"{entity.entity_uid}_"
            f"{camera.camera_position}_"
            f"{from_time.strftime('%Y-%m-%d_%H-%M-%S')}_"
            f"{to_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        )


        # ------------------------------------------------------------------
        # Delegate to VideoRecordingService
        # Wall-clock timestamps come directly from the image queryset —
        # this is the key link between real time and encoded frame index.
        # ------------------------------------------------------------------
        service = VideoRecordingService()
        video_model = service.create_video_from_images(
            images=list(images),
            annotated_frames=annotated_frames,   # pass pre-annotated frames
            camera=camera,
            framerate=3,
            video_name=video_name,
            from_time=from_time,
            to_time=to_time,
            tenant=tenant,
            expires_at=(now + timedelta(hours=6)).replace(tzinfo=timezone.utc),
        )
 
        if video_model is None:
            raise ValueError("VideoRecordingService returned None — encoding failed")

        # for image in images:

        #     timestamp_str = image.timestamp.astimezone(tenant_tz).strftime(DATETIME_FORMAT) + f" | {entity.description}"
        #     annotator = Annotator(
        #             im=cv2.imread(image.image_file.path)
        #         )
            
        #     bg_color = (
        #         int(os.getenv("TIMESTAMP_BG_COLOR_R", 0)),
        #         int(os.getenv("TIMESTAMP_BG_COLOR_G", 0)),
        #         int(os.getenv("TIMESTAMP_BG_COLOR_B", 0)),
        #     )
        #     annotator.add_legendV2(
        #             legend_text=timestamp_str, 
        #             font=1, 
        #             font_scale=1, 
        #             font_thickness=1,
        #             pos=os.getenv("TIMESTAMP_POSITION", "top-left"),
        #             bg_color=bg_color,
        #             alpha=os.getenv("TIMESTAMP_BG_ALPHA", 0.6),
        #         )
            
        #     frames.append(
        #         annotator.im.data
        #     )
        #     frame_timestamps.append(image.timestamp)
            
        # video_name = (
        #     f"{tenant.tenant_name}_"
        #     f"{entity.entity_uid}_"
        #     f"{camera.camera_position}_"
        #     f"{from_time.strftime('%Y-%m-%d_%H-%M-%S')}_{to_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        # )
    
        # video_model = get_video(
        #     video_id=str(generate_unique_id()),
        #     video_name=video_name,
        #     timestamp=datetime.now(tz=timezone.utc),
        #     from_time=from_time,
        #     to_time=to_time,
        #     expires_at=(datetime.now(tz=timezone.utc) + timedelta(hours=6)).replace(tzinfo=timezone.utc),
        #     camera_id=camera_id,
        # )
        
        # video_file = get_media_path(video_model, video_name)
        # if not os.path.exists(
        #     os.path.dirname(
        #         f"{settings.MEDIA_ROOT}/{video_file}"
        #     )
        # ):
        #     os.makedirs(
        #         os.path.dirname(
        #             f"{settings.MEDIA_ROOT}/{video_file}"
        #         )
        #     )
            
        # success, manifest = gen_video(
        #     frames=frames,
        #     video_path=f"{settings.MEDIA_ROOT}/{video_file}",
        #     video_id=video_model.video_id,
        #     frame_timestamps=frame_timestamps,
        #     framerate=3,
        # )
        
        # video_model.video_size = os.stat(f"{settings.MEDIA_ROOT}/{video_file}").st_size
        # h, m, s = get_video_length(path=f"{settings.MEDIA_ROOT}/{video_file}")
        # video_model.duration = timedelta(hours=h, minutes=m, seconds=s)
        # video_model.video_file = video_file
        # video_model.save()
        
        
        # ------------------------------------------------------------------
        # Sync to cloud archive
        # ------------------------------------------------------------------
        archive_request = VideoArchiveRequest.from_video_model(
            video=video_model,
            media_url=video_model.video_file.url,
        )

        # logging.info("Archive Data %s", archive_request.model_dump(mode='json'))
        sync(
            url=f"http://{os.getenv('EDGE_CLOUD_SYNC_HOST', '0.0.0.0')}:{os.getenv('EDGE_CLOUD_SYNC_PORT', '27092')}/api/v2/event/media",
            media_file=f"{video_model.video_file.path}",
            params={   
                'event_id': video_model.video_id,
                'source_id': "video-archive",
                'blob_name': os.path.basename(video_model.video_file.path),
                'container_name': "video_archive",
                'target': "video_archive",
                'data': json.dumps(archive_request.model_dump(mode='json')),
                # 'data': json.dumps(
                #     {
                #         "tenant_domain": tenant.domain,
                #         "location": entity.entity_uid,
                #         "sensor_box_location": camera.sensor_box.sensor_box_location,
                #         "camera_id": camera.camera_id,
                #         "video_id": video_model.video_id,
                #         "media_id": video_model.video_id,
                #         "media_name": video_model.video_name,
                #         "media_url": video_model.video_file.url,
                #         "media_type": "video",
                #         "start_time": video_model.start_time.strftime(DATETIME_FORMAT),
                #         "end_time": video_model.end_time.strftime(DATETIME_FORMAT),
                #     }
                # )
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
    close_old_connections()  # Ensure we don't have stale DB connections in the worker process
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