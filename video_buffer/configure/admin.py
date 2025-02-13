from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import ( 
    AppConfig,
    DataSource,
    DataAcquisitionConfig,
)

# Register your models here.
@admin.register(AppConfig)
class AppConfigAdmin(ModelAdmin):
    list_display = ("is_configured", "created_at")
    
@admin.register(DataSource)
class DataSourceAdmin(ModelAdmin):
    list_display = ("name", "interface", "is_available", "last_detected")
    
@admin.register(DataAcquisitionConfig)
class DataAcquisitionConfigAdmin(ModelAdmin):
    list_display = ("camera", "selected_source", )