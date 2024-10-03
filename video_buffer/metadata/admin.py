from django.contrib import admin
from .models import Metadata, MetadataColumn, MetadataLocalization, Filter, FilterItem, FilterLocalization, FilterItemLocalization, Language

# Register your models here.
@admin.register(Metadata)
class MetadataAdmin(admin.ModelAdmin):
    list_display = ('primary_key', 'description')
    search_fields = ('primary_key', 'description')
    
    class MetadataColumnInline(admin.TabularInline):
        model = MetadataColumn
        extra = 1
        show_change_link = True
        
    inlines = [MetadataColumnInline]
    
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(MetadataColumn)
class MetadataColumnAdmin(admin.ModelAdmin):
    list_display = ('metadata', 'column_name', 'type', 'is_required', 'is_active')
    list_filter = ('is_required', 'is_active', 'metadata')
    search_fields = ('column_name', 'metadata__primary_key')
    
    class MetadataLocalizationInline(admin.TabularInline):
        model = MetadataLocalization
        extra = 1
        
    inlines = [MetadataLocalizationInline]

@admin.register(MetadataLocalization)
class MetadataLocalizationAdmin(admin.ModelAdmin):
    list_display = ('metadata_column', 'language', 'title')
    list_filter = ('language', 'metadata_column')
    search_fields = ('title', 'metadata_column__column_name')

@admin.register(Filter)
class FilterAdmin(admin.ModelAdmin):
    list_display = ('filter_name', 'type', 'is_active')
    search_fields = ('filter_name', )
    list_filter = ('is_active', 'type')
    
    class FilterItemInline(admin.TabularInline):
        model = FilterItem
        extra = 1
    
    inlines = [FilterItemInline]

@admin.register(FilterItem)
class FilterItemAdmin(admin.ModelAdmin):
    list_display = ('filter', 'item_key', 'is_active')
    search_fields = ('item_key', )
    list_filter = ('is_active', 'filter')
    
    class FilterItemLocalizationInline(admin.TabularInline):
        model = FilterItemLocalization
        extra = 1
    
    inlines = [FilterItemLocalizationInline]

@admin.register(FilterLocalization)
class FilterLocalizationAdmin(admin.ModelAdmin):
    list_display = ('filter', 'language', 'title')
    list_filter = ('language', 'filter')
    search_fields = ('title', 'filter__filter_name')

@admin.register(FilterItemLocalization)
class FilterItemLocalizationAdmin(admin.ModelAdmin):
    list_display = ('filter_item', 'language', 'item_value')
    list_filter = ('language', 'filter_item')
    search_fields = ('item_value', 'filter_item__item_key')