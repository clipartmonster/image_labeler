"""Add ``x_coord`` and ``y_coord`` to ``label_data.line_width_responses``.

The line-width measurement UI already sends the click coordinates for each
sample, but they were previously discarded on save. Persisting them lets us
review *where* a labeler measured each line (not just the widths).

The table is unmanaged (``managed = False``), so this uses ``RunSQL`` with
``ADD COLUMN IF NOT EXISTS``. Columns are nullable because rows created before
this change have no stored coordinates.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("labeling_api", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "label_data.line_width_responses" '
                "ADD COLUMN IF NOT EXISTS x_coord INTEGER; "
                'ALTER TABLE "label_data.line_width_responses" '
                "ADD COLUMN IF NOT EXISTS y_coord INTEGER;"
            ),
            reverse_sql=(
                'ALTER TABLE "label_data.line_width_responses" '
                "DROP COLUMN IF EXISTS x_coord; "
                'ALTER TABLE "label_data.line_width_responses" '
                "DROP COLUMN IF EXISTS y_coord;"
            ),
        ),
    ]
