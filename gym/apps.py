from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _enable_sqlite_wal(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")


class GymConfig(AppConfig):
    name = "gym"

    def ready(self):
        connection_created.connect(_enable_sqlite_wal)
