import os
import cv2
import uuid
import django
django.setup()

import time
import logging
import subprocess
import numpy as np
from celery import Celery
from celery import shared_task
from django.core.management import call_command
from datetime import datetime, timedelta, timezone

@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, ignore_result=True,
             name='cleanup.tasks.cleanup.core.cleanup_expired_files')
def cleanup_expired_files(self, **kwargs):
    try:
        call_command("cleanup_expired_files")
        
    except Exception as err:
        raise ValueError(f"Error cleaning up expired files: {err}")