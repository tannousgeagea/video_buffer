import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Create a superuser automatically'

    def handle(self, *args, **kwargs):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
        
        if username and email and password:
            # Check if the user already exists
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {username}'))
            else:
                self.stdout.write(self.style.WARNING(f'User {username} already exists.'))
        else:
            # Fall back to Django's default createsuperuser behavior
            call_command('createsuperuser', interactive=True)