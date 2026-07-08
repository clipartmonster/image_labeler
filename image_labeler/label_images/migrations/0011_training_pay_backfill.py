"""Backfill training-batch payment to match the standard rate.

Training batches were previously created with ``payment_amount=0`` as a
placeholder. They are now paid at the same rate as regular assignments.
This migration only touches training rows that still have the old default
of 0 so any manual adjustments are preserved.
"""

from decimal import Decimal

from django.conf import settings
from django.db import migrations


def _backfill_training_pay(apps, schema_editor):
    BatchAssignment = apps.get_model("label_images", "BatchAssignment")
    rate = Decimal(str(settings.LABELER_PAY_PER_BATCH))
    BatchAssignment.objects.filter(is_training=True, payment_amount=0).update(
        payment_amount=rate,
    )


def _noop_reverse(apps, schema_editor):
    # Don't reset payments to 0 on rollback; that would undo legitimate values.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("label_images", "0010_training_result"),
    ]

    operations = [
        migrations.RunPython(_backfill_training_pay, _noop_reverse),
    ]
