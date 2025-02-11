import subprocess
from django.core.management.base import BaseCommand
from configure.models import DataSource

class Command(BaseCommand):
    help = "Detect available ROS2 topics and log them into the database"

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Detecting available ROS2 topics...")

        try:
            # Run the ROS2 CLI command to list topics
            result = subprocess.run(["ros2", "topic", "list"], capture_output=True, text=True)
            topics = result.stdout.strip().split("\n") if result.stdout else []

            if not topics or topics == ['']:
                self.stdout.write(self.style.WARNING("⚠️ No active ROS2 topics detected."))
                topics = []

            detected_topics = []
            for topic in topics:
                obj, created = DataSource.objects.update_or_create(
                    name=topic,
                    interface="ros2",
                    defaults={"is_available": True}
                )
                detected_topics.append(topic)

                if created:
                    self.stdout.write(self.style.SUCCESS(f"✅ New topic added: {topic}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"🔄 Topic updated: {topic}"))

            # Mark any topics that are no longer detected as unavailable
            DataSource.objects.filter(interface="ros2").exclude(name__in=detected_topics).update(is_available=False)

            self.stdout.write(self.style.SUCCESS("🎯 ROS2 topic detection completed successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error detecting ROS2 topics: {e}"))
