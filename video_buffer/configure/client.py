import django
django.setup()
from django.core.cache import cache
from configure.models import DataSource, DataAcquisitionConfig
    
class ConfigManager:
    """
    Manages configuration settings, including:
    1. Global settings from ConfigSetting
    2. Available data sources (ROS2, MQTT, API)
    3. Active data acquisition source
    4. Caching for performance
    """

    CACHE_TIMEOUT = 300

    @classmethod
    def get_available_sources(cls, interface):
        """
        Fetch available data sources for a given interface type (ROS2, MQTT, API).
        Cached for faster access.
        """
        cache_key = f"available_sources:{interface}"
        sources = cache.get(cache_key)

        if sources is None:
            sources = list(DataSource.get_available_sources(interface).values("name", "message_type"))
            cache.set(cache_key, sources, cls.CACHE_TIMEOUT)

        return sources

    ## 🌟 Fetching a Data Source's Message Type ##
    @classmethod
    def get_message_type(cls, source_name):
        """Returns the message type of a given data source."""
        cache_key = f"message_type:{source_name}"
        msg_type = cache.get(cache_key)

        if msg_type is None:
            try:
                msg_type = DataSource.objects.get(name=source_name).message_type
                cache.set(cache_key, msg_type, cls.CACHE_TIMEOUT)
            except DataSource.DoesNotExist:
                msg_type = "Unknown"

        return msg_type

    ## 🌟 Fetching Camera for a Given Data Source ##
    @classmethod
    def get_camera_for_source(cls, source_name):
        """Returns the camera associated with a given data source (if any)."""
        cache_key = f"camera_for_source:{source_name}"
        camera_info = cache.get(cache_key)

        if camera_info is None:
            try:
                config = DataAcquisitionConfig.objects.filter(selected_source__name=source_name, is_active=True).first()
                camera_info = {
                    "id": config.camera.id,
                    "name": config.camera.sensor_box.sensor_box_name,
                    "location": config.camera.sensor_box.sensor_box_location,
                }
                cache.set(cache_key, camera_info, cls.CACHE_TIMEOUT)
            except DataAcquisitionConfig.DoesNotExist:
                camera_info = None

        return camera_info

    ## 🌟 Fetching Active Data Acquisition Source ##
    @classmethod
    def get_active_data_sources(cls):
        """
        Returns all currently active data sources for data acquisition.
        Cached for fast access.
        """
        cache_key = "active_data_sources"
        active_sources = cache.get(cache_key)

        if active_sources is None:
            configs = DataAcquisitionConfig.objects.filter(is_active=True).select_related("selected_source", "camera__sensor_box")

            active_sources = [
                {
                    "source_name": config.selected_source.name if config.selected_source else None,
                    "message_type": config.selected_source.message_type if config.selected_source else None,
                    "camera": {
                        "id": config.camera.id,
                        "name": config.camera.sensor_box.sensor_box_name,
                        "location": config.camera.sensor_box.sensor_box_location,
                    } if config.camera else None
                }
                for config in configs
            ]

            cache.set(cache_key, active_sources, cls.CACHE_TIMEOUT)

        return active_sources