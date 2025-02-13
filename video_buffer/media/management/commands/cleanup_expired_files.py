import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from database.models import Image, Video

class Command(BaseCommand):
    help = 'Cleans up expired images and videos from storage and database'

    def handle(self, *args, **kwargs):
        # Get current time
        now = timezone.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Clean up expired images
        expired_images = Image.objects.filter(expires_at__lte=now)
        image_count = expired_images.count()
        for image in expired_images:
            if os.path.exists(image.image_file.path):
                self.stdout.write(f"{now_str}: Deleting image file: {image.image_file.path}")
                os.remove(image.image_file.path)  # Delete the file from storage
            image.delete()  # Remove the record from the database

        # Clean up expired videos
        expired_videos = Video.objects.filter(expires_at__lte=now)
        video_count = expired_videos.count()
        for video in expired_videos:
            if os.path.exists(video.video_file.path):
                self.stdout.write(f"{now_str}: Deleting video file: {video.video_file.path}")
                os.remove(video.video_file.path)  # Delete the file from storage
            video.delete()  # Remove the record from the database

        # Output the result
        self.stdout.write(self.style.SUCCESS(f"{now_str}: Deleted {image_count} expired images and {video_count} expired videos."))
