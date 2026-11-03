import os

from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the initial staff superuser from temporary environment variables.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not any((username, email, password)):
            self.stdout.write('Initial admin bootstrap is not configured; skipping.')
            return
        if not all((username, email, password)):
            raise CommandError(
                'Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL and '
                'DJANGO_SUPERUSER_PASSWORD together.'
            )

        user_model = get_user_model()
        if user_model.objects.filter(**{user_model.USERNAME_FIELD: username}).exists():
            self.stdout.write('Initial admin already exists; no changes made.')
            return

        user = user_model(**{
            user_model.USERNAME_FIELD: username,
            'email': email,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        })
        password_validation.validate_password(password, user)
        user.set_password(password)
        user.save()
        self.stdout.write('Initial staff admin created successfully.')
