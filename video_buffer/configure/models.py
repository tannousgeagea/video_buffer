from django.db import models
from tenants.models import Camera

# Create your models here.
class AppConfig(models.Model):
    """Stores global application configuration status."""
    is_configured = models.BooleanField(default=False)  # False until configured
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @classmethod
    def is_app_ready(cls):
        """Returns True if the app is fully configured."""
        return cls.objects.filter(is_configured=True).exists()

class DataSource(models.Model):
    """Represents a generic data source (ROS2 topic, MQTT topic, API endpoint, etc.)"""
    
    INTERFACE_CHOICES = [
        ('ros2', 'ROS2 Topic'),
        ('mqtt', 'MQTT Topic'),
        ('api', 'REST API Endpoint'),
        ('websocket', 'WebSocket Feed'),
        ('file', 'File Source'),
    ]

    name = models.CharField(max_length=255, unique=True) 
    interface = models.CharField(max_length=50, choices=INTERFACE_CHOICES) 
    is_available = models.BooleanField(default=False)
    last_detected = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_interface_display()})"

    @classmethod
    def get_available_sources(cls, interface):
        """Return available data sources for a given interface type"""
        return cls.objects.filter(interface=interface, is_available=True)

class DataAcquisitionConfig(models.Model):
    """Stores the selected data source for the data acquisition app"""
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True)
    selected_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Using: {self.selected_source.name if self.selected_source else 'None'}"
    
    @classmethod
    def get_selected_source(cls):
        """Returns the currently selected data source"""
        config = cls.objects.first()
        return config.selected_source if config else None