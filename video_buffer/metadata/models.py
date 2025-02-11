import string
from django.db import models
from tenants.models import Tenant, EntityType, PlantEntity
from django.core.exceptions import ValidationError
    
class Language(models.Model):
    """
    Model to define and manage supported languages.
    """
    code = models.CharField(max_length=10, unique=True)  # ISO 639-1 language codes, e.g., 'en', 'fr'
    name = models.CharField(max_length=50)  # e.g., 'English', 'French'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'language'
        verbose_name_plural = 'Languages'

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class PlantEntityLocalization(models.Model):
    plant_entity = models.ForeignKey(
        PlantEntity,
        on_delete=models.RESTRICT,
        related_name='plant_entity_localization'
    )
    
    language = models.ForeignKey(Language, on_delete=models.RESTRICT)
    title = models.CharField(max_length=255, help_text="Localized title of the plant entity.")
    description = models.TextField(blank=True, null=True, help_text="Localized description of the plant entity.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'plant_entity_localization'
        verbose_name_plural = 'Plant Entity Localizations'
        unique_together = ('plant_entity', 'language')
        indexes = [
            models.Index(fields=['plant_entity', 'language']),
        ]

    def __str__(self):
        return f"Localization for '{self.plant_entity.entity_uid}' in {self.language}"