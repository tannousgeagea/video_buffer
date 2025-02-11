from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from tenants.models import Tenant, EntityType, PlantEntity
from metadata.models import PlantEntityLocalization
from .models import (
    SensorBox,
    TenantStorageSettings,
)


class PlantEntityLocalizationInline(TabularInline):  # or StackedInline
    model = PlantEntityLocalization
    extra = 1
    # fields = ('language', 'title', 'description', 'created_at')
    # readonly_fields = ('created_at',)

class EntityTypeInline(TabularInline):
    model = EntityType
    extra = 1

class PlantEntityInline(TabularInline):
    model = PlantEntity
    extra = 1

class SensorBoxInline(TabularInline):
    model = SensorBox
    extra = 1

class TenantStorageSettingsInline(TabularInline):
    model = TenantStorageSettings
    extra = 1
    
    
# Register your models here.
@admin.register(Tenant)
class TenantAdmin(ModelAdmin):
    list_display = ('tenant_id', 'tenant_name', 'location', 'domain', 'is_active', 'created_at')
    search_fields = ('tenant_name', 'location', 'domain')
    list_filter = ('is_active',)
    
    inlines = [EntityTypeInline, TenantStorageSettingsInline]
    
@admin.register(EntityType)
class EntityTypeAdmin(ModelAdmin):
    """
    Admin interface for the EntityType model.
    """
    list_display = ('tenant', 'entity_type', 'created_at')  # Display plant, entity type, and creation date
    search_fields = ('entity_type', 'tenant__tenant_name')  # Search by entity type and plant name
    list_filter = ('tenant', 'created_at')  # Add filters for plant and creation date
    ordering = ('-created_at',)  # Order by creation date, newest first
    readonly_fields = ('created_at',)  # Make created_at field read-only
    
    inlines = [PlantEntityInline]

@admin.register(PlantEntity)
class PlantEntityAdmin(ModelAdmin):
    """
    Admin interface for the PlantEntity model.
    """
    list_display = ('entity_type', 'entity_uid', 'description', 'created_At')  # Display fields in the list view
    search_fields = ('entity_uid', 'description', 'entity_type__entity_type')  # Search by UID, description, and entity type
    list_filter = ('entity_type', 'created_At')  # Add filters for entity type and creation date
    ordering = ('-created_At',)  # Order by creation date, newest first
    readonly_fields = ('created_At',)  # Make created_At field read-only    
    inlines = [PlantEntityLocalizationInline, SensorBoxInline]
    
@admin.register(SensorBox)
class SensorBoxAdmin(ModelAdmin):
    """
    Admin interface for the PlantEntity model.
    """
    list_display = ("plant_entity", "sensor_box_name", 'sensor_box_location', 'created_at')
    list_filter = ('plant_entity', 'created_at',)
    search_fields = ('sensor_box_location', )
    
@admin.register(TenantStorageSettings)
class TenantStorageSettingsAdmin(ModelAdmin):
    """
    Admin interface for the TenantStorageSetting model.
    """
    list_display = ("tenant", "provider_name", "account_name")
    list_filter = ("tenant", "created_at")
    search_filelds = ("tenant__tenant_name")
    