

from cleanup.config.celery_utils import create_celery
from cleanup.tasks.cleanup.core import cleanup_expired_files


celery = create_celery()
celery.autodiscover_tasks(['cleanup.tasks'])