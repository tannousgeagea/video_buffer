import json
import os
import re
import socket

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from configure.models import AppConfig, DataAcquisitionConfig, DataSource
from tenants.models import Camera, EntityType, PlantEntity, SensorBox, Tenant

# <eb|sb><N>.<sensor letter><N>[-<N>].<location>.<domain prefix>.want
# e.g. eb1.g3.herten.agr.want, eb1.g1-2.herten.agr.want, sb1.c1-2.lisbon.valorsul.want
HOSTNAME_PATTERN = re.compile(
    r"^(?P<box_prefix>eb|sb)(?P<box_num>\d+)\.(?P<sensor_spec>[a-zA-Z]+\d+(?:-\d+)?)\."
    r"(?P<location>[a-zA-Z0-9]+)\.(?P<domain_prefix>[a-zA-Z0-9]+)\.want$",
    re.IGNORECASE,
)
SENSOR_SPEC_PATTERN = re.compile(r"^(?P<letter>[a-zA-Z]+)(?P<start>\d+)(?:-(?P<end>\d+))?$")
EDGE_TO_SENSOR_BOX_PREFIX = re.compile(r"^eb(?=\d)", re.IGNORECASE)

# Extend as new sensor types are deployed. Kept in sync with media_manager's setup_edge_box.
SENSOR_TYPE_NAMES = {
    "g": "gate",
    "c": "crane",
    "h": "trichter",
}


class Command(BaseCommand):
    help = (
        "Derive Tenant/PlantEntity/SensorBox/Camera rows from environment for the "
        "video archive edge box, e.g. 'eb1.g3.herten.agr.want' -> tenant 'agr' at Herten, "
        "sensor box gate03. Hostname is read from Systemname or EDGE_BOX_HOSTNAME, falling "
        "back to the OS hostname. The sensor box hostname is read from SENSOR_BOX_HOSTNAME, "
        "or derived by replacing the 'eb' prefix with 'sb'. Cameras and data acquisition "
        "sources come from the CAMERA_CONFIG and DATA_ACQUISITION_CONFIG JSON env vars. "
        "Idempotent (safe to run on every container start); marks the app configured only "
        "once a sensor box, at least one camera, and at least one active data acquisition "
        "config exist."
    )

    def handle(self, *args, **kwargs):
        edge_box_hostname = os.getenv("Systemname") or os.getenv("EDGE_BOX_HOSTNAME") or socket.gethostname()
        sensor_box_hostname = os.getenv("SENSOR_BOX_HOSTNAME") or EDGE_TO_SENSOR_BOX_PREFIX.sub(
            "sb", edge_box_hostname, count=1
        )

        match = HOSTNAME_PATTERN.match(sensor_box_hostname)
        if not match:
            self.stdout.write(self.style.WARNING(
                f"Sensor box hostname '{sensor_box_hostname}' (derived from edge box hostname "
                f"'{edge_box_hostname}') doesn't match the naming convention "
                f"(<eb|sb><N>.<sensor><N>[-<N>].<location>.<domain>.want) — skipping."
            ))
            return

        with transaction.atomic():
            sensor_boxes = self._setup_plant_and_sensor_boxes(match, sensor_box_hostname)
            cameras = self._setup_cameras(sensor_boxes)
            has_active_source = self._setup_data_acquisition(cameras)

            if sensor_boxes and cameras and has_active_source:
                AppConfig.objects.update_or_create(pk=1, defaults={"is_configured": True})
                self.stdout.write(self.style.SUCCESS("✅ App configuration complete — marked as configured."))
            else:
                self.stdout.write(self.style.WARNING(
                    "⚠️ Plant/sensor box setup done, but camera and/or data acquisition config "
                    "is missing — app not marked as configured yet."
                ))

    def _setup_plant_and_sensor_boxes(self, match, sensor_box_hostname):
        box_prefix = match.group("box_prefix").lower()
        box_num = match.group("box_num")
        sensor_spec = match.group("sensor_spec")
        location = match.group("location").lower()
        domain_prefix = match.group("domain_prefix").lower()

        sensor_match = SENSOR_SPEC_PATTERN.match(sensor_spec)
        if not sensor_match:
            raise CommandError(f"Could not parse sensor spec '{sensor_spec}' from hostname '{sensor_box_hostname}'")

        letter = sensor_match.group("letter").lower()
        start = int(sensor_match.group("start"))
        end = int(sensor_match.group("end")) if sensor_match.group("end") else start

        sensor_name = SENSOR_TYPE_NAMES.get(letter)
        if sensor_name is None:
            raise CommandError(
                f"Unknown sensor type '{letter}' in hostname '{sensor_box_hostname}'. "
                f"Known types: {', '.join(SENSOR_TYPE_NAMES)}"
            )

        tenant, created = Tenant.objects.update_or_create(
            tenant_id=domain_prefix,
            defaults={
                "tenant_name": domain_prefix.upper(),
                "location": location.title(),
                "domain": f"{domain_prefix}.wasteant.com",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} tenant '{tenant.tenant_id}'"))

        entity_type, _ = EntityType.objects.get_or_create(tenant=tenant, entity_type="plant")
        plant_entity, created = PlantEntity.objects.get_or_create(
            entity_type=entity_type,
            entity_uid=f"{domain_prefix}.{location}",
            defaults={"description": f"{location.title()} plant"},
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Found'} plant entity '{plant_entity.entity_uid}'"
        ))

        sensor_boxes = []
        for n in range(start, end + 1):
            sensor_box_name = f"{box_prefix}{box_num}.{letter}{n}.{location}.{domain_prefix}.want"
            location_label = f"{sensor_name}{n:02d}"

            sensor_box, created = SensorBox.objects.update_or_create(
                plant_entity=plant_entity,
                sensor_box_name=sensor_box_name,
                defaults={"sensor_box_location": location_label},
            )
            sensor_boxes.append(sensor_box)
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Found'} sensor box '{sensor_box_name}' ({location_label})"
            ))

        return sensor_boxes

    def _setup_cameras(self, sensor_boxes):
        """Creates Camera rows on every resolved sensor box from the CAMERA_CONFIG env var.

        CAMERA_CONFIG is a JSON object or list of objects, e.g.:
        '[{"camera_id": "cam01", "camera_position": "front"}, {"camera_id": "cam02", "camera_position": "top"}]'
        """
        raw = os.getenv("CAMERA_CONFIG")
        if not raw:
            self.stdout.write(self.style.WARNING("CAMERA_CONFIG not set — skipping camera setup."))
            return []

        try:
            camera_specs = json.loads(raw)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Could not parse CAMERA_CONFIG: {e}"))
            return []

        if isinstance(camera_specs, dict):
            camera_specs = [camera_specs]

        cameras = []
        for spec in camera_specs:
            camera_id = spec.get("camera_id")
            if not camera_id:
                self.stdout.write(self.style.ERROR(f"❌ CAMERA_CONFIG entry missing 'camera_id': {spec}"))
                continue

            for sensor_box in sensor_boxes:
                camera, created = Camera.objects.update_or_create(
                    sensor_box=sensor_box,
                    camera_id=camera_id,
                    defaults={
                        "camera_position": spec.get("camera_position", ""),
                        "is_active": spec.get("is_active", True),
                    },
                )
                cameras.append(camera)
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if created else 'Found'} camera '{camera_id}' on '{sensor_box.sensor_box_name}'"
                ))

        return cameras

    def _setup_data_acquisition(self, cameras):
        """Creates DataSource/DataAcquisitionConfig rows from the DATA_ACQUISITION_CONFIG env var.

        DATA_ACQUISITION_CONFIG is a JSON object or list of objects, e.g.:
        '[{"camera_id": "cam01", "interface": "ros2", "source_name": "/camera/cam01/image_raw",
           "message_type": "sensor_msgs/msg/Image"}]'

        `camera_id` is optional; when it uniquely matches one of the cameras just resolved,
        the config is linked to that camera.
        """
        raw = os.getenv("DATA_ACQUISITION_CONFIG")
        if not raw:
            self.stdout.write(self.style.WARNING("DATA_ACQUISITION_CONFIG not set — skipping data acquisition setup."))
            return False

        try:
            daq_specs = json.loads(raw)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Could not parse DATA_ACQUISITION_CONFIG: {e}"))
            return False

        if isinstance(daq_specs, dict):
            daq_specs = [daq_specs]

        cameras_by_id = {}
        for camera in cameras:
            cameras_by_id.setdefault(camera.camera_id, []).append(camera)

        has_active_source = False
        for spec in daq_specs:
            interface = spec.get("interface")
            source_name = spec.get("source_name")
            if not interface or not source_name:
                self.stdout.write(self.style.ERROR(
                    f"❌ DATA_ACQUISITION_CONFIG entry missing 'interface' or 'source_name': {spec}"
                ))
                continue

            # detect_ros2_topics may already own this row's is_available/message_type — don't
            # clobber live detection state, only fill in a source that isn't tracked yet.
            source, created = DataSource.objects.get_or_create(
                name=source_name,
                interface=interface,
                defaults={
                    "is_available": spec.get("is_available", True),
                    "message_type": spec.get("message_type"),
                },
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Found'} data source '{source_name}' ({interface})"
            ))

            camera = None
            camera_id = spec.get("camera_id")
            if camera_id:
                matches = cameras_by_id.get(camera_id, [])
                if len(matches) == 1:
                    camera = matches[0]
                elif len(matches) > 1:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ camera_id '{camera_id}' matches {len(matches)} cameras — "
                        f"leaving data acquisition config unlinked to a specific camera."
                    ))

            is_active = spec.get("is_active", True)
            config, created = DataAcquisitionConfig.objects.update_or_create(
                camera=camera,
                selected_source=source,
                defaults={"is_active": is_active},
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Found'} data acquisition config for '{source_name}'"
            ))
            has_active_source = has_active_source or is_active

        return has_active_source
