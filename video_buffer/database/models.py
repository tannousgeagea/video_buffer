from django.db import models

# Create your models here.
class Image(models.Model):
    image_id = models.CharField(max_length=255, unique=True)
    image_name = models.CharField(max_length=255)
    image_file = models.ImageField(upload_to='images/')
    image_size = models.IntegerField(null=True, blank=True)  # Size in bytes
    image_format = models.CharField(max_length=50, null=True, blank=True)  # JPEG, PNG, etc.
    timestamp = models.DateTimeField()  # Time of capture
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Expiration time for cleanup
    source = models.CharField(max_length=255, null=True, blank=True)  # Optional source of the image

    class Meta:
        db_table = 'image'
        verbose_name = 'Image'
        verbose_name_plural = "Images"

    def __str__(self) -> str:
        return f"Image: {self.image_id} created at {self.created_at}"

    
class Video(models.Model):
    video_id = models.CharField(max_length=255, unique=True)
    video_name = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')  # Changed to FileField for videos
    video_size = models.IntegerField(null=True, blank=True)  # Size in bytes
    video_format = models.CharField(max_length=50, null=True, blank=True)  # MP4, AVI, etc.
    timestamp = models.DateTimeField()  # Time when video generation started
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)  # Start time of the video content
    end_time = models.DateTimeField(null=True, blank=True)  # End time of the video content
    duration = models.DurationField(null=True, blank=True)  # Duration of the video
    meta_info = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Expiration time for cleanup

    class Meta:
        db_table = 'video'
        verbose_name = 'Video'
        verbose_name_plural = "Videos"

    def __str__(self) -> str:
        return f"Video: {self.video_id} created at {self.created_at}"

