from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a new friend account with the given username and password."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("password", type=str)

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        User.objects.create_user(username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created user '{username}'."))
