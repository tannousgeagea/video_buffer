from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    Image,
    Video
)

# Register your models here.
@admin.register(Image)
class ImageAdmin(ModelAdmin):
    list_display = ('image_id', 'image_file', 'camera', 'is_processed', 'expires_at')
    search_fields = ('image_id', 'image_name')
    list_filter = ('is_processed', 'created_at', 'expires_at', 'camera')

@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ('video_id', 'video_file', 'start_time', 'end_time', 'expires_at', 'show_video_size')
    search_fields = ('video_id', 'video_name')
    list_filter = ('created_at', 'expires_at')

    def show_video_size(self, obj):
        return f"{obj.video_size / (1024 * 1024):.2f}" if obj.video_size else obj.video_size
    show_video_size.short_description = "Video Size (MB)"