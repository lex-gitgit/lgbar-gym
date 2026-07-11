import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BACKUP_DIR = settings.BASE_DIR / "backups"
DEFAULT_KEEP = 14


class Command(BaseCommand):
    help = (
        "Snapshot the SQLite database into backups/, pruning old snapshots. "
        "Safe to run while the app is live: uses SQLite's online backup API, "
        "which produces a consistent copy even in WAL mode with concurrent writers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", type=int, default=DEFAULT_KEEP,
            help=f"Number of most recent backups to retain (default {DEFAULT_KEEP}).",
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES["default"]
        if "sqlite3" not in db_config["ENGINE"]:
            raise CommandError("backup_db only supports the sqlite3 backend.")

        db_path = str(db_config["NAME"])
        if not Path(db_path).exists():
            raise CommandError(f"Database file not found: {db_path}")

        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"db_{timestamp}.sqlite3"

        source = sqlite3.connect(db_path)
        try:
            target = sqlite3.connect(str(dest))
            try:
                with target:
                    source.backup(target)
            finally:
                target.close()
        finally:
            source.close()

        self.stdout.write(self.style.SUCCESS(f"Backed up to {dest}"))

        keep = options["keep"]
        backups = sorted(
            BACKUP_DIR.glob("db_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        for old in backups[keep:]:
            old.unlink()
            self.stdout.write(f"Pruned {old.name}")
