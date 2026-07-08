"""Add ``date_created`` to ``label_data.line_width_samples``.

The table is unmanaged (``managed = False``) so this migration uses
:class:`~django.db.migrations.RunSQL` to apply the schema change
without Django attempting to create the table from scratch.

The column is added with ``DEFAULT NOW()`` so existing rows are
back-filled and new inserts have a safety net even if Django's
``auto_now_add`` were ever bypassed.
"""

from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "label_data.line_width_samples" '
                "ADD COLUMN IF NOT EXISTS date_created DATE NOT NULL DEFAULT NOW();"
            ),
            reverse_sql=(
                'ALTER TABLE "label_data.line_width_samples" '
                "DROP COLUMN IF EXISTS date_created;"
            ),
        ),
    ]
