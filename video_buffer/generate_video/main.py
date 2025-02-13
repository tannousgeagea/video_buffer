

from generate_video.config.celery_utils import create_celery
from generate_video.tasks.video.core import generate_video_for_available_source


celery = create_celery()
celery.autodiscover_tasks(['generate_video.tasks'])