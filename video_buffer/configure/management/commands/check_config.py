from django.core.management.base import BaseCommand
from configure.models import AppConfig

class Command(BaseCommand):
    help = "Checks if the app is configured before allowing startup"

    def handle(self, *args, **kwargs):
        if AppConfig.objects.filter(is_configured=True).exists():
            self.stdout.write(self.style.SUCCESS("✅ App is configured. Starting services..."))
            exit(0)  # Exit normally, allowing Supervisor to continue
        else:
            self.stdout.write(self.style.WARNING("❌ App is NOT configured. Waiting..."))
            exit(1)  # Exit with error, making Supervisor retry
