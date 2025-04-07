from django.db import models
from tenants.models import (
    SensorBox, Camera
)

def get_image_path(instance, filename):
    return f"images/{instance.camera_id}/{filename}"

def get_media_path(instance, filename):
    return f"videos/{filename}"

# Create your models here.
class Image(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name="images")
    image_id = models.CharField(max_length=255, unique=True)
    image_name = models.CharField(max_length=255)
    image_file = models.ImageField(upload_to=get_image_path)
    image_size = models.IntegerField(null=True, blank=True)
    image_format = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        db_table = 'image'
        verbose_name = 'Image'
        verbose_name_plural = "Images"

    def __str__(self) -> str:
        return f"Image: {self.image_id} created at {self.created_at}"

    
class Video(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos")
    video_id = models.CharField(max_length=255, unique=True)
    video_name = models.CharField(max_length=255)
    video_file = models.FileField(upload_to=get_media_path)
    video_size = models.IntegerField(null=True, blank=True)
    video_format = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    images_used = models.ManyToManyField(Image, related_name="videos")

    class Meta:
        db_table = 'video'
        verbose_name = 'Video'
        verbose_name_plural = "Videos"

    def __str__(self) -> str:
        return f"Video {self.video_id} ({self.start_time} - {self.end_time})"

