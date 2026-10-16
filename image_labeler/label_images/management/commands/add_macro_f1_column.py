"""Add ``val_f1`` (macro-averaged F1) to ``models.model_results``.

``models.model_results`` is an unmanaged table that lives in both the dev and prod
databases, so Django migrations do not cover it. This command adds the column to
every configured database and is safe to re-run.

An earlier version of this command added the column as ``val_macro_f1``; if that
name is still present it is renamed rather than left behind. The file keeps its
original name so the command path stays stable.

Usage::

    python manage.py add_macro_f1_column           # dev + prod
    python manage.py add_macro_f1_column --dry-run
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections

COLUMN = "val_f1"
OLD_COLUMN = "val_macro_f1"
TABLE = '"models"."model_results"'


class Command(BaseCommand):
    help = "Add the val_f1 column to models.model_results in every database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            help="Only touch this database alias (default: every configured alias).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without altering anything.",
        )

    def handle(self, *args, **options):
        only = options.get("database")
        dry_run = options.get("dry_run")

        aliases = [only] if only else sorted(settings.DATABASES)

        for alias in aliases:
            if alias not in settings.DATABASES:
                self.stderr.write(f"{alias}: not a configured database")
                continue

            connection = connections[alias]

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) FROM information_schema.tables
                    WHERE table_schema = 'models' AND table_name = 'model_results'
                    """
                )
                if not cursor.fetchone()[0]:
                    self.stdout.write(f"{alias}: no models.model_results table, skipped")
                    continue

                def has_column(name):
                    cursor.execute(
                        """
                        SELECT count(*) FROM information_schema.columns
                        WHERE table_schema = 'models' AND table_name = 'model_results'
                          AND column_name = %s
                        """,
                        [name],
                    )
                    return cursor.fetchone()[0] > 0

                if has_column(COLUMN):
                    self.stdout.write(f"{alias}: {COLUMN} already present")
                    continue

                if has_column(OLD_COLUMN):
                    if dry_run:
                        self.stdout.write(f"{alias}: would rename {OLD_COLUMN} to {COLUMN}")
                        continue
                    cursor.execute(
                        f"ALTER TABLE {TABLE} RENAME COLUMN {OLD_COLUMN} TO {COLUMN}"
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"{alias}: renamed {OLD_COLUMN} to {COLUMN}")
                    )
                    continue

                if dry_run:
                    self.stdout.write(f"{alias}: would add {COLUMN}")
                    continue

                cursor.execute(
                    f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} double precision"
                )
                self.stdout.write(self.style.SUCCESS(f"{alias}: added {COLUMN}"))
