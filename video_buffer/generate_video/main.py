

from generate_video.config.celery_utils import create_celery
from generate_video.tasks.video.core import generate_video


celery = create_celery()
celery.autodiscover_tasks(['generate_video.tasks'])