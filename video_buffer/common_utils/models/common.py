import django
django.setup()
import logging

import os
import cv2
import numpy as np
from typing import Optional, Dict
from datetime import datetime, timezone
from django.conf import settings

from database.models import (
    Image, Video, get_image_path
)


def save_image(
    cv_image:np.ndarray,
    image_id:str,
    image_name:str,
    timestamp:datetime,
    expires_at:datetime,
    image_size:Optional[str]=None,
    image_format:Optional[str]=None,
    meta_info:Optional[Dict]=None,
    source:Optional[str]=None,
):
    try:
        
        image = Image(
            image_id=image_id,
            image_name=image_name,
            timestamp=timestamp.replace(tzinfo=timezone.utc),
            expires_at=expires_at.replace(tzinfo=timezone.utc),
            image_size=image_size,
            image_format=image_format,
            meta_info=meta_info,
            source=source
        )
        
        image_file = get_image_path(image, filename=image_name)
        image_path = f"{settings.MEDIA_ROOT}/{image_file}"
        
        print(image_path)
        if not os.path.exists(
            os.path.dirname(image_path)
        ):
            os.makedirs(
                os.path.dirname(image_path)
            )
            
        
        cv2.imwrite(image_path, cv_image)
        image.image_file = image_file
        image.save()
        
    except Exception as err:
        print(err)
        logging.error(f"Error saving image: {err}")
        

def get_images(from_time:datetime, to_time:datetime):
    return Image.objects.filter(
        timestamp__gte=from_time, 
        timestamp__lt=to_time
        ).order_by('timestamp')
    
def get_video(
    video_id:str,
    video_name:str,
    timestamp:datetime,
    from_time:datetime,
    to_time:datetime,
    expires_at:datetime,
):
    try:
        video = Video(
            video_id=video_id,
            video_name=video_name,
            timestamp=timestamp.replace(tzinfo=timezone.utc),
            start_time=from_time.replace(tzinfo=timezone.utc),
            end_time=to_time.replace(tzinfo=timezone.utc),
            expires_at=expires_at.replace(tzinfo=timezone.utc),
        )
        
        return video
        
    except Exception as err:
        logging.error(f"Error saving image: {err}")
        return None