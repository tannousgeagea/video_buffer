import os
import celery
from functools import lru_cache
from kombu import Queue
from cleanup import tasks
from celery.schedules import crontab

def route_task(name, args, kwargs, options, task=None, **kw):
    print(name)
    if ":" in name:
        queue, _ = name.split(":")
        return {"queue": queue}
    return {"queue": "celery"}


RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", '5672')

class BaseConfig:
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", f"amqp://guest:guest@{RABBITMQ_HOST}:{RABBITMQ_PORT}//")
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "rpc://")

    CELERY_TASK_QUEUES: list = (
        # default queue
        Queue("celery"),
        # custom queue
    )

    CELERY_TASK_ROUTES = (route_task,)
    ACCEPT_CONTENT = ['json', 'pickle']
    TASK_SERIALIZE = 'pickle'
    RESULT_SERIALIZE = 'pickle'
    TIMEZONE = 'UTC'
    ENABLE_UTC = True
    
    CELERY_BEAT_SCHEDULE = {
        'clean-up-expired-files': {
            'task': 'cleanup.tasks.cleanup.core.cleanup_expired_files',
            'schedule': crontab('*/5'),
            'options': {
                'queue': f'{os.getenv("CLEANUP_QUEUE_NAME", "celery")}'
            },
        },
    }

class DevelopmentConfig(BaseConfig):
    pass


@lru_cache()
def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
    }
    config_name = os.environ.get("CELERY_CONFIG", "development")
    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()