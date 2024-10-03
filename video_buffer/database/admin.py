from django.contrib import admin
from .models import Image, Video

admin.site.site_header = "Video Buffer Admin"
admin.site.site_title = "Video Buffer"
admin.site.index_title = "Welcome to the Video Buffer Dashboard"

# Register your models here.
@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'image_name', 'created_at', 'image_file', 'is_processed', 'expires_at')
    list_display_links = ('image_id', 'image_name')
    search_fields = ('image_id', 'image_name')
    list_filter = ('is_processed', 'created_at', 'expires_at')
    readonly_fields = ('created_at',)
    fields = ('image_id', 'image_name', 'image_file', 'is_processed', 'meta_info', 'timestamp', 'expires_at')
    ordering = ('-created_at',)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('video_id', 'video_name', 'video_file', 'created_at', 'start_time', 'end_time', 'expires_at', 'show_video_size')
    list_display_links = ('video_id', 'video_name')
    search_fields = ('video_id', 'video_name')
    list_filter = ('created_at', 'expires_at')
    readonly_fields = ('created_at',)
    fields = ('video_id', 'video_name', 'video_file', 'start_time', 'end_time', 'duration', 'meta_info', 'timestamp', 'expires_at')
    ordering = ('-created_at',)

    def show_video_size(self, obj):
        return f"{obj.video_size / (1024 * 1024):.2f}" if obj.video_size else obj.video_size
    show_video_size.short_description = "Video Size (MB)"